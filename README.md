# Orquestrum

**Specification-Driven Development (SDD) framework for multi-agent AI systems.**

Orquestrum is a collection of orchestrator agents and specialized skills that guide a software project through a structured pipeline — from discovery to release. It is tool-agnostic: the canonical source is converted to work with Claude Code, OpenCode, Cursor, Aider, and Windsurf.

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

Six orchestrators, each owning one or more pipeline phases:

| Agent     | Role                                                                                  | Phases          |
| --------- | ------------------------------------------------------------------------------------- | --------------- |
| **Helm**  | Meta-orchestrator — classifies work tier, routes to correct agent, validates gates    | All             |
| **Trace** | Onboarding Lead — maps existing codebases without documentation into the SDD pipeline | -1              |
| **Lore**  | Product Strategist — owns glossary, specs, and architectural decisions                | 0–1             |
| **Forge** | Dev Lead — translates specs into architecture, epics, and executable tasks            | 2–3             |
| **Ward**  | Quality Lead — code review, functional QA, and failure learning                       | 4               |
| **Cast**  | Ship & Support Lead — versioned releases, runbooks, and production triage             | 5 + maintenance |

---

## Skills

17 specialized skills delegated by agents. Skills declare `chain` in their frontmatter for automatic sequencing:

| Phase | Skill                  | Produces                                | Chains to |
| ----- | ---------------------- | --------------------------------------- | --------- |
| -1    | `codebase-mapper`      | Architecture as-is from existing code   | reverse-spec |
| -1    | `reverse-spec`         | Extracted spec from existing behavior   | — |
| 0     | `glossary-manager`     | Canonical domain vocabulary             | spec-manager |
| 0–1   | `discovery-manager`    | Combined glossary + spec (efficient)    | adr-manager |
| 1     | `spec-manager`         | Requirements + success criteria         | adr-manager |
| 1     | `adr-manager`          | Architectural decision records          | pattern-manager |
| 1     | `pattern-manager`      | Design pattern catalog and adoption log | architecture-manager |
| 2     | `architecture-manager` | System diagram + component map          | — |
| 3     | `epic-manager`         | Vertical feature slices                 | task-manager |
| 3     | `task-manager`         | Executable tasks with TDD derivation    | — |
| 4     | `review-manager`       | Code review (security, SOLID, LGPD)     | qa-manager |
| 4     | `qa-manager`           | Functional QA against spec criteria     | learning-manager |
| 4     | `learning-manager`     | Root cause analysis of failures         | — |
| 5     | `changelog-manager`    | SemVer changelog + release document     | runbook-manager |
| 5     | `runbook-manager`      | Operational procedures                  | — |
| 5     | `archive-manager`      | Consolidated task/log summaries         | runbook-manager |

---

## Installation

### Prerequisites

```bash
git clone https://github.com/johnt1000/orquestrum
cd orquestrum
chmod +x scripts/*.sh
```

### Generate integration packages

```bash
# No provider — model not set, user chooses at runtime
./scripts/convert.sh --all
./scripts/convert.sh --tool opencode

# Choose a provider — models are resolved and locked in the generated agents
./scripts/convert.sh --all --provider claude    # anthropic/claude-*
./scripts/convert.sh --all --provider copilot   # github-copilot/claude-*
./scripts/convert.sh --all --provider glm       # zai-coding-plan/glm-*
```

### Install into a project

```bash
# Claude Code — project-local
./scripts/install.sh --tool claude-code --target /path/to/your/project

# OpenCode — global (recommended)
./scripts/install.sh --tool opencode --target ~/.config/opencode

# OpenCode — project-local or custom path
./scripts/install.sh --tool opencode --target /path/to/your/project/.opencode

# Cursor / Aider / Windsurf — project-local
./scripts/install.sh --tool cursor --target /path/to/your/project
./scripts/install.sh --tool aider --target /path/to/your/project
./scripts/install.sh --tool windsurf --target /path/to/your/project

# Auto-detect installed tools (project-local)
./scripts/install.sh --auto --target /path/to/your/project
```

### Install external dependencies

Orquestrum integrates with external agent and skill repositories. Use `scripts/deps.sh` to install them:

```bash
# Install all external dependencies (agency-agents + anthropics/skills including supabase)
./scripts/deps.sh --target ~/.config/opencode

# Install specific dependency only
./scripts/deps.sh --target ~/.config/opencode --only agency   # agency-agents (~184 agents)
./scripts/deps.sh --target ~/.config/opencode --only skills   # anthropics/skills (~17 skills, includes supabase)
```

**External dependencies:**
- **agency-agents** (msitarzewski/agency-agents) — 184+ specialized agents for Forge delegation
- **anthropics/skills** — 17 skills including Supabase integration
- **supabase/agent-skills** — Skipped (already included in anthropics/skills)

> Note: `deps.sh` clones to temporary directories (`mktemp -d`) and does not pollute the Orquestrum repository.

**Claude Code** — agents to `.claude/agents/`, docs/skills to `.sdd/` (paths resolved relative to project root)  
**OpenCode** — 6 flat agent files with `mode: primary` (all visible in Tab picker), docs/skills to `--target`  
**Cursor** — 20 rule files in `.cursor/rules/` with `.sdd/docs` paths and embedded reference content  
**Aider** — single `CONVENTIONS.md` with all agents, skills, and `.sdd/docs` paths  
**Windsurf** — single `.windsurfrules` with all agents, skills, and `.sdd/docs` paths

---

## OpenCode agent hierarchy

All 6 agents are emitted as `mode: primary` — they appear in the Tab picker and can be called directly by the user or via Task tool by other agents.

**Helm** is the only agent with a restricted `permission.task` — it can only route to the 5 orchestrators:

```
Helm (primary, restricted task permissions)
├─ Lore - Product Strategist (primary, unrestricted) — can call any agent
├─ Forge - Dev Lead (primary, unrestricted) — can call any agent, Tier 0 fast-path
├─ Ward - Quality Lead (primary, unrestricted) — can call any agent
├─ Cast - Ship & Support (primary, unrestricted) — can call any agent
└─ Trace - Onboarding (primary, unrestricted) — can call any agent
```

Skills remain as documentation in `skills/` — orchestrators read `__OPENCODE_ROOT__/skills/<name>/SKILL.md` and execute instructions inline. Skills are **not** registered as separate agents.

Agency-agents (from [msitarzewski/agency-agents](https://github.com/msitarzewski/agency-agents)) are callable by all non-Helm orchestrators. Forge delegates to them via the Task tool using exact `subagent_type` values.

**Delegation mapping** (Forge → agency-agents):

| Task Domain | `subagent_type` | Notes |
|------------|---------------|-------|
| Backend / API | `senior-developer` | Laravel/Livewire/FluxUI specialist |
| Database / Schema | `database-optimizer` | PostgreSQL/MySQL schema & query optimization |
| Security / Auth | `security-engineer` | Threat modeling, secure code review |
| UI / UX / Frontend | `frontend-developer` | React/Vue/Angular, UI implementation |
| AI / Automation / n8n | `ai-engineer` | ML pipelines, AI-powered features |
| Infra / Docker / CI-CD | `devops-automator` | Infrastructure automation, cloud ops |

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
| **Balanced** | `anthropic/claude-sonnet-4-6` | `github-copilot/claude-sonnet-4.5` | `zai-coding-plan/glm-4.7` | Lore, Forge, Ward, Trace + most skills |
| **Mechanical** | `anthropic/claude-haiku-4-5-20251001` | `github-copilot/claude-haiku-4.5` | `zai-coding-plan/glm-4.5-air` | Cast, glossary, changelog, runbook |

See `docs/MODELS.md` for the full assignment breakdown. Provider profiles are defined in `models/profiles.sh`.

When generated **without** `--provider`, the `model` field is omitted from agent frontmatter — the user chooses the model at runtime. When generated **with** `--provider`, the model is locked per the tier assignment.

---

## Static RAG

Skills for Cursor, Aider, and Windsurf include their reference knowledge **embedded at convert time** — no runtime file reads required. Claude Code and OpenCode keep references as separate files (cheaper context).

The `pattern-manager` reference uses a **fragmented structure** — an index file lists all patterns, and individual pattern files are loaded on demand. This reduces context from ~8,000 tokens (monolithic) to ~2,000-4,000 tokens per session.

---

## Path resolution

Canonical source uses bare paths (`docs/SDLC.md`, `skills/.../SKILL.md`). `convert.sh` rewrites them per tool:

| Tool | Docs/skills prefix | Resolved at |
|------|--------------------|-------------|
| claude-code | `.sdd/docs` / `.sdd/skills` | Runtime (relative to project CWD) |
| opencode | `__OPENCODE_ROOT__` placeholder | Install time — replaced with absolute `--target` path |
| cursor | `.sdd/docs` / `.sdd/skills` | Runtime (relative to project CWD) |
| aider | `.sdd/docs` / `.sdd/skills` | Runtime (relative to project CWD) |
| windsurf | `.sdd/docs` / `.sdd/skills` | Runtime (relative to project CWD) |

---

## Development

```bash
# Validate all agents and skills before converting
./scripts/lint-agents.sh

# Lint must pass before convert
./scripts/lint-agents.sh && ./scripts/convert.sh --all
```

The lint checks:

- Frontmatter has required fields: `name`, `description`
- No hardcoded tool-specific paths (`.opencode/`, `.claude/`, `.cursor/`) in canonical source

### Adding an agent or skill

1. Create the file with valid frontmatter (`name`, `description` required)
2. Use only canonical paths in the body: `docs/`, `skills/`, `./references/`, `./assets/`
3. For skills: add `chain` (optional) and `inject_references: full|compact` to frontmatter
4. Run `./scripts/lint-agents.sh` — must pass with zero errors
5. Run `./scripts/convert.sh --all` to update `integrations/`

---

## Repository structure

```
agents/       ← 6 orchestrator agents (canonical source)
models/       ← Provider profiles (profiles.sh) for --provider flag
skills/       ← 16 specialized skills (SKILL.md + assets/ + references/)
docs/         ← Pipeline governance (SDLC.md, TIERS.md, MODELS.md, CONVENTIONS.md)
scripts/      ← convert.sh, install.sh, lint-agents.sh
integrations/ ← Generated by convert.sh — do not edit manually
```

---

## License

MIT
