# MCP Server

`orquestrum mcp` runs a Model Context Protocol server over stdio. LLM agents (Claude Code, opencode, anything MCP-aware) connect to it to query orquestrum state and emit rich domain events that the Stop hook cannot capture.

Companion to `docs/governance/OBSERVABILITY.md` (the storage layer the MCP server reads/writes) and `docs/governance/COST.md` (budget thresholds the `orq_budget_status` tool checks against).

---

## What it is, what it isn't

| It is | It isn't |
|---|---|
| A read/write API on top of `.orquestrum/metrics/events.jsonl` | A new storage format — same JSONL the Stop hook already produces |
| A way for agents to query state mid-turn | A replacement for the Stop hook — the hook stays as ground truth |
| Cross-project (reads `~/.orquestrum/registry.toml`) | A telemetry collector — events stay local |
| Strictly typed via Pydantic (rejects bad input at the boundary) | A stateful server — no in-memory cache; every call re-reads the JSONL |

The architecture is **hybrid**:

```
┌─ Stop / SubagentStop hook ──┐    ┌─ MCP server (orq_*) ──────┐
│ runs once per turn          │    │ runs whenever agent calls │
│ token counts from API       │    │ rich domain events        │
│ source of truth for tokens  │    │ real-time queries         │
└────────────┬────────────────┘    └────────────┬──────────────┘
             │                                  │
             └─────────► events.jsonl ◄─────────┘
                              │
                              ▼
                    consumers: dashboard, web UI
```

Both write to the same file. Consumers don't change.

---

## Tools

All tools are namespaced `orq_*` for discoverability. Each returns a structured envelope `{ok: true, ...result}` on success or `{ok: false, error: "...", kind: "_ToolError"}` on validation/IO failure — agents act on `ok` directly.

### Read-only

| Tool | Returns | When to call |
|---|---|---|
| `orq_session_summary(project=None, tier=None)` | totals + by-skill + by-agent for the current (or named) project | "How much have I spent in this session?" |
| `orq_budget_status(tier, project=None)` | input/output tokens vs threshold, `over_input`, `over_output`, `pct_*`, top contributor | Before delegating heavy work — back off if `pct_input > 0.8` |
| `orq_recent_events(project=None, since_iso=None, agent=None, kind=None, limit=50)` | filtered list, descending by ts | "What did Forge run in the last hour?" |
| `orq_list_projects()` | every registered project + last_event_ts + total_calls + total_cost_usd | Operator overview |
| `orq_project_summary(project)` | aggregate scoped to one named project (does not need cwd) | Helm planning across projects |
| `orq_cost_today(project=None, date_iso=None)` | per-project breakdown + grand total for one calendar day (UTC) | Daily cost-of-day reporting |

### Write

| Tool | Effect | Notes |
|---|---|---|
| `orq_record_event(...)` | append `kind: "llm_call"` event | Use sparingly — the Stop hook is canonical for tokens |
| `orq_skill_completed(skill, agent, status, gates_passed, gates_failed, artifacts_emitted, confidence_avg)` | append `kind: "skill_completion"` | Call at end of every skill — these fields the hook can't see |

Events written via MCP are tagged with `"source": "mcp"` to distinguish them from hook-emitted events.

### Resources

| URI | Content |
|---|---|
| `orq://session/current` | JSON of current project's aggregated session, or `{project: null}` outside any project |
| `orq://projects` | JSON list of every entry in `~/.orquestrum/registry.toml` |

---

## Validation contract

Inputs go through `orquestrum/mcp/schemas.py` (Pydantic v2). Constraints enforced:

| Field | Constraint |
|---|---|
| `tier` | one of `deep`, `sharp`, `balanced`, `mechanical`, `unknown` |
| `kind` | `llm_call` or `skill_completion` |
| `status` | `completed`, `failed`, or `partial` |
| `in_tokens`, `out_tokens`, `cached_tokens` | `>= 0` |
| `confidence_avg` | `0.0 <= x <= 1.0` |
| `limit` | `1 <= n <= 1000` |
| `tier` for `orq_budget_status` | rejects `unknown` (no thresholds defined) |

Validation errors come back as actionable strings: `"tier: must be one of: deep, sharp, balanced, mechanical, unknown"` — the agent can self-correct without reading Pydantic internals.

---

## Project resolution

Tools that need "the current project" call `orquestrum.lib.paths.find_project_root()` (walks up from the server's cwd looking for `.orquestrum/`). Tools that take an explicit `project=...` resolve via `orquestrum.lib.registry.find_by_name()`.

When neither resolves, the tool returns:

```json
{
  "ok": false,
  "error": "no .orquestrum/ found walking up from cwd. Run `orquestrum init` here, or pass project=<name>.",
  "kind": "_ToolError"
}
```

---

## Installation

The orquestrum claude-code integration registers the server automatically. After `orquestrum install --tool claude-code --target <path>`, the target's `.claude/settings.json` contains:

```json
{
  "mcpServers": {
    "orquestrum": {
      "command": "orquestrum",
      "args": ["mcp"],
      "type": "stdio"
    }
  }
}
```

Re-installing replaces this entry surgically — user-installed MCP servers (`filesystem`, `github`, etc.) are preserved. See `orquestrum/core/install.py::_merge_claude_settings` for the merge logic.

For other clients (manual config, opencode, etc.), add the equivalent block to your client's MCP config and point to the `orquestrum` executable.

---

## Tool allowlists in agent frontmatter

**Removed in v0.5.1.** Earlier versions emitted a `tools:` field in Helm and Flux frontmatter to restrict them at the API level. Claude Code, however, **hides** any subagent that declares `tools:` from the interactive Shift+Tab agent picker — they become subagent-only (callable only via Task), which broke the most common UX path: a user typing `@"Helm - The Architect"` would not find Helm in the picker.

Tradeoff accepted: tool discipline for coordinators (Helm, Flux) is now enforced **via prompt content** rather than at the API level. Each agent's body opens with explicit "⛔ MANDATORY DELEGATION RULES" listing the tools it must not use (Edit, Bash, Grep, Glob for coordinators) — the LLM follows the prompt, and in practice this has been at least as reliable as the API restriction was.

The dict `ClaudeCodeAdapter._CLAUDE_TOOLS_ALLOWLIST` in `orquestrum/core/convert.py` is now intentionally empty. Adding entries to it would re-hide those agents from the picker. See commit `39c1ed5` for the full rationale.

The 6 specialist agents (Lore, Forge, Cipher, Ward, Cast, Trace) never had `tools:` restrictions — they inherit all native tools plus all MCP tools, including the write ones. Forge or Ward calling `orq_skill_completed` at the end of a skill is the canonical write path; coordinators don't author metric events (still enforced by prompt).

---

## CLI hub — `orquestrum mcp` subcommands

Beyond running the server, `orquestrum mcp` exposes a small management hub for **all** MCP servers in `~/.claude/settings.json` (orquestrum's own + any third-party ones the user added). All operations are `settings.json` CRUD plus a smoke-test — no JSON-editing by hand needed.

| Subcommand | What it does |
|---|---|
| `orquestrum mcp` (no args) | Default — runs the server. Backward-compat with the form `settings.json` registers (`{"command": "orquestrum", "args": ["mcp"]}`). |
| `orquestrum mcp run` | Explicit form of the above. |
| `orquestrum mcp list` | Print a table of every server in `--target/.claude/settings.json` with NAME / COMMAND / TYPE / OWNER (orquestrum vs user). |
| `orquestrum mcp tools` | Catalog of the 6 read-only + 2 write `orq_*` tools + 2 resources. AST-based — does not start the server. |
| `orquestrum mcp add NAME --command CMD [--args ARG …] [--type stdio\|http]` | Register a third-party MCP server. Replaces existing entry of same name (idempotent). |
| `orquestrum mcp remove NAME [--force]` | Unregister. Refuses to remove `orquestrum` without `--force` (agents would lose access to all `orq_*` tools). |
| `orquestrum mcp validate [--timeout SEC]` | For each registered server, attempt to spawn the binary + a probe arg. Reports ✓/✗ + elapsed ms. Timeout-as-healthy (server waiting on stdio). |

Examples:

```bash
orquestrum mcp list                                          # current state
orquestrum mcp tools                                         # see what orq exposes
orquestrum mcp add filesystem \
    --command npx --args -y @modelcontextprotocol/server-filesystem /tmp
orquestrum mcp add github --command mcp-github
orquestrum mcp validate                                      # spawn each + report
orquestrum mcp remove filesystem
```

The `orquestrum setup --advanced` wizard uses these helpers internally — section [8/9] lists current MCPs and offers to add common ones (filesystem, github, postgres) interactively.

### Manual launch (debugging)

The server is intended to be spawned by an MCP client, but you can drive it manually for inspection:

```bash
# Inspector UI (recommended)
npx @modelcontextprotocol/inspector orquestrum mcp

# Pipe a JSON-RPC request directly
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | orquestrum mcp
```

### Querying from agents

Inside any orquestrum-installed agent body, write the call inline:

```
Use mcp__orquestrum__orq_budget_status with tier="deep" before
delegating to Forge for a large refactor. If pct_input > 0.8, split
the work or warn the operator.
```

The agent calls the tool the same way it calls Read or Bash — Claude Code routes through the MCP transport transparently.

### Cross-project queries

```
mcp__orquestrum__orq_cost_today
→ {
    "ok": true,
    "date": "2026-05-03",
    "total_cost_usd": 1.247,
    "total_calls": 38,
    "per_project": [
      {"project_path": "/home/x/proj-a", "cost_usd": 0.42, "calls": 12},
      {"project_path": "/home/x/proj-b", "cost_usd": 0.83, "calls": 26}
    ]
  }
```

---

## Failure modes

| Failure | Behavior |
|---|---|
| `mcp` package import fails | `orquestrum mcp` raises ImportError immediately at startup; the rest of the CLI is unaffected (lazy import in `commands/mcp.py`) |
| `events.jsonl` corrupt (one bad line) | `read_events` skips the malformed line and continues — partial events are visible |
| Project root not found | tool returns `{ok: false, error: "...orquestrum init..."}`; agent can fall back to `project=` form |
| Pydantic validation fails | tool returns flat `error` string with field name and constraint; agent retries with corrected input |
| `lib.models.estimate_cost` import fails | `_estimate_cost_safe` returns `0.0` so events still record (degraded) |
| Two writers race on `events.jsonl` | OS-level append is atomic for `< PIPE_BUF` (~4 KB); each event well under that |

The server NEVER raises uncaught exceptions to the MCP client — every tool is wrapped in `try/except _ToolError` returning the structured envelope.

---

## Schema additions

The MCP server adds one new field to every event it writes: `"source": "mcp"`. Hook-emitted events lack this field; consumers that want to distinguish can `event.get('source') == 'mcp'`.

`orq_skill_completed` writes the full `skill_completion` schema documented in `docs/governance/OBSERVABILITY.md` — no new fields.

---

## When NOT to use the MCP server

- **Recording token usage from inside the agent.** The Stop hook is the source of truth. Manual `orq_record_event` is for the rare case where the agent calls an external (non-Anthropic) model the hook can't see.
- **Replacing the Stop hook.** The hook is the only path with access to Claude Code's actual `usage` counters. The MCP server augments; it doesn't replace.
- **Storing prompts or business-confidential content.** Same rule as the rest of metrics: counts and metadata yes, content no.
- **Hot-path mid-turn writes.** stdio MCP has minimal latency, but every write touches disk. Don't call `orq_record_event` thousands of times per turn — batch into a single `orq_skill_completed` at the end.

---

## Cross-references

- `docs/governance/OBSERVABILITY.md` — event schema, aggregation, dashboard
- `docs/governance/COST.md` — budget thresholds the `orq_budget_status` tool checks
- `agents/helm.md` — uses `orq_*` tools for routing decisions
- `orquestrum/mcp/server.py` — implementation
- `orquestrum/mcp/schemas.py` — input validation
- `tests/mcp/test_server.py` — coverage of every tool
