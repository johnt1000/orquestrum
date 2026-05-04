"""orquestrum doctor — environment health-check.

Runs a series of read-only checks and prints a colored report. Exits 0 when
everything is green; exits 1 if any required check fails. Warnings (yellow)
do not affect the exit code.
"""
from __future__ import annotations
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

GREEN  = '\033[0;32m'
RED    = '\033[0;31m'
YELLOW = '\033[1;33m'
BLUE   = '\033[0;34m'
DIM    = '\033[2m'
NC     = '\033[0m'


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        'doctor',
        help='Diagnose the local environment (python, uv, extras, integrations).',
        description=(
            'Run a battery of read-only health checks and print a colored '
            'report. Five sections:\n\n'
            '  Runtime         — python ≥ 3.10, uv, install method\n'
            '  Optional extras — ui, webview\n'
            '  Framework       — SDD source assets, integration cache, registry\n'
            '  Current dir     — whether cwd is a linked orquestrum project\n\n'
            'Exit code 0 = green; exit 1 = at least one error. Warnings '
            'never affect the exit code. Use --json for a machine-readable '
            'summary that CI / scripts can parse.'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            'Examples:\n'
            '  orquestrum doctor              # full check (colored output)\n'
            '  orquestrum doctor --json       # machine-readable JSON summary\n'
            '  orquestrum doctor || echo failed   # use exit code in scripts\n'
            '\n'
            'See also:\n'
            '  orquestrum extras --help       Install missing extras\n'
            '  orquestrum repos list          Inspect registered projects'
        ),
    )
    p.add_argument('--json', action='store_true', dest='as_json',
                   help='Emit a machine-readable JSON summary on stdout')
    p.set_defaults(handler=_handler)


# ─── reporter ─────────────────────────────────────────────────────────────────

class Report:
    def __init__(self) -> None:
        self.errors = 0
        self.warnings = 0
        self.results: list[dict] = []

    def ok(self, label: str, detail: str = '') -> None:
        self.results.append({'status': 'ok', 'label': label, 'detail': detail})
        line = f'  {GREEN}✓{NC} {label}'
        if detail:
            line += f' {DIM}({detail}){NC}'
        print(line)

    def fail(self, label: str, detail: str = '', fix: str = '') -> None:
        self.errors += 1
        self.results.append({'status': 'fail', 'label': label, 'detail': detail, 'fix': fix})
        print(f'  {RED}✗{NC} {label}' + (f' {DIM}— {detail}{NC}' if detail else ''))
        if fix:
            print(f'    {DIM}fix:{NC} {fix}')

    def warn(self, label: str, detail: str = '', fix: str = '') -> None:
        self.warnings += 1
        self.results.append({'status': 'warn', 'label': label, 'detail': detail, 'fix': fix})
        print(f'  {YELLOW}!{NC} {label}' + (f' {DIM}— {detail}{NC}' if detail else ''))
        if fix:
            print(f'    {DIM}fix:{NC} {fix}')

    def section(self, title: str) -> None:
        print()
        print(f'{BLUE}=== {title} ==={NC}')


# ─── individual checks ────────────────────────────────────────────────────────

def _check_python(r: Report) -> None:
    major, minor = sys.version_info[:2]
    version = f'{major}.{minor}.{sys.version_info.micro}'
    if (major, minor) >= (3, 10):
        r.ok('python ≥ 3.10', detail=version)
    else:
        r.fail('python ≥ 3.10', detail=version,
               fix='install Python 3.10+ (pyenv, brew, or asdf)')


def _check_uv(r: Report) -> None:
    uv_path = shutil.which('uv')
    if not uv_path:
        r.fail('uv installed', fix='curl -LsSf https://astral.sh/uv/install.sh | sh')
        return
    try:
        out = subprocess.run([uv_path, '--version'], capture_output=True, text=True, timeout=5)
        ver = out.stdout.strip() or out.stderr.strip()
    except Exception:
        ver = uv_path
    r.ok('uv installed', detail=ver)


def _check_orquestrum_install(r: Report) -> None:
    """Detect how the orquestrum CLI is installed (uv-tool / venv / unknown)."""
    from orquestrum.commands.extras import _detect_env
    mode = _detect_env()
    if mode == 'uv-tool':
        r.ok('orquestrum install method', detail='uv tool (recommended)')
    elif mode == 'venv':
        r.ok('orquestrum install method', detail='editable venv (development)')
    else:
        r.warn('orquestrum install method', detail='unknown',
               fix='uv tool install --editable . (from repo) or pip install orquestrum')


def _check_extras(r: Report) -> None:
    from orquestrum.commands.extras import _EXTRAS, _is_installed
    for name in _EXTRAS:
        if _is_installed(name):
            r.ok(f'extra: {name}', detail='installed')
        else:
            # webview is opt-in; ui is needed for `orquestrum web`
            if name == 'ui':
                r.warn(f'extra: {name}', detail='missing (needed for `orquestrum web`)',
                       fix=f'orquestrum extras install {name}')
            else:
                r.warn(f'extra: {name}', detail='missing (optional)',
                       fix=f'orquestrum extras install {name}')


def _check_integrations(r: Report) -> None:
    from orquestrum.lib.paths import (
        canonical_assets_root, convert_output_root, is_dev_mode,
    )

    # Surface which source the CLI is reading from — bundled vs. dev repo.
    source = canonical_assets_root()
    mode = 'dev repo' if is_dev_mode() else 'bundled (wheel)'
    r.ok('SDD source assets', detail=f'{mode} — {source}')

    integrations_dir = convert_output_root()
    if not integrations_dir.is_dir():
        r.warn('integration cache', detail=f'missing — {integrations_dir}',
               fix='orquestrum convert --all')
        return
    expected = {'claude-code', 'opencode'}
    found = {p.name for p in integrations_dir.iterdir() if p.is_dir()}
    missing = expected - found
    label = f'integration cache ({integrations_dir})'
    if missing:
        r.warn(label, detail=f'missing: {sorted(missing)}',
               fix='orquestrum convert --all')
    else:
        r.ok(label, detail=f'{len(found)} tools')


def _check_registry(r: Report) -> None:
    try:
        from orquestrum.lib import registry
        projects = registry.load_registry()
    except Exception as e:
        r.warn('project registry', detail=f'unreadable: {e}',
               fix='check ~/.orquestrum/registry.toml syntax')
        return
    if not projects:
        r.ok('project registry', detail='empty (no projects yet)')
        return
    stale = [p for p in projects if not Path(p.get('path', '')).is_dir()]
    if stale:
        names = ', '.join(p.get('name', '?') for p in stale)
        r.warn('project registry', detail=f'{len(stale)} stale entries: {names}',
               fix='orquestrum repos prune')
    else:
        r.ok('project registry', detail=f'{len(projects)} project(s), all paths valid')


def _check_current_project(r: Report) -> None:
    """If cwd looks like an Orquestrum-linked project, validate basic markers."""
    cwd = Path.cwd()
    orq_dir = cwd / '.orquestrum'
    manifest = cwd / 'ORQUESTRUM.md'
    if not orq_dir.is_dir() and not manifest.exists():
        r.ok('current directory', detail='not an Orquestrum project (skipped)')
        return
    if orq_dir.is_dir() and manifest.exists():
        r.ok('current Orquestrum project', detail=str(cwd))
    else:
        missing = []
        if not orq_dir.is_dir():
            missing.append('.orquestrum/')
        if not manifest.exists():
            missing.append('ORQUESTRUM.md')
        r.warn('current Orquestrum project', detail=f'incomplete (missing {", ".join(missing)})',
               fix='orquestrum init --tool <claude-code|opencode|...>')


# ─── handler ──────────────────────────────────────────────────────────────────

def _handler(args: argparse.Namespace) -> int:
    r = Report()

    r.section('Runtime')
    _check_python(r)
    _check_uv(r)
    _check_orquestrum_install(r)

    r.section('Optional extras')
    _check_extras(r)

    r.section('Framework artifacts')
    _check_integrations(r)
    _check_registry(r)

    r.section('Current directory')
    _check_current_project(r)

    print()
    if args.as_json:
        import json
        print(json.dumps({
            'errors': r.errors,
            'warnings': r.warnings,
            'results': r.results,
        }, indent=2))

    if r.errors:
        suffix = f', {r.warnings} warning(s)' if r.warnings else ''
        print(f'{RED}✗ {r.errors} error(s){NC}{suffix}')
        return 1

    suffix = f', {r.warnings} warning(s)' if r.warnings else ''
    print(f'{GREEN}✓ all required checks passed{NC}{suffix}')
    return 0
