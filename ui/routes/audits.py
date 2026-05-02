"""audits.py — read-only routes that run audit scripts via the async job runner.

Each audit submits an asyncio Job (orquestrum.core.* invoked as a module)
and redirects to /jobs/{id}, where HTMX polls until the subprocess
finishes. Long-running scripts no longer block the request thread.
"""
from __future__ import annotations
import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from ui.lib import jobs

router = APIRouter(prefix='/audits')


_REPO_ROOT = Path(__file__).resolve().parent.parent.parent  # ui/routes/audits.py → repo root

_AUDITS = {
    'payload': {
        'label':       'Reference Payload Audit',
        'description': 'Sums bytes injected by each skill via inject_references; flags > threshold.',
        'module':      'orquestrum.core.audit.payload',
        'render_md':   True,
        'timeout_s':   120,
    },
    'parity': {
        'label':       'Provider Parity Test',
        'description': 'Validates that the same canonical source produces structurally equivalent '
                       'output across claude / copilot / glm.',
        'module':      'orquestrum.core.tests.parity.run',
        'render_md':   False,
        'timeout_s':   180,
    },
    'attention-distribution': {
        'label':       'Attention Score Distribution',
        'description': 'Walks artifacts with attention frontmatter; reports band counts, '
                       'percentiles, calibration signal (R2).',
        'module':      'orquestrum.core.audit.attention_distribution',
        'render_md':   True,
        'timeout_s':   120,
    },
}


@router.get('', response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    templates = request.app.state.templates
    return templates.TemplateResponse(request, 'audits_index.html', {'audits': _AUDITS})


@router.post('/{name}')
@router.get('/{name}')
async def run(request: Request, name: str) -> RedirectResponse:
    if name not in _AUDITS:
        raise HTTPException(status_code=404, detail=f'unknown audit: {name}')
    cfg  = request.app.state.config
    spec = _AUDITS[name]

    cwd = cfg.root if cfg.is_framework else _REPO_ROOT
    job = jobs.submit(
        label=spec['label'],
        cmd=[sys.executable, '-u', '-m', spec['module']],
        cwd=cwd,
        timeout_s=spec['timeout_s'],
        render_md=spec['render_md'],
        extra={'back_url': '/audits'},
    )
    return RedirectResponse(f'/jobs/{job.id}', status_code=303)
