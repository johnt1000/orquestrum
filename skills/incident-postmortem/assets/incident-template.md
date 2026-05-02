---
id: INC-XXX
title: "{TITLE}"
status: Open # Open | Resolved | Closed (with prevention)
severity: SEV-1 # SEV-1 (critical) | SEV-2 (high) | SEV-3 (medium) | SEV-4 (low)
incident_started: YYYY-MM-DD HH:mm Z
detected: YYYY-MM-DD HH:mm Z
mitigated: YYYY-MM-DD HH:mm Z
resolved: YYYY-MM-DD HH:mm Z
duration_minutes: 0
hotfix_ref: "{HOTFIX-vX.Y.Z or none}"
on_call: "{role only — no individual names}"
# Human Attention Mediation
attention_score: 100
attention_band:  green
attention_factors: []
---

# INC-XXX — {TITLE}

> Blameless postmortem. Focuses on systems and processes, not individuals.

---

## Summary

| Field | Value |
|-------|-------|
| Severity | SEV-{1-4} |
| Duration | {minutes} |
| Users impacted | {N or %} |
| Revenue / data impact | {if quantifiable} |
| First detection signal | {alert / user report / metric} |

---

## Timeline (UTC)

| Time | Event | Source |
|------|-------|--------|
| HH:mm | {event} | {monitoring / log / report} |

---

## Root Cause (5 Whys)

1. **Why did {symptom} happen?** → {answer}
2. **Why did {answer-1} happen?** → {answer}
3. **Why did {answer-2} happen?** → {answer}
4. **Why did {answer-3} happen?** → {answer}
5. **Why did {answer-4} happen?** → {actionable root cause}

**Root cause:** {one sentence stating the actionable cause}

---

## Contributing Factors

> Things that made the incident worse, harder to detect, or harder to mitigate.

- {factor — e.g. "alert threshold too high; first signal lost in noise"}
- {factor}

---

## Corrective Actions

| Action | Owner (role) | Due | Success criterion |
|--------|-------------|-----|-------------------|
| {what to do} | {role} | YYYY-MM-DD | {observable outcome} |

---

## Prevention Measures

> Changes that prevent this **class** of incident, not just this instance.

- {architectural change, monitoring addition, process change}
- {change}

---

## Lessons for `learning-manager`

> One-line summary of the reusable pattern, formatted for the L-XXX extraction.

{single sentence — e.g. "Background jobs without idempotency guards retry-explode under DB outage."}

---

## ⚠ Audit Warnings

{populated by self-audit}
