#!/usr/bin/env bash
# install.sh — copies an integration package into a target project
#
# Usage:
#   ./scripts/install.sh --tool <tool> --target <path>
#   ./scripts/install.sh --auto --target <path>
#
# Run scripts/convert.sh first to generate integrations/.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
INTEGRATIONS="$ROOT/integrations"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log()  { echo -e "${BLUE}[install]${NC} $*"; }
ok()   { echo -e "${GREEN}[✓]${NC} $*"; }
warn() { echo -e "${YELLOW}[!]${NC} $*"; }
err()  { echo -e "${RED}[✗]${NC} $*" >&2; }

usage() {
  echo "Usage:"
  echo "  $0 --tool <tool> --target <project-path>"
  echo "  $0 --auto --target <project-path>"
  echo ""
  echo "  Tools: claude-code, opencode, cursor, aider, windsurf"
  echo ""
  echo "  Run ./scripts/convert.sh --all before installing."
  exit 1
}

detect_tools() {
  local target="$1"
  local found=()

  { [[ -d "$HOME/.claude" ]] || command -v claude &>/dev/null; } && found+=("claude-code") || true
  { [[ -d "$HOME/.config/opencode" ]] || [[ -d "$target/.opencode" ]] || command -v opencode &>/dev/null 2>&1; } && found+=("opencode") || true
  { [[ -d "$target/.cursor" ]] || command -v cursor &>/dev/null 2>&1; } && found+=("cursor") || true
  command -v aider &>/dev/null 2>&1 && found+=("aider") || true
  { [[ -f "$target/.windsurfrules" ]] || command -v windsurf &>/dev/null 2>&1; } && found+=("windsurf") || true

  echo "${found[*]:-}"
}

install_tool() {
  local tool="$1"
  local target="$2"
  local src="$INTEGRATIONS/$tool"

  if [[ ! -d "$src" ]]; then
    err "Integration package not found: $src"
    err "Run first: ./scripts/convert.sh --tool $tool"
    return 1
  fi

  local abs_target; abs_target="$(eval echo "$target")"
  log "Installing $tool → $abs_target"
  rm -rf "$abs_target"
  mkdir -p "$abs_target"
  cp -r "$src"/. "$abs_target/"

  case "$tool" in
    opencode)
      find "$abs_target" -name "*.md" -exec \
        sed -i '' "s|__OPENCODE_ROOT__|${abs_target}|g" {} \;
      ;;
  esac

  ok "$tool installed into $abs_target"
}

TOOL=""
TARGET=""
AUTO=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --tool)   TOOL="$2"; shift 2 ;;
    --target) TARGET="$2"; shift 2 ;;
    --auto)   AUTO=true; shift ;;
    -h|--help) usage ;;
    *) err "Unknown argument: $1"; usage ;;
  esac
done

[[ -z "$TARGET" ]] && { err "--target is required"; usage; }
[[ ! -d "$TARGET" ]] && { err "Target directory does not exist: $TARGET"; exit 1; }

echo ""

if $AUTO; then
  read -ra tools <<< "$(detect_tools "$TARGET")"
  if [[ ${#tools[@]} -eq 0 ]]; then
    warn "No supported tools detected in $TARGET"
    warn "Install one of: claude-code, opencode, cursor, aider, windsurf"
    exit 1
  fi
  log "Detected tools: ${tools[*]}"
  echo ""
  for t in "${tools[@]}"; do
    install_tool "$t" "$TARGET"
  done
elif [[ -n "$TOOL" ]]; then
  install_tool "$TOOL" "$TARGET"
else
  usage
fi

echo ""
