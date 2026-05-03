"""edit_skill.py — refine skill frontmatter through the UI.

Onda 5 mirrors edit_agent.py: 2-col layout, /preview HTMX endpoint,
HTMX-aware /edit returning diff partial. Same atomic write at apply.
"""
from __future__ import annotations
import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from ui.lib import edit_validator

import frontmatter as fm

router = APIRouter(prefix='/skills')


def _slug_to_path(cfg, slug: str) -> Path:
    if not cfg.is_framework:
        raise HTTPException(status_code=400, detail='/skills/edit only in framework mode')
    skill_dir = cfg.root / 'skills' / slug
    skill_md  = skill_dir / 'SKILL.md'
    if not skill_md.exists():
        raise HTTPException(status_code=404, detail=f'skill not found: {slug}')
    return skill_md


def _existing_slugs(cfg) -> list[str]:
    skills_dir = cfg.root / 'skills'
    if not skills_dir.is_dir():
        return []
    return sorted(d.name for d in skills_dir.iterdir()
                  if d.is_dir() and (d / 'SKILL.md').exists())


def _coerce_form_to_fm(orig: dict, form: dict) -> dict:
    new = dict(orig)
    if 'name' in form:           new['name']        = form['name'].strip()
    if 'description' in form:    new['description'] = form['description'].strip()

    for field in ('inject_references', 'inject_fewshot'):
        if field in form:
            new[field] = form[field].strip()

    if 'emits_confidence' in form:
        new['emits_confidence'] = (form['emits_confidence'] == '1')
    elif 'emits_confidence' in new:
        new['emits_confidence'] = False

    if 'depends_on' in form:
        raw = form['depends_on'].strip()
        new['depends_on'] = [d.strip() for d in raw.split(',') if d.strip()] if raw else []

    chain_next      = form.get('chain_next', '').strip()
    chain_condition = form.get('chain_condition', '').strip()
    if chain_next or chain_condition:
        new['chain'] = {}
        if chain_next:
            new['chain']['next'] = chain_next
        if chain_condition:
            new['chain']['condition'] = chain_condition
    elif 'chain' in new and not chain_next and not chain_condition:
        new.pop('chain', None)

    return new


def _hidden_fields_from_fm(new_fm: dict) -> dict:
    out: dict = {
        'name':              new_fm.get('name', ''),
        'description':       new_fm.get('description', ''),
        'inject_references': new_fm.get('inject_references', ''),
        'inject_fewshot':    new_fm.get('inject_fewshot', ''),
        'depends_on':        ', '.join(new_fm.get('depends_on') or []),
    }
    chain = new_fm.get('chain') or {}
    out['chain_next']      = chain.get('next', '')
    out['chain_condition'] = chain.get('condition', '')
    if new_fm.get('emits_confidence'):
        out['emits_confidence'] = '1'
    return out


def _is_htmx(request: Request) -> bool:
    return request.headers.get('hx-request', '').lower() == 'true'


@router.get('/{slug}/edit', response_class=HTMLResponse)
async def show(request: Request, slug: str) -> HTMLResponse:
    cfg       = request.app.state.config
    templates = request.app.state.templates
    path      = _slug_to_path(cfg, slug)
    post      = fm.load(str(path))
    return templates.TemplateResponse(
        request, 'edit_skill.html',
        {
            'slug':            slug,
            'path':            str(path.relative_to(cfg.root)),
            'fm':              dict(post.metadata),
            'errors':          [],
            'errors_by_field': {},
            'preview':         None,
            'diff':            None,
            'all_slugs':       _existing_slugs(cfg),
            'valid_inject':    sorted(edit_validator.VALID_INJECT_VALUES),
        },
    )


@router.post('/{slug}/preview', response_class=HTMLResponse)
async def preview_card(request: Request, slug: str) -> HTMLResponse:
    cfg       = request.app.state.config
    templates = request.app.state.templates
    path      = _slug_to_path(cfg, slug)
    post      = fm.load(str(path))

    form_data = dict(await request.form())
    new_fm    = _coerce_form_to_fm(dict(post.metadata), form_data)
    return templates.TemplateResponse(
        request, '_partials/skill_preview.html',
        {'fm': new_fm},
    )


@router.post('/{slug}/edit', response_class=HTMLResponse)
async def preview(request: Request, slug: str) -> HTMLResponse:
    cfg       = request.app.state.config
    templates = request.app.state.templates
    path      = _slug_to_path(cfg, slug)
    post      = fm.load(str(path))

    form_data = dict(await request.form())
    new_fm = _coerce_form_to_fm(dict(post.metadata), form_data)

    all_slugs = _existing_slugs(cfg)
    errors = edit_validator.validate_skill_frontmatter(new_fm, all_slugs)
    diff   = edit_validator.diff_frontmatter(dict(post.metadata), new_fm)
    ebf    = edit_validator.errors_by_field(errors)

    if _is_htmx(request):
        return templates.TemplateResponse(
            request, '_partials/diff.html',
            {
                'diff':            diff,
                'errors':          errors,
                'errors_by_field': ebf,
                'apply_url':       f'/skills/{slug}/edit/apply',
                'hidden_fields':   _hidden_fields_from_fm(new_fm),
                'confirm_text':    f'Apply changes to skills/{slug}/SKILL.md?',
            },
        )

    return templates.TemplateResponse(
        request, 'edit_skill.html',
        {
            'slug':            slug,
            'path':            str(path.relative_to(cfg.root)),
            'fm':              new_fm,
            'errors':          errors,
            'errors_by_field': ebf,
            'preview':         True,
            'diff':            diff,
            'all_slugs':       all_slugs,
            'valid_inject':    sorted(edit_validator.VALID_INJECT_VALUES),
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

    all_slugs = _existing_slugs(cfg)
    errors = edit_validator.validate_skill_frontmatter(new_fm, all_slugs)
    if errors:
        return templates.TemplateResponse(
            request, 'edit_skill.html',
            {
                'slug':            slug,
                'path':            str(path.relative_to(cfg.root)),
                'fm':              new_fm,
                'errors':          errors,
                'errors_by_field': edit_validator.errors_by_field(errors),
                'preview':         True,
                'diff':            edit_validator.diff_frontmatter(dict(post.metadata), new_fm),
                'all_slugs':       all_slugs,
                'valid_inject':    sorted(edit_validator.VALID_INJECT_VALUES),
            },
        )

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
        request, 'edit_skill_applied.html',
        {'slug': slug, 'path': str(path.relative_to(cfg.root))},
    )
