# Project initialization (`orquestrum init`)

What `init` does, what it does NOT do, and the contract it establishes about which files orquestrum may write inside a project.

Companion to [`docs/governance/MCP.md`](MCP.md) (MCP server registration), [`docs/governance/OBSERVABILITY.md`](OBSERVABILITY.md) (what the metrics hook records), and [`docs/governance/DISTRIBUTION.md`](DISTRIBUTION.md) (how the CLI itself is installed).

---

## Contract

> **Inside the project, orquestrum writes ONLY to `<project>/.orquestrum/`.** Nothing else. No `.claude/` agents in the repo, no `.sdd/` at the root, no scripts in `bundle/`. Agents and skills, when the user opts into them, are installed at `~/.claude/` (global) and shared across every project.

This is the entire footprint inside a project after `orquestrum init`:

```
<project>/
└── .orquestrum/
    ├── config.toml      # safe to commit — meta + chosen integrations
    ├── manifest.md      # safe to commit — pipeline state + history
    ├── .gitignore       # blocks the dirs below
    └── metrics/         # gitignored — events.jsonl, session.json, dashboard.*
```

The `.gitignore` inside `.orquestrum/` blocks:

| Path | Why |
|------|-----|
| `metrics/` | Per-session event log; can include `session_id` and timing data the user may not want versioned |
| `integrations/` | Convert output (regenerable; same content lives in the global cache `~/.orquestrum/cache/integrations/`) |
| `services/` | Future runtime state (placeholder) |
| `plugins/` | Future extension content (placeholder) |
| `events.jsonl`, `session.json`, `dashboard.{md,html}` | Specific names already covered by `metrics/`, listed explicitly to defend against accidental relocation |

`config.toml` and `manifest.md` are deliberately commit-friendly — they describe what the project is, not what it does session-by-session.

---

## What `init` always does

1. Create `<project>/.orquestrum/`
2. Write `config.toml` with the user's chosen prompt outcomes
3. Write `manifest.md` (pipeline state machine — auto-managed above the marker, user-editable below)
4. Write `.gitignore` with the block list above
5. Create empty `metrics/` directory
6. Migrate `<project>/ORQUESTRUM.md` (legacy ≤v0.4 manifest location) → `<project>/.orquestrum/manifest.md` and delete the legacy file, with an inline log line
7. Register the project in `~/.orquestrum/registry.toml`

These steps are unconditional and cannot be skipped. They are small, fast, and only touch `.orquestrum/` (or migrate from a single legacy file at the project root).

---

## What `init` asks (the 3 prompts)

```
[1/3] Enable metrics collection? (Stop hook records tokens/cost per turn)
      [Y/n] >

      Where should the metrics hook be installed?
      [g] global   — ~/.claude/settings.json (all projects)
      [p] project  — ./.claude/settings.json (this project only)
      [s] skip     — do not install now (you can re-run init later)
      > G

[2/3] Register orquestrum MCP server? (Helm/Flux query budget mid-turn)
      [Y/n] >

      Where? [g/p/s] > G

      Note: agents always install to ~/.claude/agents/ (never to this project).
[3/3] Install Claude Code subagents now? (8 orchestrators, ~50 KB total)
      [y/N] >
```

Defaults (used when `--yes` is passed or stdin is not a TTY):

| Prompt | Default |
|--------|---------|
| Metrics hook | enabled, scope `global` |
| MCP server   | enabled, scope `global` |
| Agents now   | NOT installed |

The agents prompt has no scope question — agents always go to `~/.claude/agents/`. Project-level agent installs are intentionally not offered: they would land bulky generated content inside the repo, which the contract above disallows.

---

## Skipping the prompts

| Trigger | Behaviour |
|---------|-----------|
| `--yes` / `-y` / `--non-interactive` | Use defaults silently |
| `$ORQUESTRUM_NONINTERACTIVE=1` env var | Same as `--yes` |
| stdin is not a TTY (piped input, CI) | Same as `--yes` |

---

## `config.toml` shape after init

```toml
# Created by `orquestrum init`. Safe to commit.
[project]
name      = "myproject"
created   = "2026-05-04"

[metrics]
tier    = "balanced"
enabled = true
scope   = "global"        # global | project | skip

[mcp]
enabled = true
scope   = "global"

[agents]
# false = agents not installed by `init`; run
#   orquestrum install --tool claude-code --target ~
# whenever you want them. Always installed GLOBAL — never to the project.
installed = false
```

Re-running `init` on an already-initialized project rewrites `config.toml` from scratch with the new prompt outcomes — there is no merge logic. The `manifest.md` is preserved and updated additively (new history entry, refreshed `last_sync`).

---

## Migration from older versions

| From | What `init` does on first re-run |
|------|-----------------------------------|
| ≤v0.4 with `<project>/ORQUESTRUM.md` at root | Reads the old file, writes `.orquestrum/manifest.md`, deletes the root file, logs `Migrated legacy ORQUESTRUM.md → .orquestrum/manifest.md` |
| v0.4 with `<project>/.claude/agents/` (left over from `init --tool claude-code`) | **Not touched.** The user decides whether to remove via `orquestrum uninstall`, or `git rm` if they want them gone from the repo. `init` never deletes content it didn't write |
| v0.4 with `<project>/.sdd/` (legacy) | Same — left in place |
| v0.3.0 with `<project>/.sdd/` at root (pre-isolation) | Same — left in place |

---

## Removed in v0.5

These flags previously existed on `init` and have been retired:

| Flag | Replacement |
|------|-------------|
| `--tool <tool>` | `orquestrum install --tool <tool> --target ~` (separate, explicit) |
| `--provider <provider>` | Choose a provider when running `convert` / `install` |

Passing either flag to `init` returns exit code 2 with a migration message.

---

## Tool installs are separate

```bash
# 1. Bootstrap the local config (always)
orquestrum init --yes

# 2. Install agents whenever the user actually wants them (optional)
orquestrum install --tool claude-code --target ~       # global
orquestrum install --tool opencode --target ~/.config/opencode
```

Splitting these is deliberate. `init` is fast and idempotent and writes only `.orquestrum/`. `install` is a heavier operation that writes (or merges into) settings outside the project. Conflating them in v0.4 made `init --tool X` quietly drop hundreds of agent/skill files into the repo — exactly the failure mode v0.5 closes.

---

## Cross-references

- [`orquestrum/commands/init_impl.py`](../../orquestrum/commands/init_impl.py) — `run_init()` orchestration
- [`orquestrum/commands/init.py`](../../orquestrum/commands/init.py) — argparse + legacy flag rejection
- [`orquestrum/lib/prompts.py`](../../orquestrum/lib/prompts.py) — `ask_yn`, `ask_choice`, `ask_text`
- [`orquestrum/lib/manifest.py`](../../orquestrum/lib/manifest.py) — manifest path + legacy migration
- [`tests/commands/test_init.py`](../../tests/commands/test_init.py) — bootstrap, defaults, migration, CLI
- [`tests/lib/test_prompts.py`](../../tests/lib/test_prompts.py) — prompt helper coverage
