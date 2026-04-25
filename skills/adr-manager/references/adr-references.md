# Formal Reference: Architecture Decision Records (ADR)

This reference defines quality criteria for technical decision documentation.

## 1. What is an ADR?

An ADR is a short document that captures an architectural decision, the context in which it was made, and the consequences it produces. The goal is not just to document _what_ was done, but _why_ it was done.

## 2. Quality Components

### A. Context (The "Why")

- Must describe the current problem, not the solution.
- Must include constraints (technological, financial, time-related).
- **Criterion:** A developer new to the project should understand the pressure/need at the time by reading this field.

### B. Decision Flow

- Represents the logical reasoning.
- **Problem:** The trigger.
- **Options:** Which alternatives were discarded? (e.g.: Ruby vs Go vs Node).
- **Decision:** The final choice.

### C. Consequences (The "Price")

Every architectural decision is a **trade-off**.

- **Positive:** Performance gains, ease of maintenance, lower cost.
- **Negative:** Conscious "technical debt", training requirements, greater infrastructure complexity.
- **Note:** If an ADR has no negative consequences, it probably was not analyzed in sufficient depth.

## 3. ADR States

- **Proposed:** The idea is being discussed.
- **Accepted:** The decision has been made and must be implemented.
- **Deprecated:** A new decision (a new ADR) has superseded this one. Reference the new ADR.

## 4. Writing Style

- Use active voice and professional tone.
- Be concise: ADRs that take more than 5 minutes to read tend to be ignored.

## 5. Pattern Adoption ADR

When a design pattern is adopted for the first time in the project, create an ADR documenting the decision. Subsequent adoptions of the same pattern in other components are recorded in the `pattern-manager` — they do not require a new ADR.

**Trigger:** "We will use Repository for data access" → mandatory ADR.

**Specific fields for a pattern ADR:**

- **Context:** The structural problem the pattern solves (e.g.: "services access the database directly, making testing and technology replacement difficult")
- **Options:** Which alternatives were considered (e.g.: Active Record vs Repository vs Query Objects)
- **Decision:** The chosen pattern with justification
- **Positive consequences:** Gains in testability, maintainability, flexibility
- **Negative consequences:** Additional complexity, learning curve, more files

**Reference for available patterns:** `skills/pattern-manager/references/pattern-references.md`

**After creating the ADR:** Run `pattern-manager` in Adoption Mode to register WHERE the pattern applies in `docs/00-discovery/patterns/PATTERNS.md`.

## 6. Development Workflow ADRs

Decisions about how the team works — not just about technology — also deserve an ADR when they have relevant trade-offs and need to be understood by new members.

**Recommended workflow ADRs for every new project:**

| Decision | Typical context |
|---------|----------------|
| **Branching strategy** | Trunk-Based vs GitFlow vs GitHub Flow — impacts CI/CD, integration frequency, and risk of merge hell |
| **Commit convention** | Conventional Commits vs free-form — impacts automatic changelog, traceability, and history readability |
| **Release strategy** | SemVer + tags vs release branches vs continuous delivery |
| **Feature flags** | When and how to use — required in TBD to safely merge incomplete code |

**Specific fields for a workflow ADR:**

- **Context:** The problem the decision solves (e.g.: "long-lived branches cause frequent merge conflicts and hinder CI")
- **Options:** Alternatives considered (e.g.: GitFlow vs GitHub Flow vs Trunk-Based)
- **Decision:** The chosen strategy with concrete rules (branch naming, maximum lifetime, commit convention)
- **Positive consequences:** Continuous integration, readable history, automatic changelog
- **Negative consequences:** Feature flag discipline required, atomic commits demand more care
