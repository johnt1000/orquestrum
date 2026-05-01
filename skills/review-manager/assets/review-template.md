---
id: REV-vX
title: "{TITLE}"
status: Pending # Approved | Changes Requested | Rejected
version: 1.0
reviewer: "{agent/human}"
complexity: Medium # Low | Medium | High
traceability_score: "0/0 (0%)"  # X requirements covered / Y total — filled by Ward
created: YYYY-MM-DD HH:mm
updated: YYYY-MM-DD HH:mm
last_validated: YYYY-MM-DD
drift_risk: low # low | medium | high
---

# REVIEW vX — {TITLE}

Status: 🟢 Approved | 🟡 Changes Requested | 🔴 Rejected  
Date: YYYY-MM-DD HH:mm

---

## Scope

- Tasks:
  - [T1](../../02-planning/tasks/T1.md)
- Spec: [spec-vX](../../00-discovery/spec/spec-vX.md)

---

## Summary

{technical summary of the review performed}

---

## Findings

### 🔴 Critical

- {e.g.: SQL Injection vulnerability identified in module X}

### 🟡 Medium

- {e.g.: Missing logs at n8n failure points}

### 🟢 Minor

- {e.g.: Variable naming outside Ruby on Rails conventions}

---

## Security Considerations

- {Potential risks to data privacy or infrastructure stability}

---

## Recommendations

- {Practical actions for the developer to apply}

---

## Decision

Approved | Changes Required | Rejected

---

## References

- Tasks: [T1](../../02-planning/tasks/T1.md)
- Spec: [spec-vX](../../00-discovery/spec/spec-vX.md)
- Architecture: [arch-v1](../../01-design/architecture/arch-v1.md)
- ADR: [ADR-001](../../00-discovery/adr/ADR-001.md)

---

## ⚠ Audit Warnings

<!-- Self-audit section — filled by Ward before handoff. If no warnings: "No warnings — artifact passed self-audit." -->

- [ ] {placeholder or warning detected}

---

## Handoff Checklist

> Complete before signaling completion to Ward / qa-manager.

- [ ] All `{...}` placeholders replaced with real content
- [ ] Every finding has a severity level and a status (Open / Resolved)
- [ ] All OWASP Top 10 items checked
- [ ] LGPD compliance noted (if personal data involved)
- [ ] `Approved Artifacts` section lists exact file paths reviewed
- [ ] `traceability_score` computed: Req → Task → QA criterion coverage %
- [ ] Final status is `Approved` or `Changes Requested` (not Draft)
- [ ] If `Changes Requested`: correction Task ID linked
- [ ] `## ⚠ Audit Warnings` section completed (even if empty)
- [ ] Handoff to: **qa-manager** (Ward) — bring Approved Artifacts list and any open findings
