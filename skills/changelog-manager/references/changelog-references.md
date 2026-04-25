# Formal Reference: Changelog and Release Management

## 1. Keep a Changelog

Formatting standard for changelogs in `CHANGELOG.md`.

**Principles:**
- Changelogs are for humans, not machines
- There must be an `[Unreleased]` entry for changes not yet released
- Versions are listed in descending chronological order (most recent at the top)
- Each version has a release date
- Changes are classified into categories

**Categories:**

| Category | Usage |
|-----------|-----|
| `Added` | New functionality that did not exist before |
| `Changed` | Change in the behavior of existing functionality |
| `Deprecated` | Functionality that will be removed in a future release |
| `Removed` | Functionality removed in this release |
| `Fixed` | Bug fix |
| `Security` | Vulnerability fix or compliance improvement |

## 2. Semantic Versioning (SemVer 2.0.0)

Format: `MAJOR.MINOR.PATCH`

| Component | When to increment | Example |
|-----------|-------------------|---------|
| `MAJOR` | Breaking change — breaks compatibility with previous version | `1.0.0 → 2.0.0` |
| `MINOR` | New functionality, no breaking change | `1.0.0 → 1.1.0` |
| `PATCH` | Bug fix, no breaking change | `1.0.0 → 1.0.1` |

**Rules:**
- Once published, a version must **never** be modified
- `0.x.y` indicates the software is not yet stable (API may change)
- Pre-releases use a suffix: `1.0.0-alpha`, `1.0.0-beta.1`

## 3. What is a Breaking Change?

Breaking changes require a MAJOR bump and mandatory Migration Notes documentation.

**Examples of breaking changes:**
- Removal of an API endpoint
- Change in the request/response contract (required field added, field removed)
- Database schema change that requires manual migration
- Change to a required environment variable
- Removal of functionality that users depend on

**Examples that are NOT breaking changes:**
- Addition of a new optional field in the API response
- New functionality accessible via a new endpoint
- Internal performance improvements
- Bug fix that restores documented behavior

## 4. Release Checklist

### Pre-release
- [ ] All QAs in scope have status `Passed`
- [ ] Breaking changes identified and documented
- [ ] Migration Notes written (if applicable)
- [ ] Version number determined by SemVer
- [ ] MAJOR confirmed with the user (if applicable)

### Release
- [ ] `CHANGELOG.md` updated with new version at the top
- [ ] `[Unreleased]` is empty after the release
- [ ] `RELEASE-vX.Y.Z.md` created with full details
- [ ] Release date is the actual date, not a future date

## 5. Example CHANGELOG.md Entry

```markdown
## [1.2.0] - 2026-04-24

### Added
- Session scheduling system with email confirmation
- Endpoint `GET /api/v1/sessions` with filter by psychologist and date

### Fixed
- Fixed race condition in simultaneous session cancellation

### Security
- Health data is now encrypted at rest (AES-256)
- Logs no longer expose the patient's CPF
```
