"""Section helpers for `orquestrum setup --advanced`.

The fast `_run_setup()` in setup.py asks 3 questions and is intentionally
minimal. The advanced wizard groups questions into 4 sections:

  Core    — claude-code, opencode, provider lock
  Extras  — ui, webview
  Deps    — agency-agents, anthropics/skills
  MCP     — list current + offer common third-party servers

Each section is a small function that uses `prompts.ask_yn`/`ask_choice`
directly and delegates the actual install to existing commands
(`extras._install`, `deps.main`, `mcp_cmd._add`). No new install logic.

The functions return a dict that `_run_setup_advanced` aggregates into
a single "Running:" report at the end.
"""
from __future__ import annotations
from pathlib import Path
from typing import Any

from orquestrum.lib import prompts


_BOLD = '\033[1m'
_DIM  = '\033[2m'
_NC   = '\033[0m'


# ─── Section: Core ─────────────────────────────────────────────────────────


def section_core(*, interactive: bool, state: dict) -> dict[str, Any]:
    """Prompt for claude-code + opencode + provider. Returns the user's
    choices; caller dispatches the installs. Numbering [1/9]..[3/9]."""
    print()
    print(f'{_BOLD}=== Core ==={_NC}')

    cc_installed = state['claude-code']['installed']
    oc_installed = state['opencode']['installed']

    install_cc = prompts.ask_yn(
        '[1/9] Install Claude Code integration?'
        if not cc_installed
        else '[1/9] Update Claude Code integration?',
        default=not cc_installed,
        interactive=interactive,
    )
    install_oc = prompts.ask_yn(
        '[2/9] Install OpenCode integration?'
        if not oc_installed
        else '[2/9] Update OpenCode integration?',
        default=False,
        interactive=interactive,
    )
    provider = prompts.ask_choice(
        '[3/9] Default provider for new installs?',
        [
            ('c', 'claude    — anthropic models (recommended)'),
            ('g', 'glm       — zai-coding-plan models'),
            ('o', 'copilot   — github-copilot models'),
        ],
        default='c',
        interactive=interactive,
    )
    provider_name = {'c': 'claude', 'g': 'glm', 'o': 'copilot'}[provider]
    return {
        'install_cc': install_cc,
        'install_oc': install_oc,
        'provider':   provider_name,
    }


# ─── Section: Extras ───────────────────────────────────────────────────────


def section_extras(*, interactive: bool) -> dict[str, bool]:
    """Prompt for ui + webview. Numbering [4/9]..[5/9]."""
    print()
    print(f'{_BOLD}=== UI / Extras ==={_NC}')

    install_ui = prompts.ask_yn(
        '[4/9] Enable web dashboard? (`ui` extras: FastAPI + Uvicorn)',
        default=True,
        interactive=interactive,
    )
    install_webview = prompts.ask_yn(
        '[5/9] Install `webview` extras (native window via pywebview)?',
        default=False,
        interactive=interactive,
    )
    return {'install_ui': install_ui, 'install_webview': install_webview}


# ─── Section: External deps ────────────────────────────────────────────────


def section_deps(*, interactive: bool) -> dict[str, bool]:
    """Prompt for agency-agents + anthropics/skills. Numbering [6/9]..[7/9]."""
    print()
    print(f'{_BOLD}=== External dependencies ==={_NC}')

    install_agency = prompts.ask_yn(
        '[6/9] Install agency-agents (~184 specialist agents)?',
        default=False,
        interactive=interactive,
    )
    install_skills = prompts.ask_yn(
        '[7/9] Install anthropics/skills (17 skills incl. supabase)?',
        default=False,
        interactive=interactive,
    )
    return {'install_agency': install_agency, 'install_skills': install_skills}


# ─── Section: MCP servers ──────────────────────────────────────────────────


# Common MCPs we know about. Each entry: (key, label, command, args, hint)
_COMMON_MCPS: list[tuple[str, str, str, list[str], str]] = [
    ('filesystem',
     'Add filesystem MCP (gives agents file access)?',
     'npx', ['-y', '@modelcontextprotocol/server-filesystem'],
     'Path to expose'),
    ('github',
     'Add github MCP (gives agents GitHub API access)?',
     'npx', ['-y', '@modelcontextprotocol/server-github'],
     ''),
    ('postgres',
     'Add postgres MCP (database access)?',
     'npx', ['-y', '@modelcontextprotocol/server-postgres'],
     'Connection URL'),
]


def section_mcp(*, interactive: bool, target: Path) -> list[dict[str, Any]]:
    """Prompt to manage MCP servers. Lists current + offers common
    third-party MCPs. Returns a list of `mcp add` arg-dicts the caller
    will invoke. Numbering [8/9].

    `target` is the directory whose `.claude/settings.json` we'll edit.
    """
    print()
    print(f'{_BOLD}=== MCP servers ==={_NC}')

    manage = prompts.ask_yn(
        f'[8/9] Manage MCP servers in {target}/.claude/settings.json?',
        default=True,
        interactive=interactive,
    )
    if not manage:
        return []

    # Show current state
    from orquestrum.lib import settings_io
    settings_path = target / '.claude' / 'settings.json'
    settings = settings_io.load_claude_settings(settings_path)
    current = settings_io.list_mcp_servers(settings)
    print()
    print('  Currently registered:')
    if not current:
        print(f'    {_DIM}(none){_NC}')
    else:
        for name in sorted(current):
            entry = current[name]
            cmd = entry.get('command', '?')
            print(f'    ✓ {name:<14} {cmd}')

    # Offer common MCPs (each defaults N — opt-in)
    print()
    print('  Common MCPs (skip any with [n]):')
    to_add: list[dict[str, Any]] = []
    for key, question, cmd, args, hint in _COMMON_MCPS:
        if key in current:
            print(f'    {_DIM}(already registered: {key} — skipping){_NC}')
            continue
        if not prompts.ask_yn(f'    {question}', default=False,
                              interactive=interactive):
            continue
        # If the MCP needs a path/URL argument, prompt for it
        extra_arg = None
        if hint:
            default_value = '/tmp' if key == 'filesystem' else ''
            extra_arg = prompts.ask_text(
                f'      {hint}',
                default=default_value,
                interactive=interactive,
            )
        full_args = list(args) + ([extra_arg] if extra_arg else [])
        to_add.append({
            'name': key,
            'command': cmd,
            'args': full_args,
            'server_type': 'stdio',
        })
    return to_add


# ─── Section: OpenCode MCP (conditional) ───────────────────────────────────


def section_opencode_mcp(
    *, interactive: bool, opencode_being_installed: bool,
) -> bool:
    """Ask whether to mirror MCP setup into OpenCode config too. Only
    relevant when OpenCode was selected in the Core section. Numbering
    [9/9]. Returns True if user wants the same MCP setup mirrored.

    NOTE: OpenCode config lives at ~/.config/opencode/config.json (or
    similar). Actual mirror logic is out of scope for this section —
    we just collect intent here. Future work.
    """
    if not opencode_being_installed:
        return False
    print()
    return prompts.ask_yn(
        '[9/9] Mirror MCP setup to OpenCode (~/.config/opencode/config.json)?',
        default=False,
        interactive=interactive,
    )
