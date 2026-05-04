"""orquestrum install → delegates to orquestrum/core/install.py.

Installs a previously-generated integration package (from `convert`)
into a target location. Three target patterns:

  - global Claude Code:  --target ~                   → ~/.claude/...
  - global OpenCode:     --target ~/.config/opencode  → that exact dir
  - project-scoped:      --target /path/to/project    → project/.claude or .opencode

Always merges into existing settings.json (never overwrites user keys).
"""
from __future__ import annotations
import argparse


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        'install',
        help='Install a generated integration package into a target.',
        description=(
            'Install a previously-generated integration package (output of '
            '`orquestrum convert`) into a target location. Designed to be '
            'idempotent and surgical: existing user settings, hooks, and '
            'MCP servers are preserved; only the orquestrum-owned entries '
            'get added or replaced.\n\n'
            'Target patterns:\n'
            '  --target ~                          → global Claude Code (~/.claude/)\n'
            '  --target ~/.config/opencode         → global OpenCode\n'
            '  --target /path/to/project           → project-scoped\n\n'
            'Use `--auto` to detect installed tools at the target and '
            'install matching integrations without specifying --tool.'
        ),
        epilog=(
            'Flags (forwarded to orquestrum.core.install):\n'
            '  --tool TOOL          claude-code | opencode\n'
            '  --auto               Auto-detect tools at the target\n'
            '  --target PATH        Install destination (required)\n'
            '  --force              Overwrite existing files (use with care)\n'
            '\n'
            'Examples:\n'
            '  orquestrum install --tool claude-code --target ~                    # global claude-code\n'
            '  orquestrum install --tool opencode --target ~/.config/opencode      # global opencode\n'
            '  orquestrum install --auto --target /path/to/project                 # detect tools\n'
            '  orquestrum install --tool claude-code --target ./project --force    # force project install\n'
            '\n'
            'See also:\n'
            '  orquestrum setup --help        # Wizard that orchestrates convert + install\n'
            '  orquestrum convert --help      # Generate the package this command installs\n'
            '  orquestrum uninstall --help    # Surgical removal via persistent manifest'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=True,
    )

    p.set_defaults(handler=_handler)


def _handler(args: argparse.Namespace) -> int | None:
    from orquestrum.core.install import main as wrapped
    wrapped(args.passthrough or [])
    return 0
