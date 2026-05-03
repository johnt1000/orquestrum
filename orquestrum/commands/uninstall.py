"""orquestrum uninstall — remove Orquestrum from a project or uninstall the CLI."""
from __future__ import annotations
import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        'uninstall',
        help='Remove Orquestrum from a project, or uninstall the CLI itself.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            'Examples:\n'
            '  orquestrum uninstall --dry-run        # preview what would be removed\n'
            '  orquestrum uninstall                  # remove from current project\n'
            '  orquestrum uninstall --all            # remove from every registered project\n'
            '  orquestrum uninstall --self           # uninstall the CLI itself'
        ),
    )
    p.add_argument('-y', '--yes', action='store_true',
                   help='Skip confirmation prompt')
    p.add_argument('--dry-run', action='store_true', dest='dry_run',
                   help='Print what would be removed without making changes')
    p.add_argument('--all', action='store_true', dest='all_',
                   help='Remove from all registered projects')
    p.add_argument('--self', action='store_true', dest='self_uninstall',
                   help='Uninstall the orquestrum CLI globally')
    p.set_defaults(handler=_handler)


def _handler(args: argparse.Namespace) -> int:
    if args.self_uninstall:
        return _uninstall_self(yes=args.yes, dry_run=args.dry_run)
    if args.all_:
        return _uninstall_all(yes=args.yes, dry_run=args.dry_run)
    return _uninstall_project(Path.cwd(), yes=args.yes, dry_run=args.dry_run)


# ── self ─────────────────────────────────────────────────────────────────────

def _uninstall_self(*, yes: bool, dry_run: bool = False) -> int:
    from orquestrum.commands.extras import _detect_env
    mode = _detect_env()

    if mode == 'uv-tool':
        cmd = ['uv', 'tool', 'uninstall', 'orquestrum']
    elif mode == 'venv':
        cmd = ['pip', 'uninstall', 'orquestrum', '-y']
    else:
        print('Could not detect install method automatically. Run one of:')
        print('  uv tool uninstall orquestrum')
        print('  pip uninstall orquestrum')
        return 0

    if dry_run:
        print(f'(dry-run) Would run: {" ".join(cmd)}')
        return 0

    if not yes:
        answer = input(f'Run `{" ".join(cmd)}`? [y/N] ').strip().lower()
        if answer not in ('y', 'yes'):
            print('Aborted.')
            return 0

    result = subprocess.run(cmd)
    return result.returncode


# ── project ───────────────────────────────────────────────────────────────────

def _describe_removal(project_root: Path, tool: str | None) -> list[str]:
    """Return a list of items that will be removed (for preview).

    Prefers the persistent install manifest (`~/.orquestrum/installs.json`)
    as the source of truth — orquestrum only proposes to remove files it
    actually installed. Falls back to the legacy heuristic when no manifest
    record exists (e.g. installs that predate the manifest).
    """
    from orquestrum.commands.update_impl import _orquestrum_agent_filenames
    from orquestrum.lib import installs_manifest
    items: list[str] = []

    # Source of truth — manifest knows exactly which files we wrote.
    record = installs_manifest.get_install(tool, project_root) if tool else None

    if record is not None:
        # File-by-file accounting; user content under shared dirs is safe.
        for rel in record.files:
            if (project_root / rel).is_file():
                items.append(rel)
        # Directories only listed when empty after files would be removed
        # (i.e. orquestrum-owned and would actually be reclaimed).
        for rel in record.directories:
            d = project_root / rel
            if d.is_dir():
                items.append(f'{rel}/ (if empty after file removal)')
    elif tool == 'claude-code':
        # Pre-manifest heuristic — kept for projects installed by older CLIs.
        agents_dir = project_root / '.claude' / 'agents'
        if agents_dir.is_dir():
            for fname in _orquestrum_agent_filenames():
                if (agents_dir / fname).exists():
                    items.append(f'.claude/agents/{fname}')
        if (project_root / '.sdd').is_dir():
            items.append('.sdd/')
        if (project_root / '.claude' / 'settings.json').exists():
            items.append('.claude/settings.json (orquestrum hooks)')
    elif tool == 'opencode':
        agents_dir = project_root / '.opencode' / 'agents'
        if agents_dir.is_dir():
            for fname in _orquestrum_agent_filenames():
                if (agents_dir / fname).exists():
                    items.append(f'.opencode/agents/{fname}')
        if (project_root / '.opencode' / 'docs').is_dir():
            items.append('.opencode/docs/')
    elif tool == 'cursor':
        if (project_root / '.cursor' / 'rules').is_dir():
            items.append('.cursor/rules/')
    elif tool == 'aider':
        if (project_root / 'CONVENTIONS.md').exists():
            items.append('CONVENTIONS.md')
    elif tool == 'windsurf':
        if (project_root / '.windsurfrules').exists():
            items.append('.windsurfrules')

    if (project_root / '.orquestrum').is_dir():
        items.append('.orquestrum/')
    if (project_root / 'ORQUESTRUM.md').exists():
        items.append('ORQUESTRUM.md')
    items.append('registry entry')
    return items


def _do_remove(project_root: Path, tool: str | None) -> list[str]:
    """Execute the removal. Returns list of removed items."""
    from orquestrum.commands.update_impl import _cleanup_old_tool
    from orquestrum.lib import registry

    removed: list[str] = []

    # 1. Remove integration files (tool-specific, never shared dirs)
    if tool:
        removed += _cleanup_old_tool(project_root, tool)

    # 2. Remove .orquestrum/
    orq_dir = project_root / '.orquestrum'
    if orq_dir.is_dir():
        shutil.rmtree(orq_dir)
        removed.append('.orquestrum/')

    # 3. Remove ORQUESTRUM.md
    manifest = project_root / 'ORQUESTRUM.md'
    if manifest.exists():
        manifest.unlink()
        removed.append('ORQUESTRUM.md')

    # 4. Deregister
    entry = registry.unregister_project(path=project_root)
    if entry:
        removed.append(f'registry entry ({entry.get("name", project_root.name)})')

    return removed


def _uninstall_one(project_root: Path, *, yes: bool, prefix: str = '', dry_run: bool = False) -> bool:
    from orquestrum.commands.update_impl import _project_tool

    if not (project_root / '.orquestrum').is_dir():
        print(f'{prefix}  not initialized — skipped')
        return True

    tool, _ = _project_tool(project_root)
    items = _describe_removal(project_root, tool)

    if dry_run:
        print(f'{prefix}(dry-run) Would remove from {project_root}:')
        for item in items:
            print(f'{prefix}  - {item}')
        return True

    if not yes:
        print(f'{prefix}Will remove from {project_root}:')
        for item in items:
            print(f'{prefix}  - {item}')
        answer = input(f'{prefix}Proceed? [y/N] ').strip().lower()
        if answer not in ('y', 'yes'):
            print(f'{prefix}Aborted.')
            return False

    removed = _do_remove(project_root, tool)
    print(f'{prefix}  removed {len(removed)} item(s)')
    return True


def _uninstall_project(project_root: Path, *, yes: bool, dry_run: bool = False) -> int:
    if not (project_root / '.orquestrum').is_dir():
        print('error: not in an Orquestrum project. Nothing to remove.', file=sys.stderr)
        return 1
    _uninstall_one(project_root, yes=yes, dry_run=dry_run)
    return 0


def _uninstall_all(*, yes: bool, dry_run: bool = False) -> int:
    from orquestrum.lib import registry
    projects = registry.load_registry()
    if not projects:
        print('No projects registered.')
        return 0

    print(f'{len(projects)} project(s) registered:')
    for p in projects:
        print(f'  {p["name"]:<24} {p["path"]}')

    if dry_run:
        print('\n(dry-run) Would attempt to uninstall from each of the above.')
        for i, proj in enumerate(projects, 1):
            path = Path(proj['path'])
            print(f'\n[{i}/{len(projects)}] {proj["name"]} ({path})')
            if not path.is_dir():
                print('  (would skip — path no longer exists)')
                continue
            _uninstall_one(path, yes=True, prefix='  ', dry_run=True)
        return 0

    if not yes:
        answer = input('\nRemove Orquestrum from all of them? [y/N] ').strip().lower()
        if answer not in ('y', 'yes'):
            print('Aborted.')
            return 0

    ok_count = skip_count = 0
    for i, proj in enumerate(projects, 1):
        path = Path(proj['path'])
        print(f'\n[{i}/{len(projects)}] {proj["name"]} ({path})')
        if not path.is_dir():
            print('  skipped (path no longer exists)')
            skip_count += 1
            continue
        _uninstall_one(path, yes=True, prefix='  ')
        ok_count += 1

    print(f'\n{ok_count} removed, {skip_count} skipped.')
    return 0
