"""orquestrum web — launch the local console (FastAPI + Uvicorn)."""
from __future__ import annotations
import argparse
import os
import sys
import webbrowser
from pathlib import Path


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        'web',
        help='Launch the local web console (live metrics + project state).',
        description=(
            'Start the local FastAPI + Uvicorn dashboard. Auto-detects '
            'whether you are in a project (shows live session/cost/budget '
            'for that project) or in the framework repo (shows registry of '
            'all projects + global stats). Use --mode to force one or the '
            'other.\n\n'
            'Requires the `ui` extra. If missing, the command fails with '
            'an actionable hint to run `orquestrum extras install ui`. '
            'For a windowed (native) experience instead of browser, also '
            'install the `webview` extra.'
        ),
        epilog=(
            'Examples:\n'
            '  orquestrum web                             # auto-detect, open browser\n'
            '  orquestrum web --mode project              # force project view\n'
            '  orquestrum web --mode framework            # force framework view\n'
            '  orquestrum web --port 7700                 # custom port\n'
            '  orquestrum web --no-browser                # server-only (curl/HTTPie)\n'
            '  orquestrum web --target /path/to/project   # web for a different project\n'
            '\n'
            'See also:\n'
            '  orquestrum dashboard --help    Static markdown/HTML snapshot\n'
            '  orquestrum extras install ui   Install the required extras'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument('--target', default=None,
                   help='Project / framework root (default: cwd or $ORQ_ROOT)')
    p.add_argument('--mode', choices=['project', 'framework', 'auto'], default='auto',
                   help='Force a specific mode (default: auto-detect)')
    p.add_argument('--port', type=int, default=None,
                   help='TCP port (default 7700 or $ORQ_PORT)')
    p.add_argument('--host', default='127.0.0.1',
                   help='Bind host (default 127.0.0.1; do NOT bind 0.0.0.0)')
    p.add_argument('--no-browser', action='store_true',
                   help='Disable automatic window/browser (server-only mode)')
    p.set_defaults(handler=_handler)


def _wait_ready(url: str, timeout: float = 10.0) -> bool:
    import time
    import urllib.request
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            urllib.request.urlopen(url + '/health', timeout=0.5)
            return True
        except Exception:
            time.sleep(0.1)
    return False


def _run_server_thread(app, host: str, port: int) -> None:
    import threading
    import uvicorn
    t = threading.Thread(
        target=uvicorn.run,
        kwargs=dict(app=app, host=host, port=port, log_level='info'),
        daemon=True,
    )
    t.start()


def _open_window(url: str, title: str = 'Orquestrum') -> None:
    import webview
    webview.create_window(title, url, width=1280, height=800, min_size=(800, 600))
    webview.start()


def _handler(args: argparse.Namespace) -> int | None:
    # Lazy imports — fastapi/uvicorn are optional [ui] deps
    try:
        import uvicorn
        from ui.config import resolve as resolve_config, DEFAULT_PORT
        from ui.server import create_app
    except ImportError as e:
        print('error: web console requires the [ui] extras. Run:', file=sys.stderr)
        print('       uv sync --extra ui                              (web console)', file=sys.stderr)
        print('       uv sync --extra ui --extra webview              (app window mode)', file=sys.stderr)
        print(f'       (missing: {e.name})', file=sys.stderr)
        return 2

    mode_arg = None if args.mode == 'auto' else args.mode
    try:
        config = resolve_config(mode_arg=mode_arg, root_arg=args.target, port_arg=args.port)
    except ValueError as e:
        print(f'config error: {e}', file=sys.stderr)
        return 2

    print('Orquestrum Console')
    print(f'  mode: {config.mode}')
    print(f'  root: {config.root}')
    if config.metrics_dir:
        print(f'  metrics_dir: {config.metrics_dir}')
    url = f'http://{args.host}:{config.port}'
    print(f'  bind: {url}')
    print()

    app = create_app(config)

    if args.no_browser:
        uvicorn.run(app, host=args.host, port=config.port, log_level='info')
        return 0

    # App window mode if pywebview is available
    try:
        import webview as _webview_check  # noqa: F401
        has_webview = True
    except ImportError:
        has_webview = False

    if has_webview:
        _run_server_thread(app, args.host, config.port)
        if not _wait_ready(url):
            print('warning: server did not respond in 10s; opening window anyway',
                  file=sys.stderr)
        _open_window(url)
    else:
        # Fallback: system browser tab
        try:
            webbrowser.open(url)
        except Exception:
            pass
        uvicorn.run(app, host=args.host, port=config.port, log_level='info')

    return 0
