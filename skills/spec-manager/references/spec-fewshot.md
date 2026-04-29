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

---
