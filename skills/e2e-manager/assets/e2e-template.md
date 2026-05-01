---
id: E2E-{ref}
title: "{TITLE}"
mode: Scenario # Regression
status: Draft # Active | Completed | Failed
version: 1.0
spec_ref: spec-vX
created: YYYY-MM-DD HH:mm
updated: YYYY-MM-DD HH:mm
coverage_score: "0/0 (0%)"  # covered SC-XX / total SC-XX
last_validated: YYYY-MM-DD
drift_risk: low # low | medium | high
---

# E2E-{ref} — {TITLE}

Mode: Scenario | Regression  
Status: 🟡 Draft | 🟢 Active | 🔵 Completed | 🔴 Failed  
Created: YYYY-MM-DD HH:mm

---

## Scope

- Spec: [spec-vX](../../00-discovery/spec/spec-vX.md)
- SC-XX in scope: SC-01, SC-02, SC-03

---

## Critical User Paths

> Sequences of SC-XX that represent primary feature delivery, authentication, or data submission. These paths block release if any scenario fails.

| Path | SC-XX sequence | Blocks release? |
|------|---------------|:---------------:|
| {e.g. New user registration} | SC-01 → SC-02 → SC-03 | ✅ Yes |
| {e.g. Password recovery} | SC-04 → SC-05 | ✅ Yes |
| {e.g. Profile update} | SC-06 | ❌ No |

---

## Scenarios

> One row per scenario. Each SC-XX must have ≥1 happy-path + ≥1 error-case scenario.

| ID | SC | Type | Given | When | Then | Test file | Status |
|----|-----|------|-------|------|------|-----------|--------|
| E2E-01 | SC-01 | happy | {initial state} | {user action} | {expected result} | `e2e/{path}.spec.ts` | ⬜ Pending |
| E2E-02 | SC-01 | error | {invalid state} | {user action with invalid input} | {expected error result} | `e2e/{path}.spec.ts` | ⬜ Pending |
| E2E-03 | SC-02 | happy | | | | | ⬜ Pending |

Status values: ⬜ Pending · ✅ Passed · ❌ Failed · ⚠️ Blocked · ⏭ Skipped

---

## Coverage Matrix

| SC-XX | Scenario IDs | Happy path | Error case | Status |
|-------|-------------|:----------:|:----------:|--------|
| SC-01 | E2E-01, E2E-02 | ✅ | ✅ | ⬜ Pending |
| SC-02 | E2E-03 | ✅ | ❌ missing | ⚠️ Partial |

Coverage score: **0/0 (0%)** — updated after regression run.

---

## Failures (Regression mode only)

> Fill during Regression execution. Leave empty in Scenario mode.

| Scenario | Failure type | Root cause | Action |
|----------|-------------|-----------|--------|
| E2E-02 | code bug | {description} | New Task T{ID} |
| E2E-03 | environment | {env precondition missing} | Flux backlog |
| E2E-04 | spec drift | {SPEC diverged from implementation} | Lore → spec update |

---

## ⚠ Audit Warnings

<!-- Self-audit section — filled before handoff. If no warnings: "No warnings — artifact passed self-audit." -->

- [ ] {placeholder or warning detected}

---

## Handoff Checklist

> Complete before signaling completion.

- [ ] All `{...}` placeholders replaced with real content
- [ ] Every SC-XX in scope has ≥1 happy-path + ≥1 error-case scenario
- [ ] All Critical User Paths identified with `Blocks release?` column filled
- [ ] Coverage matrix completed — score computed
- [ ] `coverage_score` field in frontmatter updated
- [ ] **Scenario mode:** Handoff to **task-manager** — bring scenario map as Red-phase guide
- [ ] **Regression mode:** Handoff to **qa-manager** — bring E2E results as `e2e` validation_method evidence
