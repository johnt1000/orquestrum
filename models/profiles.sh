#!/usr/bin/env bash
# profiles.sh — model tier mappings per provider
#
# Each provider defines 3 tiers:
#   deep       — deep reasoning, ambiguity resolution, creative synthesis
#   balanced   — structured non-trivial tasks, design, validation, decomposition
#   mechanical — fast, template-driven, predictable output
#
# Canonical model names (used as sed search patterns in agent bodies):
#   claude-opus-4-6          → deep
#   claude-sonnet-4-6        → balanced
#   claude-haiku-4-5-20251001 → mechanical
#
# Usage:
#   source models/profiles.sh
#   resolve_model_tier claude deep       # → anthropic/claude-opus-4-6
#   resolve_model_tier glm balanced      # → zai-coding-plan/glm-4.7

CANONICAL_DEEP="claude-opus-4-6"
CANONICAL_BALANCED="claude-sonnet-4-6"
CANONICAL_MECHANICAL="claude-haiku-4-5-20251001"

resolve_model_tier() {
  local provider="$1"
  local tier="$2"

  case "${provider}__${tier}" in
    claude__deep)       echo "anthropic/claude-opus-4-6" ;;
    claude__balanced)   echo "anthropic/claude-sonnet-4-6" ;;
    claude__mechanical) echo "anthropic/claude-haiku-4-5-20251001" ;;
    copilot__deep)      echo "github-copilot/claude-opus-4.5" ;;
    copilot__balanced)  echo "github-copilot/claude-sonnet-4.5" ;;
    copilot__mechanical) echo "github-copilot/claude-haiku-4.5" ;;
    glm__deep)          echo "zai-coding-plan/glm-5.1" ;;
    glm__balanced)      echo "zai-coding-plan/glm-4.7" ;;
    glm__mechanical)    echo "zai-coding-plan/glm-4.5-air" ;;
    *)
      echo "Unknown provider/tier: ${provider}/${tier}" >&2
      return 1
      ;;
  esac
}

apply_provider_models() {
  local provider="$1"
  local deep balanced mechanical

  deep="$(resolve_model_tier "$provider" "deep")"
  balanced="$(resolve_model_tier "$provider" "balanced")"
  mechanical="$(resolve_model_tier "$provider" "mechanical")"

  sed \
    -e "s|${CANONICAL_DEEP}|${deep}|g" \
    -e "s|${CANONICAL_BALANCED}|${balanced}|g" \
    -e "s|${CANONICAL_MECHANICAL}|${mechanical}|g"
}
