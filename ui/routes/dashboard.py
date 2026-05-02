from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from ui.lib import live_metrics

router = APIRouter()


@router.get('/dashboard', response_class=HTMLResponse)
async def show(request: Request) -> HTMLResponse:
    cfg       = request.app.state.config
    templates = request.app.state.templates

    registry_projects: list[dict] = []
    if not cfg.is_linked:
        try:
            from orquestrum.lib.registry import load_registry
            registry_projects = load_registry()
        except Exception:
            pass

    sess   = live_metrics.session_for(cfg.metrics_dir, tier='balanced')
    budget = live_metrics.budget_for(cfg.metrics_dir, tier='balanced')

    by_skill = []
    if sess:
        by_skill = sorted(
            sess.by_skill.items(),
            key=lambda kv: int(kv[1].get('input_tokens', 0)),
            reverse=True,
        )[:10]

    return templates.TemplateResponse(
        request,
        'dashboard.html',
        {
            'sess':                 sess,
            'budget':               budget,
            'by_skill':             by_skill,
            'thresholds':           live_metrics.SOFT_THRESHOLDS,
            'is_linked':            cfg.is_linked,
            'linked_project_root':  str(cfg.linked_project_root) if cfg.linked_project_root else None,
            'registry_projects':    registry_projects,
        },
    )
