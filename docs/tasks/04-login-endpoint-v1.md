# Task 04 — Implement /login endpoint (v1)

Owner: Senior Developer
Priority: high
Estimated: 3h

Description:
Implement POST /login to authenticate user and create session cookie.

Requirements:
- Verify credentials using bcrypt.compare
- Reset failed_login_count on successful login
- Increment failed_login_count and set locked_until if threshold exceeded
- Create server-side session and set HttpOnly Secure cookie
- Return 200 on success, 401 on invalid credentials

Deliverables:
- Endpoint implementation
- Session creation (Redis-backed or in-memory for dev)
- Integration tests

Acceptance criteria:
- Successful login sets session cookie and subsequent authenticated requests succeed
- Failed attempts follow lockout rules

Checklist (PR):
- [ ] Endpoint implemented
- [ ] Session cookie secure settings
- [ ] Tests added
- [ ] Assigned reviewers: Code Reviewer, Security Engineer
