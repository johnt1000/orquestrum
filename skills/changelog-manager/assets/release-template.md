---
id: RELEASE-vX.Y.Z
title: "{TITLE}"
status: Draft # Released
version: X.Y.Z
type: Major # Minor | Patch
created: YYYY-MM-DD
---

# Release vX.Y.Z — {TITLE}

Status: 🟡 Draft | 🟢 Released  
Date: YYYY-MM-DD

---

## Summary

{1–3 sentences describing what was delivered in this release and the value generated}

---

## Scope

### Included QAs

| QA | Title | Status |
|----|-------|--------|
| [QA-v1](../03-quality/qa/QA-v1.md) | {title} | ✅ Passed |

### Included Epics

| Epic | Title |
|------|-------|
| [E001](../02-planning/epics/E001.md) | {title} |

---

## Changes

### ✨ Added

- {new feature delivered}

### 🔄 Changed

- {change in existing feature}

### 🐛 Fixed

- {bug fix}

### 🔒 Security

- {security fix or compliance improvement}

### ⚠️ Deprecated

- {feature marked for future removal}

### 🗑️ Removed

- {feature removed}

---

## Breaking Changes

> ⚠️ This section is mandatory. If there are no breaking changes, write: "No breaking changes in this release."

{breaking change description and impact}

---

## Migration Notes

> Fill in when there is a database schema, API contract, or required configuration change.

### Schema

```sql
-- Required migrations
```

### Environment Variables

| Variable | Action | Description |
|----------|--------|-------------|
| `NEW_VAR` | Add | {what it is for} |
| `OLD_VAR` | Remove | {replaced by} |

---

## References

- Spec: [spec-vX](../00-discovery/spec/spec-vX.md)
- Architecture: [ARCHITECTURE-vX](../01-design/architecture/ARCHITECTURE-vX.md)
- QAs: (links above)

---

## Handoff Checklist

> Complete before signaling end of pipeline to Cast.

- [ ] All `{...}` placeholders replaced with real content
- [ ] Version follows SemVer (MAJOR.MINOR.PATCH)
- [ ] All artifacts shipped listed with their versions
- [ ] QA approval reference included (QA-vX document link)
- [ ] Breaking changes section explicitly states "None" or lists changes with migration notes
- [ ] Handoff to: **runbook-manager** (Cast) — bring the Artifacts Shipped list for operational documentation
