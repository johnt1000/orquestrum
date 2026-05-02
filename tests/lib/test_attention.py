"""Tests for orquestrum.lib.attention."""
import pytest
from orquestrum.lib.attention import (
    AttentionInputs,
    compute,
    parse_confidence,
    parse_inference_depth,
    days_since,
    _band_for,
)


class TestBandFor:
    def test_100_is_green(self):
        assert _band_for(100) == 'green'

    def test_80_is_green(self):
        assert _band_for(80) == 'green'

    def test_79_is_yellow(self):
        assert _band_for(79) == 'yellow'

    def test_50_is_yellow(self):
        assert _band_for(50) == 'yellow'

    def test_49_is_red(self):
        assert _band_for(49) == 'red'

    def test_0_is_red(self):
        assert _band_for(0) == 'red'


class TestComputePerfect:
    def test_perfect_inputs_score_100(self):
        result = compute(AttentionInputs())
        assert result.score == 100
        assert result.band == 'green'
        assert result.factors == []

    def test_coverage_improvement_does_not_exceed_100(self):
        result = compute(AttentionInputs(test_coverage_delta=1.0))
        assert result.score == 100  # clamped


class TestComputeDeductions:
    def test_low_confidence_deducts(self):
        result = compute(AttentionInputs(confidence=0.0))
        assert result.score == 75  # 100 - 25*(1-0) = 75
        assert any('confidence' in f for f in result.factors)

    def test_medium_confidence_deducts_less(self):
        result = compute(AttentionInputs(confidence=0.6))
        expected = 100 - 25 * (1 - 0.6)
        assert result.score == round(expected)

    def test_drift_days_capped_at_20(self):
        # drift_days=60 → min(20, 30) = 20
        r_60 = compute(AttentionInputs(drift_days=60))
        r_100 = compute(AttentionInputs(drift_days=100))
        assert r_60.score == r_100.score  # both hit the cap

    def test_drift_days_below_cap(self):
        result = compute(AttentionInputs(drift_days=10))
        assert result.score == 95  # 100 - 10/2 = 95

    def test_inference_depth_deducts_10_per_level(self):
        for depth in range(1, 4):
            result = compute(AttentionInputs(inference_depth=depth))
            assert result.score == 100 - 10 * depth
            assert any('inference_depth' in f for f in result.factors)

    def test_gate_failures_deduct_5_each(self):
        result = compute(AttentionInputs(gate_failure_count=3))
        assert result.score == 85  # 100 - 15

    def test_low_context_completeness_deducts(self):
        result = compute(AttentionInputs(context_completeness=0.0))
        assert result.score == 85  # 100 - 15*(1-0) = 85

    def test_coverage_bonus_adds_5(self):
        # Start from 95 (one drift_day unit) + 5 bonus = 100
        result = compute(AttentionInputs(drift_days=10, test_coverage_delta=0.1))
        assert result.score == 100  # 95 + 5 = 100 (clamped at 100)


class TestUpstreamPropagation:
    def test_upstream_cap_applied(self):
        # score=100 but upstream=[30] → cap = 30+10 = 40
        result = compute(AttentionInputs(upstream_scores=[30]))
        assert result.score == 40
        assert result.capped_by_upstream is True
        assert any('capped_by_upstream' in f for f in result.factors)

    def test_upstream_cap_not_applied_when_score_lower(self):
        # score=75, upstream=[90] → cap=100, no cap applied
        result = compute(AttentionInputs(confidence=0.0, upstream_scores=[90]))
        assert result.score == 75
        assert result.capped_by_upstream is False

    def test_empty_upstream_no_cap(self):
        result = compute(AttentionInputs(upstream_scores=[]))
        assert result.score == 100
        assert not result.capped_by_upstream


class TestScoreClamping:
    def test_score_never_below_zero(self):
        result = compute(AttentionInputs(
            confidence=0.0,
            drift_days=200,
            inference_depth=3,
            context_completeness=0.0,
            gate_failure_count=10,
        ))
        assert result.score >= 0

    def test_score_never_above_100(self):
        result = compute(AttentionInputs(test_coverage_delta=1.0))
        assert result.score <= 100


class TestParseConfidence:
    def test_string_high(self):
        assert parse_confidence('high') == 1.0

    def test_string_medium(self):
        assert parse_confidence('medium') == 0.6

    def test_string_low(self):
        assert parse_confidence('low') == 0.3

    def test_string_unknown(self):
        assert parse_confidence('unknown') == 0.5

    def test_none_returns_0_5(self):
        assert parse_confidence(None) == 0.5

    def test_numeric_passthrough(self):
        assert parse_confidence(0.8) == pytest.approx(0.8)

    def test_numeric_clamped_above_1(self):
        assert parse_confidence(1.5) == 1.0

    def test_numeric_clamped_below_0(self):
        assert parse_confidence(-0.3) == 0.0


class TestParseInferenceDepth:
    def test_verbatim_is_0(self):
        assert parse_inference_depth('verbatim') == 0

    def test_speculative_is_3(self):
        assert parse_inference_depth('speculative') == 3

    def test_none_is_0(self):
        assert parse_inference_depth(None) == 0

    def test_int_clamped(self):
        assert parse_inference_depth(10) == 3
        assert parse_inference_depth(-1) == 0


class TestDaysSince:
    def test_none_returns_0(self):
        assert days_since(None) == 0

    def test_invalid_string_returns_0(self):
        assert days_since('not-a-date') == 0

    def test_today_returns_0(self):
        from datetime import date
        assert days_since(date.today().isoformat()) == 0

    def test_past_date_returns_positive(self):
        assert days_since('2000-01-01') > 0
