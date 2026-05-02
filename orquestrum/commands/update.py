"""orquestrum update — re-sync integration + manifest."""
from __future__ import annotations
import argparse


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        'update',
        help='Re-sync this project (or all registered) — re-installs integration, bumps manifest.',
    )
    p.add_argument('--tool', choices=['claude-code', 'opencode', 'cursor', 'aider', 'windsurf'],
                   help='Switch to this tool (cleanup of old + install of new)')
    p.add_argument('--all', action='store_true', help='Iterate every registered project')
    p.add_argument('--check', action='store_true', help='Dry-run; show what would change')
    p.add_argument('--self', action='store_true', dest='self_update',
                   help='Print the upgrade command for the CLI itself (no auto-update)')
    p.set_defaults(handler=_handler)


def _handler(args: argparse.Namespace) -> int | None:
    from orquestrum.commands.update_impl import run_update
    return run_update(tool=args.tool, all_=args.all, check=args.check,
                      self_update=args.self_update)
