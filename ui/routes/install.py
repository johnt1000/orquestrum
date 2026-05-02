"""install.py — UI route to run scripts/install.py.

Framework mode only. Form picks tool + target dir + dry-run flag (auto detect).
Subprocess runs synchronously; output captured and shown.
"""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse

router = APIRouter(prefix='/install')

_TOOLS = ['claude-code', 'opencode', 'cursor', 'aider', 'windsurf']


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


@router.post('', response_class=HTMLResponse)
async def run(
    request: Request,
    tool:   str = Form(default=''),
    target: str = Form(...),
    auto:   str = Form(default=''),
) -> HTMLResponse:
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

    cmd = [sys.executable, '-u', 'scripts/install.py', '--target', str(target_path)]
    if auto:
        cmd.append('--auto')
    else:
        cmd += ['--tool', tool]

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
        request, 'install.html',
        {
            'tools':                _TOOLS,
            'output':               output,
            'exit_code':            exit_code,
            'last':                 {'tool': tool, 'target': str(target_path), 'auto': bool(auto)},
            'project_mode_warning': False,
        },
    )
