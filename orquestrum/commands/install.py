"""orquestrum install → delegates to orquestrum/core/install.py."""
from __future__ import annotations
import argparse


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        'install',
        help='Install a generated integration package into a target project.',
        add_help=False,
    )

    p.set_defaults(handler=_handler)


def _handler(args: argparse.Namespace) -> int | None:
    from orquestrum.core.install import main as wrapped
    wrapped(args.passthrough or [])
    return 0
