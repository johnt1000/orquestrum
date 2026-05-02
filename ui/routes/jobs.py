"""ui/routes/jobs.py — read-only views over the in-memory job runner."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from ui.lib import doc_loader, jobs

router = APIRouter(prefix='/jobs')


def _maybe_render(job: jobs.Job) -> str | None:
    if job.is_terminal and job.render_md and job.stdout:
        return doc_loader.render_markdown(job.stdout)
    return None


@router.get('/{job_id}', response_class=HTMLResponse)
async def show(request: Request, job_id: str) -> HTMLResponse:
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f'unknown job: {job_id}')
    templates = request.app.state.templates
    rendered  = _maybe_render(job)
    back_url  = job.extra.get('back_url') if job.extra else None
    return templates.TemplateResponse(
        request, 'job.html',
        {'job': job, 'rendered': rendered, 'back_url': back_url},
    )


@router.get('/{job_id}/partial', response_class=HTMLResponse)
async def partial(request: Request, job_id: str) -> HTMLResponse:
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f'unknown job: {job_id}')
    templates = request.app.state.templates
    rendered  = _maybe_render(job)
    return templates.TemplateResponse(
        request, '_job_partial.html',
        {'job': job, 'rendered': rendered},
    )
