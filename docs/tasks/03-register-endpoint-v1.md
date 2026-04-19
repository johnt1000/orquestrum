# Task 03 — Implement /register endpoint (v1)

Owner: Senior Developer
Priority: high
Estimated: 3h

Description:
Implement POST /register to create a new user with hashed password.

Requirements:
- Validate email format and password minimum length (>=8)
- Ensure email uniqueness
- Hash password using bcrypt (per ADR-001)
- Return 201 on success, 409 if email exists, 400 on validation errors

Deliverables:
- Endpoint implementation
- Input validation middleware
- Unit tests for happy path and error cases

Acceptance criteria:
- Successful registration persists user with password_hash populated (no raw password logged)
- Tests pass

Checklist (PR):
- [ ] Endpoint implemented
- [ ] Validation and error handling
- [ ] Tests added
- [ ] Assigned reviewers: Code Reviewer, Security Engineer
