from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from ui.lib import catalog_loader

router = APIRouter()


@router.get('/catalog', response_class=HTMLResponse)
async def show(request: Request) -> HTMLResponse:
    cfg       = request.app.state.config
    templates = request.app.state.templates

    if cfg.is_framework:
        agents_dir = cfg.root / 'agents'
        skills_dir = cfg.root / 'skills'
    else:
        # Project mode — agents may be installed under .claude/agents or .opencode/agents
        candidates = [
            cfg.root / '.claude' / 'agents',
            cfg.root / '.opencode' / 'agents',
        ]
        agents_dir = next((p for p in candidates if p.is_dir()), candidates[0])
        # Skills are not always present in target installs; try .sdd/skills then .opencode/skills
        skills_candidates = [
            cfg.root / '.sdd' / 'skills',
            cfg.root / '.opencode' / 'skills',
        ]
        skills_dir = next((p for p in skills_candidates if p.is_dir()), skills_candidates[0])

    agents = catalog_loader.list_agents(agents_dir)
    skills = catalog_loader.list_skills(skills_dir)

    return templates.TemplateResponse(
        request,
        'catalog.html',
        {'agents': agents, 'skills': skills,
         'agents_dir': agents_dir, 'skills_dir': skills_dir},
    )
