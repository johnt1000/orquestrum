---
id: QA-vX
title: "{TITLE}"
status: Pending # Passed | Partial | Failed
version: 1.0
created: YYYY-MM-DD HH:mm
updated: YYYY-MM-DD HH:mm
spec_ref: [spec-vX]
task_ref: [T1, T2]
# Human Attention Mediation — see docs/agent-context/CONVENTIONS.md
attention_score: 100        # int [0, 100]; lower = more human attention needed
attention_band:  green      # green | yellow | red
attention_factors: []
---

# QA vX — {TITLE}

Status: 🟢 Passed | 🟡 Partial | 🔴 Failed  
Date: YYYY-MM-DD HH:mm

---

## Scope

- Spec: [spec-vX](../../00-discovery/spec/spec-vX.md)
- Tasks:
  - [T1](../../02-planning/tasks/T1.md)

---

## Summary

{objective summary of the validation performed by the agent or human}

---

## Test Cases

> For each SC-XX from the active SPEC, record the result and the validation method used.

| SC | Result | validation_method | Notes |
|----|--------|-------------------|-------|
| SC-01 | ✅ Passed | static | — |
| SC-02 | ⚠️ Partial | e2e | {describe limitation} |
| SC-03 | ❌ Failed | automated | {describe failure} |

`validation_method` values: `static` (code read) · `e2e` (manual end-to-end) · `automated` (test suite) · `integration` (cross-service)

---

## Issues Found

1. **{ERROR-ID}:** {problem description} -> Link to log or correction task.

---

## Recommendations

- {e.g.: Suggest refactoring the database connection to avoid timeout in n8n}

---

## Next Actions

- [ ] Fix T1
- [ ] Revalidate main flow

---

## References

- Spec: [spec-vX](../../00-discovery/spec/spec-vX.md)
- Architecture: [arch-vX](../../01-design/architecture/arch-vX.md)
- Learning: [L-XXX](../learning/L-XXX.md)

---

## ⚠ Audit Warnings

<!-- Self-audit section — filled by Ward before handoff. If no warnings: "No warnings — artifact passed self-audit." -->

- [ ] {placeholder or warning detected}

---

## Handoff Checklist

> Complete before signaling completion to Ward / cast.

- [ ] All `{...}` placeholders replaced with real content
- [ ] Every SC-XX from the active SPEC has a row in the Test Cases table with `validation_method` set
- [ ] Security validation section completed
- [ ] Test execution summary filled (total passed, failed, blocked)
- [ ] Final status is `Passed` or `Partial` (not Draft)
- [ ] If `Partial` or `Failed`: blocking issues documented with linked Tasks
- [ ] `## ⚠ Audit Warnings` section completed (even if empty)
- [ ] Handoff to: **changelog-manager** (Cast) — bring QA status and approved artifact versions
