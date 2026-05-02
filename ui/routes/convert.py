"""convert.py — UI route to run orquestrum.core.convert via async job runner."""
from __future__ import annotations
import sys

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from ui.lib import jobs

router = APIRouter(prefix='/convert')

_TOOLS     = ['claude-code', 'opencode', 'cursor', 'aider', 'windsurf', 'all']
_PROVIDERS = ['(none)', 'claude', 'copilot', 'glm']


@router.get('', response_class=HTMLResponse)
async def show(request: Request) -> HTMLResponse:
    cfg       = request.app.state.config
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request, 'convert.html',
        {
            'tools':                _TOOLS,
            'providers':            _PROVIDERS,
            'output':               None,
            'project_mode_warning': not cfg.is_framework,
            'last':                 None,
        },
    )


@router.post('')
async def run(
    request: Request,
    tool:     str = Form(...),
    provider: str = Form(default='(none)'),
    dry_run:  str = Form(default=''),
) -> RedirectResponse:
    cfg = request.app.state.config

    if not cfg.is_framework:
        raise HTTPException(status_code=400, detail='/convert only available in framework mode')
    if tool not in _TOOLS:
        raise HTTPException(status_code=400, detail=f'invalid tool: {tool}')
    if provider not in _PROVIDERS:
        raise HTTPException(status_code=400, detail=f'invalid provider: {provider}')

    cmd = [sys.executable, '-u', '-m', 'orquestrum.core.convert']
    if tool == 'all':
        cmd.append('--all')
    else:
        cmd += ['--tool', tool]
    if provider and provider != '(none)':
        cmd += ['--provider', provider]
    if dry_run:
        cmd.append('--dry-run')

    label = f'convert {tool}' + (' (dry-run)' if dry_run else '')
    job = jobs.submit(
        label=label, cmd=cmd, cwd=cfg.root, timeout_s=180,
        extra={'back_url': '/convert'},
    )
    return RedirectResponse(f'/jobs/{job.id}', status_code=303)
