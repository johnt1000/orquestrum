"""Tests for orquestrum.lib.models."""
import pytest
from orquestrum.lib.models import (
    AGENT_TIERS,
    PROVIDER_MODELS,
    VALID_PROVIDERS,
    resolve_model,
    tier_collapse,
    estimate_cost,
    apply_provider_models,
)


class TestResolveModel:
    def test_helm_is_deep_for_claude(self):
        model = resolve_model('Helm - The Architect', 'claude')
        assert model == PROVIDER_MODELS['claude']['deep']

    def test_cast_is_mechanical_for_claude(self):
        model = resolve_model('Cast - Ship Lead', 'claude')
        assert model == PROVIDER_MODELS['claude']['mechanical']

    def test_balanced_agents_use_balanced_tier(self):
        for agent_name, tier in AGENT_TIERS.items():
            if tier == 'balanced':
                for provider in VALID_PROVIDERS:
                    model = resolve_model(agent_name, provider)
                    assert model == PROVIDER_MODELS[provider]['balanced']

    def test_tier_override_is_respected(self):
        model = resolve_model('Forge - Dev Lead', 'claude', tier_override='deep')
        assert model == PROVIDER_MODELS['claude']['deep']

    def test_unknown_agent_falls_back_to_balanced(self):
        model = resolve_model('Unknown Agent', 'claude')
        assert model == PROVIDER_MODELS['claude']['balanced']


class TestTierCollapse:
    def test_claude_sharp_collapses_to_balanced(self):
        assert tier_collapse('claude', 'sharp') == 'balanced'

    def test_claude_deep_does_not_collapse(self):
        assert tier_collapse('claude', 'deep') is None

    def test_copilot_sharp_does_not_collapse(self):
        assert tier_collapse('copilot', 'sharp') is None

    def test_glm_no_collapse(self):
        for tier in ('deep', 'sharp', 'balanced', 'mechanical'):
            assert tier_collapse('glm', tier) is None


class TestEstimateCost:
    def test_known_model_returns_nonzero(self):
        cost = estimate_cost('anthropic/claude-sonnet-4-6', input_tokens=1_000_000, output_tokens=0)
        assert cost == pytest.approx(3.0)

    def test_output_tokens_add_cost(self):
        cost = estimate_cost('anthropic/claude-sonnet-4-6', input_tokens=0, output_tokens=1_000_000)
        assert cost == pytest.approx(15.0)

    def test_unknown_model_returns_zero(self):
        cost = estimate_cost('unknown/model-xyz', input_tokens=999_999, output_tokens=999_999)
        assert cost == 0.0

    def test_zero_tokens_returns_zero(self):
        cost = estimate_cost('anthropic/claude-opus-4-7', input_tokens=0, output_tokens=0)
        assert cost == 0.0


class TestApplyProviderModels:
    def test_replaces_canonical_name_in_body(self):
        body = 'Use anthropic/claude-sonnet-4-6 for balanced tasks.'
        result = apply_provider_models(body, 'copilot')
        assert 'github-copilot/claude-sonnet-4.6' in result
        assert 'anthropic/claude-sonnet-4-6' not in result

    def test_no_provider_returns_content_unchanged(self):
        body = 'Use anthropic/claude-sonnet-4-6 for balanced tasks.'
        assert apply_provider_models(body, None) == body

    def test_multiple_replacements_in_one_body(self):
        body = 'deep=claude-opus-4-7, balanced=claude-sonnet-4-6'
        result = apply_provider_models(body, 'claude')
        assert 'anthropic/claude-opus-4-7' in result
        assert 'anthropic/claude-sonnet-4-6' in result
