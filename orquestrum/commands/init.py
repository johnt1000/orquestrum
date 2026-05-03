"""orquestrum init — bootstrap `<project>/.orquestrum/` and ask about
optional integrations (metrics hook, MCP server, claude-code agents).

The actual logic lives in `init_impl.run_init`; this module is the thin
argparse wrapper.

Since v0.5, `--tool` and `--provider` are gone from `init`. Tool installs
are explicit:
    orquestrum install --tool claude-code --target ~
"""
from __future__ import annotations
import argparse
import sys


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        'init',
        help=('Initialize Orquestrum in the current project. Creates '
              '.orquestrum/{config.toml, manifest.md, .gitignore, metrics/}, '
              'registers in ~/.orquestrum/registry.toml. Asks 3 prompts about '
              'optional integrations (metrics hook, MCP, agents) — pass '
              '--yes to accept defaults silently.'),
    )
    p.add_argument('--name', metavar='NAME',
                   help='Project name (default: cwd directory basename)')
    p.add_argument('-y', '--yes', '--non-interactive',
                   dest='non_interactive', action='store_true',
                   help='Accept defaults for every prompt without asking. '
                        'Defaults: metrics hook ENABLED globally, MCP server '
                        'ENABLED globally, agents NOT installed.')
    # Reject the v0.4 flags with a clear migration message instead of
    # silently ignoring them.
    p.add_argument('--tool', help=argparse.SUPPRESS)
    p.add_argument('--provider', help=argparse.SUPPRESS)
    p.set_defaults(handler=_handler)


def _handler(args: argparse.Namespace) -> int | None:
    if args.tool or args.provider:
        print(
            "init: --tool/--provider were removed in v0.5. Use:\n"
            "  orquestrum init                                  # local config\n"
            "  orquestrum install --tool <tool> --target ~      # global agents",
            file=sys.stderr,
        )
        return 2
    from orquestrum.commands.init_impl import run_init
    return run_init(name=args.name, interactive=not args.non_interactive)
