#!/usr/bin/env bash
# archive-cleanup.sh — physically deletes archived task/log/version files
#
# Reads ARCHIVE-*.md files to determine what to delete.
# Cast calls this after generating archive summaries (creative work = LLM,
# destructive work = this script).
#
# Usage:
#   scripts/archive-cleanup.sh --project /path/to/project [options]
#
# Options:
#   --project DIR     Target project root (required)
#   --archive FILE    Specific archive file(s), comma-separated (relative to project)
#                     If omitted, processes all ARCHIVE-v*.md in docs/02-planning/tasks/
#   --dry-run         Show what would be deleted without deleting
#   --skip-superseded Skip deletion of superseded SPEC/Architecture versions
#   -h, --help        Show this help

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log()  { echo -e "${BLUE}[archive-cleanup]${NC} $*"; }
ok()   { echo -e "${GREEN}[✓]${NC} $*"; }
warn() { echo -e "${YELLOW}[!]${NC} $*"; }
err()  { echo -e "${RED}[✗]${NC} $*" >&2; }

DRY_RUN=false
SKIP_SUPERSEDED=false
PROJECT=""
ARCHIVE_FILTER=""

usage() {
  sed -n '2,/^$/p' "$0" | sed 's/^# //' | sed 's/^#//'
  exit 0
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project)        PROJECT="$2"; shift 2 ;;
    --archive)        ARCHIVE_FILTER="$2"; shift 2 ;;
    --dry-run)        DRY_RUN=true; shift ;;
    --skip-superseded) SKIP_SUPERSEDED=true; shift ;;
    -h|--help)        usage ;;
    *) err "Unknown argument: $1"; exit 1 ;;
  esac
done

if [[ -z "$PROJECT" ]]; then
  err "--project is required"
  exit 1
fi

if [[ ! -d "$PROJECT" ]]; then
  err "Project directory does not exist: $PROJECT"
  exit 1
fi

TASKS_DIR="$PROJECT/docs/02-planning/tasks"
LOGS_DIR="$TASKS_DIR/logs"
SPEC_DIR="$PROJECT/docs/00-discovery/spec"
ARCH_DIR="$PROJECT/docs/01-design/architecture"
QA_DIR="$PROJECT/docs/03-quality/qa"
REVIEW_DIR="$PROJECT/docs/03-quality/review"
CHECKPOINT="$PROJECT/docs/CHECKPOINT.md"

PROTECTED_FILES=(
  "MICRO-LOG.md"
  "TASK-INDEX.md"
  "CHECKPOINT.md"
  "CHANGELOG.md"
  "RUNBOOK.md"
  "GLOSSARY.md"
)

DELETED_COUNT=0
SKIPPED_COUNT=0
ERROR_COUNT=0

dry_run_action() {
  echo -e "  ${YELLOW}[dry-run]${NC} Would delete: $1"
}

real_action() {
  if rm -f "$1" 2>/dev/null; then
    echo -e "  ${GREEN}[deleted]${NC} $1"
  else
    err "Failed to delete: $1"
    ERROR_COUNT=$((ERROR_COUNT + 1))
  fi
}

do_delete() {
  local file="$1"
  local basename; basename="$(basename "$file")"

  for protected in "${PROTECTED_FILES[@]}"; do
    if [[ "$basename" == "$protected" ]]; then
      warn "Protected file, skipping: $file"
      SKIPPED_COUNT=$((SKIPPED_COUNT + 1))
      return
    fi
  done

  if [[ ! -f "$file" ]]; then
    return
  fi

  if $DRY_RUN; then
    dry_run_action "$file"
  else
    real_action "$file"
  fi
  DELETED_COUNT=$((DELETED_COUNT + 1))
}

get_active_spec() {
  if [[ -f "$CHECKPOINT" ]]; then
    awk '/SPEC \(active\)|SPEC.*active/{for(i=1;i<=NF;i++) if($i~/spec-v/){print $i; exit}}' "$CHECKPOINT" 2>/dev/null \
      | sed 's/`//g' | xargs basename 2>/dev/null || true
  fi
}

get_active_architecture() {
  if [[ -f "$CHECKPOINT" ]]; then
    awk '/ARCHITECTURE/{for(i=1;i<=NF;i++) if($i~/ARCHITECTURE-v/){print $i; exit}}' "$CHECKPOINT" 2>/dev/null \
      | sed 's/`//g' | xargs basename 2>/dev/null || true
  fi
}

parse_task_ids_from_archive() {
  local archive="$1"
  grep '| T[0-9]' "$archive" 2>/dev/null | sed -n 's/.*| \(T[0-9][0-9]*\) .*/\1/p' | sort -u || true
}

parse_superseded_from_archive() {
  local archive="$1"
  awk '/## Superseded Artifacts/,/^---$/' "$archive" 2>/dev/null \
    | grep '^|' \
    | grep -v 'Artifact' \
    | grep -v '\-\-\-' \
    | grep -v 'Removed Version' || true
}

parse_qa_reviews_from_archive() {
  local archive="$1"
  awk '/## Tasks by Epic/,/## [A-Z]/' "$archive" 2>/dev/null \
    | grep -oE 'E[0-9]+' | sort -u || true
}

find_task_files() {
  local task_id="$1"
  local dir="$2"

  if [[ -d "$dir" ]]; then
    find "$dir" -maxdepth 1 -name "${task_id}*.md" ! -name "ARCHIVE-*" 2>/dev/null || true
  fi
}

delete_empty_files() {
  log "Scanning for empty .md files..."
  local empty_files
  empty_files="$(find "$PROJECT/docs/" -name "*.md" -empty 2>/dev/null || true)"

  if [[ -z "$empty_files" ]]; then
    ok "No empty files found"
    return
  fi

  while IFS= read -r f; do
    do_delete "$f"
  done <<< "$empty_files"
}

# ─── Resolve archive files ───────────────────────────────────────────────────

ARCHIVES=()

if [[ -n "$ARCHIVE_FILTER" ]]; then
  IFS=',' read -ra parts <<< "$ARCHIVE_FILTER"
  for part in "${parts[@]}"; do
    part="${part## }"
    part="${part%% }"
    if [[ "$part" == /* ]]; then
      ARCHIVES+=("$part")
    else
      ARCHIVES+=("$PROJECT/$part")
    fi
  done
else
  for f in "$TASKS_DIR"/ARCHIVE-v*.md; do
    [[ -f "$f" ]] && ARCHIVES+=("$f")
  done
fi

if [[ ${#ARCHIVES[@]} -eq 0 ]]; then
  warn "No archive files found"
  exit 0
fi

log "Found ${#ARCHIVES[@]} archive file(s)"
for a in "${ARCHIVES[@]}"; do
  log "  $(basename "$a")"
done

ACTIVE_SPEC="$(get_active_spec)"
ACTIVE_ARCH="$(get_active_architecture)"

if [[ -n "$ACTIVE_SPEC" ]]; then
  log "Active SPEC: $ACTIVE_SPEC"
fi
if [[ -n "$ACTIVE_ARCH" ]]; then
  log "Active Architecture: $ACTIVE_ARCH"
fi

if $DRY_RUN; then
  log "DRY RUN — no files will be deleted"
fi

echo ""

# ─── Process each archive ────────────────────────────────────────────────────

ALL_TASK_IDS=()

for archive in "${ARCHIVES[@]}"; do
  if [[ ! -f "$archive" ]]; then
    err "Archive file not found: $archive"
    continue
  fi

  archive_name="$(basename "$archive")"
  log "Processing: $archive_name"

  # 1. Extract task IDs
  task_ids="$(parse_task_ids_from_archive "$archive")"

  if [[ -z "$task_ids" ]]; then
    warn "  No task IDs found in $archive_name"
    continue
  fi

  while IFS= read -r tid; do
    ALL_TASK_IDS+=("$tid")
  done <<< "$task_ids"

  count="$(echo "$task_ids" | wc -l | tr -d ' ')"
  log "  Tasks: $count"

  # 2. Delete task files
  while IFS= read -r tid; do
    while IFS= read -r f; do
      [[ -z "$f" ]] && continue
      do_delete "$f"
    done < <(find_task_files "$tid" "$TASKS_DIR")
  done <<< "$task_ids"

  # 3. Delete log files
  while IFS= read -r tid; do
    local_log="$LOGS_DIR/${tid}-log.md"
    if [[ -f "$local_log" ]]; then
      do_delete "$local_log"
    fi
  done <<< "$task_ids"

  # 4. Delete passed QA/Approved Review for archived epics
  epic_ids="$(parse_qa_reviews_from_archive "$archive")"
  if [[ -n "$epic_ids" ]]; then
    while IFS= read -r eid; do
      [[ -z "$eid" ]] && continue
      for qa_file in "$QA_DIR"/QA-${eid}*.md "$QA_DIR"/QA-${eid}.md; do
        if [[ -f "$qa_file" ]]; then
          if ! grep -qi "not passed\|not approved" "$qa_file" 2>/dev/null && \
               grep -qi "passed\|approved" "$qa_file" 2>/dev/null; then
            do_delete "$qa_file"
          else
            warn "  QA not passed, keeping: $(basename "$qa_file")"
          fi
        fi
      done
      for review_file in "$REVIEW_DIR"/REVIEW-${eid}*.md "$REVIEW_DIR"/REVIEW-${eid}.md; do
        if [[ -f "$review_file" ]]; then
          if ! grep -qi "not passed\|not approved" "$review_file" 2>/dev/null && \
               grep -qi "passed\|approved" "$review_file" 2>/dev/null; then
            do_delete "$review_file"
          else
            warn "  Review not approved, keeping: $(basename "$review_file")"
          fi
        fi
      done
    done <<< "$epic_ids"
  fi

  echo ""
done

# ─── Delete superseded SPEC/Architecture (once, across all archives) ────────

if ! $SKIP_SUPERSEDED; then
  log "Processing superseded SPEC/Architecture versions..."
  if [[ -d "$SPEC_DIR" && -n "$ACTIVE_SPEC" ]]; then
    while IFS= read -r f; do
      [[ -z "$f" ]] && continue
      do_delete "$f"
    done < <(find "$SPEC_DIR" -name "spec-v*.md" ! -name "$ACTIVE_SPEC" 2>/dev/null)
  fi
  if [[ -d "$ARCH_DIR" && -n "$ACTIVE_ARCH" ]]; then
    while IFS= read -r f; do
      [[ -z "$f" ]] && continue
      do_delete "$f"
    done < <(find "$ARCH_DIR" -name "ARCHITECTURE-v*.md" ! -name "$ACTIVE_ARCH" 2>/dev/null)
  fi
  echo ""
fi

# ─── Delete empty files (cleanup of previous failed attempts) ────────────────

delete_empty_files

echo ""

# ─── Validation ──────────────────────────────────────────────────────────────

log "Running validation checks..."

FAILED=0

# Check 1: Zero empty files
empty_count="$(find "$PROJECT/docs/" -name "*.md" -empty 2>/dev/null | wc -l | tr -d ' ')"
if [[ "$empty_count" -eq 0 ]]; then
  ok "Check 1: Zero empty files — PASS"
else
  err "Check 1: Found $empty_count empty files — FAIL"
  FAILED=1
fi

# Check 2: No archived task file still exists on disk
ghost_count=0
for tid in "${ALL_TASK_IDS[@]}"; do
  while IFS= read -r f; do
    [[ -z "$f" ]] && continue
    if [[ -f "$f" ]]; then
      err "Check 2: Ghost task file: $f"
      ghost_count=$((ghost_count + 1))
    fi
  done < <(find_task_files "$tid" "$TASKS_DIR")
done
if [[ "$ghost_count" -eq 0 ]]; then
  ok "Check 2: No ghost task files — PASS"
else
  err "Check 2: $ghost_count ghost task file(s) — FAIL"
  FAILED=1
fi

# Check 3: SPEC cleanup — only active version should remain
if [[ -d "$SPEC_DIR" ]]; then
  spec_count="$(find "$SPEC_DIR" -name "*.md" ! -name "$ACTIVE_SPEC" 2>/dev/null | wc -l | tr -d ' ')"
  if [[ "$spec_count" -eq 0 ]]; then
    ok "Check 3: Only active SPEC remains — PASS ($ACTIVE_SPEC)"
  else
    err "Check 3: $spec_count non-active SPEC file(s) remain — FAIL"
    while IFS= read -r f; do
      err "  Remaining: $f"
    done < <(find "$SPEC_DIR" -name "*.md" ! -name "$ACTIVE_SPEC" 2>/dev/null)
    FAILED=1
  fi
else
  ok "Check 3: No SPEC directory — SKIP"
fi

# Check 4: Architecture cleanup — only active version should remain
if [[ -d "$ARCH_DIR" ]]; then
  arch_count="$(find "$ARCH_DIR" -name "*.md" ! -name "$ACTIVE_ARCH" 2>/dev/null | wc -l | tr -d ' ')"
  if [[ "$arch_count" -eq 0 ]]; then
    ok "Check 4: Only active Architecture remains — PASS ($ACTIVE_ARCH)"
  else
    err "Check 4: $arch_count non-active Architecture file(s) remain — FAIL"
    while IFS= read -r f; do
      err "  Remaining: $f"
    done < <(find "$ARCH_DIR" -name "*.md" ! -name "$ACTIVE_ARCH" 2>/dev/null)
    FAILED=1
  fi
else
  ok "Check 4: No Architecture directory — SKIP"
fi

# Check 5: No ghost files (duplicate task IDs)
duplicate_count=0
if [[ -d "$TASKS_DIR" ]]; then
  for tid in "${ALL_TASK_IDS[@]}"; do
    file_count="$(find "$TASKS_DIR" -maxdepth 1 -name "${tid}*.md" ! -name "ARCHIVE-*" 2>/dev/null | wc -l | tr -d ' ')"
    if [[ "$file_count" -gt 0 ]]; then
      err "Check 5: $tid still has $file_count file(s)"
      duplicate_count=$((duplicate_count + 1))
    fi
  done
fi
if [[ "$duplicate_count" -eq 0 ]]; then
  ok "Check 5: No ghost/duplicate task files — PASS"
else
  err "Check 5: $duplicate_count ghost task(s) — FAIL"
  FAILED=1
fi

echo ""
log "Summary:"
log "  Deleted: $DELETED_COUNT files"
log "  Skipped (protected): $SKIPPED_COUNT files"
if [[ "$ERROR_COUNT" -gt 0 ]]; then
  err "  Errors: $ERROR_COUNT"
fi
if $DRY_RUN; then
  log "  Mode: DRY RUN (no changes made)"
fi

if [[ "$FAILED" -ne 0 ]]; then
  err "Validation FAILED — manual intervention required"
  exit 1
fi

ok "All validation checks passed"
exit 0
