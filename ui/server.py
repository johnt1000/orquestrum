"""server.py — FastAPI app factory for the Orquestrum UI console.

Single-user, local-only (binds 127.0.0.1 by default). No auth, no DB —
the file system is the source of truth.
"""
from __future__ import annotations
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from ui.config import UIConfig

_HERE = Path(__file__).resolve().parent
TEMPLATES_DIR = _HERE / 'templates'
STATIC_DIR    = _HERE / 'static'


def create_app(config: UIConfig) -> FastAPI:
    app = FastAPI(
        title='Orquestrum Console',
        version='0.1.0',
        docs_url=None,           # disable auto OpenAPI UI; this is operator-facing
        redoc_url=None,
    )
    app.state.config = config

    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
    templates.env.globals['mode']         = config.mode
    templates.env.globals['orq_root']     = str(config.root)
    app.state.templates = templates

    if STATIC_DIR.is_dir():
        app.mount('/static', StaticFiles(directory=str(STATIC_DIR)), name='static')

    # Routes
    from ui.routes import health, dashboard, docs, catalog, coverage, audits, convert, install, edit_agent, edit_skill, compact
    app.include_router(health.router)
    app.include_router(dashboard.router)
    app.include_router(docs.router)
    app.include_router(catalog.router)
    app.include_router(coverage.router)
    app.include_router(audits.router)
    app.include_router(convert.router)
    app.include_router(install.router)
    app.include_router(edit_agent.router)
    app.include_router(edit_skill.router)
    app.include_router(compact.router)

    @app.get('/', response_class=HTMLResponse)
    async def index(request: Request) -> HTMLResponse:
        # Project mode → dashboard; framework mode → catalog (for now)
        if config.is_project:
            return await dashboard.show(request)
        return await catalog.show(request)

    @app.exception_handler(404)
    async def not_found(request: Request, exc):  # type: ignore[no-untyped-def]
        return JSONResponse(status_code=404, content={'error': 'not found', 'path': request.url.path})

    return app
