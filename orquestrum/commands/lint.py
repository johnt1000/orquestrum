"""orquestrum lint → delegates to orquestrum/core/lint.py."""
from __future__ import annotations
import argparse


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser('lint', help='Validate agent and skill files.')
    p.set_defaults(handler=_handler)


def _handler(args: argparse.Namespace) -> int | None:
    from orquestrum.core.lint import main as wrapped
    wrapped()
    return 0
