#!/usr/bin/env bash
# deps.sh — installs external agent/skill dependencies for Orquestrum
#
# Usage:
#   ./scripts/deps.sh --target ~/.config/opencode
#   ./scripts/deps.sh --target ~/.config/opencode --only agency
#   ./scripts/deps.sh --target ~/.config/opencode --only skills
#
# Supported dependencies:
#   - agency-agents (msitarzewski/agency-agents)
#   - anthropics/skills (includes supabase skills)
#   - supabase/agent-skills (skipped, included in anthropics/skills)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log()  { echo -e "${BLUE}[deps]${NC} $*" >&2; }
ok()   { echo -e "${GREEN}[✓]${NC} $*" >&2; }
warn() { echo -e "${YELLOW}[!]${NC} $*" >&2; }
err()  { echo -e "${RED}[✗]${NC} $*" >&2; }

usage() {
  echo "Usage:"
  echo "  $0 --target <path>              # Install all dependencies"
  echo "  $0 --target <path> --only <name> # Install specific dependency"
  echo ""
  echo "  Targets:"
  echo "    agency    - agency-agents (msitarzewski/agency-agents)"
  echo "    skills    - anthropics/skills (includes supabase)"
  echo "    all       - Both (default)"
  echo ""
  echo "  Example:"
  echo "    $0 --target ~/.config/opencode"
  echo "    $0 --target ~/.config/opencode --only agency"
  exit 1
}

clone_to_temp() {
  local repo="$1"
  local dir; dir=$(mktemp -d)

  log "Cloning $repo..."
  git clone --depth 1 --quiet "$repo" "$dir" 2>/dev/null || git clone --quiet "$repo" "$dir"

  echo "$dir"
}

install_agency() {
  local target="$1"

  log "Installing agency-agents (msitarzewski/agency-agents)..."
  local tmp; tmp=$(clone_to_temp "https://github.com/msitarzewski/agency-agents.git")

  # Run their convert.sh to generate OpenCode integration
  (cd "$tmp" && bash scripts/convert.sh 2>/dev/null || true)

  # Copy generated agents (if opencode integration was generated)
  if [[ -d "$tmp/integrations/opencode/agents" ]]; then
    mkdir -p "$target/agents"
    cp -rf "$tmp/integrations/opencode/agents/"*.md "$target/agents/"
    ok "agency-agents installed to $target/agents/"
  else
    warn "OpenCode integration not found in agency-agents, copying agent files directly..."
    # Fallback: copy all .md files from all divisions
    mkdir -p "$target/agents"
    for cat_dir in engineering design sales marketing product project-management testing support spatial-computing specialized academic finance game-development paid-media strategy; do
      [[ -d "$tmp/$cat_dir" ]] && cp -rf "$tmp/$cat_dir/"*.md "$target/agents/" || true
    done
    ok "agency-agents files copied to $target/agents/"
  fi

  rm -rf "$tmp"
}

install_skills() {
  local target="$1"

  log "Installing anthropics/skills (includes supabase)..."
  local tmp; tmp=$(clone_to_temp "https://github.com/anthropics/skills.git")

  mkdir -p "$target/skills"

  # Copy all skill directories
  local count=0
  for skill_dir in "$tmp/skills"/*/; do
    [[ ! -d "$skill_dir" ]] && continue

    local name; name=$(basename "$skill_dir")
    mkdir -p "$target/skills/$name"

    # Copy entire skill directory (SKILL.md, references/, assets/, etc.)
    cp -rf "$skill_dir"* "$target/skills/$name/"

    ((count++))
  done

  rm -rf "$tmp"
  ok "anthropics/skills installed: $count skills to $target/skills/"
}

install_supabase() {
  log "supabase/agent-skills is included in anthropics/skills, skipping separate install..."
}

TARGET=""
ONLY=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target) TARGET="$2"; shift 2 ;;
    --only)   ONLY="$2"; shift 2 ;;
    -h|--help) usage ;;
    *) err "Unknown argument: $1"; usage ;;
  esac
done

[[ -z "$TARGET" ]] && { err "--target is required"; usage; }
[[ ! -d "$TARGET" ]] && { err "Target directory does not exist: $TARGET"; exit 1; }

mkdir -p "$TARGET/agents"
mkdir -p "$TARGET/skills"

echo ""

case "$ONLY" in
  agency)
    install_agency "$TARGET"
    ;;
  skills)
    install_skills "$TARGET"
    ;;
  supabase)
    install_supabase
    ;;
  ""|all)
    install_agency "$TARGET"
    install_skills "$TARGET"
    ;;
  *)
    err "Unknown dependency: $ONLY (use: agency, skills, supabase)"
    usage
    ;;
esac

echo ""
log "Done! Review installed dependencies:"
echo "  Agents: $(ls -1 "$TARGET/agents" 2>/dev/null | wc -l | xargs)"
echo "  Skills: $(ls -1 "$TARGET/skills" 2>/dev/null | wc -l | xargs)"
