---
id: T{ID}-log
task_ref: T{ID}
epic_ref: E{ID}
status: Active  # Completed
created: YYYY-MM-DD HH:mm
---

# LOG — T{ID}

Status: 🟢 Active | 🔵 Completed  
Created: YYYY-MM-DD HH:mm

---

## Context

- Task: [T{ID}](../T{ID}.md)
- Epic: [E{ID}](../epics/E{ID}.md)

---

## Events

### YYYY-MM-DD HH:mm

- {action performed — what was done, by whom (agent), result}

---

## Errors

> Record errors encountered during execution. If none: `[No errors recorded]`

- {error identified + context}

---

## Decisions

> Technical decisions made during execution — especially deviations from the original plan.

- {decision made and reason}

---

## References

- Task: [T{ID}](../T{ID}.md)
- Spec: [spec-vX](../../../00-discovery/spec/spec-vX.md)
- Learning: [L-XXX](../../../03-quality/learning/L-XXX.md)

---

## Handoff Checklist

> Complete before marking the associated Task as Completed.

- [ ] At least one cycle entry recorded
- [ ] Each cycle entry has Red / Green / Refactor documented
- [ ] Final status is `Completed` with a dated entry
- [ ] All test results noted (pass/fail count)
- [ ] Handoff to: **task-template** — update the Task `Artifacts` section from this log
