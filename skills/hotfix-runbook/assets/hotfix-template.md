---
id: HOTFIX-vX.Y.Z
title: "{TITLE}"
status: Active # Active | Resolved | Rolled back
version: X.Y.Z
incident_started: YYYY-MM-DD HH:mm
deployed: YYYY-MM-DD HH:mm
resolved: YYYY-MM-DD HH:mm
task_ref: "T{ID}"
# Human Attention Mediation — see docs/agent-context/CONVENTIONS.md
attention_score: 65         # default yellow; hotfixes never default green
attention_band:  yellow     # yellow | red — hotfix policy: never green
attention_factors: [pipeline_skipped, hotfix_path]
---

# HOTFIX vX.Y.Z — {TITLE}

> Hotfix runbook. Abbreviated path for a critical production bug. Normal pipeline (Lore → Forge → Cipher → Ward) is bypassed; this document is the audit trail.

---

## Impact

| Field | Value |
|-------|-------|
| Users impacted | {N or %} |
| Error signal | {error message / metric / dashboard link} |
| First observed | {YYYY-MM-DD HH:mm} |
| Mitigation in place | {none / temporary measure / link} |

---

## Fix

| Field | Value |
|-------|-------|
| Task | [`T{ID}`](../../02-planning/tasks/T{ID}.md) |
| One-line description | {what was changed} |
| Files touched | {list of paths} |
| Diff size | {N lines added / N lines removed} |

**Technical paragraph:**

{2-3 sentences: what was wrong, what the fix does, why it's safe.}

---

## Test plan

| Step | Method | Pass criterion |
|------|--------|----------------|
| 1 | Manual | {observable behavior after fix} |
| 2 | Automated | {test name / file} |

---

## Release plan

| Field | Value |
|-------|-------|
| Version bump | patch (X.Y.Z → X.Y.(Z+1)) |
| Deployment window | {YYYY-MM-DD HH:mm – HH:mm} |
| Monitoring window | {duration after deploy} |
| Rollback trigger | {explicit condition, e.g. "error rate > 1% sustained 30 min"} |
| Rollback procedure | [`ROLLBACK-vX.Y.Z`](./ROLLBACK-vX.Y.Z-{slug}.md) or "redeploy previous tag" |

---

## Post-incident actions

- [ ] Run `learning-manager` to capture the L-XXX incident report
- [ ] Run `changelog-manager` to update CHANGELOG with the patch entry
- [ ] If governance issue surfaced, file note for the next Lore cycle in `Pending Work` of CHECKPOINT
- [ ] Update `attention_score` once incident is resolved and rollback is no longer armed

---

## ⚠ Audit Warnings

{populated by self-audit; "No warnings — artifact passed self-audit." if clean}
