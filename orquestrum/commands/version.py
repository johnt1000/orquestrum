"""orquestrum version — print version info."""
from __future__ import annotations
import argparse
import sys

from orquestrum import __version__


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser('version', help='Print version info.')
    p.set_defaults(handler=_handler)


def _handler(args: argparse.Namespace) -> int | None:
    print(f'orquestrum {__version__}')
    print(f'Python {sys.version.split()[0]}')
    return 0
