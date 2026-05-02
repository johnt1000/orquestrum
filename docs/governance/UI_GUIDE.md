# UI Console Guide

The Orquestrum Console is a local-only, single-user web UI for browsing the framework's docs, catalog, coverage matrix, and live session metrics. **Read-only at this stage** — Wave A. Action capabilities (run convert, edit configs, audits) come in Wave B.

---

## Quick start

```bash
# Install UI dependencies (one-time)
uv sync --extra ui

# Run from the Orquestrum repo root → framework mode
uv run scripts/ui/serve.py
# → http://127.0.0.1:7700

# Run inside an installed project → project mode
uv run scripts/ui/serve.py --mode project --root /path/to/your/project
```

Open http://127.0.0.1:7700 in any browser.

---

## Modes

The same codebase serves two modes via flag/env:

| Mode | When to use | What it shows |
|------|-------------|---------------|
| **framework** | Running from the Orquestrum repo (you're maintaining the framework itself) | The 8 canonical agents + 25 skills, all docs, coverage matrix |
| **project** | Running inside a target project that received Orquestrum (you're using the framework) | Installed agents under `.claude/agents/` or `.opencode/agents/`, project's `.orquestrum/metrics/`, project-side docs |

Mode resolution priority:

1. `--mode <framework|project>` CLI flag
2. `ORQ_MODE` env var
3. Auto-detect: presence of `agents/`, `skills/`, `scripts/lib/`, `docs/agent-context/` → framework, otherwise project.

The console refuses to start when mode and root are inconsistent (e.g. framework mode pointed at a project without `agents/`).

---

## CLI options

```
uv run scripts/ui/serve.py [--mode framework|project] [--root PATH] [--port N] [--host HOST]
```

| Option | Default | Notes |
|--------|---------|-------|
| `--mode` | auto-detect | Force `framework` or `project` |
| `--root` | `.` (cwd) | Or `$ORQ_ROOT` env |
| `--port` | `7700` | Or `$ORQ_PORT` env |
| `--host` | `127.0.0.1` | **Do NOT bind 0.0.0.0** — the console has no auth by design |

---

## Pages

| Route | Wave | What |
|-------|:----:|------|
| `/` | A | Dashboard (project mode) or catalog (framework mode) |
| `/dashboard` | A | Live metrics: tokens, cost, top skills, budget bar |
| `/docs` | A | All docs grouped by audience (🧠 agent-context, 👤 governance, 📊 baselines, 📄 other) |
| `/docs/search?q=...` | A | Full-text search via ripgrep (or Python regex fallback) |
| `/docs/view?p=PATH` | A | Render a single markdown doc |
| `/catalog` | A | Agents + skills tables with tier, max_tokens, dependencies |
| `/coverage` | A | Coverage matrix (parsed from `docs/governance/COVERAGE.md`) |
| `/audits` | B | Index of available audits (payload, parity, attention-distribution) |
| `/audits/payload` | B | Run reference payload audit and render result |
| `/audits/parity` | B | Run provider parity test and render result |
| `/audits/attention-distribution` | B | Walk artifacts with attention frontmatter; bands + percentiles |
| `/convert` | B | Form to run convert.py (tool, provider, dry-run); framework mode only |
| `/healthz` | A | JSON status for scripting / readiness checks |

---

## Stack (transparent, no surprises)

- **Backend**: Python 3.12 + FastAPI + Uvicorn
- **Frontend**: Jinja2 server-rendered templates + HTMX for partial updates
- **CSS**: Pico CSS via CDN (10 KB, no build step)
- **Markdown**: mistune (safe by default — escapes raw HTML and JS)
- **Search**: ripgrep when available, Python regex fallback
- **State**: file system only — no database, no in-memory cache

Code reuse: the UI is a thin layer over `scripts/lib/{metrics,budget,attention,models,frontmatter,paths}` — same code paths as `convert.py`, `lint.py`, and the metrics dashboard renderer.

---

## Security posture (single-user local)

- Binds `127.0.0.1` only. Refuses `0.0.0.0` by default — open it explicitly via `--host` if you know what you're doing (you probably don't).
- No authentication. The threat model is "your laptop is yours."
- Path inputs to `/docs/view` are validated to live under `--root` (no `../` escapes).
- Markdown rendering escapes raw HTML by default — no untrusted JS.
- No persistent state beyond `~/.orquestrum/targets.json` (framework mode, future Wave B).

If you want team-wide access, do not lift the bind — wait for Wave B (UI action) and add a reverse proxy with proper auth.

---

## Troubleshooting

### `config error: ORQ_ROOT does not exist or is not a directory`

The `--root` you passed (or the cwd) doesn't resolve to a directory. Check the path.

### `config error: Framework mode at <path> but agents/ is missing`

You set `--mode framework` against a path that doesn't have the canonical layout. Either point `--root` at the Orquestrum repo, or use `--mode project`.

### `No metrics yet` on dashboard

Project hasn't emitted any LLM-call events. This is expected until R3 (hook integration) lands. Today, metrics are populated manually via `scripts/lib/metrics.py:append_event()` or by the hook described in `docs/governance/ROADMAP.md` § R3.

### Search returns nothing for known terms

Check whether ripgrep is installed: `which rg`. The fallback Python regex is slower and case-sensitive in the same way; it should still work.

### Port 7700 already in use

Pass `--port 7800` (or any free port). Or `export ORQ_PORT=7800`.

---

## Wave B — what's available now

Wave B adds action capabilities. Routes shell out to existing scripts synchronously (operations finish in seconds), capture stdout, render the output. Edits use a strict preview→apply pattern with in-process lint preflight.

### Audits + run scripts

- **`/audits`** — index of available audits.
- **`/audits/payload`** — reruns `scripts/audit/payload.py`.
- **`/audits/parity`** — reruns `scripts/tests/parity/run.py`.
- **`/audits/attention-distribution`** — runs `scripts/audit/attention_distribution.py` (walks `docs/03-quality/` for `attention_score` frontmatter, reports band counts + percentiles, calibration signal — feeds ROADMAP R2).
- **`/convert`** — form (tool + provider + dry-run) → runs `scripts/convert.py`. Framework mode only.
- **`/install`** — form (target dir + tool or auto-detect) → runs `scripts/install.py`. Framework mode only. Validates target exists.

### Refining agent configurations

- **`/agents/{slug}/edit`** — three-step flow:
  1. **GET** — render form pre-populated with current frontmatter (name, description, mode, temperature, max_tokens, emoji, tools.{write,edit,bash,question}).
  2. **POST** — in-process **lint preflight** (`ui/lib/edit_validator.py`); on success, render diff table (Old vs New per changed field). On error, re-render form with error list, no write.
  3. **POST `/apply`** — atomic write: build new frontmatter, dump YAML, write to `.tmp` file in same dir, `os.replace` to original. Body untouched.

The preflight enforces the same rules as `scripts/lint.py:check_agent_file` but in-memory:
- `max_tokens` ∈ [1, 16384]
- `mode` ∈ {primary, agent, subagent}
- `temperature` ∈ [0.0, 2.0]
- `tools.{write,edit,bash,question}` all booleans
- `name`, `description`, `emoji` non-empty strings

### Wave B-2 final additions

- **`/skills/{slug}/edit`** — same three-step flow as agent edit. Form fields: name, description, inject_references, inject_fewshot, emits_confidence, depends_on (comma-separated slugs), chain.next (dropdown), chain.condition. Validator cross-references `depends_on` and `chain.next` against existing skill slugs.
- **`/compact`** — picks scope (all skills | one skill), threshold (KB), dry-run, force. Invokes `scripts/build/compress_refs.py` which compresses `*-references.md` files deterministically (drop `<!-- compact:drop -->` blocks, trim fenced code > 40 lines, cap examples at 3, trim long blockquotes). Hand-written `*.compact.md` are protected unless `--force`.

### What's still NOT in Wave B (deferred)

- Multi-target install/audit (run on N targets at once)
- Body editor (we only edit frontmatter; bodies stay in your text editor)
- Diff view of full file (today's diff shows only changed frontmatter keys)

### Wave B safety rails

- All operations bounded by 120s subprocess timeout
- Subprocess stdout + stderr are captured (no shell injection: commands are arrays, not strings)
- Path inputs (e.g. doc viewer) validated against ORQ_ROOT — no `../` escapes
- Bind remains 127.0.0.1 only — no auth added in Wave B; if you want shared access, wait for Wave C
- All outputs are display-only — the UI does not write back into agent/skill files yet

---

## Roadmap pointers

- **Wave B remaining** (install, agents/skills edit, compact) — see `docs/governance/ROADMAP.md` § R12
- **Wave C** (live monitoring) — see § R13, unblocked by R3 (hook integration done 2026-05-02)
- **Doc separation** — done in this same wave, see § R10
