# TASKS - Login system (v1)

## Feature: Auth (email/password)

Subtasks:
1. Create project scaffold (Node.js + Express)
2. Setup Postgres schema for users
3. Implement /register endpoint (validation, hashing, persistence)
4. Implement /login endpoint (verify, session create)
5. Implement /logout endpoint (destroy session)
6. Add rate-limiting / basic lockout logic
7. Add tests (unit & integration)
8. Write README and API docs

Dependencies:
- Postgres running
- (Optional) Redis for session store

Execution Order:
1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7 -> 8
