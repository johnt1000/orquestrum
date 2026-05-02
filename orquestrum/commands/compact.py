"""orquestrum compact → wraps scripts/build/compress_refs.py."""
from __future__ import annotations
import argparse


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        'compact',
        help='Compress oversized skill references deterministically.',
        add_help=False,
    )

    p.set_defaults(handler=_handler)


def _handler(args: argparse.Namespace) -> int | None:
    from orquestrum.core.build.compress_refs import main as wrapped
    wrapped(args.passthrough or [])
    return 0
