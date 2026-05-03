"""orquestrum hook — Stop / SubagentStop entry point for Claude Code.

Replaces the older `uv run <project>/.claude/sdd/scripts/hooks/emit_metrics.py`
invocation. That command used a path RELATIVE to Claude Code's cwd, which
fails the moment the user runs Claude Code from a directory that doesn't
have `.claude/sdd/scripts/hooks/emit_metrics.py` at that exact location
(every directory other than $HOME, in practice).

This subcommand sidesteps the issue entirely: settings.json points at
`orquestrum hook`, which resolves via PATH instead of via cwd. The hook
logic itself is unchanged — we just call `emit_metrics.main()`.

Reads the hook event JSON from stdin, writes one line to
`<input_json.cwd>/.orquestrum/metrics/events.jsonl`, and ALWAYS exits 0.
"""
from __future__ import annotations
import argparse
import sys


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        'hook',
        help=('Stop / SubagentStop hook entry point for Claude Code. '
              'Reads event JSON on stdin and appends one line to the '
              'project metrics log. Always exits 0.'),
        description=(
            'Hook handler invoked by Claude Code on every Stop / '
            'SubagentStop event. Settings.json registers this as '
            "`{\"command\": \"orquestrum hook\"}` — no path resolution, "
            'just PATH lookup, so it works regardless of which directory '
            'Claude Code was launched from. Never blocks the user: any '
            'error is logged to stderr and exit code is always 0.'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.set_defaults(handler=_handler)


def _handler(args: argparse.Namespace) -> int:
    from orquestrum.core.hooks.emit_metrics import main as run_hook
    run_hook()
    # emit_metrics.main() never raises, but be defensive — a non-zero
    # exit here would block Claude Code's response, which violates the
    # hook contract.
    sys.exit(0)
