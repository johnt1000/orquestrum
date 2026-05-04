"""orquestrum version — print version info."""
from __future__ import annotations
import argparse
import sys

from orquestrum import __version__


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        'version',
        help='Print orquestrum and Python versions.',
        description=(
            'Print the installed orquestrum CLI version + the Python '
            'interpreter version that is running it. Equivalent to '
            '`orquestrum --version` but adds the Python line, which is '
            'useful when reporting issues.'
        ),
        epilog=(
            'Examples:\n'
            '  orquestrum version           # full version info\n'
            '  orquestrum --version         # short form (CLI version only)\n'
            '\n'
            'See also:\n'
            '  orquestrum doctor --help     Full environment health-check\n'
            '  orquestrum update --self     Upgrade the CLI to the latest version'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.set_defaults(handler=_handler)


def _handler(args: argparse.Namespace) -> int | None:
    print(f'orquestrum {__version__}')
    print(f'Python {sys.version.split()[0]}')
    return 0
