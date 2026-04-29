## Few-Shot Examples

<!-- inject:start -->
### ✅ Good Output — Task with Artifacts and TDD Log

```markdown
## Artifacts

- `src/auth/register.ts` — registration endpoint handler
- `src/auth/register.spec.ts` — unit tests (12 cases)
- `src/auth/register.integration.spec.ts` — integration tests (4 cases)
- `src/validators/email.ts` — email validation utility
- `db/migrations/001_create_users_table.sql` — users table migration

## Acceptance Criteria

- [x] POST /register returns 201 on valid input
- [x] POST /register returns 409 on duplicate email
- [x] POST /register returns 422 on invalid email format
- [x] All 16 tests pass
```

### ❌ Anti-Pattern — Task with missing artifacts

```markdown
## Artifacts

- [to be filled after implementation]

## Acceptance Criteria

- [ ] Implementation done
- [ ] Tests written
```

**Why rejected:** Artifacts section has a placeholder — reviewer and QA cannot validate without exact file paths. Acceptance criteria are vague and non-measurable. This task would fail the Handoff Checklist and block Gate 3→4.
<!-- inject:end -->

---
