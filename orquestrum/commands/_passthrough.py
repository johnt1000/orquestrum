"""_passthrough.py — shared helper for subcommands that wrap an existing script.

Each wrapper subparser uses parse_known_args() to capture flags it doesn't
recognize, then calls the wrapped main() with that argv list. This lets the
underlying script's argparse define the actual flag set; the orquestrum
subparser's only job is dispatch.
"""
from __future__ import annotations
import argparse
from typing import Callable


def passthrough_handler(wrapped_main: Callable[[list[str] | None], int | None]):
    """Return a handler that calls wrapped_main(args.passthrough)."""
    def handler(args: argparse.Namespace) -> int | None:
        return wrapped_main(getattr(args, 'passthrough', None) or [])
    return handler
