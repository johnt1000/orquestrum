---
name: schema-manager
description: Builds and caches a structured database-schema map by parsing migration files. Replaces ad-hoc grep loops with a single CHECKPOINT-backed summary. Auto-invalidates when the migrations directory changes (sha256 hash). Framework-agnostic — works with Supabase/Postgres, Prisma, Django, Rails, raw SQL.
inject_references: compact
metadata:
  version: "1.0.0"
  author: "Jônatas Rodrigues"
  phase: 2-3
  depends_on: []
  produces: "docs/CHECKPOINT.md (## Big-File Summaries section, one block per migrations dir)"
chain:
  next: data-migration-manager
  condition: "agent is about to plan a schema change — load the cached schema map first to avoid stale assumptions"
---

# Schema Manager Skill

You build a structured map of the project's database schema by parsing
migration files **once**, caching the result in `docs/CHECKPOINT.md`,
and serving subsequent lookups from the cache.

This skill exists because real session analysis showed orchestrators
running 17+ `grep`/`find` chains against `supabase/migrations/*.sql`
to answer questions like "what columns does `meta_policy_settings`
have?" or "which migration last touched `greeting_templates`?". A
single summary block in CHECKPOINT collapses that to one read.

## When to use

Load this skill **BEFORE**:

- Writing a new migration that depends on existing column types / constraints
- Composing a SQL query that joins multiple tables
- Reviewing a PR whose impact depends on the current schema
- Answering "where is X defined?" / "what columns does X have?" questions

Skip when:

- The cached summary is fresh (your CHECKPOINT.md `## Big-File
  Summaries` already has a block for this migrations dir with a
  matching sha256). Read the cache; do not re-parse.
- You only need to write code that doesn't touch the schema.

## I/O Contract

| | Files |
|--|---------|
| **Reads** | `<migrations_dir>/*.sql` (default search paths below), `docs/CHECKPOINT.md` (existing Big-File Summary block, if any) |
| **Writes** | `docs/CHECKPOINT.md` (`## Big-File Summaries` section — appends or replaces one block per migrations dir) |
| **Depends on** | `checkpoint-manager` (for the section template — already in checkpoint-template.md) |
| **Must NOT touch** | Any file outside CHECKPOINT.md. This skill never modifies source code, settings, or data. |
| **Handoff to** | `data-migration-manager` when the cached schema reveals a gap requiring a new migration |

## Pre-execution (REQUIRED)

1. Read `./references/schema-references.md` — covers framework detection,
   parsing patterns, and known edge cases (Postgres-specific syntax,
   inheritance, partitions).
2. Read `docs/agent-context/CONVENTIONS.md` → "Big-File Summary Convention"
   — the cache section format you'll write to.

## Execution Flow

### Step 1 — Locate the migrations directory

Try in this order; pick the first that exists. Stop on first match.

| Path | Indicates |
|---|---|
| `supabase/migrations/` | Supabase project |
| `prisma/migrations/` | Prisma ORM |
| `db/migrate/` | Rails (ActiveRecord) |
| `<app>/migrations/` (Python any subdir) | Django |
| `migrations/` | Generic / raw SQL |
| `db/migrations/` | Generic alternate |

If none exists → report "no migrations dir detected" and STOP. Do not
invent a schema.

### Step 2 — Compute the dir hash (cache key)

```bash
# Combined sha256 of every migration file's content + name
( cd "<migrations_dir>" && \
  find . -type f \( -name '*.sql' -o -name '*.py' -o -name '*.rb' -o -name '*.prisma' \) \
       -print0 | sort -z | xargs -0 sha256sum ) | sha256sum | cut -c1-12
```

Take the first 12 chars. This is the cache key.

### Step 3 — Check the cache

Read `docs/CHECKPOINT.md`. Look in `## Big-File Summaries` for a block whose
`path:` matches the migrations dir AND whose `hash:` matches the value from
Step 2.

- **Hit:** print the cached summary and STOP. Do not re-parse.
- **Miss (no block, or hash mismatch):** continue to Step 4.

### Step 4 — Parse migrations

For each file in the migrations dir (sorted ascending by filename, which
is timestamp-prefixed in every supported framework), extract:

| Statement type | Recognise via | Capture |
|---|---|---|
| Table create | `CREATE TABLE [IF NOT EXISTS] (?:public\.)?<name>` | name, column list |
| Column add | `ALTER TABLE <t> ADD COLUMN <c>` | table, column, type |
| Column drop | `ALTER TABLE <t> DROP COLUMN <c>` | table, column |
| Column type change | `ALTER TABLE <t> ALTER COLUMN <c> TYPE <type>` | table, column, new type |
| Constraint add | `ALTER TABLE <t> ADD CONSTRAINT <name> <body>` | table, constraint, kind (UNIQUE/CHECK/FK) |
| Index create | `CREATE [UNIQUE] INDEX <name> ON <t>` | table, index, columns |
| RLS policy | `CREATE POLICY <name> ON <t>` | table, policy name, rls scope |

**Track the LATEST migration that touched each table.** That's the highest-value
nugget — it's the file an agent should read when modifying the table.

### Step 5 — Write the summary block to CHECKPOINT

Append (or replace, if a block for this dir already exists) one block in
`## Big-File Summaries`:

````markdown
### `<migrations_dir>`

```yaml
path:         <migrations_dir>
size_bytes:   <total bytes>
hash:         <12-char sha256 from Step 2>
recorded_at:  <YYYY-MM-DDTHH:mm:ssZ>
recorded_by:  schema-manager (orquestrum skill)
```

**Summary:**

| Table | Latest migration | Columns | Notable constraints / indexes |
|---|---|---|---|
| `users` | `20260301120000_create_users.sql` | id, email, name, created_at | UNIQUE(email), idx_users_email |
| `meta_policy_settings` | `20260504005313_add_tenant_unique.sql` | id, tenant_id, rule_key, value | UNIQUE(tenant_id, rule_key) |
| ... |

**Conventions detected:** Supabase (RLS enabled), tenant_id pattern on all writable tables, soft-delete via `deleted_at`.

**Stale flags:** none. (If a table appears in early migration but every reference is dropped later → flag here.)
````

Stay under ~80 lines per block (per the CONVENTIONS guide). Truncate
column lists at 6 + ellipsis if longer; the goal is structural overview,
not full schema dump.

### Step 6 — Output

Echo the summary block to the user/caller, then STOP. Do not modify
schema, do not propose migrations — that's `data-migration-manager`'s
job. Hand off via the chain field if a schema change is needed.

## Validation (MANDATORY)

After writing:

- [ ] `docs/CHECKPOINT.md` is still valid markdown (heading hierarchy intact)
- [ ] The new block has `hash:` matching Step 2
- [ ] The block lists every table seen via CREATE TABLE (count check)
- [ ] No source code outside CHECKPOINT.md was modified
- [ ] If you replaced a stale block, the old block is GONE (no duplicates)

If any check fails → revert the CHECKPOINT change and report.

## Output Format

```
schema-manager complete:
  Migrations dir: <path>
  Files parsed:   <N>
  Cache state:    <hit | miss → wrote new block>
  Tables tracked: <M>
  CHECKPOINT updated: yes/no
```

## Guardrails

- **NEVER** parse migrations from `node_modules/`, `.venv/`, `vendor/`,
  or any subdir of those — they're dependencies, not project schema.
- **NEVER** invent columns or constraints not present in the parsed
  files. If a table appears in CREATE but its later evolution is unclear,
  list "evolution unclear; read latest migration" in the Notes column.
- **NEVER** run psql/supabase/prisma CLIs to introspect a live DB
  unless the user explicitly asks — this skill is migration-file-based
  by design (works offline, no creds needed, deterministic).
- **DO** prefer the cache. The whole point is to avoid re-scanning.
- **DO** invalidate when hash mismatches. Schema files change; the
  cache must reflect that or downstream skills get poisoned.
