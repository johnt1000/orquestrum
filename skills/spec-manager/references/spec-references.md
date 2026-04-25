# Formal Reference: Software Specification (SPEC)

## 1. The Role of the SPEC

The SPEC is not a user manual — it is a technical delivery contract. It must answer: "What does the system do?" and "What rules must it follow?".

Before writing any requirement, answer: **"Are we solving the right problem?"** The SPEC starts with assumptions — if the assumptions are wrong, the requirements will be wrong.

## 2. Assumption Mapping (MANDATORY before requirements)

An assumption is a statement the team takes as true without having fully validated it. Every SPEC starts from assumptions — making them explicit is what separates discovery from guesswork.

**Mandatory format:**

| Field | Description |
|-------|----------|
| Assumption | Positive statement: "The user has an email available at registration" |
| Risk if false | Consequence: "Notification feature does not work" |
| Validated? | Yes (evidence) / Not validated (assumed) |

**Examples:**

| Assumption | Risk if false | Validated? |
|---------|---------------|----------|
| Users have access to email | Notifications don't arrive — alternative channel required | ❓ Not validated |
| n8n is accessible via webhook in production | Automations don't trigger | ✅ Tested locally |
| Maximum volume of 1000 req/day | Insufficient rate limit, system degrades | ❓ Estimate without data |

**Rule:** At least 3 assumptions per SPEC. If you cannot find 3, problem discovery was shallow.

**Unvalidated assumptions** must become validation tasks before or during development — not after.

---

## 3. MoSCoW Prioritization

Every requirement has a priority. Without priority, any requirement can block a launch.

| Priority | Meaning | Usage criterion |
|-----------|-------------|----------------|
| **M** — Must | Mandatory. Without this, the system cannot be launched. | Security failure, core functionality, legal requirement |
| **S** — Should | Important, but there is an acceptable workaround for now. | Improves UX, reduces friction, but does not block use |
| **C** — Could | Desirable if there is capacity. | "Nice to have" — included if time allows in the cycle |
| **W** — Won't | Explicitly out of scope for this version. | Conscious decision — not an oversight |

**Rule:** Any requirement without priority is treated as **M** — and this creates false crises.

**Anti-pattern:** More than 50% of requirements as **M** indicates scope was not cut. Revise.

---

## 4. Writing Requirements

To avoid AI hallucinations and development errors, follow the pattern:

- **Functional:** "The system MUST [action] when [trigger]."
- **Non-Functional:** "The system must respond in less than [time]" or "Must be compatible with [technology]".

## 5. Success Criteria in BDD (DoD)

Success criteria must be written in **Given / When / Then** format. This format makes them directly usable by QA without reinterpretation.

**Structure:**
```
Given {initial system state or context}
When  {action executed by the user or system event}
Then  {observable result + concrete metric if applicable}
```

**Examples:**

_Bad:_ "The system must be fast."

_Good:_
```
Given an n8n workflow with 100 records queued
When the processing trigger is activated
Then all records are processed in less than 2 seconds
```

```
Given a user with 5 consecutive failed login attempts
When a 6th attempt is made
Then the account is locked and a "Account locked" message is returned with status 403
```

**Rule:** Each criterion must map to at least one requirement (FR-XX or NFR-XX). If a criterion has no corresponding requirement, the requirement is missing from the SPEC.

## 6. Scope Management

- **In-Scope:** What will be built.
- **Out-of-Scope:** What will explicitly NOT be done in this version (crucial to avoid Scope Creep).

## 7. Integration in SDD

The SPEC is the "parent" of Epics. No task should be created if there is no corresponding requirement in an active SPEC.

## 8. Quality Checklist (pre-save)

**Discovery:**
- [ ] `Assumptions` section has at least 3 documented assumptions
- [ ] Each assumption has an identified risk and validation status
- [ ] Unvalidated assumptions have been flagged for a validation task

**Requirements:**
- [ ] All functional requirements follow the pattern "The system MUST [action] when [trigger]"
- [ ] All requirements have MoSCoW priority (M/S/C/W)
- [ ] No more than 50% of requirements classified as Must
- [ ] Functional and non-functional requirements are in separate sections

**Success Criteria:**
- [ ] Each criterion is in Given/When/Then format
- [ ] Each criterion has a concrete metric (time, count, HTTP status, etc.)
- [ ] Each criterion maps to at least one requirement (FR-XX or NFR-XX)

**Scope:**
- [ ] The `Out-of-Scope` section is filled in
- [ ] Technical, legal, and integration constraints are listed
- [ ] The Mermaid diagram represents the main flow, not a generic placeholder

## 7. Requirement Examples

**Bad:**
```
- The system must be secure.
- Login must work.
```

**Good:**
```
- The system MUST lock the account after 5 consecutive failed login attempts.
- The system MUST return 401 with message "Invalid credentials" when the password is incorrect.
- The system MUST process session scheduling in less than 2 seconds for 95% of requests.
```

---

## Few-Shot Examples

<!-- inject:start -->
### ✅ Good Output — SPEC section (Assumptions + Requirements)

```markdown
## Assumptions

| # | Assumption | Risk if false | Validated? |
|---|-----------|--------------|-----------|
| A1 | Users have a valid email address at registration | Registration flow breaks entirely | ✅ Yes |
| A2 | The system will not exceed 500 concurrent users at launch | Performance requirements may need revision | ❓ Not validated |
| A3 | Payment provider API is available 99.9% of the time | Checkout flow requires fallback handling | ✅ Yes |

## Requirements

### Functional

| ID | Priority | Requirement |
|----|----------|------------|
| RF-01 | M | The system MUST validate email format before creating an account |
| RF-02 | M | The system MUST reject duplicate email addresses with a 409 response |
| RF-03 | S | The system SHOULD send a confirmation email within 30 seconds of registration |
```

### ❌ Anti-Pattern — vague requirements without assumptions

```markdown
## Requirements

The system should handle user registration properly and validate inputs.
It must also deal with errors gracefully and be secure.
```

**Why rejected:** No assumptions documented. Requirements are prose, not structured rows. No MoSCoW priority. No RF-XX IDs. No measurable success criteria. This would be blocked at Gate 1→2 (SPEC + ADR exist).
<!-- inject:end -->
