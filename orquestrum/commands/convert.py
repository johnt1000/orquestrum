"""orquestrum convert → wraps scripts/convert.py."""
from __future__ import annotations
import argparse


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        'convert',
        help='Generate integration packages from canonical source.',
        add_help=False,  # forward --help to wrapped script
    )

    p.set_defaults(handler=_handler)


def _handler(args: argparse.Namespace) -> int | None:
    from orquestrum.core.convert import main as wrapped
    wrapped(args.passthrough or [])
    return 0
