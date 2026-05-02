# `ui/` — Orquestrum web console

Single-user, local-only FastAPI app that renders the canonical source
(framework mode) or one installed project (project mode). Launched via
`orquestrum web`.

> **Read this first if you want to add a route.** The architecture is
> deliberately tiny — no DB, no auth, no build step. The file system is
> the source of truth.

---

## Stack

- **FastAPI** — request routing + dependency injection
- **Jinja2** — server-side templating (`ui/templates/`)
- **Pico CSS** v2 — classless base, served from CDN
- **HTMX** v2 — for the bits that need polling or partial swaps (only
  the job runner uses it heavily; everything else is plain HTML)
- **mistune** — markdown rendering for `/docs/view`
- **watchfiles** — hot-reload during dev (provided by `[ui]` extra)

No JavaScript framework. No bundler. No service worker. The only inline
script lives in `templates/base.html` (form `data-confirm` /
`data-spinner` opt-in) — about a dozen lines.

---

## Directory layout

```
ui/
├── server.py              ← create_app() factory + / and 404 handlers
├── config.py              ← UIConfig dataclass, mode resolution, ORQ_ROOT validation
├── routes/                ← one APIRouter per feature (≈ 1 file per URL prefix)
│   ├── health.py          GET /healthz                    (read-only)
│   ├── dashboard.py       GET /dashboard                  (read-only)
│   ├── docs.py            GET /docs, /docs/search, /docs/view
│   ├── catalog.py         GET /catalog                    (read-only)
│   ├── coverage.py        GET /coverage                   (read-only)
│   ├── audits.py          POST /audits/{name}             (submits a job)
│   ├── convert.py         POST /convert                   (submits a job)
│   ├── install.py         POST /install                   (submits a job)
│   ├── compact.py         POST /compact                   (submits a job)
│   ├── edit_agent.py      3-step edit flow for agent frontmatter
│   ├── edit_skill.py      3-step edit flow for skill frontmatter
│   └── jobs.py            GET /jobs/{id}, /jobs/{id}/partial   (HTMX poll target)
├── templates/             ← Jinja2 templates; extend base.html
├── lib/                   ← in-process helpers (NO subprocess except via jobs.py)
│   ├── catalog_loader.py  parse agent/skill frontmatter
│   ├── doc_loader.py      enumerate docs, render markdown, ripgrep search
│   ├── edit_validator.py  preflight rules for the edit flow
│   ├── live_metrics.py    aggregate events.jsonl for /dashboard
│   └── jobs.py            async job runner with HTMX-pollable state
└── static/
    └── app.css            overrides on top of Pico CSS
```

---

## Modes

Set via `--mode` flag on `orquestrum web`, the `ORQ_MODE` env var, or
auto-detected from the directory layout (presence of
`agents/ + skills/ + orquestrum/ + docs/agent-context/` ⇒ framework).

| Mode | What it manages | What's hidden |
|------|-----------------|---------------|
| **framework** | The Orquestrum repo itself | nothing — every action is enabled |
| **project**   | One installed target project | `/convert`, `/install`, `/compact`, `/agents/*/edit`, `/skills/*/edit` are disabled |

The home page (`/`) renders mode-aware copy and only shows cards that
make sense in the current mode.

---

## Running locally

```bash
# First time
make dev          # uv tool install --editable . + uv sync extras

# Day-to-day (auto-reload on file changes via watchfiles)
orquestrum web                   # framework mode by default in the repo
orquestrum web --port 7700       # custom port
orquestrum web --mode project --target /path/to/project   # one target
```

Bind is **always** `127.0.0.1`. The console deliberately has no auth —
exposing it on a network would be a security mistake.

---

## How requests flow

```
Browser ──► server.py (FastAPI app)
              │
              ├──► routes/<feature>.py            ← thin handler
              │      │
              │      ├──► lib/<helper>.py         ← pure-Python logic, no I/O surprises
              │      └──► templates/<page>.html   ← Jinja2 renders
              │
              └──► (long jobs only) lib/jobs.py.submit() → asyncio.Task
                     ↑
                     └─── /jobs/{id}/partial      ← HTMX polls every 1s until terminal
```

State that survives a request: nothing. Every page reads from the file
system on demand. The job registry in `lib/jobs.py` is the only
in-memory state and is bounded to 50 entries.

---

## Adding a new route

See **[`CONTRIBUTING.md`](../CONTRIBUTING.md#adding-a-web-route)** for
the step-by-step. Quick version:

1. Create `ui/routes/<feature>.py` exposing `router = APIRouter(prefix='/<feature>')`.
2. Create `ui/templates/<feature>.html` extending `base.html`.
3. Register the router in `ui/server.py` (alphabetical-ish; the order
   doesn't matter functionally).
4. If the feature mutates anything, decide: synchronous (renders
   inline) or long-running (submit a job and 303-redirect to
   `/jobs/{id}`). If unsure, follow the `audits.py` pattern.

---

## Templates: opt-in attributes

Two attributes on a `<form>` give you safer / nicer UX without writing
JS yourself (handler is in `templates/base.html`):

```html
<form method="post"
      action="/something"
      data-confirm="Apply changes to disk?"   <!-- window.confirm() before submit -->
      data-spinner>                            <!-- inline spinner + disable button -->
  …
</form>
```

For long jobs, prefer redirecting to `/jobs/{id}` after submission
(automatic via `RedirectResponse`); the polling partial gives the user
live progress instead of a blank page.

---

## Things this app deliberately does NOT do

- No database, no ORM, no migrations.
- No user accounts, no roles, no CSRF tokens (single-user local-only).
- No bundler, no TypeScript, no React. HTMX islands inside Pico CSS.
- No Celery / Redis / job queue. The async job runner in `lib/jobs.py`
  is in-process and fits the workload.
- No WebSocket. HTMX short-poll is enough for the live views.

If you find yourself wanting any of the above, please raise it as an
ADR before implementing — see `docs/00-discovery/adr/`.
