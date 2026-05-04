"""orquestrum deps → delegates to orquestrum/core/deps.py.

Installs external agent/skill repositories from upstream sources:
  - agency-agents     (msitarzewski/agency-agents — 184+ specialist agents)
  - anthropics/skills (anthropics/skills — 17 skills incl. supabase)

Clones to temporary directories then copies into --target. Does not
pollute the orquestrum repo. Idempotent — re-running updates pins.
"""
from __future__ import annotations
import argparse


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        'deps',
        help='Install external agent/skill dependencies (agency-agents, anthropics/skills).',
        description=(
            'Install third-party agent and skill repositories into a '
            'target tool directory. Currently supports two upstream sources:\n\n'
            '  • agency-agents     msitarzewski/agency-agents (184+ specialist agents)\n'
            '  • skills            anthropics/skills (17 skills including supabase)\n\n'
            'The skill set is curated by upstream — orquestrum just installs '
            "them under the target tool's expected layout (`agents/` for agency, "
            '`skills/` for anthropics). Use `--only NAME` to install just one '
            'source. Use `--update-pins` after upstream releases to refresh '
            'the version pins in `orquestrum/lib/deps_pins.json`.'
        ),
        epilog=(
            'Flags (forwarded to orquestrum.core.deps):\n'
            '  --target PATH        Where to install (e.g. ~/.config/opencode, ~)\n'
            '  --only NAME          Install only one source (agency | skills)\n'
            '  --update-pins        Refresh version pins from upstream HEAD\n'
            '\n'
            'Examples:\n'
            '  orquestrum deps --target ~/.config/opencode             # install both for opencode\n'
            '  orquestrum deps --target ~ --only agency                # only agency-agents (claude-code)\n'
            '  orquestrum deps --target ~/.config/opencode --only skills\n'
            '  orquestrum deps --target ~ --update-pins                # bump pins to upstream HEAD\n'
            '\n'
            'See also:\n'
            '  orquestrum install --help    Install orquestrum itself into the target\n'
            '  orquestrum setup --advanced  Interactive wizard that calls deps automatically'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=True,
    )

    p.set_defaults(handler=_handler)


def _handler(args: argparse.Namespace) -> int | None:
    from orquestrum.core.deps import main as wrapped
    wrapped(args.passthrough or [])
    return 0
