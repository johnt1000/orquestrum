---
id: SEC-{task-ref}
title: "{TITLE}"
status: Clear # Findings | Blocked
task_ref: T{ID}
date: "{YYYY-MM-DD}"
version: 1.0
---

# Security Report — SEC-{task-ref}

**Task:** `T{ID} — {Task title}`
**Architecture ref:** `docs/01-design/architecture/ARCHITECTURE-vX.md`
**SPEC ref:** `docs/00-discovery/spec/spec-vX.md`
**Analyst:** Cipher / security-manager

---

## Status

**Overall:** Clear ✅ / Findings ⚠️ / Blocked ❌

---

## Scope Coverage

| Area | Checked | Status |
|------|:-------:|--------|
| A04 — Threat Modeling | ✅ | Clear / Findings |
| A06 — Dependency Vulnerabilities | ✅ | Clear / Findings |
| A08 — Software & Data Integrity | ✅ | Clear / Findings |
| A09 — Security Logging | ✅ | Clear / Findings |
| A10 — SSRF | ✅ | Clear / Findings |
| API Security | ✅ | Clear / Findings |
| Secrets Rotation | ✅ | Clear / Findings |
| Infrastructure Security | ✅ / N/A | Clear / Findings |

---

## Findings

### 🔴 Critical

*(None)*

### 🟠 High

*(None)*

### 🟡 Medium

*(None)*

### 🔵 Low / Informational

*(None)*

---

## Threat Model Summary

**Entry points identified:** {list or "none new"}
**Trust boundaries crossed:** {list or "none new"}
**Threat vectors documented:** {list or "none"}
**Mitigations verified:** {list or "n/a"}

---

## Correction Tasks Created

*(None — or list Task IDs)*

---

## ADR Signal

*(None — or "ADR required for {security decision}" → signal Helm/Lore)*

---

## Handoff Checklist

- [ ] All Critical and High findings have a correction Task assigned
- [ ] SEC report status is `Clear` or `Findings` (not `Blocked`) before advancing to Ward
- [ ] ADR signal sent to Helm if an architectural security decision is required
