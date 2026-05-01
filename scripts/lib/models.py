from typing import Literal, get_args

ModelTier = Literal['deep', 'balanced', 'mechanical']
Provider  = Literal['claude', 'copilot', 'glm']
Tool      = Literal['claude-code', 'opencode', 'cursor', 'aider', 'windsurf']

VALID_PROVIDERS: tuple[str, ...] = get_args(Provider)
VALID_TOOLS:     tuple[str, ...] = get_args(Tool)

PROVIDER_MODELS: dict[str, dict[str, str]] = {
    'claude': {
        'deep':       'anthropic/claude-opus-4-6',
        'balanced':   'anthropic/claude-sonnet-4-6',
        'mechanical': 'anthropic/claude-haiku-4-5-20251001',
    },
    'copilot': {
        'deep':       'github-copilot/claude-opus-4.5',
        'balanced':   'github-copilot/claude-sonnet-4.5',
        'mechanical': 'github-copilot/claude-haiku-4.5',
    },
    'glm': {
        'deep':       'zai-coding-plan/glm-5.1',
        'balanced':   'zai-coding-plan/glm-4.7',
        'mechanical': 'zai-coding-plan/glm-4.5-air',
    },
}

# Canonical model name → tier (used to substitute body text when provider changes)
CANONICAL_MODELS: dict[str, str] = {
    'claude-opus-4-6':           'deep',
    'claude-sonnet-4-6':         'balanced',
    'claude-haiku-4-5-20251001': 'mechanical',
}

AGENT_TIERS: dict[str, str] = {
    'Helm - The Architect':      'deep',
    'Cast - Ship Lead':          'mechanical',
    'Lore - Product Strategist': 'balanced',
    'Forge - Dev Lead':          'balanced',
    'Cipher - Security Lead':    'balanced',
    'Ward - Quality Lead':       'balanced',
    'Flux - Support Lead':       'balanced',
    'Trace - Onboarding Lead':   'balanced',
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


def resolve_model(agent_name: str, provider: str) -> str:
    tier = AGENT_TIERS.get(agent_name, 'balanced')
    return PROVIDER_MODELS[provider][tier]


def apply_provider_models(content: str, provider: str | None) -> str:
    """Replace canonical model names in body text with provider-specific names."""
    if not provider:
        return content
    models = PROVIDER_MODELS[provider]
    for canonical, tier in CANONICAL_MODELS.items():
        content = content.replace(canonical, models[tier])
    return content
