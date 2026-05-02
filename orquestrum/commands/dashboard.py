"""orquestrum dashboard → wraps scripts/dashboard/render.py."""
from __future__ import annotations
import argparse


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        'dashboard',
        help='Render the metrics dashboard for the current project.',
        add_help=False,
    )

    p.set_defaults(handler=_handler)


def _handler(args: argparse.Namespace) -> int | None:
    from scripts.dashboard.render import main as wrapped
    wrapped(args.passthrough or [])
    return 0
