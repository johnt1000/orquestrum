"""orquestrum.mcp.schemas — Pydantic input schemas for MCP tools.

Strict validation: any deviation (unknown tier, invalid kind, malformed
timestamp) produces an actionable error message at tool boundary instead
of a corrupt event line in events.jsonl.

The enums are wired to the canonical sources of truth in `lib.models`
so adding a tier/agent in one place updates validation everywhere.
"""
from __future__ import annotations
from typing import Literal

from pydantic import BaseModel, Field, field_validator


# Tier values must match lib.models.ModelTier. Hard-coded as Literal here
# so the JSON schema FastMCP generates includes the enum constraint.
Tier = Literal['deep', 'sharp', 'balanced', 'mechanical', 'unknown']

# Event kind matches the schema in lib/metrics.py docstring.
EventKind = Literal['llm_call', 'skill_completion']

# Skill completion status — used by Ward/Forge gates.
CompletionStatus = Literal['completed', 'failed', 'partial']


class RecordEventInput(BaseModel):
    """Input for `orq_record_event` — appends one llm_call event to the
    current project's events.jsonl. Use this when the agent has explicit
    knowledge of token usage that the Stop hook cannot capture (rare —
    prefer letting the hook be the source of truth)."""

    agent: str = Field(
        ...,
        description='Agent name. Should match one of the canonical agents in '
                    'AGENT_TIERS (e.g. "Helm - The Architect"); free-form is '
                    'allowed but tier resolution will fall back to "unknown".',
    )
    skill: str | None = Field(
        default=None,
        description='Skill being executed (optional). Leave None for top-level '
                    'agent turns that are not running a specific skill.',
    )
    tier: Tier = Field(
        default='balanced',
        description='Model tier. Must be one of: deep, sharp, balanced, '
                    'mechanical, unknown.',
    )
    model: str = Field(
        ...,
        description='Model identifier, e.g. "anthropic/claude-sonnet-4-6". '
                    'Bare names are auto-prefixed with "anthropic/" by the '
                    'cost calculator.',
    )
    in_tokens: int = Field(..., ge=0, description='Input tokens consumed.')
    out_tokens: int = Field(..., ge=0, description='Output tokens emitted.')
    cached_tokens: int = Field(default=0, ge=0,
                               description='Cache-read input tokens (free).')
    duration_ms: int | None = Field(
        default=None, ge=0,
        description='End-to-end duration of the call in milliseconds.',
    )


class SkillCompletedInput(BaseModel):
    """Input for `orq_skill_completed` — emits a skill_completion event
    with the rich fields (gates_passed, artifacts_emitted, confidence_avg)
    that the Stop hook cannot capture."""

    skill: str = Field(..., min_length=1,
                       description='Skill name, e.g. "task-manager".')
    agent: str = Field(..., min_length=1,
                       description='Agent that ran the skill.')
    status: CompletionStatus = Field(
        ...,
        description='Outcome: completed | failed | partial.',
    )
    gates_passed: int = Field(default=0, ge=0,
                              description='Number of validation gates that passed.')
    gates_failed: int = Field(default=0, ge=0,
                              description='Number of validation gates that failed.')
    artifacts_emitted: list[str] = Field(
        default_factory=list,
        description='List of artifact identifiers (paths or task IDs) the '
                    'skill produced. Used for traceability.',
    )
    confidence_avg: float | None = Field(
        default=None, ge=0.0, le=1.0,
        description='Mean confidence (0.0–1.0) across the skill\'s outputs, '
                    'when the skill emits per-output confidence.',
    )


class SessionSummaryInput(BaseModel):
    """Input for `orq_session_summary` — current project's aggregated
    metrics. Defaults to the project at the server's cwd; pass `project`
    to scope to a registered project by name."""

    project: str | None = Field(
        default=None,
        description='Registered project name (from registry.toml). When None, '
                    'resolves the project at the server\'s working directory.',
    )
    tier: Tier | None = Field(
        default=None,
        description='Optional tier annotation included in the summary.',
    )


class BudgetStatusInput(BaseModel):
    """Input for `orq_budget_status` — soft-threshold check for a tier."""

    tier: Tier = Field(
        ...,
        description='Tier whose budget thresholds are checked.',
    )
    project: str | None = Field(
        default=None,
        description='Registered project name. None → current project.',
    )

    @field_validator('tier')
    @classmethod
    def _reject_unknown(cls, v: str) -> str:
        # `unknown` makes no sense for budget queries — there are no thresholds.
        if v == 'unknown':
            raise ValueError(
                'tier must be one of: deep, sharp, balanced, mechanical '
                '(unknown has no defined budget thresholds)'
            )
        return v


class RecentEventsInput(BaseModel):
    """Input for `orq_recent_events` — filtered query over events.jsonl.
    All filters are optional; combine to narrow the result."""

    project: str | None = Field(
        default=None,
        description='Registered project name. None → current project.',
    )
    since_iso: str | None = Field(
        default=None,
        description='ISO-8601 timestamp; events strictly newer are returned. '
                    'Example: "2026-05-03T00:00:00Z".',
    )
    agent: str | None = Field(
        default=None,
        description='Filter by agent name (exact match).',
    )
    kind: EventKind | None = Field(
        default=None,
        description='Filter by event kind (llm_call | skill_completion).',
    )
    limit: int = Field(
        default=50, ge=1, le=1000,
        description='Maximum events to return. Server enforces hard cap of 1000.',
    )


class ProjectSummaryInput(BaseModel):
    """Input for `orq_project_summary` — aggregate for ANY registered project."""

    project: str = Field(
        ..., min_length=1,
        description='Registered project name (required — no default).',
    )


class CostTodayInput(BaseModel):
    """Input for `orq_cost_today` — sum of cost_usd for events emitted today
    (UTC). With no args, sums across every registered project."""

    project: str | None = Field(
        default=None,
        description='Limit to one project. None → all registered projects.',
    )
    date_iso: str | None = Field(
        default=None,
        description='Calendar day (UTC) to query, ISO-8601 date "YYYY-MM-DD". '
                    'Defaults to today.',
    )
