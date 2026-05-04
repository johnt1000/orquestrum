"""orquestrum installs — inspect + maintain the install manifest.

The manifest at `~/.orquestrum/installs.json` records every (tool, target)
pair orquestrum has installed into. It's the source of truth that
`uninstall` reads to do surgical removal. Over time it accumulates dead
entries (test residue, pytest tmp dirs, retired tools) — this command
exposes the manifest for inspection and pruning.

Subcommands:
  list    Tabulate every record (target, tool, version, files, install date)
  prune   Remove records whose target no longer exists OR whose tool was
          retired (aider/cursor/windsurf removed in v0.4)
"""
from __future__ import annotations
import argparse
import datetime as dt
import shutil
import sys
from pathlib import Path

from orquestrum.lib import installs_manifest as im


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        'installs',
        help='Inspect and prune the install manifest (~/.orquestrum/installs.json).',
        description=(
            'Manage `~/.orquestrum/installs.json` — the persistent record '
            'of every (tool, target) install orquestrum has performed. '
            'Used by `uninstall` for surgical removal.\n\n'
            'Subcommands:\n'
            '  list     Tabulate every record\n'
            '  prune    Remove stale-target + retired-tool entries (idempotent)\n\n'
            'The manifest accumulates entries over time — pytest tmp dirs '
            "from CI runs, projects you've moved or deleted, integrations "
            "for tools that have since been removed (aider/cursor/windsurf "
            'in v0.4). Pruning these is safe: only entries that point to '
            'non-existent targets or removed tools are touched.'
        ),
        epilog=(
            'Examples:\n'
            '  orquestrum installs list                # show every record\n'
            '  orquestrum installs prune --dry-run     # preview what would be removed\n'
            '  orquestrum installs prune               # actually prune (writes backup first)\n'
            '\n'
            'See also:\n'
            '  orquestrum uninstall --help    Surgical removal of one project\n'
            '  orquestrum doctor --help       Reports stale-install ratio'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sp = p.add_subparsers(dest='installs_cmd', metavar='SUBCOMMAND', required=True)

    pl = sp.add_parser(
        'list',
        help='Show every install record in the manifest.',
        description=(
            'Print a table of every install record with TOOL / TARGET / '
            'VERSION / FILES / DATE, marked ✓ when target still exists, '
            '✗ when the target dir is gone (stale).'
        ),
        epilog='Example: orquestrum installs list',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    pl.set_defaults(handler=_list)

    pp = sp.add_parser(
        'prune',
        help='Remove stale-target and retired-tool entries from the manifest.',
        description=(
            'Sweep the manifest and remove every record where:\n'
            '  • The target directory no longer exists on disk, OR\n'
            '  • The tool was retired in v0.4 (aider, cursor, windsurf).\n\n'
            'Always writes a `.bak.<YYYYMMDD>` backup before the prune so '
            'you can restore if anything looks off. Use --dry-run to see '
            'what would be removed without writing.'
        ),
        epilog=(
            'Examples:\n'
            '  orquestrum installs prune --dry-run     # preview\n'
            '  orquestrum installs prune               # do it (with backup)'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    pp.add_argument('--dry-run', action='store_true', dest='dry_run',
                    help='Print what would be removed; do not write the manifest.')
    pp.set_defaults(handler=_prune)


# ─── handlers ──────────────────────────────────────────────────────────────


def _list(args: argparse.Namespace) -> int:
    records = im.list_installs()
    if not records:
        print('No installs recorded yet.')
        print('(Run `orquestrum setup` or `orquestrum install --tool ... --target ...`)')
        return 0

    buckets = im.classify_stale(records)
    n_valid   = len(buckets['valid'])
    n_stale   = len(buckets['stale_target'])
    n_retired = len(buckets['retired_tool'])

    print(f'{len(records)} install record(s) in '
          f'~/.orquestrum/installs.json:')
    print()
    print(f'  {"":<2} {"TOOL":<12} {"FILES":>6}  {"DATE":<19}  TARGET')
    for r in sorted(records, key=lambda r: (r.tool, r.target)):
        if r in buckets['retired_tool']:
            mark = '✗'   # tool no longer supported
            note = '(retired)'
        elif r in buckets['stale_target']:
            mark = '✗'   # path gone
            note = '(stale)'
        else:
            mark = '✓'
            note = ''
        date = r.installed_at.split('T')[0] if r.installed_at else '-'
        target = r.target
        if len(target) > 60:
            target = '…' + target[-57:]
        suffix = f'  {note}' if note else ''
        print(f'  {mark:<2} {r.tool:<12} {len(r.files):>6}  {date:<19}  {target}{suffix}')
    print()
    print(f'Summary: {n_valid} valid, {n_stale} stale, {n_retired} retired-tool')
    if n_stale or n_retired:
        print(f'Run `orquestrum installs prune` to remove the {n_stale + n_retired} '
              f'dead entries.')
    return 0


def _prune(args: argparse.Namespace) -> int:
    # Compute what would change BEFORE writing
    removed_stale, removed_retired, kept = im.prune_stale(dry_run=True)
    total_removed = removed_stale + removed_retired
    if total_removed == 0:
        print('Manifest is clean — no stale or retired-tool entries to prune.')
        return 0

    print(f'Prune plan:')
    print(f'  Stale target (path gone):     {removed_stale}')
    print(f'  Retired tool (aider/cursor/…): {removed_retired}')
    print(f'  Will keep:                    {kept}')
    print()

    if args.dry_run:
        print('(dry-run — manifest not written)')
        return 0

    # Backup before writing
    from orquestrum.lib.paths import orquestrum_home
    manifest_path = orquestrum_home() / 'installs.json'
    if manifest_path.exists():
        date = dt.date.today().strftime('%Y%m%d')
        backup_path = manifest_path.with_suffix(f'.json.bak.{date}')
        shutil.copy(manifest_path, backup_path)
        print(f'  Backup → {backup_path}')

    # Now actually prune
    im.prune_stale(dry_run=False)
    print(f'✓ Pruned {total_removed} entry/entries. {kept} kept.')
    return 0
