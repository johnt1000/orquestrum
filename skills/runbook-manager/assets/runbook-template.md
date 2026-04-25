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

---

## Frontend Deployment (SPA / SSR)

> Include this section when the release includes a web frontend. Remove if backend-only release.

### CDN Cache Invalidation

**Trigger:** New frontend build deployed to CDN (CloudFront, Fastly, Cloudflare, etc.)

**Prerequisites:** Build artifacts uploaded to origin (S3, GCS, or equivalent)

#### Step 1 — Verify build fingerprinting

```bash
# Confirm JS/CSS filenames include content hash
ls dist/assets/ | grep -E '\.[a-f0-9]{8}\.(js|css)$'
```

- **Expected result:** Files named like `main.a3f9b2c1.js` — content-addressed names, safe to cache forever

#### Step 2 — Invalidate index.html only (if using content-addressed assets)

```bash
# CloudFront example
aws cloudfront create-invalidation \
  --distribution-id {DISTRIBUTION_ID} \
  --paths "/index.html" "/manifest.json" "/service-worker.js"
```

- **Expected result:** Invalidation created, status `InProgress` → `Completed` within 60 seconds

#### Step 3 — Verify new version is live

```bash
curl -I https://{YOUR_DOMAIN}/index.html | grep -i "x-cache\|etag\|last-modified"
```

- **Expected result:** Response header `X-Cache: Miss from cloudfront` on first request (confirms cache busted)

### Service Worker Update (PWA)

**Trigger:** New service worker file deployed

```bash
# Force service worker update for all active clients
# (ensure SKIP_WAITING is called in your SW update flow)
curl https://{YOUR_DOMAIN}/service-worker.js | head -5
```

- **Expected result:** First line of service worker contains the new build hash/date

---

## Mobile App Deployment

> Include this section when the release includes a mobile app. Remove if web-only release.

### iOS — App Store Connect

**Prerequisites:** Xcode build succeeds, provisioning profiles valid, version/build number incremented

#### Step 1 — Archive and upload build

```bash
# Using Fastlane (recommended)
bundle exec fastlane ios release

# Manual alternative
xcodebuild archive \
  -scheme {APP_SCHEME} \
  -archivePath {OUTPUT}.xcarchive \
  -configuration Release
xcodebuild -exportArchive \
  -archivePath {OUTPUT}.xcarchive \
  -exportPath {EXPORT_PATH} \
  -exportOptionsPlist ExportOptions.plist
```

- **Expected result:** Build appears in App Store Connect → TestFlight within 15–30 minutes

#### Step 2 — TestFlight validation

- Submit to internal testers (App Store Connect → TestFlight → Internal Testing)
- **Expected result:** Testers receive notification; build installs and launches correctly on iOS 15 and latest iOS

#### Step 3 — Submit for Review

- App Store Connect → App Store → Submit for Review
- **Expected result:** App enters "Waiting for Review" status; review typically completes in 24–48 hours

#### Rollback

- App Store Connect → App Store → Version History → Set previous version as active
- **Estimated time:** ~5 minutes to revert to last approved build

---

### Android — Google Play Console

**Prerequisites:** Signed APK/AAB generated, version code incremented

#### Step 1 — Upload build

```bash
# Using Fastlane (recommended)
bundle exec fastlane android release

# Manual alternative: upload AAB via Play Console UI
# or using Google Play Developer API
```

- **Expected result:** Build appears in Play Console → Internal testing within 5 minutes

#### Step 2 — Internal / Closed Testing

- Promote to Internal Testing → verify on Physical Android device (minimum supported version)
- **Expected result:** App installs via Play Store, all critical flows work

#### Step 3 — Production rollout (staged)

```
Play Console → Production → Create new release → 
  Set rollout percentage: 10% → monitor crash-free rate for 24h →
  Increase to 50% → monitor → 100%
```

- **Expected result:** Crash-free rate ≥ 99.5% at each stage before expanding rollout

#### Rollback

- Play Console → Releases → Halt release
- **Estimated time:** immediate halt; users on new version revert on next app check

---

### OTA Updates (React Native — Expo / CodePush)

> Use OTA updates only for JS bundle changes (no native module changes).

**When safe to OTA:** bug fixes, copy changes, non-breaking UI changes, no new native dependencies

**When NOT safe to OTA:** new native modules, permissions changes, major navigation changes

#### Expo EAS Update

```bash
eas update --branch production --message "{description of change}"
```

- **Expected result:** Update published; active users receive update on next app foreground

#### Microsoft CodePush

```bash
appcenter codepush release-react \
  -a {ORG}/{APP_NAME} \
  -d Production \
  --description "{description}"
```

- **Expected result:** Update deployed to Production deployment; rollout starts immediately

#### OTA Rollback

```bash
# Expo
eas update --branch production --rollback-to-embedded

# CodePush
appcenter codepush rollback {ORG}/{APP_NAME} Production
```

- **Expected result:** Users receive previous bundle on next app foreground
