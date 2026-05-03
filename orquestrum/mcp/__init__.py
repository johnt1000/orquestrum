"""orquestrum.mcp — MCP server exposing `orq_*` tools to LLM agents.

The server is a thin adapter over `orquestrum.lib.metrics`, `lib.budget`,
and `lib.registry`. Run via `orquestrum mcp` (stdio transport).

See docs/governance/OBSERVABILITY.md for the schema. Agents query the
server for budget status, recent events, and cross-project cost; agents
also write rich domain events (skill completions with gates/artifacts)
that the Stop hook cannot capture.
"""
