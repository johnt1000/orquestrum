"""compact.py — UI route to invoke orquestrum.core.build.compress_refs via job runner."""
from __future__ import annotations
import sys

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from ui.lib import jobs

router = APIRouter(prefix='/compact')


def _list_skills(root) -> list[str]:
    skills_dir = root / 'skills'
    if not skills_dir.is_dir():
        return []
    return sorted(d.name for d in skills_dir.iterdir()
                  if d.is_dir() and (d / 'SKILL.md').exists())


@router.get('', response_class=HTMLResponse)
async def show(request: Request) -> HTMLResponse:
    cfg       = request.app.state.config
    templates = request.app.state.templates
    skills    = _list_skills(cfg.root) if cfg.is_framework else []
    return templates.TemplateResponse(
        request, 'compact.html',
        {
            'skills':               skills,
            'output':               None,
            'project_mode_warning': not cfg.is_framework,
            'last':                 None,
        },
    )


@router.post('')
async def run(
    request: Request,
    scope:        str = Form(default='all'),
    skill:        str = Form(default=''),
    threshold_kb: int = Form(default=8),
    dry_run:      str = Form(default=''),
    force:        str = Form(default=''),
) -> RedirectResponse:
    cfg = request.app.state.config
    if not cfg.is_framework:
        raise HTTPException(status_code=400, detail='/compact only available in framework mode')

    cmd = [sys.executable, '-u', '-m', 'orquestrum.core.build.compress_refs',
           '--threshold-kb', str(threshold_kb)]
    if scope == 'one' and skill:
        cmd += ['--skill', skill]
    if dry_run:
        cmd.append('--dry-run')
    if force:
        cmd.append('--force')

    suffix = (skill if scope == 'one' else 'all') + (' (dry-run)' if dry_run else '')
    job = jobs.submit(
        label=f'compact {suffix}', cmd=cmd, cwd=cfg.root, timeout_s=120,
        extra={'back_url': '/compact'},
    )
    return RedirectResponse(f'/jobs/{job.id}', status_code=303)
