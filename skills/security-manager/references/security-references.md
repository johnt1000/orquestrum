# Formal Reference: Security Analysis (OWASP + SDD)

## 1. Scope boundary

This skill covers the OWASP gaps not handled by `review-manager`. Do NOT re-check:
- A01 (Broken Access Control) — review-manager
- A02 (Cryptographic Failures) — review-manager
- A03 (Injection: SQL, command, template) — review-manager
- A05 (Security Misconfiguration) — review-manager
- A07 (Identification & Auth Failures) — review-manager
- Hardcoded secret detection — review-manager
- Input validation — review-manager
- LGPD at-rest encryption and audit log existence — review-manager

---

## 2. OWASP A04 — Insecure Design: Threat Modeling

Threat modeling is a structured question: "What can go wrong?"

### Entry point discovery

Every HTTP endpoint, webhook, queue consumer, scheduled job, and admin CLI command is an entry point. List them all before modeling.

### Trust boundary mapping

A trust boundary is a line where data crosses between security domains:
- External user → web server
- Web server → database
- Service A → Service B (even internal)
- Public API → admin-only API

Each boundary crossing must have: authentication check, authorization check, input validation.

### STRIDE per entry point

| Threat | Question |
|--------|---------|
| **S**poofing | Can an attacker impersonate a legitimate caller? |
| **T**ampering | Can data be modified in transit or at rest? |
| **R**epudiation | Can actions be denied? Is there an audit trail? |
| **I**nformation Disclosure | Can unauthorized data be exposed? |
| **D**enial of Service | Can this entry point be exhausted? |
| **E**levation of Privilege | Can a low-privilege caller reach admin functions? |

Document each threat as: `{STRIDE type}: {description} → {mitigation or ❌ gap}`

---

## 3. OWASP A06 — Vulnerable & Outdated Components

### What to check

1. **Direct dependencies** added or updated in this Task
2. **Transitive dependencies** — flag if a direct dep pulls in a known-CVE transitive dep
3. **Unmaintained packages** — no releases in 12+ months AND used in security-relevant code

### Severity mapping

| Condition | Severity |
|-----------|---------|
| Known CVE with CVSS ≥ 9.0 | Critical |
| Known CVE with CVSS 7.0–8.9 | High |
| Known CVE with CVSS 4.0–6.9 | Medium |
| No CVE but unmaintained + security-critical path | Medium |
| Outdated but no CVE | Low |

### Where to look

`package.json`, `package-lock.json`, `Gemfile.lock`, `requirements.txt`, `poetry.lock`, `go.mod`, `go.sum`, `pom.xml`, `build.gradle`

---

## 4. OWASP A09 — Security Logging & Monitoring Failures

### What must be logged

- Authentication success and failure (username, timestamp, IP — never password)
- Authorization failure (403, permission denied)
- Admin and privileged actions
- Critical business events (payment, account deletion, role change)

### What must NOT be logged

- Passwords (any form)
- Full payment card data or tokens
- Session tokens or JWT content
- Personal health data, CPF, full name when not operationally required

### Verification pattern

Search Task artifacts for logging calls. For each security-relevant event (auth failure, permission check), verify a log call exists. For each log call, verify no sensitive field is interpolated into the message.

---

## 5. OWASP A10 — SSRF

SSRF occurs when the server makes HTTP requests to URLs controlled by the user.

### High-risk patterns

```js
// Dangerous — user-controlled URL
fetch(req.body.webhook_url)
axios.get(req.query.callback)

// Safer — allowlist approach
const ALLOWED_HOSTS = ['api.partner.com']
if (!ALLOWED_HOSTS.includes(new URL(userUrl).hostname)) throw new Error('URL not allowed')
```

### What to check

1. Any HTTP client call where the URL is derived from user input
2. File read operations from URLs
3. Redirects that follow user-provided locations
4. Webhook registration endpoints — is the registered URL validated?

### Mitigation checklist

- [ ] URL allowlist enforced at the call site
- [ ] Private IP ranges blocked (10.x, 192.168.x, 127.x, 169.254.x)
- [ ] Redirect following disabled or count-limited

---

## 6. API Security

### Rate limiting

Every endpoint performing authentication, data mutation, or expensive computation must have rate limiting. Document: window, max requests, response code on limit (429).

### Schema validation

Request body schema must be validated before processing using a schema library (Joi, Zod, JSON Schema, etc.) — not just presence checks.

### API versioning

Breaking changes require: version increment, deprecation notice, sunset date. Document in CHANGELOG Security section.

---

## 7. Secrets Rotation Policy

For each credential or secret introduced or used:
- Document lifetime (e.g., "JWT secret — rotated every 90 days")
- Document rotation mechanism (manual, automated, KMS)
- Verify rotation does not require full redeployment (hot rotation preferred)

**Minimum requirements:**
- [ ] All secrets stored in environment variables or secrets manager (not hardcoded)
- [ ] Rotation lifetime defined
- [ ] Emergency rotation procedure documented

---

## 8. Infrastructure Security (when infra files exist)

Check Terraform, Docker Compose, Kubernetes manifests, or CI/CD configuration for:

| Check | Criterion |
|-------|----------|
| IAM least-privilege | Roles grant only the permissions actually required |
| Open ports | No ports exposed beyond what the service requires |
| TLS version | TLS ≥ 1.2; TLS 1.0 and 1.1 disabled |
| Container root | Containers should not run as root |
| Secrets in env | CI/CD secrets stored as masked variables, not hardcoded in YAML |
