"""budget.py — per-tier session token budgets.

Soft warnings only — sessions are never auto-stopped. The operator decides
whether to continue, split, or adjust settings when a threshold is hit.

See docs/governance/COST.md for thresholds and rationale.
"""
from dataclasses import dataclass
from pathlib import Path
import json


# Soft warning thresholds (input tokens, output tokens) per tier.
# Tune these by analyzing the p90 of real sessions — see docs/governance/COST.md.
SOFT_THRESHOLDS: dict[str, tuple[int, int]] = {
    'deep':       (200_000, 16_000),
    'balanced':   (100_000,  8_000),
    'mechanical': ( 30_000,  2_000),
    'sharp':      (100_000,  8_000),  # treat sharp like balanced for budget
}


@dataclass
class BudgetReport:
    tier:              str
    input_tokens:      int
    output_tokens:     int
    input_threshold:   int
    output_threshold:  int
    over_input:        bool
    over_output:       bool
    top_contributor:   str | None     # name of skill/agent with highest spend
    top_contributor_in: int            # its input-token contribution

    @property
    def has_warning(self) -> bool:
        return self.over_input or self.over_output

    def format(self) -> str:
        lines: list[str] = []
        if self.over_input:
            lines.append(
                f'⚠ Budget exceeded: {self.tier} tier session has consumed '
                f'{self.input_tokens:,} input tokens (threshold {self.input_threshold:,}).'
            )
        if self.over_output:
            lines.append(
                f'⚠ Budget exceeded: {self.tier} tier session has emitted '
                f'{self.output_tokens:,} output tokens (threshold {self.output_threshold:,}).'
            )
        if self.has_warning and self.top_contributor:
            lines.append(
                f'  top contributor: {self.top_contributor} — {self.top_contributor_in:,} input tokens'
            )
            lines.append(
                f'  consider: split the session, switch to inject_references: compact, '
                f'or reduce reference loading depth'
            )
        return '\n'.join(lines)


def check_session_budget(session_json: Path, tier: str) -> BudgetReport:
    """Read .orquestrum/metrics/session.json and return a BudgetReport.

    Expected schema:
        {
          "tier": "balanced",
          "totals": {"input_tokens": 132000, "output_tokens": 5400, ...},
          "by_skill": {"review-manager": {"input_tokens": 48000, ...}, ...}
        }

    Returns a report with all-zero values if the file is missing or malformed.
    """
    in_thr, out_thr = SOFT_THRESHOLDS.get(tier, SOFT_THRESHOLDS['balanced'])

    if not session_json.exists():
        return BudgetReport(
            tier=tier, input_tokens=0, output_tokens=0,
            input_threshold=in_thr, output_threshold=out_thr,
            over_input=False, over_output=False,
            top_contributor=None, top_contributor_in=0,
        )

    try:
        data = json.loads(session_json.read_text(encoding='utf-8'))
    except (json.JSONDecodeError, OSError):
        return BudgetReport(
            tier=tier, input_tokens=0, output_tokens=0,
            input_threshold=in_thr, output_threshold=out_thr,
            over_input=False, over_output=False,
            top_contributor=None, top_contributor_in=0,
        )

    totals = data.get('totals', {})
    in_t   = int(totals.get('input_tokens',  0))
    out_t  = int(totals.get('output_tokens', 0))

    by_skill = data.get('by_skill') or {}
    top_name: str | None = None
    top_in = 0
    for name, stats in by_skill.items():
        contrib = int((stats or {}).get('input_tokens', 0))
        if contrib > top_in:
            top_in = contrib
            top_name = name

    return BudgetReport(
        tier=tier,
        input_tokens=in_t,
        output_tokens=out_t,
        input_threshold=in_thr,
        output_threshold=out_thr,
        over_input=in_t > in_thr,
        over_output=out_t > out_thr,
        top_contributor=top_name,
        top_contributor_in=top_in,
    )


def is_session_capped(session_json: Path, tier: str, hard_caps: dict[str, int] | None = None) -> bool:
    """Return True if a hard cap (from pyproject.toml) is set and exceeded."""
    if not hard_caps:
        return False
    cap = hard_caps.get(f'{tier}_input_max')
    if cap is None:
        return False
    if not session_json.exists():
        return False
    try:
        data = json.loads(session_json.read_text(encoding='utf-8'))
    except (json.JSONDecodeError, OSError):
        return False
    return int(data.get('totals', {}).get('input_tokens', 0)) > cap
