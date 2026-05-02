"""server.py — FastAPI app factory for the Orquestrum UI console.

Single-user, local-only (binds 127.0.0.1 by default). No auth, no DB —
the file system is the source of truth.
"""
from __future__ import annotations
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from ui.config import UIConfig

_HERE = Path(__file__).resolve().parent
TEMPLATES_DIR = _HERE / 'templates'
STATIC_DIR    = _HERE / 'static'


def _home_stats(config: UIConfig) -> dict:
    """Return small dict with agent/skill counts and metric summary for the home page."""
    stats: dict = {
        'agents': 0, 'skills': 0, 'event_count': 0, 'last_event': None,
        'linked_project_root': str(config.linked_project_root) if config.linked_project_root else None,
    }
    try:
        if config.is_framework:
            stats['agents'] = sum(1 for _ in (config.root / 'agents').glob('*.md'))
            stats['skills'] = sum(1 for _ in (config.root / 'skills').glob('*/SKILL.md'))
        elif config.linked_project_root:
            for sub in ('.claude/agents', '.opencode/agents'):
                d = config.linked_project_root / sub
                if d.is_dir():
                    stats['agents'] += sum(1 for _ in d.glob('*.md'))
            for sub in ('.sdd/skills', '.opencode/skills'):
                d = config.linked_project_root / sub
                if d.is_dir():
                    stats['skills'] += sum(1 for _ in d.glob('*/SKILL.md'))
        elif config.framework_root:
            stats['agents'] = sum(1 for _ in (config.framework_root / 'agents').glob('*.md'))
            stats['skills'] = sum(1 for _ in (config.framework_root / 'skills').glob('*/SKILL.md'))
        if config.metrics_dir is not None:
            events_file = config.metrics_dir / 'events.jsonl'
            if events_file.exists():
                with events_file.open('rb') as f:
                    f.seek(0, 2)
                    size = f.tell()
                    f.seek(max(0, size - 4096))
                    tail = f.read().decode('utf-8', errors='replace').splitlines()
                stats['event_count'] = sum(1 for _ in events_file.open('r', encoding='utf-8'))
                if tail:
                    stats['last_event'] = tail[-1][:120] + ('…' if len(tail[-1]) > 120 else '')
    except Exception:
        # Home page must never fail — best-effort stats
        pass
    return stats


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
    from ui.routes import health, dashboard, docs, catalog, coverage, audits, convert, install, edit_agent, edit_skill, compact, jobs
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
    app.include_router(jobs.router)

    @app.get('/', response_class=HTMLResponse)
    async def index(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request,
            'home.html',
            {'stats': _home_stats(config)},
        )

    @app.exception_handler(404)
    async def not_found(request: Request, exc) -> Response:  # type: ignore[no-untyped-def]
        # Honor Accept header: JSON for API clients, HTML for browsers
        accept = (request.headers.get('accept') or '').lower()
        if 'application/json' in accept and 'text/html' not in accept:
            return JSONResponse(status_code=404, content={'error': 'not found', 'path': request.url.path})
        try:
            return templates.TemplateResponse(
                request,
                '404.html',
                {'path': request.url.path},
                status_code=404,
            )
        except Exception:
            return JSONResponse(status_code=404, content={'error': 'not found', 'path': request.url.path})

    return app
