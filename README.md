# Orquestrum

**Specification-Driven Development (SDD) framework for multi-agent AI systems.**

> ⚠️ **Mac & Linux only.** Windows is not supported. The framework relies on POSIX paths,
> shell hooks, and `uv tool install` semantics that diverge on Windows. WSL2 is best-effort
> but unsupported. See [`docs/governance/DISTRIBUTION.md`](docs/governance/DISTRIBUTION.md).

Orquestrum is a collection of orchestrator agents and specialized skills that guide a software project through a structured pipeline — from discovery to release. The canonical source is converted to work with **Claude Code** and **OpenCode** — the two LLM agent runtimes with mature subagent + MCP support. (Earlier versions also targeted Cursor, Aider, and Windsurf; v0.4 narrowed scope to the runtimes whose orchestration capabilities match the framework's design.)

---

## How it works

Every request is classified into a **tier** by Helm (the meta-orchestrator), which determines the pipeline depth:

```
Tier 0 — Micro    → Task + Log                    (~2 LLM calls)
Tier 1 — Standard → Epic + Task + Log + QA        (~5 LLM calls)
Tier 2 — Full     → Complete pipeline             (~13 LLM calls)
```

Tiers prevent over-engineering: a typo fix never triggers a SPEC. A new payment module always does.

Forge can also operate as a direct primary for Tier 0 work — bypassing Helm entirely for the fastest path to execution.

---

## Agents

Eight orchestrators, each owning one or more pipeline phases:

| Agent      | Emoji | Role                                                                                   | Phases          |
| ---------- | ----- | -------------------------------------------------------------------------------------- | --------------- |
| **Helm**   | 🏛️   | Meta-orchestrator — classifies work tier, routes to correct agent, validates gates     | All             |
| **Trace**  | 🗺️   | Onboarding Lead — maps existing codebases without documentation into the SDD pipeline  | -1              |
| **Lore**   | 🎯   | Product Strategist — owns glossary, specs, and architectural decisions                 | 0–1             |
| **Forge**  | ⚙️   | Dev Lead — translates specs into architecture, epics, and executable tasks             | 2–3             |
| **Cipher** | 🔐   | Security Lead — threat modeling, OWASP gap analysis, dependency vulnerability assessment | 3.5           |
| **Ward**   | 🔍   | Quality Lead — code review, functional QA, and failure learning                        | 4               |
| **Cast**   | 🚀   | Ship Lead — versioned releases, runbooks, and artifact archiving                       | 5               |
| **Flux**   | 🔄   | Support Lead — ongoing maintenance, incident triage, and support backlog routing       | Maintenance     |

---

## Skills

25 specialized skills delegated by agents. Skills declare `chain` in their frontmatter for automatic sequencing:

| Phase      | Skill                  | Produces                                      | Chains to              |
| ---------- | ---------------------- | --------------------------------------------- | ---------------------- |
| -1         | `codebase-mapper`      | Architecture as-is from existing code         | `reverse-spec`         |
| -1         | `reverse-spec`         | Extracted spec from existing behavior         | —                      |
| 0          | `glossary-manager`     | Canonical domain vocabulary                   | `spec-manager`         |
| 0–1        | `discovery-manager`    | Combined glossary + spec (efficient path)     | `adr-manager`          |
| 1          | `spec-manager`         | Requirements + success criteria               | `adr-manager`          |
| 1          | `adr-manager`          | Architectural decision records                | `pattern-manager`      |
| 1          | `pattern-manager`      | Design pattern catalog and adoption log       | `architecture-manager` |
| 2          | `architecture-manager` | System diagram + component map                | —                      |
| 3          | `epic-manager`         | Vertical feature slices                       | `task-manager`         |
| 3          | `task-manager`         | Executable tasks with TDD derivation          | —                      |
| 3.5        | `security-manager`     | Threat model + OWASP gap analysis             | —                      |
| 4          | `review-manager`       | Code review (security, SOLID, LGPD)           | `qa-manager`           |
| 4          | `qa-manager`           | Functional QA against spec criteria           | `learning-manager`     |
| 4          | `learning-manager`     | Root cause analysis of failures               | —                      |
| 4          | `learning-aggregator`  | Cross-cutting learning summary (recurrences)  | —                      |
| 5          | `changelog-manager`    | SemVer changelog + release document           | `runbook-manager`      |
| 5          | `runbook-manager`      | Operational procedures                        | —                      |
| 5          | `archive-manager` (release mode) | Consolidate just-released tasks/logs       | `runbook-manager`      |
| Maint.     | `archive-manager` (prune mode)   | Proactive doc hygiene — superseded versions, empty stubs, stale drafts | — |
| 5          | `rollback-manager`     | Deterministic rollback procedure per release  | `runbook-manager`      |
| 3          | `data-migration-manager` | Schema/data migration plan with reversibility | `security-manager`   |
| 4          | `performance-manager`  | Performance targets + regression report       | `learning-manager`     |
| Maint.     | `hotfix-runbook`       | Fast-path artifact for production-critical fixes | `changelog-manager` |
| Maint.     | `incident-postmortem`  | Blameless postmortem with timeline + RCA      | `learning-manager`     |
| Cross      | `checkpoint-manager`   | CHECKPOINT.md + MEDIATION.md (attention agg.) | —                      |

---

## Installation

> Requires Python 3.12+ on macOS or Linux.

### One-liner (recommended)

```bash
curl -sSL https://raw.githubusercontent.com/johnt1000/orquestrum/main/install.sh | bash
```

Installs [`uv`](https://docs.astral.sh/uv/) if needed, then installs the `orquestrum` CLI
with the web console and app window extras. The binary lands at `~/.local/bin/orquestrum`.

Options:

```bash
bash install.sh --minimal     # CLI only, no web console
bash install.sh --no-webview  # CLI + web console, skip pywebview
```

### Manual

```bash
uv tool install git+https://github.com/johnt1000/orquestrum
orquestrum extras install ui webview   # add web console + app window
```

### Future: Homebrew + Linux package repos

Once the CLI stabilizes (≥ v0.5), distribution will expand to:

- **macOS Homebrew tap** (`brew install johnt1000/tap/orquestrum`)
- **Debian/Ubuntu APT** (`apt install orquestrum`)
- **Arch User Repository** (AUR)
- **Nix flake**

See [`docs/governance/DISTRIBUTION.md`](docs/governance/DISTRIBUTION.md) for the full plan.

---

Contributing? See [CONTRIBUTING.md](CONTRIBUTING.md).

---

## Quickstart

```bash
# 1. ONE-TIME setup (global — installs the framework on your system)
orquestrum setup                  # interactive wizard
# or
orquestrum setup --yes            # accept defaults (install claude-code,
                                  # skip opencode). Lands at ~/.claude/agents/,
                                  # ~/.claude/skills/, registers MCP +
                                  # metrics hook in ~/.claude/settings.json.

# 2. PER-PROJECT (optional — only if you want metrics + MCP for THIS project)
cd /path/to/your/project
orquestrum init --yes             # creates ./.orquestrum/{config,manifest,metrics/}
                                  # — that's the entire project footprint.

# 3. Day-to-day
orquestrum web                    # dashboard (auto-detects project)
orquestrum dashboard              # terminal summary
orquestrum audit attention        # review attention scores
```

What the two phases do:

- **`orquestrum setup`** — global, one-time. Installs agents + skills + hooks
  + MCP server under `~/.claude/`. Restart Claude Code afterwards.
- **`orquestrum init`** — per-project, optional. Connects ONE repo to
  metrics/MCP by writing `<project>/.orquestrum/`. Skip if the project
  doesn't need orquestrum tracking.

Use Claude Code normally afterwards:
  - Stop hook records tokens/cost in `<project>/.orquestrum/metrics/events.jsonl`
  - MCP server (`orquestrum`) lets agents query state mid-turn via
    `mcp__orquestrum__orq_*` tools (`session_summary`, `budget_status`,
    `recent_events`, `cost_today`, …).
  - Dashboard refresh: http://127.0.0.1:7700/dashboard

To switch tools later (e.g. claude-code → opencode):

```bash
orquestrum update --tool opencode                # cleanup + reinstall + history entry
```

---

## CLI commands

| Command | What it does |
|---------|--------------|
| `orquestrum setup [--yes]` | Wizard for first-time global install. Detects what's already on the system and asks before installing claude-code / opencode integrations under `~/.claude/` / `~/.config/opencode/`. The recommended starting point — covers `convert + install` in one interactive step. |
| `orquestrum init [--name N] [--yes]` | Bootstrap `<project>/.orquestrum/` (config, manifest, gitignore, metrics dir) and register globally. Asks 3 interactive prompts about optional integrations (metrics hook, MCP server, agents). `--yes` accepts defaults silently. Tool installs are SEPARATE — see `orquestrum setup` or `orquestrum install`. |
| `orquestrum update [--tool X] [--all] [--check] [--self]` | Re-sync this project (or all). `--tool` switches integrations with cleanup of the old one. `--self` upgrades the CLI itself (detects `uv tool` vs source install and runs the matching command — equivalent to re-running `install.sh`). |
| `orquestrum web [--mode {project,framework,auto}] [--port N] [--no-browser]` | Launch the local console. Auto-detects mode from cwd. |
| `orquestrum repos {list,add,remove}` | Manage the global registry at `~/.orquestrum/registry.toml`. |
| `orquestrum convert [--tool X] [--all] [--provider Y] [--dry-run]` | Generate integration packages from canonical source. |
| `orquestrum install --tool X --target PATH` | Deploy a generated integration into a target. |
| `orquestrum lint` | Validate agents and skills (run from the framework repo). |
| `orquestrum deps --target PATH [--only agency,skills]` | Install external agent/skill dependencies (pinned via `pinned_refs.toml`). |
| `orquestrum audit {payload,parity,attention}` | Run an audit. `payload` = reference size; `parity` = provider equivalence; `attention` = attention-score distribution. |
| `orquestrum dashboard [--metrics-dir PATH] [--tier T] [--html]` | Render a static metrics dashboard. |
| `orquestrum mcp` | Start the MCP server on stdio. Spawned automatically by Claude Code; agents call `orq_*` tools to query session/budget/cost or emit rich domain events. See [`docs/governance/MCP.md`](docs/governance/MCP.md). |
| `orquestrum compact [--threshold-kb N] [--skill X] [--dry-run]` | Compress oversized skill references deterministically. |
| `orquestrum version` | Print version info. |

Run `orquestrum <subcommand> --help` for full flag documentation.

### Diagnostic helpers

| Command | What it does |
|---------|--------------|
| `orquestrum doctor` | Verify python, uv, install method, extras, integrations, registry, and the current cwd. Exits 1 on hard failures. |
| `orquestrum doctor --json` | Machine-readable summary for scripting. |
| `orquestrum extras` | Show installed / missing optional extras (`ui`, `webview`). |
| `orquestrum uninstall --dry-run` | Preview what would be removed from this project / `--all` / `--self`. |

If you need to invoke a core module directly (rare — usually the CLI is enough):

```bash
python -m orquestrum.core.convert --all --dry-run
python -m orquestrum.core.audit.payload
```

---

## External dependencies

Orquestrum integrates with external agent and skill repositories:

```bash
orquestrum deps --target ~/.config/opencode                        # all
orquestrum deps --target ~/.config/opencode --only agency          # agency-agents (~184 agents)
orquestrum deps --target ~/.config/opencode --only skills          # anthropics/skills
```

- **agency-agents** (msitarzewski/agency-agents) — 184+ specialized agents for Forge delegation
- **anthropics/skills** — 17 skills including Supabase integration
- **supabase/agent-skills** — already included in anthropics/skills

> SHAs are pinned in `pinned_refs.toml` — see [`docs/governance/SUPPLY_CHAIN.md`](docs/governance/SUPPLY_CHAIN.md).

---

## Operational governance

Beyond the canonical pipeline, Orquestrum ships explicit policies for cost, observability, attention mediation, and coverage. These are the runtime guarantees the framework offers:

| Topic | Doc | What it covers |
|-------|-----|----------------|
| Token budgets per tier | [`docs/governance/COST.md`](docs/governance/COST.md) | Soft thresholds, dominant-cost-driver attribution |
| Metrics emission protocol | [`docs/governance/OBSERVABILITY.md`](docs/governance/OBSERVABILITY.md) | `.orquestrum/metrics/events.jsonl` schema, dashboard, privacy |
| MCP server (`orq_*` tools) | [`docs/governance/MCP.md`](docs/governance/MCP.md) | Tool catalog, validation contract, allowlist policy, hybrid arch w/ Stop hook |
| Project init contract | [`docs/governance/INIT.md`](docs/governance/INIT.md) | What `init` writes (only `.orquestrum/`), the 3 prompts, default scopes, legacy migration |
| Cache markers | [`docs/agent-context/CONVENTIONS.md`](docs/agent-context/CONVENTIONS.md) (§ Cache Segmentation) | `<!-- cache:stable -->` convention, adapter behavior |
| Human attention scoring | [`docs/agent-context/CONVENTIONS.md`](docs/agent-context/CONVENTIONS.md) (§ Human Attention Mediation) | Deterministic 0–100 score, propagation cap, MEDIATION.md |
| Performance methodology | [`docs/governance/PERFORMANCE.md`](docs/governance/PERFORMANCE.md) | Statistical hygiene, regression classification |
| Coverage matrix | [`docs/governance/COVERAGE.md`](docs/governance/COVERAGE.md) | Scenario × orchestrator mapping, when to add a 9th |
| Provider parity caveats | [`docs/governance/MODELS.md`](docs/governance/MODELS.md) (§ Provider Parity Caveats) | Tier collapses (e.g. `claude.sharp → balanced`) |
| Supply-chain pinning | [`docs/governance/SUPPLY_CHAIN.md`](docs/governance/SUPPLY_CHAIN.md) | `pinned_refs.toml` rotation, dependency review |

### Live tooling

```bash
# Render the metrics dashboard from the current project's events.jsonl
orquestrum dashboard --tier balanced --html

# Audit reference payload sizes (Phase 2 compression candidate flag)
orquestrum audit payload --output docs/baselines/payload-audit-YYYY-MM.md

# Verify provider parity (frontmatter shape + tier collapse coverage)
orquestrum audit parity

# Refresh upstream SHAs in pinned_refs.toml
orquestrum deps --update-pins
```

**Claude Code** — agents to `.claude/agents/`, skills to `.claude/skills/`, governance docs + hook scripts to `.claude/sdd/`. Subagents are picker-discoverable via `@` and `/agents`.

**OpenCode** — 8 flat agent files with `mode: primary` (all visible in Tab picker), docs/skills under the `--target` config dir.

---

## OpenCode agent hierarchy

All 8 agents are emitted as `mode: primary` — they appear in the Tab picker and can be called directly by the user or via Task tool by other agents.

**Helm** is the only agent with a restricted `permission.task` — it can only route to the 7 orchestrators:

```
Helm (primary, restricted task permissions)
├─ Trace - Onboarding Lead       (primary, unrestricted)
├─ Lore - Product Strategist     (primary, unrestricted)
├─ Forge - Dev Lead              (primary, unrestricted) — Tier 0 fast-path
├─ Cipher - Security Lead        (primary, unrestricted)
├─ Ward - Quality Lead           (primary, unrestricted)
├─ Cast - Ship Lead              (primary, unrestricted)
└─ Flux - Support Lead           (primary, unrestricted)
```

Skills remain as documentation in `skills/` — orchestrators read `__OPENCODE_ROOT__/skills/<name>/SKILL.md` and execute instructions inline. Skills are **not** registered as separate agents.

Agency-agents (from [msitarzewski/agency-agents](https://github.com/msitarzewski/agency-agents)) are callable by all non-Helm orchestrators. Forge delegates to them via the Task tool using exact `subagent_type` values.

**Delegation mapping** (Forge → agency-agents):

| Task Domain            | `subagent_type`       | Notes                                    |
| ---------------------- | --------------------- | ---------------------------------------- |
| Backend / API          | `senior-developer`    | Laravel/Livewire/FluxUI specialist       |
| Database / Schema      | `database-optimizer`  | PostgreSQL/MySQL schema & query optimization |
| Security / Auth        | `security-engineer`   | Threat modeling, secure code review      |
| UI / UX / Frontend     | `frontend-developer`  | React/Vue/Angular, UI implementation     |
| AI / Automation / n8n  | `ai-engineer`         | ML pipelines, AI-powered features        |
| Infra / Docker / CI-CD | `devops-automator`    | Infrastructure automation, cloud ops     |

When delegating, Forge provides a prompt template that requires:
- List of all created/modified artifacts
- Confirmation of acceptance criteria met
- Description of any deviations from the plan

---

## Model assignment

Models are organized in three tiers based on reasoning requirements:

| Tier | `claude` | `copilot` | `glm` | Used by |
|------|----------|-----------|-------|---------|
| **Deep** | `anthropic/claude-opus-4-6` | `github-copilot/claude-opus-4.5` | `zai-coding-plan/glm-5.1` | Helm, spec-manager, adr-manager, reverse-spec |
| **Balanced** | `anthropic/claude-sonnet-4-6` | `github-copilot/claude-sonnet-4.5` | `zai-coding-plan/glm-4.7` | Lore, Forge, Cipher, Ward, Trace, Flux + most skills |
| **Mechanical** | `anthropic/claude-haiku-4-5-20251001` | `github-copilot/claude-haiku-4.5` | `zai-coding-plan/glm-4.5-air` | Cast, glossary, changelog, runbook |

See `docs/governance/MODELS.md` for the full assignment breakdown.

When generated **without** `--provider`, the `model` field is omitted from agent frontmatter — the user chooses the model at runtime. When generated **with** `--provider`, the model is locked per the tier assignment.

---

## Static RAG

Skill references are kept as separate files for both supported tools (cheaper context — agents read on demand instead of carrying everything in the prompt).

The `pattern-manager` reference uses a **fragmented structure** — an index file lists all patterns, and individual pattern files are loaded on demand. This reduces context from ~8,000 tokens (monolithic) to ~2,000-4,000 tokens per session.

---

## Path resolution

Canonical source uses bare paths (`docs/agent-context/SDLC.md`, `skills/.../SKILL.md`). `convert.py` rewrites them per tool:

| Tool        | Docs prefix              | Skills prefix             | Resolved at                                       |
| ----------- | ------------------------ | ------------------------- | ------------------------------------------------- |
| claude-code | `.claude/sdd/docs`       | `.claude/skills`          | Runtime (relative to project CWD)                 |
| opencode    | `__OPENCODE_ROOT__/docs` | `__OPENCODE_ROOT__/skills`| Install time — placeholder replaced with absolute `--target` path |

---

## Development

```bash
# First time
make dev                       # uv tool install --editable . + uv sync extras

# Day-to-day
make lint                      # validate agents and skills (run before convert)
make convert                   # regenerate integrations/ for all tools
make web                       # FastAPI console at http://127.0.0.1:7700
make doctor                    # diagnose your environment
```

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the full workflow, instructions for adding a CLI command or a web route, and the opt-in pre-commit hook setup.

The lint checks:

- Frontmatter has required fields: `name`, `description`
- No hardcoded tool-specific paths (`.opencode/`, `.claude/`) in canonical source
- `chain.next` and `depends_on` point to existing skills
- REGISTRY.md is consistent with the skills directory

### Adding an agent or skill

1. Create the file with valid frontmatter (`name`, `description` required)
2. Use only canonical paths in the body: `docs/`, `skills/`, `./references/`, `./assets/`
3. For skills: add `chain` (optional) and `inject_references: full|compact` to frontmatter
4. Run `orquestrum lint` — must pass with zero errors
5. Run `orquestrum convert --all` to update `integrations/`

---

## Repository structure

```
agents/         ← 8 orchestrator agents (canonical source)
skills/         ← 25 specialized skills (SKILL.md + assets/ + references/)
docs/
  agent-context/  ← read by LLMs at runtime (SDLC, TIERS, CONVENTIONS)
  governance/     ← read by humans (MODELS, COST, ROADMAP, …)
  baselines/      ← auto-generated audits
orquestrum/     ← Python package: cli.py + commands/ + core/ + lib/
ui/             ← FastAPI web console (see ui/README.md)
integrations/   ← generated by `orquestrum convert` — do not edit manually
bundle/         ← stand-alone shell helpers (e.g. archive-cleanup.sh)
pyproject.toml  ← package metadata + optional [ui]/[webview] extras
```

---

## License

MIT
