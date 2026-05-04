"""orquestrum convert → delegates to orquestrum/core/convert.py.

Generates per-tool integration packages from the canonical agents/ +
skills/ sources. Output lands in `integrations/<tool>/` (dev mode) or
`~/.orquestrum/cache/integrations/<tool>/` (when installed via wheel).
"""
from __future__ import annotations
import argparse


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        'convert',
        help='Generate per-tool integration packages from canonical source.',
        description=(
            'Generate integration packages for each supported tool '
            '(claude-code, opencode) from the canonical agents/ + skills/ '
            'sources. Output lands in `integrations/<tool>/` (when running '
            'from the repo) or `~/.orquestrum/cache/integrations/<tool>/` '
            '(when installed as a wheel).\n\n'
            'The --provider flag locks the model field in the generated '
            'agent frontmatter to a specific provider (claude / copilot / '
            'glm). Without --provider, the model field is omitted and the '
            "user picks at the tool's runtime."
        ),
        epilog=(
            'Flags (forwarded to orquestrum.core.convert):\n'
            '  --all                       Generate all supported tools\n'
            '  --tool TOOL                 Generate one tool (claude-code | opencode)\n'
            '  --provider PROVIDER         Lock model: claude | copilot | glm\n'
            '  --dry-run                   Print what would be written, no file changes\n'
            '\n'
            'Examples:\n'
            '  orquestrum convert --all                            # both tools, no provider lock\n'
            '  orquestrum convert --tool claude-code               # only claude-code\n'
            '  orquestrum convert --all --provider claude          # lock to anthropic models\n'
            '  orquestrum convert --tool opencode --provider glm   # opencode + zai models\n'
            '  orquestrum convert --all --dry-run                  # preview without writing\n'
            '\n'
            'See also:\n'
            '  orquestrum install --help    Install a generated package into a project\n'
            '  orquestrum lint --help       Validate canonical sources before convert'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=True,
    )

    p.set_defaults(handler=_handler)


def _handler(args: argparse.Namespace) -> int | None:
    from orquestrum.core.convert import main as wrapped
    wrapped(args.passthrough or [])
    return 0
