# REVIEW - Login system (v1)

Required reviewers:
- Code Reviewer
- Security Engineer (optional for crypto review)

Checkpoints:
- Password hashing implemented per ADR-001
- No plaintext passwords logged
- Session tokens stored securely (HttpOnly cookie)
- Tests cover success and failure flows
- Rate-limiting present
