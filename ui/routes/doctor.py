"""doctor.py — web view of `orquestrum doctor`.

Runs doctor with --json and renders the structured result inline (no
async job needed — doctor is fast, ~200ms). Each row gets a severity
badge (✓/!/✗) plus the actionable `fix:` line when present.

The JSON shape comes from `orquestrum.commands.doctor.Report.results`
(see Report.ok/warn/fail in doctor.py).
"""
from __future__ import annotations
import json
import subprocess
import sys

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter(prefix='/system/doctor')


def _run_doctor() -> dict:
    """Spawn `orquestrum doctor --json` and parse stdout. Best-effort —
    on any failure return a stub result so the page still renders."""
    try:
        proc = subprocess.run(
            [sys.executable, '-u', '-m', 'orquestrum.cli', 'doctor', '--json'],
            capture_output=True, text=True, timeout=15,
        )
    except Exception as e:
        return {'errors': 1, 'warnings': 0, 'results': [{
            'status': 'fail',
            'label':  'doctor invocation',
            'detail': f'failed to spawn: {type(e).__name__}: {e}',
            'fix':    'check that the orquestrum CLI is installed and on PATH',
        }]}

    # doctor --json prints the human report THEN the JSON object. Find the
    # first '{' on a line by itself and parse from there.
    text = proc.stdout
    start = text.find('{')
    if start == -1:
        return {'errors': 1, 'warnings': 0, 'results': [{
            'status': 'fail',
            'label':  'doctor output',
            'detail': 'no JSON found on stdout',
            'fix':    f'run `orquestrum doctor --json` directly to debug; raw stdout was: {text[:200]}',
        }]}
    try:
        return json.loads(text[start:])
    except json.JSONDecodeError as e:
        return {'errors': 1, 'warnings': 0, 'results': [{
            'status': 'fail',
            'label':  'doctor JSON parse',
            'detail': f'malformed: {e}',
            'fix':    'this is a framework bug — file an issue with the raw output',
        }]}


@router.get('', response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    """Render the latest `orquestrum doctor --json` output as a structured
    table. Re-runs on every page load (fast)."""
    templates = request.app.state.templates
    result = _run_doctor()
    # Group results into the same sections the CLI emits so the UI mirrors
    # the human report. Without explicit sections in the JSON, we present
    # them in execution order (the CLI's order is meaningful).
    return templates.TemplateResponse(
        request,
        'system_doctor.html',
        {
            'errors':   result.get('errors', 0),
            'warnings': result.get('warnings', 0),
            'results':  result.get('results', []),
        },
    )
