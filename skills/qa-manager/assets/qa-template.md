---
id: QA-vX
title: "{TITLE}"
status: Pending # Passed | Partial | Failed
version: 1.0
created: YYYY-MM-DD HH:mm
updated: YYYY-MM-DD HH:mm
spec_ref: [spec-vX]
task_ref: [T1, T2]
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

### ✅ Passed

- {functional test validated}
- {acceptance criterion X met}

### ⚠️ Partial

- {unstable or partial behavior}

### ❌ Failed

- {error found that prevents completion}

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

## Handoff Checklist

> Complete before signaling completion to Ward / cast.

- [ ] All `{...}` placeholders replaced with real content
- [ ] Every SC-XX from the active SPEC has a test result (Pass / Fail / Blocked)
- [ ] Security validation section completed
- [ ] Test execution summary filled (total passed, failed, blocked)
- [ ] Final status is `Passed` or `Partial` (not Draft)
- [ ] If `Partial` or `Failed`: blocking issues documented with linked Tasks
- [ ] Handoff to: **changelog-manager** (Cast) — bring QA status and approved artifact versions
