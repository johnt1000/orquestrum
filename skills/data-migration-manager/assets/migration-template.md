---
id: MIG-XXX
title: "{TITLE}"
status: Drafted # Drafted | Dry-run passed | Executed | Rolled back
classification: Online # Online | Offline | Lazy
reversibility: Reversible # Reversible | Conditional | Irreversible
task_ref: T{ID}
adr_ref: ADR-XXX
pii: false # true if the migration touches PII / LGPD-protected data
created: YYYY-MM-DD HH:mm
dry_run_at: YYYY-MM-DD HH:mm
# Human Attention Mediation
attention_score: 100
attention_band:  green
attention_factors: []
---

# MIG-XXX — {TITLE}

---

## Classification

| Field | Value |
|-------|-------|
| Type | Online / Offline / Lazy |
| Reversibility | Reversible / Conditional / Irreversible |
| PII / LGPD touch | true / false |
| Downtime budget | {minutes or "0 (online)"} |

**Why this class:** {one paragraph}

---

## Forward path

| # | Statement / Action | Commit window | Lock impact |
|---|--------------------|---------------|-------------|
| 1 | `ALTER TABLE … ADD COLUMN …` | transactional | none (online) |
| 2 | backfill batch (1000 rows) | per batch | row-level |
| 3 | `ALTER TABLE … SET NOT NULL` | transactional | brief metadata |

---

## Backward path

> If Reversible or Conditional. If Irreversible, link to `rollback-manager` for the compensating action.

| # | Statement / Action | Notes |
|---|--------------------|-------|
| 1 | {undo step} | {data implications} |

---

## Test data shape

> Required. Row counts and at least one full example.

**Before:**
```
table: users
rows:  1,234,567
example: { id: 42, email: "...", created_at: "..." }
```

**After:**
```
table: users
rows:  1,234,567   # parity expected; if not, document why
example: { id: 42, email: "...", created_at: "...", new_field: "default" }
```

---

## Cutover plan

> For Online migrations.

| Phase | Trigger | Action |
|-------|---------|--------|
| Start dual-write | deploy of release vX.Y.Z | new field is written by app |
| Backfill window | post-deploy +0h | batched backfill begins |
| Cutover | backfill 100% verified | reads switch to new field |
| End dual-write | cutover +24h | old field can be dropped (next release) |

---

## Rollback compatibility

| Release rolled back? | Migration state | Action |
|----------------------|----------------|--------|
| Yes, before cutover | dual-write phase | drop new column (Reversible path) |
| Yes, after cutover | reads switched | hold migration; rollback would lose data — manual decision |

---

## PII / LGPD review

> Required if `pii: true`.

| Question | Answer |
|----------|--------|
| Does the migration copy/move PII? | yes/no |
| Is encryption preserved across the move? | yes/no |
| Does retention policy change? | yes/no |
| Cipher review reference | `SEC-{task-ref}` |

---

## ⚠ Audit Warnings

{populated by self-audit}
