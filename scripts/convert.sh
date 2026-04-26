#!/usr/bin/env bash
# convert.sh — generates integrations/<tool>/ from canonical source
#
# Usage:
#   ./scripts/convert.sh --tool <tool>
#   ./scripts/convert.sh --all
#
# Tools: claude-code, opencode, cursor, aider, windsurf

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
INTEGRATIONS="$ROOT/integrations"

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${BLUE}[convert]${NC} $*"; }
ok()  { echo -e "${GREEN}[✓]${NC} $*"; }
err() { echo -e "${RED}[✗]${NC} $*" >&2; }

usage() {
  echo "Usage: $0 --tool <tool> | --all"
  echo ""
  echo "  Tools: claude-code, opencode, cursor, aider, windsurf"
  exit 1
}

# Strip YAML frontmatter, return only the body
strip_frontmatter() {
  local file="$1"
  awk 'BEGIN{fm=0; body=0}
       /^---$/{fm++; if(fm==2){body=1}; next}
       body{print}' "$file"
}

# Read a frontmatter field value
frontmatter_field() {
  local file="$1"
  local key="$2"
  awk 'BEGIN{fm=0}
       /^---$/{fm++; next}
       fm==1 && /^'"$key"':/{sub(/^'"$key"': */,""); print; exit}' "$file"
}

# Convert an agent name field to kebab-case filename
# "Lore — Product Strategist" → "lore-product-strategist"
# "Cast — Ship & Support Lead" → "cast-ship-and-support-lead"
name_to_kebab() {
  echo "$1" \
    | tr '[:upper:]' '[:lower:]' \
    | sed 's/ — /-/g' \
    | sed 's/ & /-and-/g' \
    | sed 's/ /-/g' \
    | sed 's/[^a-z0-9-]//g' \
    | sed 's/-\{2,\}/-/g' \
    | sed 's/^-//;s/-$//'
}

# Rewrite governance paths — reads from [file] or stdin if omitted
rewrite_paths() {
  local docs_prefix="$1"   # e.g. ".sdd/docs" or "__OPENCODE_ROOT__/docs"
  local skills_prefix="$2" # e.g. ".sdd/skills" or "__OPENCODE_ROOT__/skills"
  local file="${3:-}"       # optional file path; reads stdin when absent

  sed \
    -e "s|docs/SDLC\.md|${docs_prefix}/SDLC.md|g" \
    -e "s|docs/TIERS\.md|${docs_prefix}/TIERS.md|g" \
    -e "s|docs/MODELS\.md|${docs_prefix}/MODELS.md|g" \
    -e "s|skills/\([a-zA-Z_-]*\)/SKILL\.md|${skills_prefix}/\1/SKILL.md|g" \
    -e "s|skills/\([a-zA-Z_-]*\)/references/|${skills_prefix}/\1/references/|g" \
    ${file:+"$file"}
}

# Extract blocks marked with <!-- inject:start --> / <!-- inject:end -->
extract_compact_blocks() {
  local file="$1"
  awk '/<!-- inject:start -->/{p=1; next} /<!-- inject:end -->/{p=0; next} p' "$file"
}

# Output reference content for a skill based on its inject_references frontmatter field.
# Emits nothing if inject_references is absent or "false".
# Only called for tools that cannot read files at runtime (cursor, aider, windsurf).
skill_reference_content() {
  local skill_dir="$1"
  local skill_file="$skill_dir/SKILL.md"
  local inject_mode; inject_mode="$(frontmatter_field "$skill_file" "inject_references")"

  [[ -z "$inject_mode" || "$inject_mode" == "false" ]] && return

  # Reference file names are not uniformly derived from skill name (e.g. spec-manager →
  # spec-references.md, architecture-manager → arch-references.md), so use a glob.
  local ref_file
  ref_file="$(ls "$skill_dir/references/"*-references.md 2>/dev/null | head -1)"
  [[ -z "$ref_file" ]] && return

  printf '\n---\n\n## Reference Knowledge\n\n'
  if [[ "$inject_mode" == "compact" ]]; then
    extract_compact_blocks "$ref_file"
  else
    cat "$ref_file"
  fi
}

# ─── Claude Code ─────────────────────────────────────────────────────────────

convert_claude_code() {
  local out="$INTEGRATIONS/claude-code"
  log "Generating claude-code..."
  rm -rf "$out"
  mkdir -p "$out/.claude/agents" "$out/.sdd/docs" "$out/.sdd/skills"

  for agent in "$ROOT/agents"/*.md; do
    local name; name="$(basename "$agent")"
    rewrite_paths ".sdd/docs" ".sdd/skills" "$agent" > "$out/.claude/agents/$name"
  done

  cp "$ROOT/docs/"*.md "$out/.sdd/docs/"
  cp -r "$ROOT/skills/"* "$out/.sdd/skills/"

  ok "claude-code → $out"
  echo "    .claude/agents/   ← copy to your project's .claude/agents/"
  echo "    .sdd/             ← copy to your project root"
}

# ─── OpenCode ────────────────────────────────────────────────────────────────

# Helper: return permission.task YAML block for Helm only.
# Receives: slug + all sub-orchestrator kebab names (dynamically computed from name fields).
# Other orchestrators have no task restriction — they freely call agency-agents and built-ins.
opencode_task_permission() {
  local slug="$1"; shift
  local allowed=("$@")
  case "$slug" in
    helm)
      printf "    '*': deny\n"
      for k in "${allowed[@]}"; do
        printf "    %s: allow\n" "$k"
      done
      ;;
  esac
}

# Helper: emit OpenCode frontmatter for an orchestrator agent.
# Replaces the canonical tools: block with permission: (edit/bash) and, for Helm only,
# permission.task restricting which orchestrators it can route to.
# Args: file slug [subagent_kebab...]
opencode_agent_frontmatter() {
  local file="$1"
  local slug="$2"
  shift 2
  local subagent_kebabs=("$@")
  local name; name="$(frontmatter_field "$file" "name")"
  local desc; desc="$(frontmatter_field "$file" "description")"
  local temp; temp="$(frontmatter_field "$file" "temperature")"
  local emoji; emoji="$(frontmatter_field "$file" "emoji")"
  local mode; mode="$(frontmatter_field "$file" "mode")"
  local task_perms; task_perms="$(opencode_task_permission "$slug" "${subagent_kebabs[@]}")"

  [[ "$mode" == "agent" ]] && mode="subagent"

  {
    echo "---"
    echo "name: $name"
    echo "description: $desc"
    echo "mode: $mode"
    echo "temperature: $temp"
    echo "emoji: $emoji"
    echo "permission:"
    echo "  edit: allow"
    echo "  bash: deny"
    if [[ -n "$task_perms" ]]; then
      echo "  task:"
      printf '%s\n' "$task_perms"
    fi
    echo "---"
    echo ""
    strip_frontmatter "$file" | rewrite_paths "__OPENCODE_ROOT__/docs" "__OPENCODE_ROOT__/skills"
  }
}

convert_opencode() {
  local out="$INTEGRATIONS/opencode"
  log "Generating opencode..."
  rm -rf "$out"
  mkdir -p "$out/agents" "$out/docs" "$out/skills"

  # Collect kebab names of all sub-orchestrators (non-helm), sorted for determinism.
  # Compatible with bash 3.2 (macOS system bash): no declare -A, no mapfile.
  local subagent_kebabs=()
  while IFS= read -r k; do
    subagent_kebabs+=("$k")
  done < <(
    for agent in "$ROOT/agents"/*.md; do
      local s; s="$(basename "$agent" .md)"
      [[ "$s" == "helm" ]] && continue
      local fn; fn="$(frontmatter_field "$agent" "name")"
      name_to_kebab "$fn"
    done | sort
  )

  # Generate agent files using kebab-case names derived from each agent's name field.
  # filename (without .md) = agent type in OpenCode Task tool
  for agent in "$ROOT/agents"/*.md; do
    local slug; slug="$(basename "$agent" .md)"
    local full_name; full_name="$(frontmatter_field "$agent" "name")"
    local kebab; kebab="$(name_to_kebab "$full_name")"
    opencode_agent_frontmatter "$agent" "$slug" "${subagent_kebabs[@]}" > "$out/agents/$kebab.md"
  done

  # Copy governance docs
  cp "$ROOT/docs/"*.md "$out/docs/"

  # Copy skills as reference documentation (for reading by orchestrators)
  cp -r "$ROOT/skills/"* "$out/skills/"

  ok "opencode → $out"
  echo "    Install global:   ./scripts/install.sh --tool opencode --target ~/.config/opencode"
  echo "    Install local:    ./scripts/install.sh --tool opencode --target /your/project/.opencode"
}

# ─── Cursor ──────────────────────────────────────────────────────────────────

convert_cursor() {
  local out="$INTEGRATIONS/cursor"
  log "Generating cursor..."
  rm -rf "$out"
  mkdir -p "$out/.cursor/rules"

  # Agents
  for agent in "$ROOT/agents"/*.md; do
    local slug; slug="$(basename "$agent" .md)"
    local name; name="$(frontmatter_field "$agent" "name")"
    local desc; desc="$(frontmatter_field "$agent" "description")"
    local body; body="$(strip_frontmatter "$agent" | rewrite_paths ".sdd/docs" ".sdd/skills")"

    {
      echo "---"
      echo "description: >-"
      echo "  ${desc}"
      echo "globs: []"
      echo "alwaysApply: false"
      echo "---"
      echo ""
      echo "# ${name}"
      echo ""
      echo "${body}"
    } > "$out/.cursor/rules/$slug.mdc"
  done

  # Skills (with reference injection — cursor cannot read files at runtime)
  for skill_dir in "$ROOT/skills"/*/; do
    local skill_name; skill_name="$(basename "$skill_dir")"
    local skill_file="$skill_dir/SKILL.md"
    [[ ! -f "$skill_file" ]] && continue

    local name; name="$(frontmatter_field "$skill_file" "name")"
    local desc; desc="$(frontmatter_field "$skill_file" "description")"
    local body; body="$(strip_frontmatter "$skill_file" | rewrite_paths ".sdd/docs" ".sdd/skills")"
    local ref_content; ref_content="$(skill_reference_content "$skill_dir")"

    {
      echo "---"
      echo "description: >-"
      echo "  ${desc}"
      echo "globs: []"
      echo "alwaysApply: false"
      echo "---"
      echo ""
      echo "# ${name}"
      echo ""
      echo "${body}"
      printf '%s' "${ref_content}"
    } > "$out/.cursor/rules/${skill_name}.mdc"
  done

  ok "cursor → $out"
  echo "    .cursor/rules/    ← copy to your project root"
}

# ─── Aider ───────────────────────────────────────────────────────────────────

convert_aider() {
  local out="$INTEGRATIONS/aider"
  log "Generating aider..."
  rm -rf "$out"
  mkdir -p "$out"

  local conv="$out/CONVENTIONS.md"
  {
    echo "# Orquestrum — Agent Conventions"
    echo ""
    echo "> Auto-generated by scripts/convert.sh — do not edit manually."
    echo ""
  } > "$conv"

  # Agents
  for agent in "$ROOT/agents"/*.md; do
    local name; name="$(frontmatter_field "$agent" "name")"
    {
      echo "---"
      echo ""
      echo "## Agent: ${name}"
      echo ""
      strip_frontmatter "$agent" | rewrite_paths ".sdd/docs" ".sdd/skills"
      echo ""
    } >> "$conv"
  done

  # Skills (with reference injection — aider cannot read files at runtime)
  {
    echo ""
    echo "---"
    echo ""
    echo "# Skills"
    echo ""
  } >> "$conv"

  for skill_dir in "$ROOT/skills"/*/; do
    local skill_file="$skill_dir/SKILL.md"
    [[ ! -f "$skill_file" ]] && continue

    local name; name="$(frontmatter_field "$skill_file" "name")"
    {
      echo "---"
      echo ""
      echo "## Skill: ${name}"
      echo ""
      strip_frontmatter "$skill_file" | rewrite_paths ".sdd/docs" ".sdd/skills"
      skill_reference_content "$skill_dir"
      echo ""
    } >> "$conv"
  done

  ok "aider → $out"
  echo "    CONVENTIONS.md    ← copy to your project root"
}

# ─── Windsurf ────────────────────────────────────────────────────────────────

convert_windsurf() {
  local out="$INTEGRATIONS/windsurf"
  log "Generating windsurf..."
  rm -rf "$out"
  mkdir -p "$out"

  local rules="$out/.windsurfrules"
  {
    echo "# Orquestrum — Agent Rules"
    echo ""
    echo "> Auto-generated by scripts/convert.sh — do not edit manually."
    echo ""
  } > "$rules"

  # Agents
  for agent in "$ROOT/agents"/*.md; do
    local name; name="$(frontmatter_field "$agent" "name")"
    {
      echo "---"
      echo ""
      echo "## ${name}"
      echo ""
      strip_frontmatter "$agent" | rewrite_paths ".sdd/docs" ".sdd/skills"
      echo ""
    } >> "$rules"
  done

  # Skills (with reference injection — windsurf cannot read files at runtime)
  {
    echo ""
    echo "---"
    echo ""
    echo "# Skills"
    echo ""
  } >> "$rules"

  for skill_dir in "$ROOT/skills"/*/; do
    local skill_file="$skill_dir/SKILL.md"
    [[ ! -f "$skill_file" ]] && continue

    local name; name="$(frontmatter_field "$skill_file" "name")"
    {
      echo "---"
      echo ""
      echo "## Skill: ${name}"
      echo ""
      strip_frontmatter "$skill_file" | rewrite_paths ".sdd/docs" ".sdd/skills"
      skill_reference_content "$skill_dir"
      echo ""
    } >> "$rules"
  done

  ok "windsurf → $out"
  echo "    .windsurfrules    ← copy to your project root"
}

# ─── Main ────────────────────────────────────────────────────────────────────

TOOL=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --tool) TOOL="$2"; shift 2 ;;
    --all)  TOOL="all"; shift ;;
    -h|--help) usage ;;
    *) err "Unknown argument: $1"; usage ;;
  esac
done

[[ -z "$TOOL" ]] && usage

echo ""
case "$TOOL" in
  claude-code) convert_claude_code ;;
  opencode)    convert_opencode ;;
  cursor)      convert_cursor ;;
  aider)       convert_aider ;;
  windsurf)    convert_windsurf ;;
  all)
    convert_claude_code
    convert_opencode
    convert_cursor
    convert_aider
    convert_windsurf
    echo ""
    ok "All integrations generated in integrations/"
    ;;
  *) err "Unknown tool: $TOOL"; usage ;;
esac
echo ""
