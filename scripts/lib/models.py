from typing import Literal, get_args

ModelTier = Literal['deep', 'sharp', 'balanced', 'mechanical']
Provider  = Literal['claude', 'copilot', 'glm']
Tool      = Literal['claude-code', 'opencode', 'cursor', 'aider', 'windsurf']

VALID_PROVIDERS: tuple[str, ...] = get_args(Provider)
VALID_TOOLS:     tuple[str, ...] = get_args(Tool)

PROVIDER_MODELS: dict[str, dict[str, str]] = {
    'claude': {
        'deep':       'anthropic/claude-opus-4-7',
        'sharp':      'anthropic/claude-sonnet-4-6',   # no intermediate claude model; maps to balanced
        'balanced':   'anthropic/claude-sonnet-4-6',
        'mechanical': 'anthropic/claude-haiku-4-5-20251001',
    },
    'copilot': {
        'deep':       'github-copilot/claude-opus-4.7',
        'sharp':      'github-copilot/claude-opus-4.6',  # public preview — between sonnet and opus-4.7
        'balanced':   'github-copilot/claude-sonnet-4.6',
        'mechanical': 'github-copilot/claude-haiku-4.5',
    },
    'glm': {
        'deep':       'zai-coding-plan/glm-5.1',
        'sharp':      'zai-coding-plan/glm-5-turbo',   # between glm-4.7 balanced and glm-5.1 deep
        'balanced':   'zai-coding-plan/glm-4.7',
        'mechanical': 'zai-coding-plan/glm-4.5-air',
    },
}

# Canonical model name → tier (used to substitute body text when provider changes)
CANONICAL_MODELS: dict[str, str] = {
    'claude-opus-4-7':           'deep',
    'claude-opus-4-6':           'deep',      # legacy alias — maps to same tier
    'claude-sonnet-4-6':         'balanced',
    'claude-haiku-4-5-20251001': 'mechanical',
}

# Pricing reference (USD per 1M tokens — source: Anthropic pricing, 2025)
# Used for cost estimation only; not read by adapters.
MODEL_PRICING: dict[str, dict[str, float]] = {
    'anthropic/claude-opus-4-7':        {'input': 15.0,  'output': 75.0},
    'anthropic/claude-opus-4-6':        {'input': 15.0,  'output': 75.0},
    'anthropic/claude-sonnet-4-6':      {'input':  3.0,  'output': 15.0},
    'anthropic/claude-haiku-4-5-20251001': {'input': 0.80, 'output':  4.0},
    'github-copilot/claude-opus-4.7':   {'input': 15.0,  'output': 75.0},
    'github-copilot/claude-opus-4.5':   {'input': 15.0,  'output': 75.0},   # legacy
    'github-copilot/claude-sonnet-4.6': {'input':  3.0,  'output': 15.0},
    'github-copilot/claude-sonnet-4.5': {'input':  3.0,  'output': 15.0},   # legacy
    'github-copilot/claude-haiku-4.5':  {'input':  0.80, 'output':  4.0},
    'zai-coding-plan/glm-5-turbo':      {'input':  1.50, 'output':  6.0},   # candidato 'sharp'
    'zai-coding-plan/glm-5.1':          {'input':  2.0,  'output':  8.0},
    'zai-coding-plan/glm-4.7':          {'input':  0.70, 'output':  2.8},
    'zai-coding-plan/glm-4.5-air':      {'input':  0.10, 'output':  0.4},
}

AGENT_TIERS: dict[str, str] = {
    'Helm - The Architect':      'deep',
    'Cast - Ship Lead':          'mechanical',
    'Lore - Product Strategist': 'balanced',
    'Forge - Dev Lead':          'balanced',
    'Cipher - Security Lead':    'sharp',    # threat modeling benefits from the sharp tier
    'Ward - Quality Lead':       'balanced',
    'Flux - Support Lead':       'balanced',
    'Trace - Onboarding Lead':   'balanced',
}

# Provider/tier combinations that silently fall back to another tier.
# Single source of truth — convert.py emits explicit warnings for every collapse.
# Keep this in sync with the "Provider Parity Caveats" section of docs/governance/MODELS.md.
TIER_COLLAPSES: dict[tuple[str, str], str] = {
    ('claude', 'sharp'): 'balanced',  # No intermediate Claude model between sonnet-4-6 and opus-4-7
}

HELM_NAME        = 'Helm - The Architect'
ORCHESTRATOR_NAMES = [
    'Lore - Product Strategist',
    'Forge - Dev Lead',
    'Cipher - Security Lead',
    'Ward - Quality Lead',
    'Cast - Ship Lead',
    'Flux - Support Lead',
    'Trace - Onboarding Lead',
]


def resolve_model(agent_name: str, provider: str, tier_override: str | None = None) -> str:
    tier = tier_override if tier_override else AGENT_TIERS.get(agent_name, 'balanced')
    return PROVIDER_MODELS[provider][tier]


def tier_collapse(provider: str, tier: str) -> str | None:
    """Return the tier this (provider, tier) combination collapses to, or None.

    Example: tier_collapse('claude', 'sharp') == 'balanced'.
    Used by convert.py to surface silent demotions in build output.
    """
    return TIER_COLLAPSES.get((provider, tier))


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate USD cost of a single LLM call. Returns 0.0 if model not in MODEL_PRICING.

    Wired into runtime metrics emission (Phase 3); pricing table previously dormant.
    """
    pricing = MODEL_PRICING.get(model)
    if not pricing:
        return 0.0
    return (input_tokens / 1_000_000) * pricing['input'] + (output_tokens / 1_000_000) * pricing['output']


def apply_provider_models(content: str, provider: str | None) -> str:
    """Replace canonical model names in body text with provider-specific names."""
    if not provider:
        return content
    models = PROVIDER_MODELS[provider]
    for canonical, tier in CANONICAL_MODELS.items():
        content = content.replace(canonical, models[tier])
    return content
