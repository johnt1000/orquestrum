"""orquestrum.cli — main entry point for the `orquestrum` executable.

Top-level argparse with subcommands. Each subcommand lives in
orquestrum/commands/X.py and dispatches to the canonical scripts in scripts/.

The CLI is a thin wrapper. `uv run scripts/foo.py` continues to work
unchanged for users who prefer the legacy form.
"""
from __future__ import annotations
import argparse
import sys
from typing import Callable

from orquestrum import __version__


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog='orquestrum',
        description='Specification-Driven Development framework for multi-agent AI (Mac & Linux).',
        epilog="Run `orquestrum <subcommand> --help` for subcommand-specific options.",
    )
    parser.add_argument('--version', '-V', action='version',
                        version=f'orquestrum {__version__}')
    sub = parser.add_subparsers(dest='cmd', metavar='COMMAND', required=True)

    # Each register_X function defines its subparser and sets `args.handler`.
    from orquestrum.commands import (
        convert, install, lint, deps, audit, dashboard, compact, version,
        init, web, repos, update,
    )
    convert.register(sub)
    install.register(sub)
    lint.register(sub)
    deps.register(sub)
    audit.register(sub)
    dashboard.register(sub)
    compact.register(sub)
    init.register(sub)
    update.register(sub)
    web.register(sub)
    repos.register(sub)
    version.register(sub)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    # parse_known_args lets wrapper subcommands forward unknown flags
    # to the underlying scripts (which have their own argparse).
    args, unknown = parser.parse_known_args(argv)

    handler: Callable[[argparse.Namespace], int | None] | None = getattr(args, 'handler', None)
    if handler is None:
        parser.print_help(sys.stderr)
        sys.exit(2)

    # Wrapper subcommands (convert/install/deps/dashboard/compact/audit-*) consume
    # `args.passthrough`. Native subcommands (init/update/web/repos/lint/version)
    # ignore it. Merge any unknown args after the subcommand name so things like
    # `orquestrum convert --all --dry-run` route correctly.
    existing = getattr(args, 'passthrough', None) or []
    args.passthrough = list(existing) + list(unknown)

    rc = handler(args)
    sys.exit(int(rc or 0))


if __name__ == '__main__':
    main()
