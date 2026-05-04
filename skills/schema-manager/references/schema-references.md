# Schema Manager — Reference Material

Authoritative parsing rules, framework signatures, and edge cases for the
`schema-manager` skill. Read this BEFORE running the skill so the parsed
output matches reality across migration formats.

---

## Framework signatures

Detect the project's framework by file structure, not by parsing content.
First match wins; don't try to merge multiple.

| Framework | Signature path(s) | File extensions | Naming convention |
|---|---|---|---|
| **Supabase** | `supabase/migrations/` + `supabase/config.toml` | `.sql` | `<unix_timestamp>_<description>.sql` (e.g. `20260504005313_add_tenant_unique.sql`) |
| **Prisma** | `prisma/migrations/<timestamp>_<name>/migration.sql` | `.sql` (one per dir) | dir prefix is `YYYYMMDDHHMMSS` |
| **Django** | `<app>/migrations/<NNNN>_<name>.py` (any subdir) + `manage.py` | `.py` | `0001_initial.py`, `0002_*.py`, … |
| **Rails (ActiveRecord)** | `db/migrate/<timestamp>_<name>.rb` | `.rb` | `<14-digit-timestamp>_<snake_case>.rb` |
| **Generic SQL** | `migrations/` or `db/migrations/` with `.sql` files | `.sql` | varies; sort lexically |
| **TypeORM** | `src/migrations/<timestamp>-<Name>.ts` | `.ts` | unix-ms + name |

If multiple signatures match → prefer the one whose dir has the most files
(most likely the active one).

---

## SQL pattern reference (most common case)

The vast majority of orquestrum projects use raw SQL. These regex hints
cover Postgres dialect (Supabase, raw Postgres, Rails+Postgres). Adapt
case-insensitively (`grep -iE`).

### Statement detectors

```bash
# CREATE TABLE — captures table name (handles "public." schema, IF NOT EXISTS)
grep -iE 'CREATE TABLE (IF NOT EXISTS )?(public\.)?[a-z_][a-z0-9_]*' file.sql

# ALTER TABLE — captures table + action
grep -iE 'ALTER TABLE (ONLY )?(public\.)?[a-z_][a-z0-9_]*' file.sql

# CREATE INDEX — captures index name + table
grep -iE 'CREATE (UNIQUE )?INDEX (IF NOT EXISTS )?[a-z_][a-z0-9_]* ON (public\.)?[a-z_][a-z0-9_]*' file.sql

# Constraints (UNIQUE, CHECK, FOREIGN KEY, PRIMARY KEY)
grep -iE 'ADD CONSTRAINT [a-z_][a-z0-9_]* (UNIQUE|CHECK|FOREIGN KEY|PRIMARY KEY)' file.sql

# RLS (Supabase / Postgres)
grep -iE 'CREATE POLICY [a-z_][a-z0-9_"]* ON (public\.)?[a-z_][a-z0-9_]*' file.sql
grep -iE 'ENABLE ROW LEVEL SECURITY ON (public\.)?[a-z_][a-z0-9_]*' file.sql
```

### Column extraction

When you find a CREATE TABLE, the columns are between the first `(` and
the matching `)`. Naive split on `,` works for ~95% of cases; for nested
parens (e.g. `numeric(10,2)`) walk the parentheses depth.

Capture per column:
- name (first identifier)
- type (next token, possibly with parens)
- NOT NULL / DEFAULT / PRIMARY KEY (inline modifiers — keep them; they're constraints)

Example column line:
```sql
tenant_id uuid NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
```
→ name=`tenant_id`, type=`uuid`, modifiers=`NOT NULL FK→tenants.id CASCADE`

---

## Edge cases (where naive parsing fails)

### 1. Multi-statement migrations
A single `.sql` file may have 5 CREATE TABLEs + 3 ALTER + 2 INDEX. Parse
ALL of them, not just the first. Track each separately.

### 2. Idempotent guards
```sql
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM ...) THEN
    CREATE TABLE foo (...);
  END IF;
END $$;
```
Treat the inner CREATE the same as a top-level one. The DO block is
just an idempotence wrapper.

### 3. Column rename via DROP + ADD
```sql
ALTER TABLE x DROP COLUMN old_name;
ALTER TABLE x ADD COLUMN new_name <type>;
```
Don't conclude `old_name` was permanent — the latest state is `new_name`.
Track migrations chronologically; the latest file wins.

### 4. Schema-qualified vs unqualified
`public.users` and `users` are the same in Postgres default schema.
Normalize both to `users` for the cache key (avoid duplicate rows).

### 5. CASCADE drops
```sql
DROP TABLE users CASCADE;
```
Removes the table AND every dependent (FK references, views). If a
later migration references the dropped table → stale; surface in
"Stale flags" section of the cache block.

### 6. Tenant-isolated patterns
Many real projects have `tenant_id uuid NOT NULL` on every writable
table + RLS policies enforcing it. When detected (>3 tables with this
pattern + an active RLS policy mentioning tenant_id), record under
"Conventions detected" so future agents don't propose schema changes
that bypass tenancy.

### 7. Soft-delete columns
A `deleted_at timestamptz` column on most tables → "soft-delete via
deleted_at" convention. Surface in the same Conventions block.

### 8. Generated columns / computed
```sql
search_text text GENERATED ALWAYS AS (lower(name || ' ' || email)) STORED
```
List the column normally; in modifiers note "(generated)". Don't try to
parse the expression.

### 9. ENUMs and custom types
```sql
CREATE TYPE order_status AS ENUM ('pending','paid','shipped');
ALTER TABLE orders ADD COLUMN status order_status NOT NULL;
```
Track the type definition once; reference it from columns by name.

### 10. Migration file with NO schema impact
Some files are pure data backfills (`UPDATE … SET …`) or just
`COMMENT ON …`. Skip them in the cache (no contribution to schema map).
Optionally count them in the dir hash so re-parses fire when they change.

---

## Output sizing

Per CHECKPOINT.md `## Big-File Summaries` convention: stay under ~50
lines per block. For large schemas (>30 tables):

- Show only tables touched in the last 30 days OR most-frequently-altered
- Add a footer: "+N more tables (full list in <migrations_dir>; re-run
  schema-manager with `focus=<table>` for a deep-dive)"

This keeps the cached summary readable; full detail is one targeted
re-run away.

---

## Worked example — Supabase

Given:
```
supabase/migrations/
  20260101120000_initial.sql                 (CREATE users, tenants, posts)
  20260215090000_add_rls.sql                  (CREATE POLICY × 4)
  20260301120000_add_user_avatar.sql          (ALTER users ADD avatar_url text)
  20260504005313_add_meta_policy_settings.sql (CREATE meta_policy_settings)
```

Cache block produced:

```yaml
path:         supabase/migrations
size_bytes:   18432
hash:         a3f9b2c8d1e0
recorded_at:  2026-05-04T03:00:00Z
recorded_by:  schema-manager (orquestrum skill)
```

**Summary:**

| Table | Latest migration | Columns | Notable |
|---|---|---|---|
| `users` | `20260301120000_add_user_avatar.sql` | id, email, name, avatar_url, created_at | UNIQUE(email), RLS on user_id |
| `tenants` | `20260101120000_initial.sql` | id, name, plan, created_at | RLS on owner_id |
| `posts` | `20260215090000_add_rls.sql` | id, tenant_id, user_id, body, created_at | UNIQUE(tenant_id, slug), RLS on tenant_id |
| `meta_policy_settings` | `20260504005313_add_meta_policy_settings.sql` | id, tenant_id, rule_key, value | UNIQUE(tenant_id, rule_key) |

**Conventions detected:** Supabase, RLS on all writable tables, tenant_id pattern, no soft-delete yet.

**Stale flags:** none.

---

## When the cache lies (hash collision risk)

The hash is `sha256(sorted_filenames + sorted_contents)`. Collision risk
is astronomically low. If the user reports "the cache is wrong, but the
hash matches" → trust the cache, but offer to forcibly re-parse via
`hash=force` (skips the cache check, always re-parses, overwrites the
block). That's the escape hatch.
