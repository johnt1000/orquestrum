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

14 specialized skills delegated by agents:

| Phase | Skill                  | Produces                                |
| ----- | ---------------------- | --------------------------------------- |
| -1    | `codebase-mapper`      | Architecture as-is from existing code   |
| -1    | `reverse-spec`         | Extracted spec from existing behavior   |
| 0     | `glossary-manager`     | Canonical domain vocabulary             |
| 1     | `spec-manager`         | Requirements + success criteria         |
| 1     | `adr-manager`          | Architectural decision records          |
| 1     | `pattern-manager`      | Design pattern catalog and adoption log |
| 2     | `architecture-manager` | System diagram + component map          |
| 3     | `epic-manager`         | Vertical feature slices                 |
| 3     | `task-manager`         | Executable tasks with TDD derivation    |
| 4     | `review-manager`       | Code review (security, SOLID, LGPD)     |
| 4     | `qa-manager`           | Functional QA against spec criteria     |
| 4     | `learning-manager`     | Root cause analysis of failures         |
| 5     | `changelog-manager`    | SemVer changelog + release document     |
| 5     | `runbook-manager`      | Operational procedures                  |

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
# All tools at once
./scripts/convert.sh --all

# Or per tool
./scripts/convert.sh --tool claude-code   # → integrations/claude-code/
./scripts/convert.sh --tool opencode      # → integrations/opencode/
./scripts/convert.sh --tool cursor        # → integrations/cursor/
./scripts/convert.sh --tool aider         # → integrations/aider/
./scripts/convert.sh --tool windsurf      # → integrations/windsurf/
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
**OpenCode** — 20 agents (6 orchestrators + 14 skill subagents) + docs/skills to `--target`; paths rewritten to absolute target at install time  
**Cursor** — 20 rule files in `.cursor/rules/` with `.sdd/docs` paths and embedded reference content  
**Aider** — single `CONVENTIONS.md` with all agents, skills, and `.sdd/docs` paths  
**Windsurf** — single `.windsurfrules` with all agents, skills, and `.sdd/docs` paths

---

## OpenCode agent hierarchy

OpenCode is the only tool that gets the full multi-agent delegation model. Skills become hidden subagents invocable via the Task tool, and each orchestrator has explicit `permission.task` restrictions:

```
Helm (primary)
├─ Lore   (subagent) → GlossaryManager, SpecManager, AdrManager
├─ Forge  (subagent) → PatternManager, ArchitectureManager, EpicManager, TaskManager
│                      + engineering-* (agency-agents)
├─ Ward   (subagent) → ReviewManager, QaManager, LearningManager
│                      + engineering-code-reviewer, engineering-security-engineer
├─ Cast   (subagent) → ChangelogManager, RunbookManager
│                      + engineering-technical-writer
└─ Trace  (subagent) → CodebaseMapper, ReverseSpec, AdrManager, GlossaryManager
                       + engineering-codebase-onboarding-engineer
```

All skill agents are `hidden: true` — they don't appear in the `@` autocomplete and are only invocable by their designated orchestrators. The `skills/` directory is also copied as read-only reference documentation.

Agency-agents (from [msitarzewski/agency-agents](https://github.com/msitarzewski/agency-agents)) integrate via their kebab-case OpenCode names (e.g. `engineering-code-reviewer`).

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
skills/       ← 14 specialized skills (SKILL.md + assets/ + references/)
docs/         ← Pipeline governance (SDLC.md, TIERS.md, MODELS.md)
scripts/      ← convert.sh, install.sh, lint-agents.sh
integrations/ ← Generated by convert.sh — do not edit manually
```

---

## License

MIT
