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
        help=('First-time wizard. Installs orquestrum integrations '
              '(agents, skills, hooks, MCP server) globally on the system. '
              'Asks before each action; --yes accepts safe defaults silently.'),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            'Examples:\n'
            '  orquestrum setup           # interactive wizard\n'
            '  orquestrum setup --yes     # accept defaults (install claude-code, '
            'skip opencode)\n'
            '\n'
            'Global installs land at ~/.claude/ (Claude Code) and '
            '~/.config/opencode/ (OpenCode). Project-specific config is '
            'separate — see `orquestrum init`.'
        ),
    )
    p.add_argument('-y', '--yes', '--non-interactive',
                   dest='non_interactive', action='store_true',
                   help='Accept defaults without asking. Defaults: install '
                        'claude-code if missing; skip opencode.')
    p.set_defaults(handler=_handler)


def _handler(args: argparse.Namespace) -> int:
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


def _run_setup(*, interactive: bool) -> int:
    print(f'{_BOLD}Welcome to orquestrum setup.{_NC}')
    print('This wizard installs the framework globally on your system.')
    print('Project-specific config lives elsewhere — see `orquestrum init`.')
    print()

    state = _detect_state()
    _print_detected(state)

    cc_installed = state['claude-code']['installed']
    oc_installed = state['opencode']['installed']

    cc_question = (
        '[1/2] Install Claude Code integration?'
        if not cc_installed else
        '[1/2] Update Claude Code integration?'
    )
    install_cc = prompts.ask_yn(
        cc_question,
        default=not cc_installed,   # default Y for fresh installs, N for re-runs
        interactive=interactive,
    )

    oc_question = (
        '[2/2] Install OpenCode integration?'
        if not oc_installed else
        '[2/2] Update OpenCode integration?'
    )
    install_oc = prompts.ask_yn(
        oc_question,
        default=False,   # opencode always defaults to NO (less common)
        interactive=interactive,
    )

    if not install_cc and not install_oc:
        print()
        print(f'{_DIM}No changes selected. Re-run setup whenever you want.{_NC}')
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

    print()
    if rc == 0:
        print(f'{_GREEN}✓ Setup complete.{_NC}')
        print()
        print('Next steps:')
        if install_cc:
            print('  • Restart Claude Code (it picks up new agents on launch)')
        print('  • In any project:  orquestrum init --yes')
        print('  • Try in Claude:   @"Helm - The Architect" qual o status do projeto?')
    else:
        print(f'{_RED}✗ Setup completed with errors above.{_NC} '
              'Inspect output and re-run.')
    return rc
