"""orquestrum dashboard → delegates to orquestrum/core/dashboard/render.py.

Renders a static markdown (and optional HTML) snapshot of the current
project's metrics. Reads from `.orquestrum/metrics/session.json` and
`.orquestrum/metrics/events.jsonl`. For a live, interactive view, see
`orquestrum web`.
"""
from __future__ import annotations
import argparse


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        'dashboard',
        help='Render a static metrics dashboard (markdown + optional HTML).',
        description=(
            'Render a static metrics snapshot for the current project. '
            'Reads from `.orquestrum/metrics/session.json` (rebuilt on demand) '
            'plus `.orquestrum/metrics/events.jsonl`. Output is markdown by '
            'default; pass --html for an additional standalone HTML file.\n\n'
            'For a live interactive dashboard with auto-refresh, run '
            '`orquestrum web` instead — this command is the file-on-disk '
            'snapshot, useful for committing progress to a repo or sharing '
            'a single-file report.'
        ),
        epilog=(
            'Flags (forwarded to orquestrum.core.dashboard.render):\n'
            '  --metrics-dir PATH   Override metrics dir (default .orquestrum/metrics)\n'
            '  --tier TIER          Filter to one tier (deep | balanced | mechanical)\n'
            '  --html               Also write dashboard.html\n'
            '\n'
            'Examples:\n'
            '  orquestrum dashboard                                  # render dashboard.md\n'
            '  orquestrum dashboard --html                           # also dashboard.html\n'
            '  orquestrum dashboard --tier balanced                  # only balanced-tier sessions\n'
            '  orquestrum dashboard --metrics-dir other/.orquestrum/metrics\n'
            '\n'
            'See also:\n'
            '  orquestrum web --help    Live interactive dashboard\n'
            '  orquestrum repos list    List all projects with metrics'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=True,
    )

    p.set_defaults(handler=_handler)


def _handler(args: argparse.Namespace) -> int | None:
    from orquestrum.core.dashboard.render import main as wrapped
    wrapped(args.passthrough or [])
    return 0
