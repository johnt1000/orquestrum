"""orquestrum compact → delegates to orquestrum/core/build/compress_refs.py.

Deterministic compression of oversized skill `references/*.md` files.
Produces `<file>.compact.md` siblings used by `inject_references: compact`
adapters. Idempotent — re-running with no source change is a no-op.
"""
from __future__ import annotations
import argparse


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        'compact',
        help='Compress oversized skill references deterministically.',
        description=(
            'Generate compact-mode reference files from oversized '
            '`skills/<name>/references/*.md` sources. Skills declaring '
            '`inject_references: compact` consume the compact files at '
            'build time. The compression is deterministic and idempotent — '
            "re-running on an unchanged source file produces an identical "
            'output, so this command is safe to wire into convert pipelines.\n\n'
            'Skills are processed automatically; passing --skill restricts '
            'work to a single slug. Use --dry-run to preview without '
            'writing files.'
        ),
        epilog=(
            'Flags (forwarded to orquestrum.core.build.compress_refs):\n'
            '  --threshold-kb N   Compress files larger than N KB (default 30)\n'
            '  --skill SLUG       Only process this skill (default: all)\n'
            '  --dry-run          Preview without writing\n'
            '  --force            Re-compress even if output is up-to-date\n'
            '\n'
            'Examples:\n'
            '  orquestrum compact                             # compress everything > 30 KB\n'
            '  orquestrum compact --skill task-manager        # only task-manager\n'
            '  orquestrum compact --threshold-kb 50           # raise threshold to 50 KB\n'
            '  orquestrum compact --dry-run                   # see what would change\n'
            '\n'
            'See also:\n'
            '  orquestrum convert --help    Triggers compact automatically when needed\n'
            '  orquestrum lint --help       Validates skill structure'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=True,
    )

    p.set_defaults(handler=_handler)


def _handler(args: argparse.Namespace) -> int | None:
    from orquestrum.core.build.compress_refs import main as wrapped
    wrapped(args.passthrough or [])
    return 0
