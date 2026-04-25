#!/usr/bin/env bash
# lint-agents.sh — validates agent and skill files
#
# Checks:
#   - YAML frontmatter present (opens and closes with ---)
#   - Required fields: name, description, model
#   - No tool-specific paths (.opencode/, .cursor/, etc.) in canonical source

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

errors=0
warnings=0

fail() { echo -e "  ${RED}✗${NC} $*"; ((errors+=1)); }
warn() { echo -e "  ${YELLOW}!${NC} $*"; ((warnings+=1)); }
pass() { echo -e "  ${GREEN}✓${NC} $*"; }

check_md_file() {
  local file="$1"
  local required_fields=("${@:2}")
  local label="${file#"$ROOT/"}"
  local ok=true

  # Must start with ---
  if ! head -1 "$file" | grep -q '^---$'; then
    fail "$label — missing YAML frontmatter (no opening ---)"
    return
  fi

  # Required fields in frontmatter
  for field in "${required_fields[@]}"; do
    if ! awk 'BEGIN{fm=0} /^---$/{fm++; next} fm==1 && /^'"$field"':/{found=1} END{exit !found}' "$file"; then
      fail "$label — missing required field: '$field'"
      ok=false
    fi
  done

  # No tool-specific path prefixes in body
  local tool_paths=(".opencode/" ".cursor/rules/" ".windsurfrules" ".sdd/")
  for pattern in "${tool_paths[@]}"; do
    if grep -q "$pattern" "$file" 2>/dev/null; then
      fail "$label — contains tool-specific path '${pattern}' (use plain paths: docs/, skills/)"
      ok=false
    fi
  done

  $ok && pass "$label"
}

check_assets() {
  local file="$1"
  local label="${file#"$ROOT/"}"

  if grep -q '\.opencode/' "$file" 2>/dev/null; then
    fail "$label — contains tool-specific path '.opencode/'"
  else
    pass "$label"
  fi
}

echo ""
echo -e "${BLUE}=== Agents ===${NC}"
for f in "$ROOT/agents"/*.md; do
  check_md_file "$f" name description model
done

echo ""
echo -e "${BLUE}=== Skills ===${NC}"
for f in "$ROOT/skills"/*/SKILL.md; do
  check_md_file "$f" name description model
done

echo ""
echo -e "${BLUE}=== Skill assets ===${NC}"
for f in "$ROOT/skills"/*/assets/*.md; do
  check_assets "$f"
done

echo ""
if [[ $errors -gt 0 ]]; then
  echo -e "${RED}✗ $errors error(s)${NC}$([ "$warnings" -gt 0 ] && echo ", $warnings warning(s)" || echo "")"
  exit 1
else
  echo -e "${GREEN}✓ All checks passed${NC}$([ "$warnings" -gt 0 ] && echo " ($warnings warning(s))" || echo "")"
  exit 0
fi
