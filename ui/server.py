"""server.py — FastAPI app factory for the Orquestrum UI console.

Single-user, local-only (binds 127.0.0.1 by default). No auth, no DB —
the file system is the source of truth.
"""
from __future__ import annotations
import datetime as dt
from importlib import metadata as importlib_metadata
from pathlib import Path

import jinja2
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from ui.config import UIConfig
from ui.i18n import DEFAULT as DEFAULT_LOCALE, SUPPORTED as SUPPORTED_LOCALES, translate
from ui.lib.sidebar import sidebar_counts


def _resolve_app_version() -> str:
    """Read installed package version from importlib.metadata; 'dev' fallback."""
    try:
        return importlib_metadata.version('orquestrum')
    except importlib_metadata.PackageNotFoundError:
        return 'dev'


def _time_ago(value: dt.datetime | None, locale: str = DEFAULT_LOCALE) -> str:
    """Return a compact relative-time string ('há 14s', '1 min ago')."""
    if value is None:
        return ''
    now   = dt.datetime.now(dt.timezone.utc)
    other = value if value.tzinfo else value.replace(tzinfo=dt.timezone.utc)
    delta = max(0, int((now - other).total_seconds()))

    if delta < 60:
        unit_pt, unit_en, n = 's', 's', delta
    elif delta < 3600:
        unit_pt, unit_en, n = 'min', 'min', delta // 60
    elif delta < 86400:
        unit_pt, unit_en, n = 'h', 'h', delta // 3600
    else:
        unit_pt, unit_en, n = 'd', 'd', delta // 86400

    if locale == 'en':
        return f'{n}{unit_en} ago'
    return f'há {n}{unit_pt}'

_HERE = Path(__file__).resolve().parent
TEMPLATES_DIR = _HERE / 'templates'
STATIC_DIR    = _HERE / 'static'

APP_VERSION = _resolve_app_version()  # surfaced in the brand subtitle
LOCALE_COOKIE = 'orq_lang'


def _home_stats(config: UIConfig) -> dict:
    """Return small dict with agent/skill counts and metric summary for the home page.

    Counts mirror `sidebar_counts()` in `ui/lib/sidebar.py` — in project mode,
    the count is the union of project-local + globally-installed (framework)
    agents/skills, since the project sees both. Without the merge, fresh v0.5
    projects always showed 0/0 (agents live globally; project dir has none),
    which read as "nothing works" to first-time users.
    """
    stats: dict = {
        'agents': 0, 'skills': 0, 'event_count': 0, 'last_event': None,
        'linked_project_root': str(config.linked_project_root) if config.linked_project_root else None,
    }
    try:
        if config.is_framework:
            stats['agents'] = sum(1 for _ in (config.root / 'agents').glob('*.md'))
            stats['skills'] = sum(1 for _ in (config.root / 'skills').glob('*/SKILL.md'))
        elif config.linked_project_root:
            # Use sets so project-local + framework counts dedupe by name —
            # a project that pinned its own copy of `helm` doesn't double-count.
            local_agents: set[str] = set()
            local_skills: set[str] = set()
            for sub in ('.claude/agents', '.opencode/agents', '.sdd/agents'):
                d = config.linked_project_root / sub
                if d.is_dir():
                    local_agents.update(p.stem for p in d.glob('*.md'))
            for sub in ('.sdd/skills', '.opencode/skills'):
                d = config.linked_project_root / sub
                if d.is_dir():
                    local_skills.update(p.parent.name for p in d.glob('*/SKILL.md'))
            if config.framework_root:
                fw_a = config.framework_root / 'agents'
                fw_s = config.framework_root / 'skills'
                if fw_a.is_dir():
                    local_agents.update(p.stem for p in fw_a.glob('*.md'))
                if fw_s.is_dir():
                    local_skills.update(p.parent.name for p in fw_s.glob('*/SKILL.md'))
            stats['agents'] = len(local_agents)
            stats['skills'] = len(local_skills)
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
    templates.env.globals['app_version']  = APP_VERSION
    templates.env.globals['linked_project_root'] = (
        str(config.linked_project_root) if config.linked_project_root else None
    )
    templates.env.globals['supported_locales'] = SUPPORTED_LOCALES

    @jinja2.pass_context
    def _t(ctx, key: str, **vars: object) -> str:
        request = ctx.get('request')
        locale = getattr(request.state, 'locale', DEFAULT_LOCALE) if request else DEFAULT_LOCALE
        return translate(key, locale=locale, **vars)

    templates.env.filters['t'] = _t
    templates.env.globals['t']  = _t  # also callable as t('key')

    @jinja2.pass_context
    def _time_ago_filter(ctx, value: dt.datetime | None) -> str:
        request = ctx.get('request')
        locale  = getattr(request.state, 'locale', DEFAULT_LOCALE) if request else DEFAULT_LOCALE
        return _time_ago(value, locale=locale)

    templates.env.filters['time_ago'] = _time_ago_filter

    @jinja2.pass_context
    def _sidebar_counts(ctx) -> dict:
        return sidebar_counts(config)

    templates.env.globals['sidebar_counts'] = _sidebar_counts
    app.state.templates = templates

    @app.middleware('http')
    async def locale_middleware(request: Request, call_next):
        cookie = request.cookies.get(LOCALE_COOKIE)
        request.state.locale = cookie if cookie in SUPPORTED_LOCALES else DEFAULT_LOCALE
        return await call_next(request)

    if STATIC_DIR.is_dir():
        app.mount('/static', StaticFiles(directory=str(STATIC_DIR)), name='static')

    # Routes
    from ui.routes import (
        health, dashboard, docs, catalog, coverage, audits, convert, install,
        edit_agent, edit_skill, compact, jobs, i18n, live, palette,
        installs as system_installs,
        doctor as system_doctor,
        mcp as system_mcp,
    )
    app.include_router(health.router)
    app.include_router(i18n.router)
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
    app.include_router(live.router)
    app.include_router(palette.router)
    app.include_router(system_installs.router)
    app.include_router(system_doctor.router)
    app.include_router(system_mcp.router)

    # `/` lands on the dashboard so users see actual data immediately.
    # The legacy home (5 card-selector + redundant quick-stats) is still
    # reachable at `/welcome` for first-time / no-project flows that
    # benefit from the orientation page; the sidebar's "Visão geral"
    # link already points to /dashboard.
    @app.get('/')
    async def index(request: Request):
        from fastapi.responses import RedirectResponse
        return RedirectResponse('/dashboard', status_code=303)

    @app.get('/welcome', response_class=HTMLResponse)
    async def welcome(request: Request) -> HTMLResponse:
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
