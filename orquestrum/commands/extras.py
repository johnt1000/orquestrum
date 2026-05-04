"""orquestrum extras — list and install optional dependency groups."""
from __future__ import annotations
import argparse
import subprocess
import sys

# Each extra lists the PyPI packages it installs AND the actual import names
# used to verify the install. Package name ≠ import name (`python-multipart`
# imports as `multipart`; `uvicorn[standard]` is just `uvicorn`), so we keep
# both lists explicit. `check_modules` MUST cover every runtime-required
# import — partial installs (e.g. fastapi present but jinja2 missing after
# a failed install) are detected because ALL modules must import.
_EXTRAS: dict[str, dict] = {
    'ui': {
        'description': 'Web console (FastAPI, Uvicorn, Jinja2, Mistune)',
        'check_modules': [
            'fastapi', 'uvicorn', 'jinja2', 'mistune', 'watchfiles', 'multipart',
        ],
        'packages': [
            'fastapi>=0.115',
            'uvicorn[standard]>=0.32',
            'jinja2>=3.1',
            'mistune>=3.0',
            'watchfiles>=0.24',
            'python-multipart>=0.0.20',
        ],
        'system_hint': {},
    },
    'webview': {
        'description': 'App window mode (pywebview — WKWebView / WebView2 / WebKit2GTK)',
        'check_modules': ['webview'],
        'packages': ['pywebview>=5.0'],
        'system_hint': {
            'linux': (
                'sudo apt install libwebkit2gtk-4.0-dev   # Debian/Ubuntu\n'
                '  sudo dnf install webkit2gtk4.0-devel   # Fedora/RHEL'
            ),
        },
    },
}

# Friendly aliases. Users naturally call the web dashboard extra `web`
# (because the command is `orquestrum web`). Resolve aliases at the entry
# point so the rest of the module operates on canonical names.
_ALIASES: dict[str, str] = {
    'web': 'ui',
}


def _resolve(name: str) -> str:
    """Return the canonical extra name for a possibly-aliased input.
    Returns the input unchanged when no alias matches."""
    return _ALIASES.get(name, name)


def _all_choices() -> list[str]:
    """Choices argparse accepts: canonical names + aliases."""
    return list(_EXTRAS) + list(_ALIASES)


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        'extras',
        help='List and install optional dependency groups (ui, webview).',
        description=(
            'Manage optional dependency groups (a.k.a. "extras") that '
            'enable additional orquestrum features without bloating the '
            'core install.\n\n'
            'Available extras:\n'
            '  ui (alias: web)  Web dashboard (FastAPI + Uvicorn + Jinja2 + Mistune)\n'
            '                   Required by: `orquestrum web`\n'
            '  webview          Native window (pywebview — WKWebView / WebView2 / WebKit2GTK)\n'
            '                   Required by: `orquestrum web` in window mode\n\n'
            'No subcommand → list state of all extras (installed/missing).\n'
            'Auto-detects install method (uv tool / venv / pip) and runs '
            'the matching command. Linux webview prints apt/dnf system-package '
            'hints since pywebview needs WebKit2GTK.'
        ),
        epilog=(
            'Examples:\n'
            '  orquestrum extras                          # list state of all extras\n'
            '  orquestrum extras install ui               # web dashboard (canonical)\n'
            '  orquestrum extras install web              # same — `web` is an alias for `ui`\n'
            '  orquestrum extras install webview          # native window\n'
            '  orquestrum extras install ui webview       # both at once\n'
            '\n'
            'See also:\n'
            '  orquestrum web --help          Uses the `ui` extra\n'
            '  orquestrum doctor --help       Reports which extras are missing'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub2 = p.add_subparsers(dest='extras_cmd')
    install_p = sub2.add_parser(
        'install',
        help='Install one or more extras (ui, web, webview).',
        description=(
            'Install the named extras into the active orquestrum install. '
            '`web` resolves to `ui` (alias).'
        ),
        epilog=f'Example: orquestrum extras install {" ".join(_EXTRAS)}',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    install_p.add_argument(
        'names', nargs='+', choices=_all_choices(),
        metavar='EXTRA',
        help=f'Extra(s) to install: {", ".join(_EXTRAS)} '
             f'(aliases: {", ".join(_ALIASES)})',
    )
    p.set_defaults(handler=_handler)


def _handler(args: argparse.Namespace) -> int:
    if args.extras_cmd == 'install':
        # Resolve aliases before downstream lookup
        resolved = [_resolve(n) for n in args.names]
        # Dedup while preserving order (user could type `ui web` → just `ui`)
        seen: set[str] = set()
        canonical: list[str] = []
        for n in resolved:
            if n not in seen:
                seen.add(n)
                canonical.append(n)
        return _install(canonical)
    return _list()


def _is_installed(extra: str) -> bool:
    """True iff EVERY module listed in `check_modules` for this extra is
    importable. Catches partial installs where one of the deps failed
    silently and downstream features (e.g. `orquestrum web`) still
    crash on the missing one."""
    meta = _EXTRAS[extra]
    # Backward compat: older defs used a single `check` string. Prefer
    # `check_modules` but fall back to `check` if present.
    modules = meta.get('check_modules') or [meta.get('check')]
    for mod in modules:
        if not mod:
            continue
        try:
            __import__(mod)
        except ImportError:
            return False
    return True


def _list() -> int:
    print('Available extras:')
    for name, meta in _EXTRAS.items():
        status = 'installed' if _is_installed(name) else 'missing '
        alias_note = ''
        # Show aliases inline so users know `web` works
        aliases = [a for a, target in _ALIASES.items() if target == name]
        if aliases:
            alias_note = f'  (alias: {", ".join(aliases)})'
        print(f'  {name:<10} [{status}]   {meta["description"]}{alias_note}')
    print()
    missing = [n for n in _EXTRAS if not _is_installed(n)]
    if missing:
        print(f'To install: orquestrum extras install {" ".join(missing)}')
    else:
        print('All extras installed.')
    return 0


def _detect_env() -> str:
    """Detect the Python environment running this process.
    Returns 'uv-tool', 'venv', or 'unknown'.
    Uses sys.prefix (the active venv root) — reliable even when sys.executable
    resolves to a shared Homebrew/system python symlink.
    """
    import sys
    from pathlib import Path
    prefix = Path(sys.prefix).resolve()
    for uv_tools in (
        Path.home() / '.local' / 'share' / 'uv' / 'tools',
        Path.home() / 'Library' / 'Application Support' / 'uv' / 'tools',
    ):
        try:
            prefix.relative_to(uv_tools)
            return 'uv-tool'
        except ValueError:
            pass
    if (prefix / 'pyvenv.cfg').exists():
        return 'venv'
    return 'unknown'


def _install(names: list[str]) -> int:
    import platform

    mode = _detect_env()

    # Print Linux system hints for webview before attempting install
    if 'webview' in names and platform.system() == 'Linux':
        hint = _EXTRAS['webview']['system_hint'].get('linux', '')
        if hint:
            print('Linux prerequisite required for webview:')
            print(f'  {hint}')
            print('Install the system package above, then re-run this command.')
            print()

    if mode == 'venv':
        extra_args = []
        for name in names:
            extra_args += ['--extra', name]
        cmd = ['uv', 'sync'] + extra_args
        print(f'Running: {" ".join(cmd)}')
        result = subprocess.run(cmd)
        return result.returncode

    if mode == 'uv-tool':
        packages: list[str] = []
        for name in names:
            packages.extend(_EXTRAS[name]['packages'])
        with_args = []
        for pkg in packages:
            with_args += ['--with', pkg]
        cmd = ['uv', 'tool', 'install', 'orquestrum'] + with_args
        print(f'Running: {" ".join(cmd)}')
        result = subprocess.run(cmd)
        return result.returncode

    # Unknown / plain pip
    extras_str = ','.join(names)
    print('Could not detect install method automatically. Run one of:')
    print(f'  uv sync --extra {" --extra ".join(names)}')
    print(f'  pip install "orquestrum[{extras_str}]"')
    return 0
