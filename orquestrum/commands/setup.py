"""orquestrum setup — first-time wizard for global framework installation.

Distinct from `orquestrum init`:

  - `init`  is project-scoped: connects ONE repo to the framework
            (metrics, MCP) by writing <project>/.orquestrum/. Optional.
  - `setup` is global: installs the framework itself
            (agents/skills/hooks/MCP) under ~/.claude/ or
            ~/.config/opencode/. Independent of any project.

The wizard detects what's already globally installed (via the manifest
at `~/.orquestrum/installs.json`) and asks only about what's missing or
could be updated. `--yes` skips prompts and uses safe defaults
(install claude-code; skip opencode).

Implementation reuses `core.convert.main` and `core.install.main` —
this module is pure orchestration over commands that already exist.
"""
from __future__ import annotations
import argparse
from pathlib import Path

from orquestrum.lib import prompts


_BOLD  = '\033[1m'
_GREEN = '\033[0;32m'
_RED   = '\033[0;31m'
_DIM   = '\033[2m'
_NC    = '\033[0m'


# ─── argparse registration ──────────────────────────────────────────────────


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        'setup',
        help='First-time wizard — installs framework globally on the system.',
        description=(
            'Install the orquestrum framework globally on your system: '
            'agents + skills land at `~/.claude/` (Claude Code) or '
            '`~/.config/opencode/` (OpenCode); the metrics hook + MCP '
            'server get registered in the matching settings.json.\n\n'
            'Distinct from `init`: `setup` is global and one-time per '
            'machine; `init` is per-project and optional. The wizard '
            'detects what is already installed and only asks about gaps.'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            'Examples:\n'
            '  orquestrum setup              # 3-prompt fast path (claude-code, opencode, ui)\n'
            '  orquestrum setup --advanced   # 9-prompt wizard (provider, extras, deps, MCPs)\n'
            '  orquestrum setup --yes        # silent: install claude-code + ui, skip opencode\n'
            '\n'
            'See also:\n'
            '  orquestrum init --help         Per-project bootstrap (run after setup)\n'
            '  orquestrum extras --help       Manage optional UI / webview extras\n'
            '  orquestrum mcp --help          MCP servers (list / add / remove)\n'
            '  orquestrum doctor --help       Verify the install is healthy'
        ),
    )
    p.add_argument('-y', '--yes', '--non-interactive',
                   dest='non_interactive', action='store_true',
                   help='Accept defaults without asking. Defaults: install '
                        'claude-code + ui, skip opencode.')
    p.add_argument('--advanced', action='store_true',
                   help='Run the full 9-prompt wizard (provider, extras, '
                        'deps, MCP servers). Default is the 3-prompt fast '
                        'path. Combine with --yes for silent advanced setup.')
    p.set_defaults(handler=_handler)


def _handler(args: argparse.Namespace) -> int:
    # `advanced` defaults to False so callers (tests, programmatic dispatch)
    # don't need to set it explicitly when only --yes matters.
    if getattr(args, 'advanced', False):
        return _run_setup_advanced(interactive=not args.non_interactive)
    return _run_setup(interactive=not args.non_interactive)


# ─── state detection ────────────────────────────────────────────────────────


def _claude_code_target() -> Path:
    return Path.home()


def _opencode_target() -> Path:
    return Path.home() / '.config' / 'opencode'


def _detect_state() -> dict:
    """Return what's currently installed, keyed by tool name. Reads from
    `~/.orquestrum/installs.json` (the manifest written by `install_tool`)
    so detection is exact rather than heuristic."""
    from orquestrum.lib import installs_manifest

    state: dict[str, dict] = {
        'claude-code': {'installed': False,
                        'target':    _claude_code_target()},
        'opencode':    {'installed': False,
                        'target':    _opencode_target()},
    }

    cc_target = str(_claude_code_target().resolve())
    oc_target = str(_opencode_target().resolve())

    for record in installs_manifest.list_installs():
        if record.tool == 'claude-code' and record.target == cc_target:
            state['claude-code'] = {
                'installed': True,
                'target':    Path(record.target),
                'version':   record.orquestrum_version,
                'files':     len(record.files),
                'installed_at': record.installed_at,
            }
        elif record.tool == 'opencode' and record.target == oc_target:
            state['opencode'] = {
                'installed': True,
                'target':    Path(record.target),
                'version':   record.orquestrum_version,
                'files':     len(record.files),
                'installed_at': record.installed_at,
            }
    return state


def _print_detected(state: dict) -> None:
    print(f'{_BOLD}Detected:{_NC}')
    for tool, info in state.items():
        if info['installed']:
            print(
                f'  {_GREEN}✓{_NC} {tool:<12} {info["target"]}  '
                f'{_DIM}v{info["version"]} '
                f'({info["files"]} files){_NC}'
            )
        else:
            print(
                f'  {_RED}✗{_NC} {tool:<12} {info["target"]}  '
                f'{_DIM}not installed{_NC}'
            )
    print()


# ─── wizard ────────────────────────────────────────────────────────────────


def _install_one(tool: str, target: Path, *, provider: str | None = None) -> bool:
    """Run convert (if cache missing) + install for one tool. Returns True
    on success; logs errors to stderr but never raises."""
    from orquestrum.core.convert import main as convert_main
    from orquestrum.core.install import main as install_main
    from orquestrum.lib.paths import convert_output_root

    cache_dir = convert_output_root() / tool
    if not cache_dir.is_dir():
        print(f'  {_DIM}→ orquestrum convert --tool {tool}'
              + (f' --provider {provider}' if provider else '') + f'{_NC}')
        argv = ['--tool', tool]
        if provider:
            argv += ['--provider', provider]
        try:
            convert_main(argv)
        except SystemExit as e:
            if e.code not in (None, 0):
                return False

    target.mkdir(parents=True, exist_ok=True)
    print(f'  {_DIM}→ orquestrum install --tool {tool} '
          f'--target {target}{_NC}')
    try:
        install_main(['--tool', tool, '--target', str(target)])
    except SystemExit as e:
        if e.code not in (None, 0):
            return False
    return True


def _ui_extra_installed() -> bool:
    """Check whether the `ui` extra (FastAPI + Uvicorn) is importable —
    same probe `extras.py` uses for the `ui` extra."""
    try:
        __import__('fastapi')
        return True
    except ImportError:
        return False


def _install_ui_extra() -> bool:
    """Delegate to `extras install ui`. Returns True on success."""
    from orquestrum.commands.extras import _install
    return _install(['ui']) == 0


def _run_setup(*, interactive: bool) -> int:
    print(f'{_BOLD}Welcome to orquestrum setup.{_NC}')
    print('This wizard installs the framework globally on your system.')
    print('Project-specific config lives elsewhere — see `orquestrum init`.')
    print()

    state = _detect_state()
    _print_detected(state)

    cc_installed = state['claude-code']['installed']
    oc_installed = state['opencode']['installed']
    ui_installed = _ui_extra_installed()

    cc_question = (
        '[1/3] Install Claude Code integration?'
        if not cc_installed else
        '[1/3] Update Claude Code integration?'
    )
    install_cc = prompts.ask_yn(
        cc_question,
        default=not cc_installed,   # default Y for fresh installs, N for re-runs
        interactive=interactive,
    )

    oc_question = (
        '[2/3] Install OpenCode integration?'
        if not oc_installed else
        '[2/3] Update OpenCode integration?'
    )
    install_oc = prompts.ask_yn(
        oc_question,
        default=False,   # opencode always defaults to NO (less common)
        interactive=interactive,
    )

    ui_question = (
        '[3/3] Enable web dashboard? (orquestrum web)'
        if not ui_installed else
        '[3/3] Re-install ui extras (already installed)?'
    )
    install_ui = prompts.ask_yn(
        ui_question,
        # Default Y for fresh installs (UI is highly visible/useful);
        # default N when already installed (no reason to re-run pip).
        default=not ui_installed,
        interactive=interactive,
    )

    if not install_cc and not install_oc and not install_ui:
        print()
        print(f'{_DIM}No changes selected. Re-run setup whenever you want.{_NC}')
        _print_next_steps(cc_installed_now=cc_installed, ui_installed_now=ui_installed)
        return 0

    print()
    print(f'{_BOLD}Running:{_NC}')
    rc = 0
    if install_cc:
        ok = _install_one('claude-code', _claude_code_target(), provider='claude')
        if not ok:
            rc = 1
            print(f'  {_RED}✗ claude-code: install reported errors above{_NC}')
    if install_oc:
        ok = _install_one('opencode', _opencode_target(), provider='claude')
        if not ok:
            rc = 1
            print(f'  {_RED}✗ opencode: install reported errors above{_NC}')
    if install_ui:
        print(f'  {_DIM}→ orquestrum extras install ui{_NC}')
        ok = _install_ui_extra()
        if not ok:
            rc = 1
            print(f'  {_RED}✗ ui extra: install reported errors above{_NC}')

    print()
    if rc == 0:
        print(f'{_GREEN}✓ Setup complete.{_NC}')
        cc_now = cc_installed or install_cc
        ui_now = ui_installed or install_ui
        _print_next_steps(cc_installed_now=cc_now, ui_installed_now=ui_now)
    else:
        print(f'{_RED}✗ Setup completed with errors above.{_NC} '
              'Inspect output and re-run.')
    return rc


def _print_next_steps(*, cc_installed_now: bool, ui_installed_now: bool) -> None:
    """Always mention `orquestrum web` so users discover the dashboard
    even if they declined the UI extra during setup."""
    print()
    print('Next steps:')
    if cc_installed_now:
        print('  • Restart Claude Code (it picks up new agents on launch)')
    if ui_installed_now:
        print('  • View dashboard:    orquestrum web')
    else:
        print('  • Web dashboard:     orquestrum extras install ui  (then `orquestrum web`)')
    print('  • Connect a project: orquestrum init --yes')
    print('  • Try in Claude:     @"Helm - The Architect" qual o status do projeto?')


# ─── Advanced wizard ───────────────────────────────────────────────────────


def _run_setup_advanced(*, interactive: bool) -> int:
    """Full 9-prompt wizard: Core + Extras + Deps + MCPs. Each section
    is delegated to setup_sections.* so this function stays as pure
    orchestration."""
    from orquestrum.commands import setup_sections as sections

    print(f'{_BOLD}Welcome to orquestrum setup (advanced mode).{_NC}')
    print('Configures the framework + integrations + extras + MCPs in a single pass.')
    print()

    state = _detect_state()
    _print_detected(state)

    core = sections.section_core(interactive=interactive, state=state)
    extras = sections.section_extras(interactive=interactive)
    deps = sections.section_deps(interactive=interactive)

    cc_target = _claude_code_target()
    oc_target = _opencode_target()
    mcp_to_add = sections.section_mcp(interactive=interactive, target=cc_target)
    mirror_oc = sections.section_opencode_mcp(
        interactive=interactive,
        opencode_being_installed=core['install_oc'],
    )

    nothing = (
        not core['install_cc'] and not core['install_oc']
        and not extras['install_ui'] and not extras['install_webview']
        and not deps['install_agency'] and not deps['install_skills']
        and not mcp_to_add and not mirror_oc
    )
    if nothing:
        print()
        print(f'{_DIM}No changes selected. Re-run setup whenever you want.{_NC}')
        _print_next_steps(
            cc_installed_now=state['claude-code']['installed'],
            ui_installed_now=_ui_extra_installed(),
        )
        return 0

    print()
    print(f'{_BOLD}Running:{_NC}')
    rc = 0

    # ── Core ──
    if core['install_cc']:
        ok = _install_one('claude-code', cc_target, provider=core['provider'])
        if not ok:
            rc = 1
            print(f'  {_RED}✗ claude-code: install reported errors above{_NC}')
    if core['install_oc']:
        ok = _install_one('opencode', oc_target, provider=core['provider'])
        if not ok:
            rc = 1
            print(f'  {_RED}✗ opencode: install reported errors above{_NC}')

    # ── Extras ──
    if extras['install_ui']:
        print(f'  {_DIM}→ orquestrum extras install ui{_NC}')
        from orquestrum.commands.extras import _install as _install_extras
        if _install_extras(['ui']) != 0:
            rc = 1
            print(f'  {_RED}✗ ui extras: install reported errors above{_NC}')
    if extras['install_webview']:
        print(f'  {_DIM}→ orquestrum extras install webview{_NC}')
        from orquestrum.commands.extras import _install as _install_extras
        if _install_extras(['webview']) != 0:
            rc = 1
            print(f'  {_RED}✗ webview extras: install reported errors above{_NC}')

    # ── Deps ──
    if deps['install_agency']:
        print(f'  {_DIM}→ orquestrum deps --only agency --target {cc_target}{_NC}')
        from orquestrum.core.deps import main as deps_main
        try:
            deps_main(['--target', str(cc_target), '--only', 'agency'])
        except SystemExit as e:
            if e.code not in (None, 0):
                rc = 1
                print(f'  {_RED}✗ agency-agents: install reported errors above{_NC}')
    if deps['install_skills']:
        print(f'  {_DIM}→ orquestrum deps --only skills --target {cc_target}{_NC}')
        from orquestrum.core.deps import main as deps_main
        try:
            deps_main(['--target', str(cc_target), '--only', 'skills'])
        except SystemExit as e:
            if e.code not in (None, 0):
                rc = 1
                print(f'  {_RED}✗ anthropics/skills: install reported errors above{_NC}')

    # ── MCP servers ──
    if mcp_to_add:
        from orquestrum.commands import mcp as mcp_cmd
        for entry in mcp_to_add:
            cmd_str = entry['command'] + ' ' + ' '.join(entry['args'])
            print(f'  {_DIM}→ orquestrum mcp add {entry["name"]} (command: {cmd_str}){_NC}')
            ns = argparse.Namespace(
                name=entry['name'],
                command=entry['command'],
                args=entry['args'],
                server_type=entry['server_type'],
                target=str(cc_target),
            )
            if mcp_cmd._add(ns) != 0:
                rc = 1
                print(f'  {_RED}✗ mcp add {entry["name"]}: failed{_NC}')

    if mirror_oc:
        print(f'  {_DIM}(opencode MCP mirror not yet implemented — skipping){_NC}')

    print()
    if rc == 0:
        print(f'{_GREEN}✓ Setup complete.{_NC}')
        _print_next_steps(
            cc_installed_now=state['claude-code']['installed'] or core['install_cc'],
            ui_installed_now=_ui_extra_installed() or extras['install_ui'],
        )
    else:
        print(f'{_RED}✗ Setup completed with errors above.{_NC} '
              'Inspect output and re-run.')
    return rc
