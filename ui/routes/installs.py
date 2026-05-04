"""installs.py — web view of `~/.orquestrum/installs.json` + prune button.

Mirrors the `orquestrum installs list/prune` CLI commands. Reads the
manifest directly via `lib.installs_manifest` (no subprocess for the
list — fast, runs every page render). Prune dispatches as an async
job so the page can show the same plan + outcome a CLI user sees.
"""
from __future__ import annotations
import sys

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from orquestrum.lib import installs_manifest as im
from ui.lib import jobs

router = APIRouter(prefix='/system/installs')


@router.get('', response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    """List every install record + summary counters."""
    templates = request.app.state.templates
    records = im.list_installs()
    buckets = im.classify_stale(records)
    rows = []
    for r in sorted(records, key=lambda r: (r.tool, r.target)):
        if r in buckets['retired_tool']:
            mark, note = '✗', 'retired'
        elif r in buckets['stale_target']:
            mark, note = '✗', 'stale'
        else:
            mark, note = '✓', ''
        date = r.installed_at.split('T')[0] if r.installed_at else '-'
        rows.append({
            'mark':   mark,
            'note':   note,
            'tool':   r.tool,
            'files':  len(r.files),
            'date':   date,
            'target': r.target,
        })
    return templates.TemplateResponse(
        request,
        'system_installs.html',
        {
            'rows':         rows,
            'total':        len(records),
            'valid':        len(buckets['valid']),
            'stale':        len(buckets['stale_target']),
            'retired':      len(buckets['retired_tool']),
            'has_dead':     bool(buckets['stale_target'] or buckets['retired_tool']),
        },
    )


@router.post('/prune')
async def prune(request: Request) -> RedirectResponse:
    """Run `orquestrum installs prune` as an async job and redirect to its
    output page. The CLI command writes a backup before mutating, so this
    is safe to invoke from a button click."""
    job = jobs.submit(
        label='orquestrum installs prune',
        cmd=[sys.executable, '-u', '-m', 'orquestrum.cli', 'installs', 'prune'],
        cwd=str(request.app.state.config.root),
        timeout_s=60,
        render_md=False,
        extra={'back_url': '/system/installs'},
    )
    return RedirectResponse(f'/jobs/{job.id}', status_code=303)
