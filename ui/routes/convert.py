"""convert.py — UI route to run scripts/convert.py.

Framework mode only. Form picks tool + provider + dry-run; subprocess
runs synchronously (operations ~seconds), output is captured and shown.
"""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse

router = APIRouter(prefix='/convert')

_TOOLS     = ['claude-code', 'opencode', 'cursor', 'aider', 'windsurf', 'all']
_PROVIDERS = ['(none)', 'claude', 'copilot', 'glm']


@router.get('', response_class=HTMLResponse)
async def show(request: Request) -> HTMLResponse:
    cfg       = request.app.state.config
    templates = request.app.state.templates
    if not cfg.is_framework:
        return templates.TemplateResponse(
            request, 'convert.html',
            {'tools': _TOOLS, 'providers': _PROVIDERS, 'output': None,
             'project_mode_warning': True},
        )
    return templates.TemplateResponse(
        request, 'convert.html',
        {'tools': _TOOLS, 'providers': _PROVIDERS, 'output': None,
         'project_mode_warning': False},
    )


@router.post('', response_class=HTMLResponse)
async def run(
    request: Request,
    tool:     str = Form(...),
    provider: str = Form(default='(none)'),
    dry_run:  str = Form(default=''),
) -> HTMLResponse:
    cfg       = request.app.state.config
    templates = request.app.state.templates

    if not cfg.is_framework:
        raise HTTPException(status_code=400, detail='/convert only available in framework mode')
    if tool not in _TOOLS:
        raise HTTPException(status_code=400, detail=f'invalid tool: {tool}')
    if provider not in _PROVIDERS:
        raise HTTPException(status_code=400, detail=f'invalid provider: {provider}')

    cmd = [sys.executable, '-u', 'scripts/convert.py']
    if tool == 'all':
        cmd.append('--all')
    else:
        cmd += ['--tool', tool]
    if provider and provider != '(none)':
        cmd += ['--provider', provider]
    if dry_run:
        cmd.append('--dry-run')

    try:
        proc = subprocess.run(
            cmd, cwd=str(cfg.root), capture_output=True, text=True, timeout=120,
        )
        output    = (proc.stdout or '') + (('\n--- stderr ---\n' + proc.stderr) if proc.stderr else '')
        exit_code = proc.returncode
    except subprocess.TimeoutExpired:
        output    = 'timeout after 120s'
        exit_code = -1

    return templates.TemplateResponse(
        request, 'convert.html',
        {
            'tools':     _TOOLS,
            'providers': _PROVIDERS,
            'output':    output,
            'exit_code': exit_code,
            'last':      {'tool': tool, 'provider': provider, 'dry_run': bool(dry_run)},
            'project_mode_warning': False,
        },
    )
