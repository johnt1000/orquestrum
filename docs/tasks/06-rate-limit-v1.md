# Task 06 — Rate limiting & lockout (v1)

Owner: Security Engineer
Priority: high
Estimated: 2h

Description:
Implement basic rate limiting and account lockout to mitigate brute-force.

Requirements:
- Global rate-limit per IP (e.g. 100 reqs/min) for auth endpoints
- Per-account failed login counter; lock account for X minutes after Y failures
- Ensure lockout mechanism cannot be trivially used to perform DoS on legitimate users

Deliverables:
- Middleware for rate-limiting (express-rate-limit or similar)
- Lockout logic in login flow
- Tests for lockout behavior

Acceptance criteria:
- Rate-limiting and lockout operate as configured and documented

Checklist (PR):
- [ ] Rate-limiting middleware added
- [ ] Lockout implemented and tested
- [ ] Assigned reviewers: Security Engineer, Code Reviewer
