"""orquestrum lint → delegates to orquestrum/core/lint.py.

Validates the canonical agents/ + skills/ + docs/ structure. Catches:
missing frontmatter fields, references to skills that don't exist,
chain entries pointing to nowhere, REGISTRY.md drift. Exits 1 on errors.
"""
from __future__ import annotations
import argparse


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        'lint',
        help='Validate canonical agents, skills, and registry consistency.',
        description=(
            'Validate the canonical sources in agents/ + skills/ + docs/. '
            'Checks: required frontmatter fields (name, description), chain '
            'declarations point at existing skills, references/*.md files '
            'present where promised by SKILL.md, and `skills/REGISTRY.md` '
            'matches the on-disk skill set.\n\n'
            'Always run `orquestrum lint` BEFORE `orquestrum convert` — '
            'lint failures indicate broken sources that would produce '
            'broken integration packages downstream.'
        ),
        epilog=(
            'Examples:\n'
            '  orquestrum lint              # validate everything (exit 1 on errors)\n'
            '  orquestrum lint && \\\n'
            '    orquestrum convert --all   # safe pipeline\n'
            '\n'
            'See also:\n'
            '  orquestrum convert --help    Generates integration packages\n'
            '  orquestrum doctor --help     Local environment health-check'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.set_defaults(handler=_handler)


def _handler(args: argparse.Namespace) -> int | None:
    from orquestrum.core.lint import main as wrapped
    wrapped()
    return 0
