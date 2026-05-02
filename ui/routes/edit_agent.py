"""edit_agent.py — refine agent frontmatter through the UI.

Three-step flow:
  GET  /agents/{slug}/edit         → form with current values
  POST /agents/{slug}/edit         → validate; on success show diff preview
  POST /agents/{slug}/edit/apply   → atomic write (body untouched, frontmatter rewritten)

Lint preflight is in-process (ui/lib/edit_validator.py), no subprocess.
"""
from __future__ import annotations
import os
import re
import tempfile
from pathlib import Path

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse

from ui.lib import edit_validator

import frontmatter as fm

router = APIRouter(prefix='/agents')


def _slug_to_path(cfg, slug: str) -> Path:
    """Resolve {slug} to the canonical agent file. Framework mode only."""
    if not cfg.is_framework:
        raise HTTPException(status_code=400, detail='/agents/edit only in framework mode')
    candidates = list((cfg.root / 'agents').glob('*.md'))
    # Match by computed kebab from frontmatter name
    for f in candidates:
        try:
            post = fm.load(str(f))
            name = str(post.get('name', ''))
            kebab = _name_to_kebab(name)
            if kebab == slug:
                return f
        except Exception:
            continue
    # Fallback: filename stem
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


@router.get('/{slug}/edit', response_class=HTMLResponse)
async def show(request: Request, slug: str) -> HTMLResponse:
    cfg       = request.app.state.config
    templates = request.app.state.templates
    path      = _slug_to_path(cfg, slug)
    post      = fm.load(str(path))
    return templates.TemplateResponse(
        request, 'edit_agent.html',
        {
            'slug':            slug,
            'path':            str(path.relative_to(cfg.root)),
            'fm':              dict(post.metadata),
            'errors':          [],
            'errors_by_field': {},
            'preview':         None,
            'diff':            None,
        },
    )


def _coerce_form_to_fm(orig: dict, form: dict) -> dict:
    """Take the existing frontmatter and apply user edits from the form.
    Preserve unknown keys (we only edit a defined subset).
    """
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


@router.post('/{slug}/edit', response_class=HTMLResponse)
async def preview(request: Request, slug: str) -> HTMLResponse:
    cfg       = request.app.state.config
    templates = request.app.state.templates
    path      = _slug_to_path(cfg, slug)
    post      = fm.load(str(path))

    form_data = dict(await request.form())
    new_fm = _coerce_form_to_fm(dict(post.metadata), form_data)

    errors = edit_validator.validate_agent_frontmatter(new_fm)
    diff   = edit_validator.diff_frontmatter(dict(post.metadata), new_fm)

    return templates.TemplateResponse(
        request, 'edit_agent.html',
        {
            'slug':            slug,
            'path':            str(path.relative_to(cfg.root)),
            'fm':              new_fm,
            'errors':          errors,
            'errors_by_field': edit_validator.errors_by_field(errors),
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
        # Refuse to write — re-render with errors
        return templates.TemplateResponse(
            request, 'edit_agent.html',
            {
                'slug':            slug,
                'path':            str(path.relative_to(cfg.root)),
                'fm':              new_fm,
                'errors':          errors,
                'errors_by_field': edit_validator.errors_by_field(errors),
                'preview':         True,
                'diff':            edit_validator.diff_frontmatter(dict(post.metadata), new_fm),
            },
        )

    # Atomic write: build new content, write to .tmp in same dir, os.replace
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
