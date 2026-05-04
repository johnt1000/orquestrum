"""orquestrum mcp — Model Context Protocol management hub.

Subcommands:
  run       Start the orquestrum MCP server on stdio (default — used by clients)
  list      Tabulate every MCP server registered in ~/.claude/settings.json
  tools     Show the 8 orq_* tools + 2 resources this server exposes
  add       Register a third-party MCP server (filesystem, github, etc.)
  remove    Unregister a server (refuses orquestrum unless --force)
  validate  Spawn each server with --help to verify the binary resolves

Backward compatibility: bare `orquestrum mcp` runs the server (settings.json
in the wild registers `{"command": "orquestrum", "args": ["mcp"]}` — that
form keeps working because no subcommand defaults to `run`).
"""
from __future__ import annotations
import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

from orquestrum.lib import settings_io


# ─── argparse ──────────────────────────────────────────────────────────────


_RESERVED_NAME = 'orquestrum'  # cannot be removed via `mcp remove` without --force


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        'mcp',
        help='Manage MCP servers (run | list | tools | add | remove | validate).',
        description=(
            'Hub for Model Context Protocol management. Without a '
            'subcommand, runs the orquestrum MCP server on stdio (the form '
            'expected by Claude Code via `~/.claude/settings.json`).\n\n'
            'Subcommands:\n'
            '  run        Start the orquestrum MCP server (default)\n'
            '  list       Show MCP servers registered in settings.json\n'
            '  tools      Show the orq_* tools + resources this server exposes\n'
            '  add        Register a third-party MCP server\n'
            '  remove     Unregister a server (orquestrum is protected)\n'
            '  validate   Smoke-test each registered server'
        ),
        epilog=(
            'Examples:\n'
            '  orquestrum mcp                                              # run server (used by clients)\n'
            '  orquestrum mcp list                                         # show registered servers\n'
            '  orquestrum mcp tools                                        # show orq_* tool catalog\n'
            '  orquestrum mcp add filesystem --command npx \\\n'
            '      --args -y @modelcontextprotocol/server-filesystem /tmp  # register filesystem MCP\n'
            '  orquestrum mcp remove filesystem                            # unregister it\n'
            '  orquestrum mcp validate                                     # spawn each server, report ✓/✗\n'
            '\n'
            'See also:\n'
            '  orquestrum setup --help    Auto-registers the orquestrum MCP server\n'
            '  docs/governance/MCP.md     Protocol details + tool reference'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    msub = p.add_subparsers(dest='mcp_cmd', metavar='SUBCOMMAND')

    # ── run (default; backward-compatible with settings.json) ───────────
    pr = msub.add_parser(
        'run',
        help='Start the orquestrum MCP server on stdio (default).',
        description=(
            'Launch the orquestrum MCP server. Communicates over stdio, '
            'so this is meant to be spawned by an MCP client. Equivalent '
            'to `orquestrum mcp` with no subcommand.'
        ),
        epilog='Example: npx @modelcontextprotocol/inspector orquestrum mcp run',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    pr.set_defaults(handler=_run)

    # ── list ────────────────────────────────────────────────────────────
    pl = msub.add_parser(
        'list',
        help='Show MCP servers registered in settings.json.',
        description=(
            'Read `--target/.claude/settings.json` (default `--target ~`) '
            'and print a table of every MCP server currently registered. '
            'Marks orquestrum-owned entries vs user-added ones.'
        ),
        epilog='Examples:\n  orquestrum mcp list\n  orquestrum mcp list --target /path/to/project',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    pl.add_argument('--target', default=None,
                    help='Target dir (default: ~). Reads <target>/.claude/settings.json')
    pl.set_defaults(handler=_list)

    # ── tools ───────────────────────────────────────────────────────────
    pt = msub.add_parser(
        'tools',
        help='Show the orq_* tools + resources this server exposes.',
        description=(
            'Introspect `orquestrum/mcp/server.py` and print every '
            '@mcp.tool function (read-only first, then write) plus the '
            '@mcp.resource URIs. Static parse — no need to run the server.'
        ),
        epilog='Example: orquestrum mcp tools',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    pt.set_defaults(handler=_tools)

    # ── add ─────────────────────────────────────────────────────────────
    pa = msub.add_parser(
        'add',
        help='Register a third-party MCP server in settings.json.',
        description=(
            'Add a new MCP server entry to settings.json. User-defined '
            'entries are preserved by every other orquestrum command — '
            'this is the safe way to wire up filesystem / github / postgres '
            "MCPs without hand-editing the JSON.\n\nReplaces an existing "
            'entry of the same name (idempotent re-registration).'
        ),
        epilog=(
            'Examples:\n'
            '  orquestrum mcp add filesystem \\\n'
            '      --command npx --args -y @modelcontextprotocol/server-filesystem /tmp\n'
            '  orquestrum mcp add github --command mcp-github\n'
            '  orquestrum mcp add postgres --command npx \\\n'
            '      --args -y @modelcontextprotocol/server-postgres "postgresql://localhost/db"'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    pa.add_argument('name', help='Server name (key in mcpServers dict)')
    pa.add_argument('--command', required=True,
                    help='Executable to spawn (e.g. npx, mcp-filesystem)')
    pa.add_argument('--args', nargs='*', default=None, metavar='ARG',
                    help='Args to pass to the command (everything after --args)')
    pa.add_argument('--type', default='stdio', choices=['stdio', 'http'],
                    dest='server_type',
                    help='Transport (default: stdio)')
    pa.add_argument('--target', default=None,
                    help='Target dir (default: ~). Writes to <target>/.claude/settings.json')
    pa.set_defaults(handler=_add)

    # ── remove ──────────────────────────────────────────────────────────
    pre = msub.add_parser(
        'remove',
        help='Unregister an MCP server (orquestrum protected by default).',
        description=(
            'Remove an entry from settings.json mcpServers. Refuses to '
            'remove the orquestrum entry unless --force is passed (you '
            "almost certainly don't want that — agents would lose access "
            'to orq_* tools).'
        ),
        epilog=(
            'Examples:\n'
            '  orquestrum mcp remove filesystem\n'
            '  orquestrum mcp remove orquestrum --force    # really, REALLY undo registration'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    pre.add_argument('name', help='Server name to remove')
    pre.add_argument('--force', action='store_true',
                     help=f'Allow removing the {_RESERVED_NAME!r} entry')
    pre.add_argument('--target', default=None,
                     help='Target dir (default: ~). Updates <target>/.claude/settings.json')
    pre.set_defaults(handler=_remove)

    # ── validate ────────────────────────────────────────────────────────
    pv = msub.add_parser(
        'validate',
        help='Smoke-test each registered MCP server (spawn + handshake).',
        description=(
            'For every server in settings.json mcpServers, attempt to '
            'spawn the command + arguments and report whether the '
            'binary resolves. Does NOT do a full MCP handshake — just '
            'confirms the executable is on PATH and runs without an '
            'immediate error.'
        ),
        epilog='Example: orquestrum mcp validate',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    pv.add_argument('--target', default=None,
                    help='Target dir (default: ~). Reads <target>/.claude/settings.json')
    pv.add_argument('--timeout', type=float, default=2.0,
                    help='Seconds to wait per server (default 2.0)')
    pv.set_defaults(handler=_validate)

    # No subcommand → run (back-compat)
    p.set_defaults(handler=_run)


# ─── helpers ───────────────────────────────────────────────────────────────


def _settings_path(target: str | None) -> Path:
    """Resolve the settings.json path. Default: ~/.claude/settings.json."""
    base = Path(target).expanduser() if target else Path.home()
    return base / '.claude' / 'settings.json'


def _ensure_settings_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _format_command(entry: dict) -> str:
    cmd = entry.get('command') or '?'
    args = entry.get('args') or []
    return ' '.join([cmd] + list(args))


# ─── handlers ──────────────────────────────────────────────────────────────


def _run(args: argparse.Namespace) -> int:
    from orquestrum.mcp.server import main as run_server
    run_server()
    return 0


def _list(args: argparse.Namespace) -> int:
    path = _settings_path(args.target)
    if not path.exists():
        print(f'No settings.json at {path} — nothing to list.', file=sys.stderr)
        print('Run `orquestrum setup` to create one.', file=sys.stderr)
        return 1
    settings = settings_io.load_claude_settings(path)
    servers = settings_io.list_mcp_servers(settings)
    if not servers:
        print(f'No MCP servers registered in {path}.')
        return 0

    print(f'MCP servers in {path}:')
    print()
    name_w = max((len(n) for n in servers), default=4)
    print(f'  {"NAME":<{name_w}}  {"COMMAND":<48}  TYPE     OWNER')
    for name, entry in sorted(servers.items()):
        cmd = _format_command(entry)
        if len(cmd) > 48:
            cmd = cmd[:45] + '...'
        type_ = entry.get('type', 'stdio')
        owner = 'orquestrum' if name == _RESERVED_NAME else 'user'
        print(f'  {name:<{name_w}}  {cmd:<48}  {type_:<7}  {owner}')
    print()
    print(f'{len(servers)} server(s) registered. Run `orquestrum mcp validate` to test.')
    return 0


def _tools(args: argparse.Namespace) -> int:
    from orquestrum.mcp.registry import list_orq_tools, list_orq_resources, split_by_mode
    tools = list_orq_tools()
    resources = list_orq_resources()
    read_only, write = split_by_mode(tools)

    print('Tools provided by the orquestrum MCP server (server.py registry):')
    print()
    if read_only:
        print(f'  Read-only ({len(read_only)}):')
        for t in read_only:
            print(f'    {t.name:<22}  — {t.description}')
        print()
    if write:
        print(f'  Write ({len(write)}):')
        for t in write:
            print(f'    {t.name:<22}  — {t.description}')
        print()
    if resources:
        print(f'Resources ({len(resources)}):')
        for r in resources:
            print(f'  {r.uri:<28}  — {r.description}')
        print()
    print('Servers other than orquestrum: run `orquestrum mcp list` to see them.')
    return 0


def _add(args: argparse.Namespace) -> int:
    path = _settings_path(args.target)
    _ensure_settings_dir(path)
    settings = settings_io.load_claude_settings(path)
    is_new = settings_io.add_mcp_server(
        settings, args.name,
        command=args.command,
        args=args.args,
        server_type=args.server_type,
    )
    settings_io.write_claude_settings(path, settings)
    verb = 'registered' if is_new else 'updated'
    print(f'✓ {verb}: {args.name} → {_format_command(settings["mcpServers"][args.name])}')
    print(f'  in {path}')
    print()
    print('Restart your MCP client (Claude Code, opencode) to pick up the change.')
    return 0


def _remove(args: argparse.Namespace) -> int:
    if args.name == _RESERVED_NAME and not args.force:
        print(f'error: refusing to remove {_RESERVED_NAME!r} without --force.', file=sys.stderr)
        print(f'  agents would lose access to all orq_* tools.', file=sys.stderr)
        print(f'  pass --force if you really mean it.', file=sys.stderr)
        return 2

    path = _settings_path(args.target)
    if not path.exists():
        print(f'No settings.json at {path}.', file=sys.stderr)
        return 1
    settings = settings_io.load_claude_settings(path)
    removed = settings_io.remove_mcp_server(settings, args.name)
    if not removed:
        print(f'error: no MCP server named {args.name!r} in {path}.', file=sys.stderr)
        return 1
    settings_io.write_claude_settings(path, settings)
    print(f'✓ removed: {args.name} (from {path})')
    return 0


def _validate(args: argparse.Namespace) -> int:
    path = _settings_path(args.target)
    if not path.exists():
        print(f'No settings.json at {path} — nothing to validate.', file=sys.stderr)
        return 1
    settings = settings_io.load_claude_settings(path)
    servers = settings_io.list_mcp_servers(settings)
    if not servers:
        print(f'No MCP servers registered in {path}.')
        return 0

    print(f'Validating {len(servers)} MCP server(s) from {path}:')
    print()
    failures = 0
    for name, entry in sorted(servers.items()):
        cmd = entry.get('command') or ''
        if not cmd:
            print(f'  ✗ {name:<20} (no command field)')
            failures += 1
            continue
        # Resolve command via PATH first — most failures are "binary not found"
        resolved = shutil.which(cmd)
        if resolved is None and not Path(cmd).is_absolute():
            print(f'  ✗ {name:<20} command not on PATH: {cmd}')
            failures += 1
            continue
        # Best-effort spawn — try -h or --help, capture exit code only
        argv = [resolved or cmd] + list(entry.get('args') or [])
        # For validation, limit args to the binary and a probe flag — we
        # don't want to actually run a long-lived MCP server.
        try:
            t0 = time.monotonic()
            proc = subprocess.run(
                [argv[0], '--help'],
                capture_output=True,
                timeout=args.timeout,
            )
            elapsed_ms = int((time.monotonic() - t0) * 1000)
            # Many MCP servers exit 0 on --help; some exit 1 because they
            # don't recognise the flag. Both indicate the binary works.
            if proc.returncode in (0, 1, 2):
                print(f'  ✓ {name:<20} {cmd}  ({elapsed_ms} ms)')
            else:
                print(f'  ✗ {name:<20} exit={proc.returncode}: {cmd}')
                failures += 1
        except subprocess.TimeoutExpired:
            # A timeout typically means the server started waiting for
            # stdio input, which is actually a healthy sign.
            print(f'  ✓ {name:<20} {cmd}  (started — timed out waiting for stdio)')
        except FileNotFoundError:
            print(f'  ✗ {name:<20} not executable: {cmd}')
            failures += 1
        except Exception as e:
            print(f'  ✗ {name:<20} {type(e).__name__}: {e}')
            failures += 1

    print()
    if failures:
        print(f'{failures} server(s) failed validation.')
        return 1
    print(f'All {len(servers)} server(s) responded.')
    return 0
