"""audits.py — read-only routes that run audit scripts and render output.

Each audit shells out to a script under scripts/audit/ (synchronous;
operations finish in seconds), captures stdout, renders as markdown.

No state is mutated. Scripts are idempotent and write-only to docs/baselines/
when explicitly asked via --output flag (we don't pass it from the UI).
"""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from ui.lib import doc_loader

router = APIRouter(prefix='/audits')


_REPO_ROOT = Path(__file__).resolve().parent.parent.parent  # ui/routes/audits.py → repo root

_AUDITS = {
    'payload': {
        'label':       'Reference Payload Audit',
        'description': 'Sums bytes injected by each skill via inject_references; flags > threshold.',
        'cmd':         [sys.executable, '-u', 'scripts/audit/payload.py'],
    },
    'parity': {
        'label':       'Provider Parity Test',
        'description': 'Validates that the same canonical source produces structurally equivalent '
                       'output across claude / copilot / glm.',
        'cmd':         [sys.executable, '-u', 'scripts/tests/parity/run.py'],
    },
    'attention-distribution': {
        'label':       'Attention Score Distribution',
        'description': 'Walks artifacts with attention frontmatter; reports band counts, '
                       'percentiles, calibration signal (R2).',
        'cmd':         [sys.executable, '-u', 'scripts/audit/attention_distribution.py'],
    },
}


@router.get('', response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    templates = request.app.state.templates
    return templates.TemplateResponse(request, 'audits_index.html', {'audits': _AUDITS})


@router.post('/{name}', response_class=HTMLResponse)
@router.get('/{name}',  response_class=HTMLResponse)
async def run(request: Request, name: str) -> HTMLResponse:
    if name not in _AUDITS:
        raise HTTPException(status_code=404, detail=f'unknown audit: {name}')
    cfg       = request.app.state.config
    templates = request.app.state.templates
    spec      = _AUDITS[name]

    cwd = cfg.root if cfg.is_framework else _REPO_ROOT
    try:
        proc = subprocess.run(
            spec['cmd'],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=120,
        )
        output_md = proc.stdout
        stderr    = proc.stderr
        exit_code = proc.returncode
        timed_out = False
    except subprocess.TimeoutExpired:
        output_md = ''
        stderr    = 'timeout after 120s'
        exit_code = -1
        timed_out = True

    rendered = doc_loader.render_markdown(output_md) if output_md else ''
    return templates.TemplateResponse(
        request,
        'audit_result.html',
        {
            'name':       name,
            'spec':       spec,
            'rendered':   rendered,
            'output':     output_md,
            'stderr':     stderr,
            'exit_code':  exit_code,
            'timed_out':  timed_out,
        },
    )
