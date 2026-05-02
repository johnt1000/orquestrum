# Supply Chain Policy

External agent/skill dependencies installed by `orquestrum deps` are pinned by **commit SHA**, not branch name. This document explains why and how to rotate the pins safely.

---

## What is pinned

| Name | Repository | What it provides |
|------|------------|------------------|
| `agency` | [`msitarzewski/agency-agents`](https://github.com/msitarzewski/agency-agents) | 184+ specialized agents (engineering, design, marketing, etc.) used by every non-Helm orchestrator |
| `skills` | [`anthropics/skills`](https://github.com/anthropics/skills) | Anthropic-curated skills bundle, including supabase integration |

The single source of truth is `pinned_refs.toml` at the repo root.

---

## Why pin by SHA

An earlier version of `orquestrum deps` cloned the **default branch** of each upstream. That meant:

1. **Silent drift.** A new upstream commit landed in every fresh install with no review.
2. **Reproducibility hole.** Two installs done a week apart could end up with different agents and skills, with no audit trail.
3. **Supply-chain risk.** A compromised or accidentally bad upstream commit propagates immediately.

Pinning by SHA closes all three: every install consumes the exact bytes that were reviewed when the pin was last rotated.

---

## Rotation policy

Rotation is **explicit and reviewed**. The framework never auto-updates pins.

### Cadence
- **Default: monthly review** of upstream activity. If significant changes have landed, rotate.
- **Security advisory or known bug fix upstream:** rotate immediately.
- **Before each Orquestrum release:** rotate as part of release prep, then run the full test suite (parity, lint, smoke).

### Steps

```bash
# 1. Refresh SHAs in pinned_refs.toml to current upstream HEAD
orquestrum deps --update-pins

# 2. Review what changed (look at upstream commit logs for context)
git diff pinned_refs.toml
gh repo view msitarzewski/agency-agents --json defaultBranchRef
# or visit: https://github.com/<repo>/compare/<old-sha>...<new-sha>

# 3. Smoke test: install into a scratch target and validate
orquestrum deps --target /tmp/orq-deps-smoke

# 4. Commit with the rotation date
git add pinned_refs.toml
git commit -m "chore(deps): rotate pinned SHAs ($(date +%Y-%m-%d))"
```

### What to inspect during review

When reviewing the diff between the old and new SHA on each upstream:

- New agents/skills added — do their descriptions match what we expect to delegate to them?
- Removed agents/skills — does Orquestrum still reference them anywhere?
- Tool/permission changes — did an agent gain `bash: true` access? Why?
- Frontmatter schema drift — did the `name`, `description`, or `mode` semantics change?
- Anything that looks like obfuscated content, suspicious dependencies, or a maintainer change.

If anything looks off, **do not rotate**. Open an issue upstream first.

---

## File format

`pinned_refs.toml` is a TOML array of `[[refs]]` tables. Each entry has:

| Field | Required | Notes |
|-------|----------|-------|
| `name` | yes | Identifier used by `--only NAME` |
| `repo` | yes | HTTPS clone URL |
| `sha` | yes | Full 40-char commit SHA |
| `last_pinned` | yes | ISO-8601 date (`YYYY-MM-DD`) of last rotation |
| `notes` | no | Operator notes about what this dependency provides |

Adding a new dependency: append a `[[refs]]` block, then update `orquestrum/core/deps.py` to consume it.

---

## What is NOT pinned

Orquestrum's own canonical source (this repo) is not "pinned" — its versioning is git itself. When you run `orquestrum convert` and `orquestrum install`, you get the bytes of the working tree. If reproducibility matters for an Orquestrum release, tag the commit and reference the tag.
