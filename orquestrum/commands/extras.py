"""orquestrum extras — list and install optional dependency groups."""
from __future__ import annotations
import argparse
import subprocess
import sys

_EXTRAS: dict[str, dict] = {
    'ui': {
        'description': 'Web console (FastAPI, Uvicorn, Jinja2, Mistune)',
        'check': 'fastapi',
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
        'check': 'webview',
        'packages': ['pywebview>=5.0'],
        'system_hint': {
            'linux': (
                'sudo apt install libwebkit2gtk-4.0-dev   # Debian/Ubuntu\n'
                '  sudo dnf install webkit2gtk4.0-devel   # Fedora/RHEL'
            ),
        },
    },
}


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser('extras', help='List and install optional extras (ui, webview).')
    sub2 = p.add_subparsers(dest='extras_cmd')
    install_p = sub2.add_parser('install', help='Install one or more extras.')
    install_p.add_argument('names', nargs='+', choices=list(_EXTRAS),
                           metavar='EXTRA', help=f'Extra(s) to install: {", ".join(_EXTRAS)}')
    p.set_defaults(handler=_handler)


def _handler(args: argparse.Namespace) -> int:
    if args.extras_cmd == 'install':
        return _install(args.names)
    return _list()


def _is_installed(extra: str) -> bool:
    check = _EXTRAS[extra]['check']
    try:
        __import__(check)
        return True
    except ImportError:
        return False


def _list() -> int:
    print('Available extras:')
    for name, meta in _EXTRAS.items():
        status = 'installed' if _is_installed(name) else 'missing '
        print(f'  {name:<10} [{status}]   {meta["description"]}')
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
