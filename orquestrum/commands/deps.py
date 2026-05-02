"""orquestrum deps → wraps scripts/deps.py."""
from __future__ import annotations
import argparse


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        'deps',
        help='Install external agent/skill dependencies (agency-agents, anthropics/skills).',
        add_help=False,
    )

    p.set_defaults(handler=_handler)


def _handler(args: argparse.Namespace) -> int | None:
    from orquestrum.core.deps import main as wrapped
    wrapped(args.passthrough or [])
    return 0
