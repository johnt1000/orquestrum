#!/usr/bin/env python3
"""serve.py — launch the Orquestrum UI console.

Usage:
    python -m orquestrum.core.ui.serve                      # auto-detect mode, root=.
    python -m orquestrum.core.ui.serve --mode project --root /path
    python -m orquestrum.core.ui.serve --mode framework --port 7700

Local-only by design: binds 127.0.0.1.
"""
import argparse
import sys

from ui.config import resolve, DEFAULT_PORT


def main() -> None:
    parser = argparse.ArgumentParser(description='Orquestrum UI console (local single-user)')
    parser.add_argument('--mode', choices=['framework', 'project'], default=None,
                        help='UI mode (default: auto-detect from --root)')
    parser.add_argument('--root', default=None,
                        help='Project / framework root (default: cwd or $ORQ_ROOT)')
    parser.add_argument('--port', type=int, default=None,
                        help=f'TCP port to bind on 127.0.0.1 (default: {DEFAULT_PORT} or $ORQ_PORT)')
    parser.add_argument('--host', default='127.0.0.1',
                        help='Bind host (default 127.0.0.1; do NOT bind 0.0.0.0 — there is no auth)')
    args = parser.parse_args()

    try:
        config = resolve(mode_arg=args.mode, root_arg=args.root, port_arg=args.port)
    except ValueError as e:
        print(f'config error: {e}', file=sys.stderr)
        sys.exit(2)

    print(f'Orquestrum Console')
    print(f'  mode: {config.mode}')
    print(f'  root: {config.root}')
    if config.metrics_dir:
        print(f'  metrics_dir: {config.metrics_dir}')
    print(f'  bind: http://{args.host}:{config.port}')
    print()

    import uvicorn
    from ui.server import create_app
    app = create_app(config)
    uvicorn.run(app, host=args.host, port=config.port, log_level='info')


if __name__ == '__main__':
    main()
