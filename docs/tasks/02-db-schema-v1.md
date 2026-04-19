# Task 02 — DB schema and migration (v1)

Owner: Database Specialist
Priority: high
Estimated: 2h

Description:
Design and implement Postgres schema for users table and provide a migration script.

Deliverables:
- SQL migration or ORM migration to create users table with fields: id (uuid primary key), email (unique), password_hash, created_at, updated_at, failed_login_count (int default 0), locked_until (timestamp nullable)
- README on how to run migration
- Index on email

Acceptance criteria:
- Migration runs successfully and table exists
- Unique constraint on email enforced

Checklist (PR):
- [ ] Migration file added
- [ ] Documentation on running migration
- [ ] Assigned reviewers: Database Specialist, Code Reviewer
