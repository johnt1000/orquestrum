"""orquestrum init — placeholder for E2 (real implementation in commands/init_impl)."""
from __future__ import annotations
import argparse


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        'init',
        help='Initialize Orquestrum in the current project (creates .orquestrum/, ORQUESTRUM.md, registers in ~/.orquestrum/registry.toml).',
    )
    p.add_argument('--tool', choices=['claude-code', 'opencode', 'cursor', 'aider', 'windsurf'],
                   help='Also install the integration for this tool')
    p.add_argument('--provider', choices=['claude', 'copilot', 'glm'],
                   help='Provider to lock when --tool is set')
    p.add_argument('--name', metavar='NAME',
                   help='Project name (default: directory basename)')
    p.set_defaults(handler=_handler)


def _handler(args: argparse.Namespace) -> int | None:
    from orquestrum.commands.init_impl import run_init
    return run_init(tool=args.tool, provider=args.provider, name=args.name)
