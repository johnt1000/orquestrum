"""edit_agent.py — refine agent frontmatter through the UI.

Onda 5 — three flows now coexist:
  GET  /agents/{slug}/edit              → 2-col page (form + live preview + empty diff)
  POST /agents/{slug}/preview           → HTMX swap target — live agent card from in-flight form
  POST /agents/{slug}/edit              → validate; return diff partial (HX-Request) or full page
  POST /agents/{slug}/edit/apply        → atomic write + applied confirmation page

Lint preflight is in-process (ui/lib/edit_validator.py), no subprocess.
"""
from __future__ import annotations
import os
import re
import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from ui.lib import edit_validator

import frontmatter as fm

try:
    from orquestrum.lib.models import AGENT_TIERS
except ImportError:
    AGENT_TIERS = {}

router = APIRouter(prefix='/agents')


def _slug_to_path(cfg, slug: str) -> Path:
    """Resolve {slug} to the canonical agent file. Framework mode only."""
    if not cfg.is_framework:
        raise HTTPException(status_code=400, detail='/agents/edit only in framework mode')
    candidates = list((cfg.root / 'agents').glob('*.md'))
    for f in candidates:
        try:
            post = fm.load(str(f))
            name = str(post.get('name', ''))
            kebab = _name_to_kebab(name)
            if kebab == slug:
                return f
        except Exception:
            continue
    for f in candidates:
        if f.stem == slug:
            return f
    raise HTTPException(status_code=404, detail=f'agent not found: {slug}')


def _name_to_kebab(name: str) -> str:
    s = name.lower()
    s = re.sub(r'\s*[—–-]\s*', '-', s)
    s = s.replace(' & ', '-and-').replace(' ', '-')
    s = re.sub(r'[^a-z0-9-]', '', s)
    s = re.sub(r'-{2,}', '-', s)
    return s.strip('-')


def _coerce_form_to_fm(orig: dict, form: dict) -> dict:
    """Merge form fields into the existing frontmatter dict."""
    new = dict(orig)
    if 'name' in form:           new['name']        = form['name'].strip()
    if 'description' in form:    new['description'] = form['description'].strip()
    if 'mode' in form:           new['mode']        = form['mode'].strip()
    if 'emoji' in form:          new['emoji']       = form['emoji'].strip()
    if 'temperature' in form:
        try:
            new['temperature'] = float(form['temperature'])
        except (TypeError, ValueError):
            new['temperature'] = form['temperature']
    if 'max_tokens' in form:
        try:
            new['max_tokens'] = int(form['max_tokens'])
        except (TypeError, ValueError):
            new['max_tokens'] = form['max_tokens']

    tools = dict(orig.get('tools') or {})
    for key in ('write', 'edit', 'bash', 'question'):
        tools[key] = (form.get(f'tools_{key}') == '1')
    new['tools'] = tools
    return new


def _hidden_fields_from_fm(new_fm: dict) -> dict:
    """Flat dict the diff_pane macro embeds as <input type=hidden> in the apply form."""
    out: dict = {
        'name':        new_fm.get('name', ''),
        'description': new_fm.get('description', ''),
        'mode':        new_fm.get('mode', ''),
        'emoji':       new_fm.get('emoji', ''),
        'temperature': new_fm.get('temperature', ''),
        'max_tokens':  new_fm.get('max_tokens', ''),
    }
    tools = new_fm.get('tools') or {}
    for key in ('write', 'edit', 'bash', 'question'):
        if tools.get(key):
            out[f'tools_{key}'] = '1'
    return out


def _is_htmx(request: Request) -> bool:
    return request.headers.get('hx-request', '').lower() == 'true'


def _agent_tier(name: str) -> str:
    return AGENT_TIERS.get(name, '?')


@router.get('/{slug}/edit', response_class=HTMLResponse)
async def show(request: Request, slug: str) -> HTMLResponse:
    cfg       = request.app.state.config
    templates = request.app.state.templates
    path      = _slug_to_path(cfg, slug)
    post      = fm.load(str(path))
    fm_dict   = dict(post.metadata)
    return templates.TemplateResponse(
        request, 'edit_agent.html',
        {
            'slug':            slug,
            'path':            str(path.relative_to(cfg.root)),
            'fm':              fm_dict,
            'tier':            _agent_tier(fm_dict.get('name', '')),
            'errors':          [],
            'errors_by_field': {},
            'preview':         None,
            'diff':            None,
        },
    )


@router.post('/{slug}/preview', response_class=HTMLResponse)
async def preview_card(request: Request, slug: str) -> HTMLResponse:
    """HTMX endpoint — returns just the live card partial for the right pane."""
    cfg       = request.app.state.config
    templates = request.app.state.templates
    path      = _slug_to_path(cfg, slug)
    post      = fm.load(str(path))

    form_data = dict(await request.form())
    new_fm    = _coerce_form_to_fm(dict(post.metadata), form_data)
    return templates.TemplateResponse(
        request, '_partials/agent_preview.html',
        {'fm': new_fm, 'tier': _agent_tier(new_fm.get('name', ''))},
    )


@router.post('/{slug}/edit', response_class=HTMLResponse)
async def preview(request: Request, slug: str) -> HTMLResponse:
    """Validate + diff. HTMX → diff partial only. Plain POST → full page (no-JS fallback)."""
    cfg       = request.app.state.config
    templates = request.app.state.templates
    path      = _slug_to_path(cfg, slug)
    post      = fm.load(str(path))

    form_data = dict(await request.form())
    new_fm = _coerce_form_to_fm(dict(post.metadata), form_data)

    errors = edit_validator.validate_agent_frontmatter(new_fm)
    diff   = edit_validator.diff_frontmatter(dict(post.metadata), new_fm)
    ebf    = edit_validator.errors_by_field(errors)

    if _is_htmx(request):
        return templates.TemplateResponse(
            request, '_partials/diff.html',
            {
                'diff':            diff,
                'errors':          errors,
                'errors_by_field': ebf,
                'apply_url':       f'/agents/{slug}/edit/apply',
                'hidden_fields':   _hidden_fields_from_fm(new_fm),
                'confirm_text':    f'Apply changes to {slug}.md?',
            },
        )

    return templates.TemplateResponse(
        request, 'edit_agent.html',
        {
            'slug':            slug,
            'path':            str(path.relative_to(cfg.root)),
            'fm':              new_fm,
            'tier':            _agent_tier(new_fm.get('name', '')),
            'errors':          errors,
            'errors_by_field': ebf,
            'preview':         True,
            'diff':            diff,
        },
    )


@router.post('/{slug}/edit/apply', response_class=HTMLResponse)
async def apply(request: Request, slug: str) -> HTMLResponse:
    cfg       = request.app.state.config
    templates = request.app.state.templates
    path      = _slug_to_path(cfg, slug)
    post      = fm.load(str(path))

    form_data = dict(await request.form())
    new_fm = _coerce_form_to_fm(dict(post.metadata), form_data)

    errors = edit_validator.validate_agent_frontmatter(new_fm)
    if errors:
        return templates.TemplateResponse(
            request, 'edit_agent.html',
            {
                'slug':            slug,
                'path':            str(path.relative_to(cfg.root)),
                'fm':              new_fm,
                'tier':            _agent_tier(new_fm.get('name', '')),
                'errors':          errors,
                'errors_by_field': edit_validator.errors_by_field(errors),
                'preview':         True,
                'diff':            edit_validator.diff_frontmatter(dict(post.metadata), new_fm),
            },
        )

    # Atomic write
    new_post = fm.Post(post.content, **new_fm)
    new_text = fm.dumps(new_post)
    if not new_text.endswith('\n'):
        new_text += '\n'

    fd, tmp = tempfile.mkstemp(prefix=path.stem + '.', suffix='.md.tmp', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(new_text)
        os.replace(tmp, path)
    except Exception:
        Path(tmp).unlink(missing_ok=True)
        raise

    return templates.TemplateResponse(
        request, 'edit_agent_applied.html',
        {'slug': slug, 'path': str(path.relative_to(cfg.root))},
    )
