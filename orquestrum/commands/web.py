"""orquestrum web — launch the local console (FastAPI + Uvicorn)."""
from __future__ import annotations
import argparse
import os
import sys
import webbrowser
from pathlib import Path


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser('web', help='Launch the local web console.')
    p.add_argument('--target', default=None,
                   help='Project / framework root (default: cwd or $ORQ_ROOT)')
    p.add_argument('--mode', choices=['project', 'framework', 'auto'], default='auto',
                   help='Force a specific mode (default: auto-detect)')
    p.add_argument('--port', type=int, default=None,
                   help='TCP port (default 7700 or $ORQ_PORT)')
    p.add_argument('--host', default='127.0.0.1',
                   help='Bind host (default 127.0.0.1; do NOT bind 0.0.0.0)')
    p.add_argument('--no-browser', action='store_true',
                   help='Do not auto-open a browser tab')
    p.set_defaults(handler=_handler)


def _handler(args: argparse.Namespace) -> int | None:
    # Lazy imports — fastapi/uvicorn are optional [ui] deps
    try:
        import uvicorn
        from ui.config import resolve as resolve_config, DEFAULT_PORT
        from ui.server import create_app
    except ImportError as e:
        print('error: web console requires the [ui] extras. Run:', file=sys.stderr)
        print('       uv sync --extra ui                   (in editable mode)', file=sys.stderr)
        print('       uv tool install --with fastapi --with uvicorn[standard] \\', file=sys.stderr)
        print('         --with jinja2 --with mistune --with python-multipart --with watchfiles \\', file=sys.stderr)
        print('         --editable /path/to/orquestrum', file=sys.stderr)
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

    if not args.no_browser and os.environ.get('DISPLAY') is not False:
        # Best-effort browser open; ignore failures (headless, sandboxed, etc.)
        try:
            webbrowser.open(url)
        except Exception:
            pass

    app = create_app(config)
    uvicorn.run(app, host=args.host, port=config.port, log_level='info')
    return 0
