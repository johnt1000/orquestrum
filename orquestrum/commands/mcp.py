"""orquestrum mcp — start the MCP server (stdio transport).

The server exposes `orq_*` tools that LLM agents (Claude Code, opencode,
etc.) call via the Model Context Protocol. Registration happens in the
target project's settings.json (or ~/.claude/settings.json globally).

This subcommand is the only stable way to launch the server; downstream
tools should not import `orquestrum.mcp.server` directly.
"""
from __future__ import annotations
import argparse


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        'mcp',
        help='Start the orquestrum MCP server on stdio (for use by '
             'Claude Code / opencode / any MCP client).',
        description=(
            'Run the orquestrum MCP server. Communicates over stdio, so '
            'this command is meant to be spawned by an MCP client (e.g. '
            'Claude Code reads ~/.claude/settings.json mcpServers entry '
            'and starts this process). Manual run: pipe an MCP request '
            'on stdin to test, or use `npx @modelcontextprotocol/inspector '
            'orquestrum mcp`.'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.set_defaults(handler=_handler)


def _handler(args: argparse.Namespace) -> int:
    # Lazy import — `mcp` is only loaded if the subcommand actually runs,
    # so other CLI commands stay unaffected if the dep is missing during
    # bootstrap.
    from orquestrum.mcp.server import main as run_server
    run_server()
    return 0
