from dataclasses import replace
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from ui.lib import catalog_loader

router = APIRouter()


def _local_agent_dirs(root: Path) -> list[Path]:
    return [root / '.claude' / 'agents', root / '.opencode' / 'agents']


def _local_skill_dirs(root: Path) -> list[Path]:
    return [root / '.sdd' / 'skills', root / '.opencode' / 'skills']


@router.get('/catalog', response_class=HTMLResponse)
async def show(request: Request) -> HTMLResponse:
    cfg       = request.app.state.config
    templates = request.app.state.templates

    if cfg.is_framework:
        # Framework mode: root IS the canonical source — all resources tagged 'global'
        agents_raw = catalog_loader.list_agents(cfg.root / 'agents')
        skills_raw = catalog_loader.list_skills(cfg.root / 'skills')
        agents = [replace(a, sources=('global',)) for a in agents_raw]
        skills = [replace(s, sources=('global',)) for s in skills_raw]
    else:
        # Project mode: merge local (installed in project) vs global (canonical framework)
        project_root   = cfg.linked_project_root or cfg.root
        global_agents  = (cfg.framework_root / 'agents') if cfg.framework_root else None
        global_skills  = (cfg.framework_root / 'skills') if cfg.framework_root else None

        agents = catalog_loader.merged_agents(_local_agent_dirs(project_root), global_agents)
        skills = catalog_loader.merged_skills(_local_skill_dirs(project_root), global_skills)

    has_local  = any('local'  in a.sources for a in agents)
    has_global = any('global' in a.sources for a in agents)

    return templates.TemplateResponse(
        request,
        'catalog.html',
        {
            'agents':     agents,
            'skills':     skills,
            'has_local':  has_local,
            'has_global': has_global,
        },
    )
