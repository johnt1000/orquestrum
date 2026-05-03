"""ui/routes/jobs.py — read-only views over the in-memory job runner.

Three endpoints:
  GET /jobs              — Onda 6 index page: 3 columns (running/recent/failed)
  GET /jobs/{id}         — single-job detail view with live partial polling
  GET /jobs/{id}/partial — HTMX swap target showing live state
"""
from __future__ import annotations
import time

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from ui.lib import doc_loader, jobs

router = APIRouter()


def _maybe_render(job: jobs.Job) -> str | None:
    if job.is_terminal and job.render_md and job.stdout:
        return doc_loader.render_markdown(job.stdout)
    return None


def _partition_jobs(now: float | None = None) -> tuple[list[jobs.Job], list[jobs.Job], list[jobs.Job]]:
    """Group the in-memory ring into (running, recent_done, failed_or_timeout).

    Recent = done jobs whose completion was within the last 24 h.
    Failed/timeout always shown regardless of age.
    Each list is sorted newest first.
    """
    now = now or time.time()
    running: list[jobs.Job] = []
    done:    list[jobs.Job] = []
    failed:  list[jobs.Job] = []
    for j in jobs._jobs.values():
        if j.state == 'running':
            running.append(j)
        elif j.state == 'done':
            if j.completed_at and (now - j.completed_at) <= 24 * 3600:
                done.append(j)
        else:  # 'failed' | 'timed_out'
            failed.append(j)
    running.sort(key=lambda j: j.started_at, reverse=True)
    done.sort(key=lambda j: j.completed_at or j.started_at, reverse=True)
    failed.sort(key=lambda j: j.completed_at or j.started_at, reverse=True)
    return running, done, failed


@router.get('/jobs', response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    """Onda 6 — Jobs index. Three columns: running, recent done, failed."""
    running, recent_done, failed = _partition_jobs()
    return request.app.state.templates.TemplateResponse(
        request,
        'jobs_index.html',
        {
            'running':     running,
            'recent_done': recent_done,
            'failed':      failed,
        },
    )


@router.get('/jobs/{job_id}', response_class=HTMLResponse)
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


@router.get('/jobs/{job_id}/partial', response_class=HTMLResponse)
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
