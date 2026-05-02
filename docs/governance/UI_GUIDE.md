# UI Console Guide

The Orquestrum Console is a local-only, single-user web UI. It browses
docs, the catalog, the coverage matrix, and live session metrics; in
framework mode it can also edit agent/skill frontmatter, run audits,
generate integrations, install them into a target project, and compress
oversized skill references — all from the browser.

> Status: **Wave B (read/write)**. Wave A (read-only) shipped in R11 and
> Wave B in R12; Wave C (live monitoring) is tracked as R13. UX
> overhaul (R14) added the home page, async job runner, side-by-side
> diff, and inline form validation.

---

## Quick start

```bash
# Install the UI extra (one-time)
orquestrum extras install ui

# Run from the Orquestrum repo root → framework mode (auto-detected)
orquestrum web
# → http://127.0.0.1:7700

# Run inside an installed project → project mode
orquestrum web --target /path/to/your/project --mode project
```

`make web` is a shortcut for the first form. `make doctor` reports
whether the `[ui]` extra is installed.

---

## Modes

The same codebase serves two modes via flag/env:

| Mode | When to use | What it shows |
|------|-------------|---------------|
| **framework** | Running from the Orquestrum repo (you maintain the framework itself) | The 8 canonical agents + 25 skills, all docs, coverage matrix, plus the action endpoints (convert/install/compact/edit) |
| **project**   | Running inside a target project that received Orquestrum (you use the framework) | Installed agents under `.claude/agents/` or `.opencode/agents/`, project's `.orquestrum/metrics/`, project-side docs. Action endpoints are disabled. |

Mode resolution priority:

1. `--mode <framework|project>` CLI flag
2. `ORQ_MODE` env var
3. Auto-detect: presence of `agents/`, `skills/`, `orquestrum/`,
   `docs/agent-context/` → framework, otherwise project.

The console refuses to start when mode and root are inconsistent (e.g.
framework mode pointed at a path without `agents/`).

---

## CLI options

```
orquestrum web [--target PATH] [--mode framework|project] [--port N] [--host HOST] [--no-browser]
```

| Option | Default | Notes |
|--------|---------|-------|
| `--target` | cwd | Or `$ORQ_ROOT` env |
| `--mode` | auto-detect | Force `framework` or `project` |
| `--port` | `7700` | Or `$ORQ_PORT` env |
| `--host` | `127.0.0.1` | **Do NOT bind 0.0.0.0** — the console has no auth by design |
| `--no-browser` | open browser | Suppress the auto-open on startup |

---

## Pages

Every page extends `ui/templates/base.html`, which provides the global
nav (with `aria-current="page"` on the active link), the mode badge,
and the inline JS handler for `data-confirm` / `data-spinner`.

| Route | Mode | What |
|-------|:----:|------|
| `/` | both | Home — hero + cards + quick stats; mode-aware copy |
| `/dashboard` | both | Live metrics: tokens, cost, top skills, budget bar |
| `/docs` | both | All docs grouped by audience (🧠 agent-context, 👤 governance, 📊 baselines) |
| `/docs/search?q=...` | both | Full-text search via ripgrep (or Python regex fallback) |
| `/docs/view?p=PATH` | both | Render a single markdown doc |
| `/catalog` | both | Agents + skills tables with tier, max_tokens, dependencies |
| `/coverage` | both | Coverage matrix (parsed from `docs/governance/COVERAGE.md`) |
| `/audits` | both | Index of available audits (payload, parity, attention-distribution) |
| `/audits/{name}` | both | **Submits an async job**, redirects to `/jobs/{id}` |
| `/convert` | framework | Form (tool, provider, dry-run); submits a job |
| `/install` | framework | Form (target dir, tool or auto-detect); submits a job |
| `/compact` | framework | Form (scope, threshold, dry-run, force); submits a job |
| `/agents/{slug}/edit` | framework | 3-step edit flow (form → preview+diff → apply atomic) |
| `/skills/{slug}/edit` | framework | Same 3-step flow with skill-specific fields |
| `/jobs/{id}` | both | Live progress for an async job; HTMX polls every 1s until terminal |
| `/jobs/{id}/partial` | both | HTMX swap target — drops `hx-trigger` when the job is done |
| `/healthz` | both | JSON status for scripting / readiness checks |

---

## Stack (transparent, no surprises)

- **Backend**: Python 3.12 + FastAPI + Uvicorn
- **Frontend**: Jinja2 server-rendered templates + HTMX for partial
  updates and job polling
- **CSS**: Pico CSS via CDN (10 KB, no build step) + ~100 lines of
  overrides in `ui/static/app.css`
- **Markdown**: mistune (safe by default — escapes raw HTML and JS)
- **Search**: ripgrep when available, Python regex fallback
- **State**: file system + a 50-entry in-memory job registry
  (`ui/lib/jobs.py`); no DB, no on-disk cache

Code reuse: the UI is a thin layer over `orquestrum/lib/{metrics,
budget,attention,models,frontmatter,paths}` — same code paths as
`orquestrum convert`, `orquestrum lint`, and the dashboard renderer.

See [`ui/README.md`](../../ui/README.md) for the directory layout,
request flow diagram, and "how to add a route" pointer.

---

## Async jobs and HTMX polling (R14 Onda 2)

Long-running operations (convert, install, audits, compact) used to
block the request thread for up to 120s. They now submit a Job and
303-redirect to `/jobs/{id}`; the page renders a live progress
partial that polls itself every second until the subprocess reaches
a terminal state, then drops the polling attribute and renders the
final output.

- Markdown-emitting audits (payload, attention-distribution) get
  rendered HTML; everything else stays in `<pre>`.
- The job registry is bounded (50 entries, LRU-evicted).
- Subprocess invocations use `python -m orquestrum.core.X` so the
  CLI and the UI share one source of truth.

---

## Editing agents and skills

Three-step flow at `/agents/{slug}/edit` and `/skills/{slug}/edit`:

1. **GET** — render the form pre-populated with current frontmatter.
2. **POST** — in-process **lint preflight** (`ui/lib/edit_validator.py`
   mirrors `orquestrum/core/lint.py:check_*`); on success render a
   side-by-side diff (old / new per changed key); on failure highlight
   the affected inputs (`aria-invalid="true"` + inline
   `<small role="alert">`) with the exact validator message.
3. **POST `/apply`** — atomic write: dump YAML to a `.tmp` file in the
   same dir, `os.replace` to the original. Body is untouched. Form
   carries a `data-confirm` attribute so the user gets a confirmation
   prompt before disk is written.

Validator rules (single source of truth):

- Agents: `max_tokens` ∈ [1, 16384]; `mode` ∈ {primary, agent,
  subagent}; `temperature` ∈ [0.0, 2.0]; `tools.{write,edit,bash,
  question}` all booleans; `name`, `description`, `emoji` non-empty.
- Skills: `inject_references`, `inject_fewshot` ∈ {false, full,
  compact}; `emits_confidence` boolean; `chain.next` + `depends_on`
  cross-checked against existing skill slugs.

---

## Security posture (single-user local)

- Binds `127.0.0.1` only. Refuses `0.0.0.0` by default — open it
  explicitly via `--host` if you know what you're doing (you probably
  don't).
- No authentication. The threat model is "your laptop is yours."
- Path inputs to `/docs/view` are validated to live under `--target`
  (no `../` escapes).
- Markdown rendering escapes raw HTML by default — no untrusted JS.
- Subprocess invocations use array-form `cmd` (no shell, no
  injection); jobs have a timeout (120-180s).
- 404 returns HTML by default and JSON only when the client sets
  `Accept: application/json`.

If you want team-wide access, do not lift the bind — wait for Wave C
or add a reverse proxy with proper auth.

---

## Troubleshooting

### `config error: ORQ_ROOT does not exist or is not a directory`

The `--target` you passed (or the cwd) doesn't resolve to a
directory. Check the path.

### `config error: Framework mode at <path> but agents/ is missing`

You set `--mode framework` against a path that doesn't have the
canonical layout. Either point `--target` at the Orquestrum repo, or
use `--mode project`.

### `No metrics yet` on dashboard

Project hasn't emitted any LLM-call events. The empty state on
`/dashboard` lists the three steps to start collecting; see
[`HOOKS.md`](HOOKS.md) for the hook contract.

### Search returns nothing for known terms

Check whether ripgrep is installed: `which rg`. The Python regex
fallback is slower and case-sensitive; it should still work.

### Port 7700 already in use

Pass `--port 7800` (or any free port). Or `export ORQ_PORT=7800`.

### A job page is stuck on "Running…" forever

Open `/jobs/{id}/partial` directly to see the raw state; if the
subprocess crashed before producing output, `state` will be `failed`
and `stderr` will be populated. Job timeouts default to 120-180s
depending on the route.

---

## Roadmap pointers

- **R11 — Wave A (read-only)** — done 2026-05-02
- **R12 — Wave B (action)** — done 2026-05-02
- **R13 — Wave C (live monitoring)** — pending; unblocked by R3
  (hook integration)
- **R14 — UX & Onboarding** — done 2026-05-02 (home page, doctor,
  jobs, side-by-side diff, inline validation, Makefile, pre-commit)
- **Onda 4 (tests + CI)** — pending; see ROADMAP § R14 Onda 4 for
  the suggested triggers
