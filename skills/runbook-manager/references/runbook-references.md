# Formal Reference: Operational Runbooks

## 1. What is a Runbook?

A Runbook is a document that describes step-by-step operational procedures so that any operator — human or AI agent — can execute a task without relying on tacit knowledge.

**A good runbook allows someone who has never seen the system to:**
- Deploy a new version
- Roll back after a failure
- Diagnose the most common problems
- Run backup and restore

## 2. Principles of an Effective Runbook (SRE)

### Actionable
Each step must have an exact command or specific action. Never write "configure the service" — write the command.

### Verifiable
After each critical step, include "Expected result". The operator must not guess whether the step worked.

### Secure
Never document secret values. Document only the names of environment variables. Use a secrets manager.

### Up-to-date
An outdated runbook is more dangerous than no runbook. Update it with every release that changes infrastructure or procedures.

## 3. Procedure Structure

```markdown
## {Procedure Name}

**Trigger:** {when to execute this procedure}
**Prerequisites:** {what must be ready before starting}
**Estimated time:** {X minutes}

### Step 1 — {step description}
```bash
exact command here
```
- **Expected result:** {output or system state}

### Step 2 — {description}
...

**Rollback:** {what to do if this procedure fails}
```

## 4. Health Checks — Standards

### For Docker/Podman containers
```bash
docker inspect --format='{{.State.Health.Status}}' {container_name}
# Expected result: "healthy"
```

### For HTTP APIs
```bash
curl -f -s -o /dev/null -w "%{http_code}" http://localhost:{PORT}/health
# Expected result: 200
```

### For PostgreSQL
```bash
pg_isready -h localhost -p 5432 -U {user}
# Expected result: "accepting connections"
```

### For n8n
```bash
curl -f http://localhost:5678/healthz
# Expected result: {"status":"ok"}
```

## 5. Reading Logs in Proxmox/Docker

| Scenario | Command |
|---------|---------|
| Last 100 lines | `docker logs {container} --tail 100` |
| Follow in real time | `docker logs {container} -f` |
| Filter errors | `docker logs {container} 2>&1 \| grep -i error` |
| Logs since last deploy | `docker logs {container} --since {timestamp}` |
| Proxmox (host) logs | `journalctl -u pve-cluster --since "1 hour ago"` |

## 6. Complete Runbook Checklist

- [ ] Environment variables listed (names only)
- [ ] Deploy procedure documented with expected result per step
- [ ] Rollback procedure documented
- [ ] Health checks for all main components
- [ ] Log reading commands documented
- [ ] Backup and Restore documented
- [ ] At least 3 common problems with diagnosis and resolution
- [ ] Escalation contacts for critical incidents (LGPD, infra)
- [ ] Up-to-date date (synchronized with last release)

## 7. Secrets and Environment Variables

**NEVER document:**
- Passwords
- API keys
- Access tokens
- Connection strings with credentials

**ALWAYS document:**
- Variable name: `DATABASE_URL`
- What it is for: "PostgreSQL connection string"
- Where to configure: "`.env` locally or Vault/Secret Manager in production"
- Whether it is required or optional

## 8. Integration with Learning Manager

When an incident is resolved and documented in `docs/03-quality/learning/`, extract the diagnosis and resolution to the "Common Problem Diagnosis" section of the runbook. This transforms one-off learnings into permanent operational knowledge.
