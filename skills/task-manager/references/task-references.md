# Formal Reference: Task Execution and Code Quality

## 1. Task Granularity

A Task must be small enough to be completed in a single work cycle, but large enough to produce a functional artifact or a clear state change in the system.

## 2. Dependency Management

- **Blockers:** If a Task `T02` depends on `T01`, it must not leave `Pending` status until `T01` is `Completed`.
- **Parallelism:** Tasks without direct dependencies must be prioritized to optimize development time.

## 3. Execution Logs

A Task Log is not just a history, but a knowledge base for debugging. It must contain:

- Errors encountered during implementation.
- Last-minute decisions that do not justify a full ADR.
- Terminal commands used (e.g.: database migrations, deploys).

## 4. Artifact Traceability

Whenever a code file is created or changed, it must be cited in the `Artifacts` section. This allows the AI to "connect the dots" between the documentation and the actual source code.

## 5. Implementation Principles

Before marking a Task as `Completed`, verify that the written code respects the principles below. These are minimum quality criteria — they are not optional.

| Principle | Verification question |
|-----------|------------------------|
| **DRY** | Is there identical or very similar logic elsewhere in the project? If so, was it extracted to a shared function/module? |
| **YAGNI** | Was any functionality added that the SPEC or Task did not request? If so, remove it. |
| **KISS** | Could the code be written more simply and still meet the requirement? If so, simplify. |
| **SOLID-D** | Does the component instantiate its dependencies with an internal `new`? If so, use dependency injection. |
| **Fail Fast** | Are input validations at the beginning of the function, before any processing? |
| **SoC** | Does the component have exactly one responsibility? Does it not mix business + infra + presentation? |

**Verification shortcut:** If you cannot name the component with a 5-word phrase that describes exactly what it does → it probably violates SRP/SoC.

## 6. TDD — Test-Driven Development

### Mandatory cycle for Tier 2, recommended for Tier 1

```
🔴 RED    → Write the failing test (derived from SC-XX of the SPEC)
🟢 GREEN  → Implement the minimum to make the test pass
🔵 REFACTOR → Apply principles (DRY/KISS/SOLID) without breaking tests
```

**Never skip RED.** Writing the test after the code is not TDD — it is test-after with more bureaucracy.

### How to derive tests from SC-XX of the SPEC

Each SC-XX in Given/When/Then format becomes a direct test case:

```
SPEC SC-01:
  Given an unauthenticated user
  When makes POST /sessions with valid payload
  Then receives 401 Unauthorized

→ Test case:
  test('POST /sessions without token returns 401', async () => {
    const res = await request(app).post('/sessions').send(validPayload)
    expect(res.status).toBe(401)
  })
```

### Test types by layer

| Type | What it tests | Speed | When to use |
|------|------------|-----------|------------|
| **Unit** | Isolated function/class with mocked deps | Fast (ms) | Always — business logic |
| **Integration** | Component + real deps (DB, service) | Medium (s) | When Repository/Adapter is tested |
| **E2E / Contract** | Complete API flow | Slow (s-min) | Happy path + critical scenarios |

**Pyramid rule:** many more unit tests than integration, many more integration than e2e. Inverting the pyramid is the most common mistake.

### TDD anti-patterns to avoid

| Anti-pattern | Symptom | Fix |
|-------------|---------|---------|
| **Test-after** | Tests written after the code already works | Go back to the start — write the failing test first |
| **Test that never fails** | Test passes before any implementation | The test is testing the mock, not the real code |
| **God test** | One test validates 5+ different behaviors | Break into smaller tests with 1 assertion per test |
| **Fragile test** | Breaks due to string or formatting change, not logic | Test behavior, not implementation |
| **Accumulated skips** | `test.skip` / `xit` accumulated without issue | Each skip needs justification in the log |

---

## 7. Definition of Done (DoD) — Checklist

A Task can only be marked as `Completed` when:

**Code:**
- [ ] All listed artifacts were created/modified
- [ ] Code compiles/runs without critical errors
- [ ] The SPEC criteria this task covers are implemented
- [ ] No credentials or sensitive data were hardcoded

**Tests (Tier 1+):**
- [ ] Test files listed in the `Artifacts` section
- [ ] Tests cover at least the SC-XX of the SPEC this task addresses
- [ ] All tests pass (zero failures, zero unjustified skips)
- [ ] Red → Green → Refactor cycle completed (Tier 2 mandatory)

**Log:**
- [ ] `T{ID}-log.md` has at least one entry describing what was done
- [ ] Relevant TDD cycles recorded in the log (e.g.: "RED failed on X, GREEN implemented Y, REFACTOR extracted Z")

## 8. Git Conventions

### Conventional Commits

Mandatory format for each commit:

```
{type}({scope}): {imperative description, lowercase, no period at end}

[optional body — when the why is not obvious from the title]

[optional footer — refs: T001, breaking change]
```

**Allowed types:**

| Type | When to use |
|------|------------|
| `feat` | New behavior observable by the user |
| `fix` | Bug fix |
| `refactor` | Restructuring without behavior change |
| `test` | Addition or correction of tests |
| `docs` | Documentation only |
| `chore` | Build, config, dependencies, scripts |
| `perf` | Performance improvement without behavior change |
| `ci` | Changes in CI/CD |

**Correct examples:**
```
feat(auth): add JWT refresh token rotation
fix(users): prevent duplicate email on concurrent registration
refactor(payments): extract StripeAdapter from PaymentService
test(auth): add integration tests for token expiration
```

**Wrong examples:**
```
update stuff               ← no type, no scope, vague
Fixed bug                  ← uppercase, no type
feat: add many new things  ← scope too broad, multiple purposes
```

**Granularity rule:** One commit = one cohesive purpose. If the title requires `and`, split into two commits.

**Breaking changes:** add `!` after the type/scope and describe in the footer:
```
feat(api)!: rename /users endpoint to /accounts

BREAKING CHANGE: /users removed, use /accounts
```

---

### Trunk-Based Development (TBD)

**Principle:** `main` is always deployable. All work converges to `main` frequently — ideally in less than 24h.

**Branch naming by task:**
```
{type}/{T-ID}-{kebab-description}

Examples:
feat/T001-user-registration
fix/T003-duplicate-email-validation
refactor/T005-extract-stripe-adapter
```

**Rules:**
- Branch created from an up-to-date `main`
- One branch per task (never accumulate tasks in one branch)
- Maximum lifetime of 1-2 days — if exceeded, rebase with `main` or subdivide the task
- Never commit directly to `main` (except critical hotfix with approval)
- Incomplete code that needs to merge before it is ready for the user → use a feature flag

**Do not do:**
```
feature/all-auth-features  ← long-lived branch accumulating work
dev                        ← parallel branch that diverges from main
jonatas/my-changes         ← person branch, not a task branch
```

---

## 9. Example Artifacts Section

**Bad:**
```markdown
## Artifacts
- database files
- endpoint created
```

**Good:**
```markdown
## Artifacts
- `src/models/session.rb` — ActiveRecord Model for sessions table
- `db/migrate/20260424_create_sessions.rb` — Table creation migration
- `src/controllers/sessions_controller.rb` — Basic sessions CRUD
- `spec/models/session_spec.rb` — Model unit tests
```

---

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
