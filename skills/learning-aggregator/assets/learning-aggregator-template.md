---
version: "v{N}"
generated_at: "{YYYY-MM-DD}"
documents_analyzed: {COUNT}
status: Active
---

# Learning Summary — v{N}

**Period / scope:** {e.g., Sprint 3 / Phase 4 / all learnings to date}
**Documents analyzed:** {COUNT} (`L-XXX` files)
**Patterns found:** {PATTERN_COUNT}

---

## Recurring Patterns

<!-- One section per cluster with 2+ occurrences, ordered by frequency desc -->

### P-01 — {Pattern Name}

**Occurrences:** {N} | **Impact:** High / Medium / Low
**Affected documents:** {L-001, L-003, L-007}

**Description:** {One paragraph describing the recurring failure mode.}

**Prevention recommendation:** {Concrete action — convention change, checklist item, or tooling suggestion.}

---

### P-02 — {Pattern Name}

**Occurrences:** {N} | **Impact:** High / Medium / Low
**Affected documents:** {L-002, L-005}

**Description:** {One paragraph.}

**Prevention recommendation:** {Concrete action.}

---

## Isolated Incidents

Single-occurrence signals not yet confirmed as patterns. Monitor in future aggregations.

| ID | Title | Root cause summary |
|----|-------|--------------------|
| L-XXX | {Title} | {One sentence} |

---

## Systemic Observations

{Optional. Cross-cutting observations that don't fit a single cluster — e.g., "3 of 5 failures occurred during phase transitions", "all High-impact incidents involved external API calls".)

---

## Recommended Actions

Priority-ordered list of concrete next steps derived from patterns above.

1. **{Action 1}** — addresses P-01, P-02. Owner: {agent/team}. Target: {phase or sprint}.
2. **{Action 2}** — addresses P-03. Owner: {agent/team}.
3. **{Action 3}** — monitoring recommendation for isolated incidents.
