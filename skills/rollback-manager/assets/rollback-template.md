---
id: ROLLBACK-vX.Y.Z
title: "{TITLE}"
status: Drafted # Drafted | Verified | Executed | Superseded
release_ref: vX.Y.Z
reversibility: Conditional # Reversible | Conditional | Irreversible
created: YYYY-MM-DD HH:mm
verified_in_staging: YYYY-MM-DD HH:mm
# Human Attention Mediation
attention_score: 100
attention_band:  green
attention_factors: []
---

# ROLLBACK vX.Y.Z — {TITLE}

> Rollback procedure for release vX.Y.Z. Companion to CHANGELOG-vX.Y.Z.

---

## Reversibility class

**Class:** {Reversible | Conditional | Irreversible}

{One paragraph explaining why. Include the migration path if applicable.}

If **Irreversible**, sign-off is required:
- Signed by: `{role}` on `{YYYY-MM-DD}`
- Justification: {single sentence}

---

## Pre-conditions

- [ ] {state condition that must hold before rollback runs}
- [ ] {condition}

---

## Execution Steps

| # | Command / Action | Expected outcome |
|---|------------------|------------------|
| 1 | `{exact command or UI step}` | {observable result} |
| 2 | `{...}` | {...} |

---

## Verification

> Explicit checks that the rollback succeeded. Not subjective.

| Check | How | Pass criterion |
|-------|-----|----------------|
| App version | `curl /version` | returns previous tag |
| DB schema | query `information_schema` | columns / tables match prior version |
| Error rate | dashboard `{link}` | back to baseline within {N} minutes |

---

## Automatic trigger

| Field | Value |
|-------|-------|
| Condition | {e.g. "error rate > 2% sustained 5 min"} |
| Source | {monitoring path} |
| Cooldown | {time before re-triggering allowed} |
| Notification | {channel / on-call role} |

---

## Data implications

> What is lost or invalidated by running this rollback. Required for Conditional and Irreversible.

- {row class / file / state}
- {...}

---

## ⚠ Audit Warnings

{populated by self-audit}
