"""mcp.py — web view of `orquestrum mcp list/tools/add/remove/validate`.

Reads `~/.claude/settings.json` directly via `lib.settings_io` (instant,
no subprocess). The `tools` list comes from `mcp.registry` (AST parse
of the server module — no MCP SDK import). Add/remove/validate dispatch
as POSTs that call the same lib helpers the CLI uses.
"""
from __future__ import annotations
import sys
from pathlib import Path

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from orquestrum.lib import settings_io
from orquestrum.mcp.registry import list_orq_tools, list_orq_resources, split_by_mode
from ui.lib import jobs

router = APIRouter(prefix='/system/mcp')


_RESERVED_NAME = 'orquestrum'  # protected from accidental remove


def _settings_path() -> Path:
    """Resolve to ~/.claude/settings.json regardless of cwd."""
    return Path.home() / '.claude' / 'settings.json'


def _format_command(entry: dict) -> str:
    cmd = entry.get('command') or '?'
    args = entry.get('args') or []
    return ' '.join([cmd] + list(args))


@router.get('', response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    """List MCP servers + the orquestrum tool catalog. Single page so the
    user sees both 'what's wired up' and 'what calls am I exposing'."""
    templates = request.app.state.templates
    settings_path = _settings_path()
    settings = settings_io.load_claude_settings(settings_path)
    servers_dict = settings_io.list_mcp_servers(settings)

    server_rows = []
    for name in sorted(servers_dict):
        entry = servers_dict[name]
        owner = 'orquestrum' if name == _RESERVED_NAME else 'user'
        server_rows.append({
            'name':    name,
            'command': _format_command(entry),
            'type':    entry.get('type', 'stdio'),
            'owner':   owner,
            'protected': name == _RESERVED_NAME,
        })

    tools = list_orq_tools()
    read_only, write = split_by_mode(tools)
    resources = list_orq_resources()

    return templates.TemplateResponse(
        request,
        'system_mcp.html',
        {
            'settings_path': str(settings_path),
            'settings_exists': settings_path.exists(),
            'server_rows':   server_rows,
            'server_count':  len(server_rows),
            'read_only_tools': read_only,
            'write_tools':     write,
            'resources':       resources,
        },
    )


@router.post('/add')
async def add(
    request: Request,
    name:    str = Form(...),
    command: str = Form(...),
    args:    str = Form(''),
    server_type: str = Form('stdio'),
) -> RedirectResponse:
    """Register a third-party MCP. `args` is whitespace-separated."""
    settings_path = _settings_path()
    settings = settings_io.load_claude_settings(settings_path)
    arg_list = args.split() if args else None
    settings_io.add_mcp_server(
        settings, name.strip(),
        command=command.strip(),
        args=arg_list,
        server_type=server_type,
    )
    settings_io.write_claude_settings(settings_path, settings)
    return RedirectResponse('/system/mcp', status_code=303)


@router.post('/remove')
async def remove(
    request: Request,
    name:  str = Form(...),
    force: str = Form(''),    # checkbox value when ticked
) -> RedirectResponse:
    """Unregister an MCP. Refuses 'orquestrum' unless `force=on`."""
    if name == _RESERVED_NAME and force != 'on':
        # Refuse silently — page reload will show the entry still there
        return RedirectResponse('/system/mcp', status_code=303)
    settings_path = _settings_path()
    settings = settings_io.load_claude_settings(settings_path)
    settings_io.remove_mcp_server(settings, name)
    settings_io.write_claude_settings(settings_path, settings)
    return RedirectResponse('/system/mcp', status_code=303)


@router.post('/validate')
async def validate(request: Request) -> RedirectResponse:
    """Spawn `orquestrum mcp validate` as a job; redirect to its output."""
    job = jobs.submit(
        label='orquestrum mcp validate',
        cmd=[sys.executable, '-u', '-m', 'orquestrum.cli', 'mcp', 'validate'],
        cwd=str(request.app.state.config.root),
        timeout_s=60,
        render_md=False,
        extra={'back_url': '/system/mcp'},
    )
    return RedirectResponse(f'/jobs/{job.id}', status_code=303)
