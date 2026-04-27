---
session_id: "{SESSION_ID}"
updated: YYYY-MM-DD HH:mm
tier: 0 # 0 | 1 | 2
phase: 0 # -1 | 0 | 1 | 2 | 3 | 4 | 5
orchestrator: "{lore | forge | ward | cast | trace | —}"
---

# CHECKPOINT

> Session state snapshot. Written by the last active orchestrator. Read by Helm at the start of every new session.

---

## Active Context

| Field | Value |
|-------|-------|
| Tier | {0 / 1 / 2} |
| Phase | {-1 … 5} |
| Last orchestrator | {lore / forge / ward / cast / trace / —} |
| Last action | {one-line description of what was last completed} |

---

## Active Artifacts

> Paths of the most recent authoritative artifact for each type. Leave blank if not yet produced.

| Type | Path |
|------|------|
| GLOSSARY | `docs/00-discovery/glossary/GLOSSARY.md` |
| SPEC (active) | `docs/00-discovery/spec/spec-v{N}-{slug}.md` |
| ADR (latest) | `docs/00-discovery/adr/ADR-{XXX}-{slug}.md` |
| ARCHITECTURE | `docs/01-design/architecture/ARCHITECTURE-v{N}-{slug}.md` |
| TASK-INDEX | `docs/02-planning/tasks/TASK-INDEX.md` |
| REVIEW (latest) | `docs/03-quality/review/REVIEW-{ref}-{slug}.md` |
| QA (latest) | `docs/03-quality/qa/QA-{ref}-{slug}.md` |

---

## Pending Work

> Items started but not yet completed. Remove each line when the work is done.

- [ ] {description} — responsible: {orchestrator} — artifact: {expected path}

---

## Decisions Made This Session

> Architectural or scope decisions that affected routing. Remove stale entries after 2 sessions.

- {YYYY-MM-DD} — {decision summary} — ADR: {ADR-XXX or "pending"}

---

## Notes for Next Session

> Context that does not fit above but is needed for continuity.

{free text}
