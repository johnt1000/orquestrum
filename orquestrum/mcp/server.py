"""orquestrum.mcp.server — FastMCP server exposing orq_* tools.

Architecture
------------
Thin adapter over `orquestrum.lib.metrics`, `lib.budget`, `lib.registry`,
`lib.paths`. Every tool either reads the per-project events.jsonl (via
`read_events`/`aggregate`) or appends one line (`append_event`). No new
storage format; this server is read/write API on top of the same JSONL
the Stop hook already produces.

Project resolution
------------------
Tools that operate on "the current project" use `paths.find_project_root()`
(walks up from cwd looking for `.orquestrum/`). Tools that take a
`project` argument resolve via `registry.find_by_name()` against
`~/.orquestrum/registry.toml`.

When neither resolves, tools return a structured error with actionable
suggestion (e.g. "run orquestrum init here, or pass project=<name>").
"""
from __future__ import annotations
import datetime as dt
import json
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP
from pydantic import ValidationError

from orquestrum import __version__
from orquestrum.lib import paths, registry
from orquestrum.lib.budget import check_session_budget
from orquestrum.lib.metrics import (
    append_event, aggregate, read_events, rebuild_session, now_iso,
)
from orquestrum.lib.models import AGENT_TIERS

from orquestrum.mcp.schemas import (
    BudgetStatusInput, CostTodayInput, ProjectSummaryInput,
    RecentEventsInput, RecordEventInput, SessionSummaryInput,
    SkillCompletedInput,
)


_INSTRUCTIONS = """\
Orquestrum metrics and routing-context server.

Use these tools to:
  • Record rich domain events the Stop hook can't capture
    (orq_skill_completed for gates/artifacts/confidence).
  • Query session state mid-turn (orq_session_summary, orq_budget_status).
  • Aggregate across projects (orq_cost_today, orq_list_projects).
  • Inspect history (orq_recent_events with filters).

The Stop / SubagentStop hook in ~/.claude/settings.json is the source of
truth for raw token counts. This server adds domain semantics on top.
"""


mcp = FastMCP(
    name='orquestrum',
    instructions=_INSTRUCTIONS,
)


# ─── helpers (resolution + error formatting) ────────────────────────────────


class _ToolError(Exception):
    """Raised inside a tool to short-circuit with an actionable message."""


def _resolve_project_root(project: str | None) -> Path:
    """Resolve a project name (or None=current) to its abs root.

    Raises _ToolError with a user-friendly message when nothing matches.
    """
    if project:
        entry = registry.find_by_name(project)
        if entry is None:
            registered = [p['name'] for p in registry.load_registry()]
            raise _ToolError(
                f"project '{project}' is not in the registry. "
                f"Registered: {registered or '(none)'}. "
                f"Run `orquestrum repos add <path>` to register."
            )
        return Path(entry['path'])

    root = paths.find_project_root()
    if root is None:
        raise _ToolError(
            'no .orquestrum/ found walking up from cwd. '
            'Run `orquestrum init` here, or pass project=<name>.'
        )
    return root


def _metrics_dir(project_root: Path) -> Path:
    return project_root / '.orquestrum' / 'metrics'


def _events_path(project_root: Path) -> Path:
    return _metrics_dir(project_root) / 'events.jsonl'


def _format_error(exc: Exception) -> dict[str, Any]:
    """Uniform error envelope for tool returns."""
    return {
        'ok':    False,
        'error': str(exc),
        'kind':  type(exc).__name__,
    }


def _validate(model_cls, raw: dict[str, Any]):
    """Pydantic-validate or convert the ValidationError into a flat error
    string the agent can act on without parsing pydantic internals."""
    try:
        return model_cls(**raw)
    except ValidationError as e:
        msgs = [f"{'.'.join(str(p) for p in err['loc'])}: {err['msg']}"
                for err in e.errors()]
        raise _ToolError('; '.join(msgs)) from e


# ─── tools ───────────────────────────────────────────────────────────────────


@mcp.tool(
    annotations={'destructiveHint': True, 'idempotentHint': False,
                 'readOnlyHint': False, 'openWorldHint': False},
)
def orq_record_event(
    agent: str,
    model: str,
    in_tokens: int,
    out_tokens: int,
    skill: str | None = None,
    tier: str = 'balanced',
    cached_tokens: int = 0,
    duration_ms: int | None = None,
) -> dict[str, Any]:
    """Append one llm_call event to the current project's events.jsonl.

    Use SPARINGLY — the Stop / SubagentStop hook in settings.json is the
    canonical source of token usage (Claude Code's API counters are the
    only authoritative number). Call this tool only when you have token
    info the hook cannot capture (e.g. external model calls outside the
    Anthropic transport).

    Returns: {ok, event_path, written_event} on success, {ok=false, error}
    on validation or filesystem failure.
    """
    try:
        validated = _validate(RecordEventInput, dict(
            agent=agent, model=model, in_tokens=in_tokens, out_tokens=out_tokens,
            skill=skill, tier=tier, cached_tokens=cached_tokens,
            duration_ms=duration_ms,
        ))
        root = _resolve_project_root(None)
        events_path = _events_path(root)

        event = {
            'ts':            now_iso(),
            'kind':          'llm_call',
            'agent':         validated.agent,
            'skill':         validated.skill or '(no-skill)',
            'tier':          validated.tier,
            'model':         validated.model,
            'in_tokens':     validated.in_tokens,
            'out_tokens':    validated.out_tokens,
            'cached_tokens': validated.cached_tokens,
            'cost_usd':      _estimate_cost_safe(validated.model,
                                                 validated.in_tokens,
                                                 validated.out_tokens),
            'duration_ms':   validated.duration_ms,
            'source':        'mcp',  # distinguishes from hook-emitted events
        }
        append_event(events_path, event)
        return {'ok': True, 'event_path': str(events_path), 'written_event': event}
    except _ToolError as e:
        return _format_error(e)


@mcp.tool(
    annotations={'destructiveHint': True, 'idempotentHint': False,
                 'readOnlyHint': False, 'openWorldHint': False},
)
def orq_skill_completed(
    skill: str,
    agent: str,
    status: str,
    gates_passed: int = 0,
    gates_failed: int = 0,
    artifacts_emitted: list[str] | None = None,
    confidence_avg: float | None = None,
) -> dict[str, Any]:
    """Emit a skill_completion event (gates_passed, artifacts_emitted,
    confidence_avg) — fields the Stop hook cannot capture.

    Call this at the end of every skill execution so the dashboard +
    learning-aggregator can see gate pass rates and confidence drift.
    """
    try:
        validated = _validate(SkillCompletedInput, dict(
            skill=skill, agent=agent, status=status,
            gates_passed=gates_passed, gates_failed=gates_failed,
            artifacts_emitted=artifacts_emitted or [],
            confidence_avg=confidence_avg,
        ))
        root = _resolve_project_root(None)
        events_path = _events_path(root)

        event = {
            'ts':                now_iso(),
            'kind':              'skill_completion',
            'skill':             validated.skill,
            'agent':             validated.agent,
            'status':            validated.status,
            'gates_passed':      validated.gates_passed,
            'gates_failed':      validated.gates_failed,
            'artifacts_emitted': validated.artifacts_emitted,
            'confidence_avg':    validated.confidence_avg,
            'source':            'mcp',
        }
        append_event(events_path, event)
        return {'ok': True, 'event_path': str(events_path), 'written_event': event}
    except _ToolError as e:
        return _format_error(e)


@mcp.tool(
    annotations={'readOnlyHint': True, 'idempotentHint': True,
                 'openWorldHint': False},
)
def orq_session_summary(
    project: str | None = None,
    tier: str | None = None,
) -> dict[str, Any]:
    """Aggregated session totals + by-skill + by-agent breakdown.

    Rebuilds session.json from events.jsonl on every call, so reads always
    reflect the latest hook + MCP writes.
    """
    try:
        validated = _validate(SessionSummaryInput,
                              dict(project=project, tier=tier))
        root = _resolve_project_root(validated.project)
        sess = rebuild_session(_metrics_dir(root), tier=validated.tier)
        return {'ok': True, 'project_path': str(root), **sess.to_dict()}
    except _ToolError as e:
        return _format_error(e)


@mcp.tool(
    annotations={'readOnlyHint': True, 'idempotentHint': True,
                 'openWorldHint': False},
)
def orq_budget_status(
    tier: str,
    project: str | None = None,
) -> dict[str, Any]:
    """Soft-threshold budget check for a tier. Returns input/output token
    usage, thresholds, and whether the session is above / approaching limits.
    """
    try:
        validated = _validate(BudgetStatusInput,
                              dict(tier=tier, project=project))
        root = _resolve_project_root(validated.project)
        # rebuild_session ensures session.json is current before budget reads it
        rebuild_session(_metrics_dir(root), tier=validated.tier)
        report = check_session_budget(_metrics_dir(root) / 'session.json',
                                      validated.tier)
        # check_session_budget always returns a BudgetReport (zeros when no
        # session.json yet), so we can read attributes without a None check.
        pct_in  = (report.input_tokens  / report.input_threshold) \
                  if report.input_threshold else 0.0
        pct_out = (report.output_tokens / report.output_threshold) \
                  if report.output_threshold else 0.0
        return {
            'ok':                 True,
            'tier':               validated.tier,
            'project_path':       str(root),
            'input_tokens':       report.input_tokens,
            'output_tokens':      report.output_tokens,
            'input_threshold':    report.input_threshold,
            'output_threshold':   report.output_threshold,
            'over_input':         report.over_input,
            'over_output':        report.over_output,
            'pct_input':          round(pct_in, 4),
            'pct_output':         round(pct_out, 4),
            'has_warning':        report.has_warning,
            'top_contributor':    report.top_contributor,
            'top_contributor_in': report.top_contributor_in,
        }
    except _ToolError as e:
        return _format_error(e)


@mcp.tool(
    annotations={'readOnlyHint': True, 'idempotentHint': True,
                 'openWorldHint': False},
)
def orq_recent_events(
    project: str | None = None,
    since_iso: str | None = None,
    agent: str | None = None,
    kind: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    """Return up to `limit` recent events matching the filters.

    Filters compose with AND semantics. `since_iso` is exclusive (events
    strictly newer than the timestamp). Default order: most recent first.
    """
    try:
        validated = _validate(RecentEventsInput, dict(
            project=project, since_iso=since_iso, agent=agent,
            kind=kind, limit=limit,
        ))
        root = _resolve_project_root(validated.project)
        events = read_events(_events_path(root))

        if validated.since_iso:
            events = [e for e in events
                      if e.get('ts') and e['ts'] > validated.since_iso]
        if validated.agent:
            events = [e for e in events if e.get('agent') == validated.agent]
        if validated.kind:
            events = [e for e in events if e.get('kind') == validated.kind]

        events.sort(key=lambda e: e.get('ts') or '', reverse=True)
        events = events[:validated.limit]
        return {'ok': True, 'project_path': str(root),
                'count': len(events), 'events': events}
    except _ToolError as e:
        return _format_error(e)


@mcp.tool(
    annotations={'readOnlyHint': True, 'idempotentHint': True,
                 'openWorldHint': False},
)
def orq_list_projects() -> dict[str, Any]:
    """List every project registered in ~/.orquestrum/registry.toml,
    each with a quick summary (last_event_ts, total_calls, total_cost_usd).
    """
    rows: list[dict[str, Any]] = []
    for entry in registry.load_registry():
        path = Path(entry['path'])
        events = read_events(path / '.orquestrum' / 'metrics' / 'events.jsonl') \
            if path.is_dir() else []
        last_ts = max((e.get('ts') or '' for e in events), default='')
        cost = round(sum(float(e.get('cost_usd') or 0) for e in events), 6)
        rows.append({
            'name':           entry.get('name'),
            'path':           entry.get('path'),
            'tool':           entry.get('tool'),
            'provider':       entry.get('provider'),
            'last_event_ts':  last_ts or None,
            'total_calls':    sum(1 for e in events if e.get('kind') == 'llm_call'),
            'total_cost_usd': cost,
            'path_exists':    path.is_dir(),
        })
    return {'ok': True, 'count': len(rows), 'projects': rows}


@mcp.tool(
    annotations={'readOnlyHint': True, 'idempotentHint': True,
                 'openWorldHint': False},
)
def orq_project_summary(project: str) -> dict[str, Any]:
    """Aggregated session totals for a SPECIFIC registered project.
    Same shape as orq_session_summary but does not require cwd to be
    inside the project."""
    try:
        validated = _validate(ProjectSummaryInput, dict(project=project))
        root = _resolve_project_root(validated.project)
        sess = rebuild_session(_metrics_dir(root))
        return {'ok': True, 'project_path': str(root), **sess.to_dict()}
    except _ToolError as e:
        return _format_error(e)


@mcp.tool(
    annotations={'readOnlyHint': True, 'idempotentHint': True,
                 'openWorldHint': False},
)
def orq_cost_today(
    project: str | None = None,
    date_iso: str | None = None,
) -> dict[str, Any]:
    """Sum of cost_usd for events emitted on a calendar day (UTC).

    With no arguments: sums across every registered project for today.
    With `project`: scope to one project. With `date_iso` (YYYY-MM-DD):
    query a different day.
    """
    try:
        validated = _validate(CostTodayInput,
                              dict(project=project, date_iso=date_iso))
        target_day = validated.date_iso or dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%d')

        if validated.project:
            roots = [_resolve_project_root(validated.project)]
        else:
            roots = []
            for entry in registry.load_registry():
                p = Path(entry['path'])
                if p.is_dir():
                    roots.append(p)

        total_cost = 0.0
        per_project: list[dict[str, Any]] = []
        total_calls = 0
        for root in roots:
            events = read_events(_events_path(root))
            day_events = [e for e in events
                          if (e.get('ts') or '').startswith(target_day)]
            sub_cost = round(sum(float(e.get('cost_usd') or 0)
                                 for e in day_events), 6)
            sub_calls = sum(1 for e in day_events if e.get('kind') == 'llm_call')
            total_cost = round(total_cost + sub_cost, 6)
            total_calls += sub_calls
            per_project.append({
                'project_path': str(root),
                'cost_usd':     sub_cost,
                'calls':        sub_calls,
            })

        return {
            'ok':            True,
            'date':          target_day,
            'total_cost_usd': total_cost,
            'total_calls':    total_calls,
            'per_project':    per_project,
        }
    except _ToolError as e:
        return _format_error(e)


# ─── resources ──────────────────────────────────────────────────────────────


@mcp.resource('orq://session/current')
def _resource_current_session() -> str:
    """JSON of the current project's aggregated session. Empty object when
    cwd is not inside an Orquestrum project."""
    root = paths.find_project_root()
    if root is None:
        return json.dumps({'project': None,
                           'message': 'no .orquestrum/ at or above cwd'})
    sess = rebuild_session(_metrics_dir(root))
    return json.dumps({'project_path': str(root), **sess.to_dict()},
                      indent=2, ensure_ascii=False)


@mcp.resource('orq://projects')
def _resource_projects() -> str:
    """JSON list of every registered project."""
    rows = registry.load_registry()
    return json.dumps({'count': len(rows), 'projects': rows},
                      indent=2, ensure_ascii=False)


# ─── helpers ────────────────────────────────────────────────────────────────


def _estimate_cost_safe(model: str, in_tokens: int, out_tokens: int) -> float:
    """Wrap lib.models.estimate_cost so import failures never crash a tool.

    Mirrors the defensive pattern already used in
    orquestrum/core/hooks/emit_metrics.py — a dependency change should
    never block metric emission.
    """
    try:
        from orquestrum.lib.models import estimate_cost
        return round(estimate_cost(model, in_tokens, out_tokens), 6)
    except Exception:
        return 0.0


# ─── entry point ────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> None:
    """Start the MCP server on stdio. Called by `orquestrum mcp`."""
    # FastMCP's run() blocks on stdio. We don't accept argv flags today;
    # accepted as a list for symmetry with other orquestrum core entries.
    _ = argv
    mcp.run()


if __name__ == '__main__':
    main()
