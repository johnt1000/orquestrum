"""orquestrum update — re-sync integration + manifest."""
from __future__ import annotations
import argparse


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        'update',
        help='Re-sync project(s) after framework update; --self upgrades the CLI.',
        description=(
            'Two modes:\n\n'
            '  • DEFAULT (project re-sync): re-runs convert + install for the '
            'current project (or all registered projects with --all), then '
            'bumps `last_sync` in the manifest. Use after `update --self` '
            'or after pulling new agents/skills from the framework repo.\n\n'
            '  • --self: upgrade the orquestrum CLI itself. Auto-detects the '
            'install method (uv tool / venv / unknown) and runs the matching '
            'upgrade command (e.g. `uv tool upgrade orquestrum`).\n\n'
            'Use --check for a dry-run that prints what would change without '
            'touching anything. Use --tool to switch a project from one tool '
            'to another (cleanup of old + install of new).'
        ),
        epilog=(
            'Examples:\n'
            '  orquestrum update                      # re-sync current project\n'
            '  orquestrum update --all                # re-sync every registered project\n'
            '  orquestrum update --check              # dry-run, show diffs\n'
            '  orquestrum update --tool opencode      # switch from claude-code → opencode\n'
            '  orquestrum update --self               # upgrade the CLI binary\n'
            '\n'
            'See also:\n'
            '  orquestrum repos list          # See which projects --all would touch\n'
            '  orquestrum doctor --help       # Verify install state after --self'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument('--tool', choices=['claude-code', 'opencode'],
                   help='Switch project to this tool (cleanup old + install new)')
    p.add_argument('--all', action='store_true',
                   help='Iterate every registered project (use with care)')
    p.add_argument('--check', action='store_true',
                   help='Dry-run mode — show what would change without writing')
    p.add_argument('--self', action='store_true', dest='self_update',
                   help='Upgrade the orquestrum CLI itself. Detects install '
                        'mode (uv tool / venv / unknown) and runs the '
                        'matching upgrade command.')
    p.set_defaults(handler=_handler)


def _handler(args: argparse.Namespace) -> int | None:
    from orquestrum.commands.update_impl import run_update
    return run_update(tool=args.tool, all_=args.all, check=args.check,
                      self_update=args.self_update)
