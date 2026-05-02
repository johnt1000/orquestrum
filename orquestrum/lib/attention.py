"""attention.py — deterministic human-attention scoring for artifacts.

Single source of truth for the formula that turns countable signals
(confidence rating, drift age, inference depth, context completeness,
gate failures, test coverage delta) into a 0–100 score and a 3-band
visual signal.

NO LLM IS CALLED. Score is computed from inputs alone — by design.
LLMs systematically inflate self-assessment.

See docs/agent-context/CONVENTIONS.md → Human Attention Mediation for usage.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Literal


Band = Literal['green', 'yellow', 'red']

# Confidence rating textual → numeric mapping
CONFIDENCE_NUMERIC: dict[str, float] = {
    'high':   1.0,
    'medium': 0.6,
    'low':    0.3,
    'unknown': 0.5,
}

# Inference depth textual → numeric (only used if caller passes a string)
INFERENCE_DEPTH_NUMERIC: dict[str, int] = {
    'verbatim':    0,
    'summarized':  1,
    'inferred':    2,
    'speculative': 3,
}


@dataclass
class AttentionInputs:
    confidence:            float = 1.0   # ∈ [0, 1]
    drift_days:            int   = 0
    inference_depth:       int   = 0     # 0..3
    context_completeness:  float = 1.0   # ∈ [0, 1]
    gate_failure_count:    int   = 0
    test_coverage_delta:   float = 0.0   # negative = regression, positive = improvement
    upstream_scores:       list[int] = field(default_factory=list)  # for propagation cap


@dataclass
class AttentionResult:
    score:    int                          # ∈ [0, 100], lower = more attention
    band:     Band                         # green | yellow | red
    factors:  list[str]                    # human-readable list of dominant deductions
    capped_by_upstream: bool = False       # True when propagation rule lowered the score

    def emoji(self) -> str:
        return {'green': '🟢', 'yellow': '🟡', 'red': '🔴'}[self.band]

    def to_frontmatter(self) -> dict:
        """Frontmatter shape to embed in artifact YAML."""
        return {
            'attention_score':   self.score,
            'attention_band':    self.band,
            'attention_factors': self.factors,
        }


def _band_for(score: int) -> Band:
    if score >= 80:
        return 'green'
    if score >= 50:
        return 'yellow'
    return 'red'


def compute(inputs: AttentionInputs) -> AttentionResult:
    """Apply the deterministic formula. No randomness, no LLM call.

    Formula (lower score = more human attention required):
      score = 100
        - 25 * (1 - confidence)
        - min(20, drift_days / 2)
        - 10 * inference_depth                  # 0..3 → 0..30 deduction
        -  5 * gate_failure_count
        - 15 * (1 - context_completeness)
        +  5 if test_coverage_delta > 0 else 0
      clamp [0, 100]

    Then apply propagation cap:
      score = min(score, max(upstream_scores) + 10)
      (only if upstream_scores non-empty)
    """
    factors: list[str] = []
    score = 100.0

    if inputs.confidence < 1.0:
        deduct = 25 * (1 - inputs.confidence)
        score -= deduct
        if deduct >= 5:
            factors.append(f'confidence:{inputs.confidence:.2f}')

    if inputs.drift_days > 0:
        deduct = min(20.0, inputs.drift_days / 2)
        score -= deduct
        if inputs.drift_days >= 30:
            factors.append(f'drift_days:{inputs.drift_days}')

    if inputs.inference_depth > 0:
        deduct = 10 * inputs.inference_depth
        score -= deduct
        factors.append(f'inference_depth:{inputs.inference_depth}')

    if inputs.gate_failure_count > 0:
        score -= 5 * inputs.gate_failure_count
        factors.append(f'gate_failures:{inputs.gate_failure_count}')

    if inputs.context_completeness < 1.0:
        deduct = 15 * (1 - inputs.context_completeness)
        score -= deduct
        if deduct >= 5:
            factors.append(f'context_incomplete:{1 - inputs.context_completeness:.2f}')

    if inputs.test_coverage_delta > 0:
        score += 5

    score = max(0.0, min(100.0, score))
    capped = False

    if inputs.upstream_scores:
        cap = max(inputs.upstream_scores) + 10
        if score > cap:
            score = float(cap)
            capped = True
            factors.append(f'capped_by_upstream:{max(inputs.upstream_scores)}')

    final = int(round(score))
    return AttentionResult(
        score=final,
        band=_band_for(final),
        factors=factors,
        capped_by_upstream=capped,
    )


# ─── Convenience helpers for skill authors ────────────────────────────────────

def parse_confidence(value: str | float | int | None) -> float:
    """Accept 'high'|'medium'|'low'|'unknown' or raw 0..1 numeric."""
    if value is None:
        return 0.5
    if isinstance(value, (int, float)):
        return float(max(0.0, min(1.0, value)))
    return CONFIDENCE_NUMERIC.get(str(value).lower(), 0.5)


def parse_inference_depth(value: str | int | None) -> int:
    if value is None:
        return 0
    if isinstance(value, int):
        return max(0, min(3, value))
    return INFERENCE_DEPTH_NUMERIC.get(str(value).lower(), 0)


def days_since(iso_date: str | None) -> int:
    """Return days between today and an ISO date string. Returns 0 if missing/invalid."""
    if not iso_date:
        return 0
    try:
        d = datetime.fromisoformat(iso_date).date() if 'T' in iso_date else date.fromisoformat(iso_date)
    except (ValueError, TypeError):
        return 0
    return max(0, (date.today() - d).days)
