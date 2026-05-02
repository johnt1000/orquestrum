"""orquestrum audit {payload,parity,attention} — dispatcher to script audits."""
from __future__ import annotations
import argparse


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        'audit',
        help='Run an audit script (payload | parity | attention).',
    )
    audit_sub = p.add_subparsers(dest='audit_cmd', metavar='AUDIT', required=True)

    pp = audit_sub.add_parser('payload', help='Reference payload audit per skill.', add_help=False)

    pp.set_defaults(handler=_payload)

    pa = audit_sub.add_parser('parity', help='Provider parity tests.', add_help=False)

    pa.set_defaults(handler=_parity)

    pn = audit_sub.add_parser('attention', help='Attention score distribution.', add_help=False)

    pn.set_defaults(handler=_attention)


def _payload(args: argparse.Namespace) -> int | None:
    from scripts.audit.payload import main as wrapped
    wrapped(args.passthrough or [])
    return 0


def _parity(args: argparse.Namespace) -> int | None:
    from scripts.tests.parity.run import main as wrapped
    return wrapped(args.passthrough or []) or 0


def _attention(args: argparse.Namespace) -> int | None:
    from scripts.audit.attention_distribution import main as wrapped
    wrapped(args.passthrough or [])
    return 0
