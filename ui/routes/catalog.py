"""catalog routes — Onda 3 split into /catalog/agents and /catalog/skills.

Old /catalog kept as a 303 redirect to /catalog/agents for backward compat
(older bookmarks, the sidebar's previous link).
"""
from dataclasses import replace
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from ui.lib import catalog_loader, live_metrics

router = APIRouter()


def _local_agent_dirs(root: Path) -> list[Path]:
    return [root / '.claude' / 'agents', root / '.opencode' / 'agents']


def _local_skill_dirs(root: Path) -> list[Path]:
    return [root / '.sdd' / 'skills', root / '.opencode' / 'skills']


def _load_catalog(cfg) -> tuple[list, list, bool, bool]:
    """Return (agents, skills, has_local, has_global) — same logic in both routes."""
    if cfg.is_framework:
        agents_raw = catalog_loader.list_agents(cfg.root / 'agents')
        skills_raw = catalog_loader.list_skills(cfg.root / 'skills')
        agents = [replace(a, sources=('global',)) for a in agents_raw]
        skills = [replace(s, sources=('global',)) for s in skills_raw]
    else:
        project_root  = cfg.linked_project_root or cfg.root
        global_agents = (cfg.framework_root / 'agents') if cfg.framework_root else None
        global_skills = (cfg.framework_root / 'skills') if cfg.framework_root else None
        agents = catalog_loader.merged_agents(_local_agent_dirs(project_root), global_agents)
        skills = catalog_loader.merged_skills(_local_skill_dirs(project_root), global_skills)

    has_local  = any('local'  in a.sources for a in agents)
    has_global = any('global' in a.sources for a in agents)
    return agents, skills, has_local, has_global


@router.get('/catalog', response_class=HTMLResponse)
async def show(request: Request) -> RedirectResponse:
    """Backward-compat: old /catalog redirects to the new agents page."""
    return RedirectResponse(url='/catalog/agents', status_code=303)


@router.get('/catalog/agents', response_class=HTMLResponse)
async def agents_page(request: Request) -> HTMLResponse:
    cfg       = request.app.state.config
    templates = request.app.state.templates

    agents, skills, has_local, has_global = _load_catalog(cfg)

    # Per-agent sparkline series for the cards
    events = live_metrics.events_for(cfg.metrics_dir)
    series = live_metrics.agent_calls_series(
        events,
        short_names=[a.short_name for a in agents],
    )

    return templates.TemplateResponse(
        request,
        'catalog_agents.html',
        {
            'agents':       agents,
            'series':       series,
            'skills_count': len(skills),
            'has_local':    has_local,
            'has_global':   has_global,
        },
    )


@router.get('/catalog/skills', response_class=HTMLResponse)
async def skills_page(request: Request) -> HTMLResponse:
    cfg       = request.app.state.config
    templates = request.app.state.templates

    agents, skills, has_local, has_global = _load_catalog(cfg)

    # Per-skill 7d call counts for the table
    events       = live_metrics.events_for(cfg.metrics_dir)
    skill_counts = live_metrics.skill_calls_period(events)

    return templates.TemplateResponse(
        request,
        'catalog_skills.html',
        {
            'skills':       skills,
            'skill_counts': skill_counts,
            'agents_count': len(agents),
            'has_local':    has_local,
            'has_global':   has_global,
        },
    )
