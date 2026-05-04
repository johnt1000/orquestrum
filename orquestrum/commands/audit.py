"""orquestrum audit {payload,parity,attention} — dispatcher to script audits.

Three independent audit subcommands that produce reports about the
framework or the current project:

  - payload    inventory of skill reference sizes (compress candidates)
  - parity     cross-provider parity test (claude vs copilot vs glm)
  - attention  distribution of attention_score across artifacts in the project
"""
from __future__ import annotations
import argparse


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        'audit',
        help='Run an audit (payload | parity | attention).',
        description=(
            'Run one of three audits over the framework or the current '
            'project. Each subcommand has its own flags — pass `--help` '
            'after the subcommand name (e.g. `orquestrum audit payload --help`).'
        ),
        epilog=(
            'Subcommands:\n'
            '  payload      Per-skill reference payload sizes (compress candidates)\n'
            '  parity       Provider parity tests (claude vs copilot vs glm)\n'
            '  attention    Attention-score distribution across project artifacts\n'
            '\n'
            'Examples:\n'
            '  orquestrum audit payload                      # default thresholds\n'
            '  orquestrum audit payload --threshold-kb 50    # raise the threshold\n'
            '  orquestrum audit parity --providers claude,glm\n'
            '  orquestrum audit attention --root .\n'
            '  orquestrum audit attention --threshold-n 50 --output /tmp/attn.md\n'
            '\n'
            'See also:\n'
            '  orquestrum compact --help    Compress oversized references found by `audit payload`\n'
            '  orquestrum lint --help       Validate canonical sources'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    audit_sub = p.add_subparsers(dest='audit_cmd', metavar='AUDIT', required=True)

    pp = audit_sub.add_parser(
        'payload',
        help='Reference payload audit per skill.',
        description=(
            'Walk every `skills/<name>/references/*.md` and report which '
            'files exceed the threshold. Used to identify candidates for '
            '`orquestrum compact`.'
        ),
        epilog=(
            'Flags (forwarded to orquestrum.core.audit.payload):\n'
            '  --threshold-kb N   Files larger than N KB are flagged (default 30)\n'
            '  --output PATH      Write report to file instead of stdout\n'
            '\n'
            'Example: orquestrum audit payload --threshold-kb 40 --output payload.md'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=True,
    )
    pp.set_defaults(handler=_payload)

    pa = audit_sub.add_parser(
        'parity',
        help='Cross-provider parity tests.',
        description=(
            'Verify that the conversion output is byte-identical (modulo '
            'expected per-provider differences like the model field) across '
            'the supported providers. Used to catch regressions in the '
            'convert pipeline.'
        ),
        epilog=(
            'Flags (forwarded to orquestrum.core.tests.parity.run):\n'
            '  --providers CSV    Comma-separated subset (default: all)\n'
            '  --json             Emit a CI-friendly JSON report\n'
            '\n'
            'Example: orquestrum audit parity --providers claude,glm --json'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=True,
    )
    pa.set_defaults(handler=_parity)

    pn = audit_sub.add_parser(
        'attention',
        help='Attention-score distribution across artifacts.',
        description=(
            'Read attention_score frontmatter from every artifact under '
            '<root>/docs/ and print a distribution + top-N list. Helps '
            'identify which artifacts need human attention first '
            '(see docs/agent-context/CONVENTIONS.md → Human Attention Mediation).'
        ),
        epilog=(
            'Flags (forwarded to orquestrum.core.audit.attention_distribution):\n'
            '  --root PATH        Project root to scan (default: cwd)\n'
            '  --threshold-n N    Top-N to list in the report (default 30)\n'
            '  --output PATH      Write report to file instead of stdout\n'
            '\n'
            'Example: orquestrum audit attention --root . --threshold-n 50 --output attn.md'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=True,
    )
    pn.set_defaults(handler=_attention)


def _payload(args: argparse.Namespace) -> int | None:
    from orquestrum.core.audit.payload import main as wrapped
    wrapped(args.passthrough or [])
    return 0


def _parity(args: argparse.Namespace) -> int | None:
    from orquestrum.core.tests.parity.run import main as wrapped
    return wrapped(args.passthrough or []) or 0


def _attention(args: argparse.Namespace) -> int | None:
    from orquestrum.core.audit.attention_distribution import main as wrapped
    wrapped(args.passthrough or [])
    return 0
