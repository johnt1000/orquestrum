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
        help='Initialize Orquestrum in the current project (writes only .orquestrum/).',
        description=(
            'Bootstrap Orquestrum in the current project. Creates '
            '`.orquestrum/{config.toml, manifest.md, .gitignore, metrics/}` '
            'and registers the project in `~/.orquestrum/registry.toml`.\n\n'
            'Distinct from `setup`: `init` is project-scoped and OPTIONAL. '
            'Projects that do not want orquestrum metrics/MCP linkage simply '
            'skip running it. The framework itself (agents/skills) lives '
            'globally at `~/.claude/` — never inside this project.\n\n'
            'Asks 3 prompts about optional integrations (metrics hook, MCP '
            'server, agents). Pass `--yes` to accept defaults silently. '
            'Detects v0.4 layout and migrates `ORQUESTRUM.md` → '
            '`.orquestrum/manifest.md` automatically.'
        ),
        epilog=(
            'Examples:\n'
            '  orquestrum init                    # interactive wizard (3 prompts)\n'
            '  orquestrum init --yes              # silent, accept defaults\n'
            '  orquestrum init --name my-app      # override project name\n'
            '\n'
            'See also:\n'
            '  orquestrum setup --help        # Global wizard (framework install, runs once)\n'
            '  orquestrum repos list          # Show all registered projects\n'
            '  orquestrum update --help       # Re-sync after framework update'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument('--name', metavar='NAME',
                   help='Project name (default: current directory basename)')
    p.add_argument('-y', '--yes', '--non-interactive',
                   dest='non_interactive', action='store_true',
                   help='Accept defaults for every prompt without asking. '
                        'Defaults: metrics hook ENABLED globally, MCP server '
                        'ENABLED globally, agents NOT installed.')
    p.add_argument('--per-project', action='store_true', dest='per_project',
                   help='Force the metrics-hook + MCP prompts even when global '
                        'registration already exists. Default behavior: skip '
                        'those prompts when `orquestrum setup` has already '
                        'registered them globally.')
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
    return run_init(
        name=args.name,
        interactive=not args.non_interactive,
        per_project=getattr(args, 'per_project', False),
    )
