"""palette.py — GET /palette returns the command palette modal partial.

Index of navigable items:
  Pages   — hardcoded list of the main routes
  Agents  — from catalog_loader (8 in framework)
  Skills  — from catalog_loader (25 in framework)
  Docs    — from doc_loader
  Actions — fixed list (operações shortcut links)

Filtering is done client-side in the modal's inline JS — the full index
fits comfortably in one HTML response (≈70 entries × ~80 bytes ≈ 6 KB).
"""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from ui.lib import catalog_loader, doc_loader

router = APIRouter()


@dataclass
class PaletteItem:
    category: str          # i18n key suffix: 'page' | 'agent' | 'skill' | 'doc' | 'action'
    label:    str
    href:     str
    hint:     str = ''     # secondary text (e.g. agent emoji + tier)
    keywords: str = ''     # extra tokens for client-side filter


def _pages() -> list[PaletteItem]:
    return [
        PaletteItem('page', 'nav.overview',        '/dashboard',        keywords='dashboard'),
        PaletteItem('page', 'nav.agents',          '/catalog/agents',   keywords='catalog'),
        PaletteItem('page', 'nav.skills',          '/catalog/skills',   keywords='catalog'),
        PaletteItem('page', 'nav.live_session',    '/live/session',     keywords='live tail'),
        PaletteItem('page', 'nav.live_routing',    '/live/routing',     keywords='live sankey'),
        PaletteItem('page', 'nav.live_attention',  '/live/attention',   keywords='live timeline'),
        PaletteItem('page', 'nav.docs',            '/docs',             keywords='documentation'),
        PaletteItem('page', 'nav.coverage',        '/coverage',         keywords='coverage'),
        PaletteItem('page', 'nav.jobs',            '/jobs',             keywords='jobs'),
        PaletteItem('page', 'nav.operations',      '/audits',           keywords='audit'),
    ]


def _actions() -> list[PaletteItem]:
    return [
        PaletteItem('action', 'palette.action.convert',  '/convert', keywords='generate integration'),
        PaletteItem('action', 'palette.action.install',  '/install', keywords='deploy'),
        PaletteItem('action', 'palette.action.compact',  '/compact', keywords='compress refs'),
        PaletteItem('action', 'palette.action.audits',   '/audits',  keywords='payload parity attention'),
        PaletteItem('action', 'palette.action.health',   '/health',  keywords='status'),
    ]


def _agents(cfg) -> list[PaletteItem]:
    if cfg.is_framework:
        rows = catalog_loader.list_agents(cfg.root / 'agents')
    elif cfg.framework_root:
        rows = catalog_loader.list_agents(cfg.framework_root / 'agents')
    else:
        return []
    out: list[PaletteItem] = []
    for a in rows:
        href = f'/agents/{a.slug}/edit' if cfg.is_framework else '/catalog/agents'
        out.append(PaletteItem(
            category='agent',
            label=a.name,
            href=href,
            hint=f'{a.emoji} · {a.tier}',
            keywords=a.slug,
        ))
    return out


def _skills(cfg) -> list[PaletteItem]:
    if cfg.is_framework:
        rows = catalog_loader.list_skills(cfg.root / 'skills')
    elif cfg.framework_root:
        rows = catalog_loader.list_skills(cfg.framework_root / 'skills')
    else:
        return []
    out: list[PaletteItem] = []
    for s in rows:
        href = f'/skills/{s.slug}/edit' if cfg.is_framework else '/catalog/skills'
        out.append(PaletteItem(
            category='skill',
            label=s.name,
            href=href,
            hint=s.slug,
            keywords=(s.description or '')[:60],
        ))
    return out


def _docs(cfg) -> list[PaletteItem]:
    try:
        entries = doc_loader.list_docs(cfg.root)
    except Exception:
        return []
    out: list[PaletteItem] = []
    for d in entries[:60]:  # cap to keep payload small
        out.append(PaletteItem(
            category='doc',
            label=d.title or d.rel,
            href=f'/docs/view?p={d.rel}',
            hint=d.audience,
            keywords=d.rel,
        ))
    return out


@router.get('/palette', response_class=HTMLResponse)
async def palette(request: Request) -> HTMLResponse:
    cfg       = request.app.state.config
    templates = request.app.state.templates
    items: list[PaletteItem] = []
    items += _pages()
    items += _actions()
    items += _agents(cfg)
    items += _skills(cfg)
    items += _docs(cfg)
    return templates.TemplateResponse(
        request,
        '_components/palette_modal.html',
        {'items': items},
    )
