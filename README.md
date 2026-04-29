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
| **Cast**  | Ship & Support Lead — versioned releases, runbooks, and production triage             | 5 + sustentação |

---

## Skills

16 specialized skills delegated by agents:

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
# All tools at once (default provider: claude)
./scripts/convert.sh --all

# Choose a provider — models are resolved at conversion time
./scripts/convert.sh --all --provider claude    # anthropic/claude-* (default)
./scripts/convert.sh --all --provider copilot   # github-copilot/claude-*
./scripts/convert.sh --all --provider glm       # zai-coding-plan/glm-*

# Or per tool + provider
./scripts/convert.sh --tool opencode --provider glm
./scripts/convert.sh --tool claude-code --provider copilot
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

**Claude Code** — agents to `.claude/agents/`, docs/skills to `.sdd/` (paths resolved relative to project root)  
**OpenCode** — 6 flat agent files (`agents/<Name>.md`) + docs/skills to `--target`; paths rewritten to absolute target at install time  
**Cursor** — 20 rule files in `.cursor/rules/` with `.sdd/docs` paths and embedded reference content  
**Aider** — single `CONVENTIONS.md` with all agents, skills, and `.sdd/docs` paths  
**Windsurf** — single `.windsurfrules` with all agents, skills, and `.sdd/docs` paths

---

## OpenCode agent hierarchy

OpenCode receives 6 flat agent files (`agents/helm-the-architect.md`, `agents/lore-product-strategist.md`, …). The filename without `.md` is the agent type used by OpenCode's Task tool.

**Helm** is the only agent with a restricted `permission.task` — it can only route to the 5 orchestrators:

```
Helm (primary, permission.task: lore-product-strategist | forge-dev-lead | ward-quality-lead | cast-ship-and-support-lead | trace-onboarding-lead)
├─ lore-product-strategist  (subagent) — executes skills inline; can call any agent including agency-agents
├─ forge-dev-lead (subagent) — executes skills inline; can call any agent including agency-agents
├─ ward-quality-lead  (subagent) — executes skills inline; can call any agent including agency-agents
├─ cast-ship-and-support-lead (subagent) — executes skills inline; can call any agent including agency-agents
└─ trace-onboarding-lead (subagent) — executes skills inline; can call any agent including agency-agents
```

Skills remain as documentation in `skills/` — orchestrators read `__OPENCODE_ROOT__/skills/<name>/SKILL.md` and execute instructions inline. Skills are **not** registered as separate agents, keeping the setup simple.

Agency-agents (from [msitarzewski/agency-agents](https://github.com/msitarzewski/agency-agents)) integrate via their kebab-case OpenCode names (e.g. `engineering-code-reviewer`). Since non-Helm orchestrators have no `permission.task` restriction, they can call agency-agents freely.

---

## Model assignment

Models are organized in three tiers based on reasoning requirements:

| Tier | `claude` | `copilot` | `glm` | Used by |
|------|----------|-----------|-------|---------|
| **Deep** | `anthropic/claude-opus-4-6` | `github-copilot/claude-opus-4.5` | `zai-coding-plan/glm-5.1` | Helm, spec-manager, adr-manager, reverse-spec |
| **Balanced** | `anthropic/claude-sonnet-4-6` | `github-copilot/claude-sonnet-4.5` | `zai-coding-plan/glm-4.7` | Lore, Forge, Ward, Trace + most skills |
| **Mechanical** | `anthropic/claude-haiku-4-5-20251001` | `github-copilot/claude-haiku-4.5` | `zai-coding-plan/glm-4.5-air` | Cast, glossary, changelog, runbook |

See `docs/MODELS.md` for the full assignment breakdown. Provider profiles are defined in `models/profiles.sh`.

---

## Static RAG

Skills for Cursor, Aider, and Windsurf include their reference knowledge **embedded at convert time** — no runtime file reads required. Claude Code and OpenCode keep references as separate files (cheaper context).

The `pattern-manager` reference (1,020 lines of engineering principles and design patterns) is injected in compact mode — only the core principles and quick-reference guide (~320 lines).

## Path resolution

Canonical source uses bare paths (`docs/SDLC.md`, `skills/.../SKILL.md`). `convert.sh` rewrites them per tool:

| Tool | Docs/skills prefix | Resolved at |
|------|--------------------|-------------|
| claude-code | `.sdd/docs` / `.sdd/skills` | Runtime (relative to project CWD) |
| opencode | `__OPENCODE_ROOT__` placeholder | Install time — replaced with absolute `--target` path |
| cursor | `.sdd/docs` / `.sdd/skills` | Runtime (relative to project CWD) |
| aider | `.sdd/docs` / `.sdd/skills` | Runtime (relative to project CWD) |
| windsurf | `.sdd/docs` / `.sdd/skills` | Runtime (relative to project CWD) |

OpenCode resolves at install time because it is typically installed globally (`~/.config/opencode/`), where a project-relative path would not resolve correctly.

---

## Development

```bash
# Validate all agents and skills before converting
./scripts/lint-agents.sh

# Lint must pass before convert
./scripts/lint-agents.sh && ./scripts/convert.sh --all
```

The lint checks:

- Frontmatter has required fields: `name`, `description`, `model`
- No hardcoded tool-specific paths (`.opencode/`, `.claude/`, `.cursor/`) in canonical source

### Adding an agent or skill

1. Create the file with valid frontmatter (`name`, `description`, `model` required)
2. Use only canonical paths in the body: `docs/`, `skills/`, `./references/`, `./assets/`
3. For skills: add `inject_references: full` (or `compact`) to frontmatter
4. Run `./scripts/lint-agents.sh` — must pass with zero errors
5. Run `./scripts/convert.sh --all` to update `integrations/`

---

## Repository structure

```
agents/       ← 6 orchestrator agents (canonical source)
models/       ← Provider profiles (profiles.sh)
skills/       ← 14 specialized skills (SKILL.md + assets/ + references/)
docs/         ← Pipeline governance (SDLC.md, TIERS.md, MODELS.md)
scripts/      ← convert.sh, install.sh, lint-agents.sh
integrations/ ← Generated by convert.sh — do not edit manually
```

---

## License

MIT
