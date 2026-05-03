"""live.py — R13 / Onda 4 live observability pages.

Three pages:
  /live/session           — full page, event tail with HTMX 2s polling
  /live/session/partial   — HTMX swap target, accepts ?agent= ?skill= ?kind=
  /live/routing           — sankey-lite (agent → skill bars)
  /live/attention         — SVG scatter timeline of attention scores

All read-only; events come from .orquestrum/metrics/events.jsonl,
attention scores from docs/03-quality/**.md frontmatter.
"""
from __future__ import annotations
import datetime as dt
from typing import Any

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse

from ui.lib import live_metrics
from ui.lib.attention import attention_timeline, scatter_points

router = APIRouter()

_TAIL_LIMIT = 50


def _filter_value(raw: str | None) -> str | None:
    """HTML <select> with empty option submits ''. Treat as no filter."""
    return raw if raw else None


def _session_payload(cfg, agent: str | None, skill: str | None, kind: str | None) -> dict[str, Any]:
    events = live_metrics.events_for(cfg.metrics_dir)
    return {
        'events':  live_metrics.recent_events(
            events, limit=_TAIL_LIMIT,
            agent=agent, skill=skill, kind=kind,
        ),
        'facets':  live_metrics.event_facets(events),
        'density': live_metrics.event_density(events, buckets=30, bucket_minutes=2),
        'agent':   agent,
        'skill':   skill,
        'kind':    kind,
        'limit':   _TAIL_LIMIT,
    }


@router.get('/live/session', response_class=HTMLResponse)
async def session_page(request: Request,
                       agent: str | None = Query(default=None),
                       skill: str | None = Query(default=None),
                       kind:  str | None = Query(default=None)) -> HTMLResponse:
    cfg = request.app.state.config
    return request.app.state.templates.TemplateResponse(
        request,
        'live_session.html',
        _session_payload(cfg,
                         _filter_value(agent),
                         _filter_value(skill),
                         _filter_value(kind)),
    )


@router.get('/live/session/partial', response_class=HTMLResponse)
async def session_partial(request: Request,
                          agent: str | None = Query(default=None),
                          skill: str | None = Query(default=None),
                          kind:  str | None = Query(default=None)) -> HTMLResponse:
    """HTMX-swapped event tail (must match the wrapper id in live_session.html)."""
    cfg = request.app.state.config
    return request.app.state.templates.TemplateResponse(
        request,
        '_components/event_tail.html',
        _session_payload(cfg,
                         _filter_value(agent),
                         _filter_value(skill),
                         _filter_value(kind)),
    )


@router.get('/live/routing', response_class=HTMLResponse)
async def routing_page(request: Request) -> HTMLResponse:
    cfg    = request.app.state.config
    events = live_metrics.events_for(cfg.metrics_dir)
    rows   = live_metrics.routing_matrix(events, days=7)
    return request.app.state.templates.TemplateResponse(
        request,
        'live_routing.html',
        {'rows': rows, 'days': 7},
    )


@router.get('/live/attention', response_class=HTMLResponse)
async def attention_page(request: Request) -> HTMLResponse:
    cfg   = request.app.state.config
    root  = cfg.linked_project_root or cfg.root
    items = attention_timeline(root, days=30)
    pts   = scatter_points(items, width=800, height=240, padding=28)
    bands = {'green': 0, 'yellow': 0, 'red': 0}
    for it in items:
        bands[it.band] += 1
    return request.app.state.templates.TemplateResponse(
        request,
        'live_attention.html',
        {
            'points':     pts,
            'items':      items,
            'bands':      bands,
            'days':       30,
            'svg_width':  800,
            'svg_height': 240,
            'svg_padding': 28,
        },
    )
