"""install.py — UI route to run orquestrum.core.install via async job runner."""
from __future__ import annotations
import sys
from pathlib import Path

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from ui.lib import jobs

router = APIRouter(prefix='/install')

_TOOLS = ['claude-code', 'opencode']


@router.get('', response_class=HTMLResponse)
async def show(request: Request) -> HTMLResponse:
    cfg       = request.app.state.config
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request, 'install.html',
        {
            'tools':                _TOOLS,
            'output':               None,
            'project_mode_warning': not cfg.is_framework,
            'last':                 None,
        },
    )


@router.post('')
async def run(
    request: Request,
    tool:   str = Form(default=''),
    target: str = Form(...),
    auto:   str = Form(default=''),
):
    cfg       = request.app.state.config
    templates = request.app.state.templates

    if not cfg.is_framework:
        raise HTTPException(status_code=400, detail='/install only available in framework mode')

    target_path = Path(target).expanduser().resolve()
    err: str | None = None
    if not target_path.exists():
        err = f'Target does not exist: {target_path}'
    elif not target_path.is_dir():
        err = f'Target is not a directory: {target_path}'
    elif tool and tool not in _TOOLS:
        err = f'Invalid tool: {tool}'
    elif not auto and not tool:
        err = 'Pick a tool or check "auto-detect"'

    if err:
        return templates.TemplateResponse(
            request, 'install.html',
            {
                'tools':                _TOOLS,
                'output':               None,
                'error':                err,
                'project_mode_warning': False,
                'last':                 {'tool': tool, 'target': str(target_path), 'auto': bool(auto)},
            },
        )

    cmd = [sys.executable, '-u', '-m', 'orquestrum.core.install', '--target', str(target_path)]
    if auto:
        cmd.append('--auto')
    else:
        cmd += ['--tool', tool]

    label = f'install {"auto" if auto else tool} → {target_path.name}'
    job = jobs.submit(
        label=label, cmd=cmd, cwd=cfg.root, timeout_s=180,
        extra={'back_url': '/install'},
    )
    return RedirectResponse(f'/jobs/{job.id}', status_code=303)
