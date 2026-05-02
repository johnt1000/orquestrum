#!/usr/bin/env python3
"""archive_cleanup.py — physically deletes archived task/log/version files.

Reads ARCHIVE-*.md files to determine what to delete.
Cast calls this after generating archive summaries (creative work = LLM,
destructive work = this script).

Usage:
    orquestrum archive-cleanup --project /path/to/project [options]

Options:
    --project DIR       Target project root (required)
    --archive FILE      Specific archive file(s), comma-separated (relative to project)
                        If omitted, processes all ARCHIVE-v*.md in docs/02-planning/tasks/
    --dry-run           Show what would be deleted without deleting
    --skip-superseded   Skip deletion of superseded SPEC/Architecture versions
    -h, --help          Show this help
"""
import argparse
import re
import sys
from pathlib import Path

from orquestrum.lib.log import log, ok, warn, err, set_prefix

set_prefix('archive-cleanup')

PROTECTED_FILES = {
    'MICRO-LOG.md',
    'TASK-INDEX.md',
    'CHECKPOINT.md',
    'CHANGELOG.md',
    'RUNBOOK.md',
    'GLOSSARY.md',
}

deleted_count = 0
skipped_count = 0
error_count   = 0


def do_delete(path: Path, dry_run: bool) -> None:
    global deleted_count, skipped_count, error_count

    if path.name in PROTECTED_FILES:
        warn(f'Protected file, skipping: {path}')
        skipped_count += 1
        return

    if not path.is_file():
        return

    if dry_run:
        print(f'  [dry-run] Would delete: {path}')
    else:
        try:
            path.unlink()
            print(f'  [deleted] {path}')
        except OSError as e:
            err(f'Failed to delete: {path} — {e}')
            error_count += 1
            return

    deleted_count += 1


def get_active_spec(checkpoint: Path) -> str:
    if not checkpoint.is_file():
        return ''
    text = checkpoint.read_text(encoding='utf-8', errors='replace')
    for line in text.splitlines():
        if re.search(r'SPEC.*active|active.*SPEC', line, re.IGNORECASE):
            m = re.search(r'(spec-v[\w.-]+\.md)', line, re.IGNORECASE)
            if m:
                return m.group(1).strip('`')
    return ''


def get_active_architecture(checkpoint: Path) -> str:
    if not checkpoint.is_file():
        return ''
    text = checkpoint.read_text(encoding='utf-8', errors='replace')
    for line in text.splitlines():
        if 'ARCHITECTURE' in line:
            m = re.search(r'(ARCHITECTURE-v[\w.-]+\.md)', line)
            if m:
                return m.group(1).strip('`')
    return ''


def parse_task_ids_from_archive(archive: Path) -> list[str]:
    ids: set[str] = set()
    for line in archive.read_text(encoding='utf-8', errors='replace').splitlines():
        if '| T' in line:
            m = re.search(r'\|\s*(T\d+)\s', line)
            if m:
                ids.add(m.group(1))
    return sorted(ids)


def parse_epic_ids_from_archive(archive: Path) -> list[str]:
    text = archive.read_text(encoding='utf-8', errors='replace')
    in_section = False
    ids: set[str] = set()
    for line in text.splitlines():
        if re.match(r'##\s+Tasks by Epic', line):
            in_section = True
            continue
        if in_section and re.match(r'##\s+[A-Z]', line):
            break
        if in_section:
            for m in re.finditer(r'E\d+', line):
                ids.add(m.group(0))
    return sorted(ids)


def find_task_files(task_id: str, tasks_dir: Path) -> list[Path]:
    if not tasks_dir.is_dir():
        return []
    return [
        f for f in tasks_dir.glob(f'{task_id}*.md')
        if not f.name.startswith('ARCHIVE-')
    ]


def delete_empty_files(project: Path, dry_run: bool) -> None:
    log('Scanning for empty .md files...')
    docs = project / 'docs'
    if not docs.is_dir():
        ok('No docs directory — skipping empty-file scan')
        return

    empty = [f for f in docs.rglob('*.md') if f.stat().st_size == 0]
    if not empty:
        ok('No empty files found')
        return

    for f in empty:
        do_delete(f, dry_run)


def is_passed(path: Path) -> bool:
    text = path.read_text(encoding='utf-8', errors='replace').lower()
    if re.search(r'\bnot\s+(?:passed|approved)\b', text):
        return False
    return bool(re.search(r'\b(?:passed|approved)\b', text))


def resolve_archives(project: Path, archive_filter: str, tasks_dir: Path) -> list[Path]:
    if archive_filter:
        archives: list[Path] = []
        for part in archive_filter.split(','):
            part = part.strip()
            p = Path(part) if part.startswith('/') else project / part
            archives.append(p)
        return archives
    return sorted(tasks_dir.glob('ARCHIVE-v*.md'))


def main() -> None:
    global deleted_count, skipped_count, error_count

    parser = argparse.ArgumentParser(
        description='Physically delete archived task/log/version files.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            'Examples:\n'
            '  orquestrum archive-cleanup --project /path/to/project\n'
            '  orquestrum archive-cleanup --project /path/to/project --dry-run\n'
            '  orquestrum archive-cleanup --project /path/to/project --archive docs/02-planning/tasks/ARCHIVE-v1.md'
        ),
    )
    parser.add_argument('--project', required=True, metavar='DIR',
                        help='Target project root')
    parser.add_argument('--archive', metavar='FILE',
                        help='Specific archive file(s), comma-separated (relative to project)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would be deleted without deleting')
    parser.add_argument('--skip-superseded', action='store_true',
                        help='Skip deletion of superseded SPEC/Architecture versions')
    args = parser.parse_args()

    project = Path(args.project).expanduser().resolve()
    if not project.is_dir():
        err(f'Project directory does not exist: {project}')
        sys.exit(1)

    tasks_dir  = project / 'docs' / '02-planning' / 'tasks'
    logs_dir   = tasks_dir / 'logs'
    spec_dir   = project / 'docs' / '00-discovery' / 'spec'
    arch_dir   = project / 'docs' / '01-design' / 'architecture'
    qa_dir     = project / 'docs' / '03-quality' / 'qa'
    review_dir = project / 'docs' / '03-quality' / 'review'
    checkpoint = project / 'docs' / 'CHECKPOINT.md'

    archives = resolve_archives(project, args.archive or '', tasks_dir)

    if not archives:
        warn('No archive files found')
        sys.exit(0)

    log(f'Found {len(archives)} archive file(s)')
    for a in archives:
        log(f'  {a.name}')

    active_spec = get_active_spec(checkpoint)
    active_arch = get_active_architecture(checkpoint)

    if active_spec:
        log(f'Active SPEC: {active_spec}')
    if active_arch:
        log(f'Active Architecture: {active_arch}')

    if args.dry_run:
        log('DRY RUN — no files will be deleted')

    print()

    all_task_ids: list[str] = []

    for archive in archives:
        if not archive.is_file():
            err(f'Archive file not found: {archive}')
            continue

        log(f'Processing: {archive.name}')

        task_ids = parse_task_ids_from_archive(archive)
        if not task_ids:
            warn(f'  No task IDs found in {archive.name}')
            continue

        all_task_ids.extend(task_ids)
        log(f'  Tasks: {len(task_ids)}')

        for tid in task_ids:
            for f in find_task_files(tid, tasks_dir):
                do_delete(f, args.dry_run)

        for tid in task_ids:
            log_file = logs_dir / f'{tid}-log.md'
            if log_file.is_file():
                do_delete(log_file, args.dry_run)

        for eid in parse_epic_ids_from_archive(archive):
            for qa_file in list(qa_dir.glob(f'QA-{eid}*.md')) + [qa_dir / f'QA-{eid}.md']:
                if qa_file.is_file():
                    if is_passed(qa_file):
                        do_delete(qa_file, args.dry_run)
                    else:
                        warn(f'  QA not passed, keeping: {qa_file.name}')
            for rv_file in list(review_dir.glob(f'REVIEW-{eid}*.md')) + [review_dir / f'REVIEW-{eid}.md']:
                if rv_file.is_file():
                    if is_passed(rv_file):
                        do_delete(rv_file, args.dry_run)
                    else:
                        warn(f'  Review not approved, keeping: {rv_file.name}')

        print()

    # ── Superseded SPEC / Architecture ────────────────────────────────────────

    if not args.skip_superseded:
        log('Processing superseded SPEC/Architecture versions...')
        if spec_dir.is_dir() and active_spec:
            for f in spec_dir.glob('spec-v*.md'):
                if f.name != active_spec:
                    do_delete(f, args.dry_run)
        if arch_dir.is_dir() and active_arch:
            for f in arch_dir.glob('ARCHITECTURE-v*.md'):
                if f.name != active_arch:
                    do_delete(f, args.dry_run)
        print()

    # ── Empty files ────────────────────────────────────────────────────────────

    delete_empty_files(project, args.dry_run)

    print()

    # ── Validation ────────────────────────────────────────────────────────────

    log('Running validation checks...')
    failed = False

    docs = project / 'docs'
    empty_count = sum(1 for f in docs.rglob('*.md') if f.stat().st_size == 0) if docs.is_dir() else 0
    if empty_count == 0:
        ok('Check 1: Zero empty files — PASS')
    else:
        err(f'Check 1: Found {empty_count} empty files — FAIL')
        failed = True

    ghost_count = 0
    for tid in all_task_ids:
        for f in find_task_files(tid, tasks_dir):
            if f.is_file():
                err(f'Check 2: Ghost task file: {f}')
                ghost_count += 1
    if ghost_count == 0:
        ok('Check 2: No ghost task files — PASS')
    else:
        err(f'Check 2: {ghost_count} ghost task file(s) — FAIL')
        failed = True

    if spec_dir.is_dir():
        non_active = [f for f in spec_dir.glob('*.md') if f.name != active_spec]
        if not non_active:
            ok(f'Check 3: Only active SPEC remains — PASS ({active_spec})')
        else:
            err(f'Check 3: {len(non_active)} non-active SPEC file(s) remain — FAIL')
            for f in non_active:
                err(f'  Remaining: {f}')
            failed = True
    else:
        ok('Check 3: No SPEC directory — SKIP')

    if arch_dir.is_dir():
        non_active = [f for f in arch_dir.glob('*.md') if f.name != active_arch]
        if not non_active:
            ok(f'Check 4: Only active Architecture remains — PASS ({active_arch})')
        else:
            err(f'Check 4: {len(non_active)} non-active Architecture file(s) remain — FAIL')
            for f in non_active:
                err(f'  Remaining: {f}')
            failed = True
    else:
        ok('Check 4: No Architecture directory — SKIP')

    dup_count = 0
    if tasks_dir.is_dir():
        for tid in all_task_ids:
            remaining = find_task_files(tid, tasks_dir)
            if remaining:
                err(f'Check 5: {tid} still has {len(remaining)} file(s)')
                dup_count += len(remaining)
    if dup_count == 0:
        ok('Check 5: No ghost/duplicate task files — PASS')
    else:
        err(f'Check 5: {dup_count} ghost task(s) — FAIL')
        failed = True

    print()
    log('Summary:')
    log(f'  Deleted: {deleted_count} files')
    log(f'  Skipped (protected): {skipped_count} files')
    if error_count > 0:
        err(f'  Errors: {error_count}')
    if args.dry_run:
        log('  Mode: DRY RUN (no changes made)')

    if failed:
        err('Validation FAILED — manual intervention required')
        sys.exit(1)

    ok('All validation checks passed')


if __name__ == '__main__':
    main()
