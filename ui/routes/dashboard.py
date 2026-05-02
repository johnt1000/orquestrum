from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from ui.lib import live_metrics

router = APIRouter()


@router.get('/dashboard', response_class=HTMLResponse)
async def show(request: Request) -> HTMLResponse:
    cfg       = request.app.state.config
    templates = request.app.state.templates

    sess = live_metrics.session_for(cfg.metrics_dir, tier='balanced')
    budget = live_metrics.budget_for(cfg.metrics_dir, tier='balanced')

    # Sort by skill input tokens, top 10
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
            'sess':       sess,
            'budget':     budget,
            'by_skill':   by_skill,
            'thresholds': live_metrics.SOFT_THRESHOLDS,
        },
    )
