---
id: RUNBOOK-v1
title: "Operational Runbook — {PROJECT_NAME}"
updated: YYYY-MM-DD
environment: production # staging
release_ref: RELEASE-vX.Y.Z
---

# Operational Runbook — {PROJECT_NAME}

Updated: YYYY-MM-DD  
Release: [vX.Y.Z](./RELEASE-vX.Y.Z.md)

> **Usage:** Execute each step in the order indicated. Verify the "Expected result" after each step before continuing. If the result differs from expected, stop and follow the Rollback procedure.

---

## Environment Variables

> ⚠️ List only variable **names** — never the values.

| Variable | Service | Required | Description |
|----------|---------|----------|-------------|
| `DATABASE_URL` | API | Yes | Database connection string |
| `SECRET_KEY_BASE` | API | Yes | Session signing key |
| `N8N_WEBHOOK_URL` | n8n | Yes | n8n base URL for webhooks |
| `{VAR_NAME}` | {service} | Yes/No | {description} |

---

## Deploy

**Trigger:** New release approved by QA  
**Prerequisites:** Recent backup confirmed, maintenance window agreed

### Step 1 — {step name}

```bash
{exact command}
```

- **Expected result:** {what should appear in the terminal or system}

### Step 2 — {step name}

```bash
{exact command}
```

- **Expected result:** {expected output}

---

## Rollback

**Trigger:** Deploy failed or system unstable after deploy  
**Estimated time:** ~{X} minutes

### Step 1 — {step name}

```bash
{rollback command}
```

- **Expected result:** {system returns to previous state}

---

## Health Checks

**Frequency:** Run after any deploy or restart

| Component | Command | Expected Result |
|-----------|---------|----------------|
| API | `curl -f http://localhost:{PORT}/health` | `{"status":"ok"}` |
| Database | `{ping command}` | `pong` or connection established |
| n8n | `curl -f http://localhost:5678/healthz` | `{"status":"ok"}` |
| {Component} | `{command}` | `{expected result}` |

---

## Log Reading

| Component | Command | What to look for |
|-----------|---------|-----------------|
| API | `docker logs {container} --tail 100` | 5xx errors, exceptions, timeouts |
| n8n | `docker logs n8n --tail 100 -f` | Workflow failures, webhook errors |
| {Component} | `{command}` | `{error patterns}` |

---

## Backup & Restore

### Manual Backup

**Trigger:** Before any deploy  
**Automatic frequency:** {daily/weekly}

```bash
{backup command}
```

- **Expected result:** File `backup-YYYY-MM-DD.{ext}` created at `{location}`

### Restore

**Trigger:** Data corruption, schema rollback

```bash
{restore command}
```

- **Expected result:** {system state after restore}

---

## Common Problem Diagnosis

### Problem: {observed symptom}

**Symptom:** {what the operator sees — error message, unexpected behavior}

**Diagnosis:**

```bash
{investigation command}
```

**Probable cause:** {explanation}

**Resolution:**

```bash
{correction command}
```

**Expected result:** {system operating normally}

**Related learning:** [{L-XXX}](../03-quality/learning/L-XXX.md)

---

## Escalation Contacts

| Situation | Responsible | Channel |
|-----------|------------|---------|
| Critical data incident (LGPD) | {name} | {channel} |
| Infrastructure failure | {name} | {channel} |

---

## References

- Architecture: [ARCHITECTURE-vX](../01-design/architecture/ARCHITECTURE-vX.md)
- Current release: [RELEASE-vX.Y.Z](./RELEASE-vX.Y.Z.md)
- Learnings: [docs/03-quality/learning/](../03-quality/learning/)
