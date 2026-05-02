"""compact.py — UI route to invoke scripts/build/compress_refs.py.

Framework mode only. Form picks: scope (all skills | one skill) + threshold +
dry-run. Subprocess runs compress_refs.py and renders output.
"""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse

router = APIRouter(prefix='/compact')


@router.get('', response_class=HTMLResponse)
async def show(request: Request) -> HTMLResponse:
    cfg       = request.app.state.config
    templates = request.app.state.templates
    skills    = []
    if cfg.is_framework:
        skills_dir = cfg.root / 'skills'
        if skills_dir.is_dir():
            skills = sorted(d.name for d in skills_dir.iterdir()
                            if d.is_dir() and (d / 'SKILL.md').exists())
    return templates.TemplateResponse(
        request, 'compact.html',
        {
            'skills':               skills,
            'output':               None,
            'project_mode_warning': not cfg.is_framework,
            'last':                 None,
        },
    )


@router.post('', response_class=HTMLResponse)
async def run(
    request: Request,
    scope:        str = Form(default='all'),
    skill:        str = Form(default=''),
    threshold_kb: int = Form(default=8),
    dry_run:      str = Form(default=''),
    force:        str = Form(default=''),
) -> HTMLResponse:
    cfg       = request.app.state.config
    templates = request.app.state.templates
    if not cfg.is_framework:
        raise HTTPException(status_code=400, detail='/compact only available in framework mode')

    cmd = [sys.executable, '-u', 'scripts/build/compress_refs.py',
           '--threshold-kb', str(threshold_kb)]
    if scope == 'one' and skill:
        cmd += ['--skill', skill]
    if dry_run:
        cmd.append('--dry-run')
    if force:
        cmd.append('--force')

    try:
        proc = subprocess.run(
            cmd, cwd=str(cfg.root), capture_output=True, text=True, timeout=60,
        )
        output    = (proc.stdout or '') + (('\n--- stderr ---\n' + proc.stderr) if proc.stderr else '')
        exit_code = proc.returncode
    except subprocess.TimeoutExpired:
        output    = 'timeout after 60s'
        exit_code = -1

    skills_list: list[str] = []
    skills_dir = cfg.root / 'skills'
    if skills_dir.is_dir():
        skills_list = sorted(d.name for d in skills_dir.iterdir()
                             if d.is_dir() and (d / 'SKILL.md').exists())

    return templates.TemplateResponse(
        request, 'compact.html',
        {
            'skills':               skills_list,
            'output':               output,
            'exit_code':            exit_code,
            'last': {'scope': scope, 'skill': skill, 'threshold_kb': threshold_kb,
                     'dry_run': bool(dry_run), 'force': bool(force)},
            'project_mode_warning': False,
        },
    )
