"""mcp.registry — introspection of orq_* tools + resources without
running the MCP server.

The server in `mcp/server.py` registers tools via `@mcp.tool(...)` and
resources via `@mcp.resource(URI)`. To list these for `orquestrum mcp
tools`, we parse the source file with `ast` rather than importing
`FastMCP` (which would pull in the whole `mcp` package and start
initialising state we don't need).

This keeps the listing fast, dependency-light, and stable across
FastMCP versions — the public MCP introspection API is async and
designed for clients, not for "show me what this server has" CLI use.
"""
from __future__ import annotations
import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ToolInfo:
    name: str
    description: str
    annotations: dict[str, bool]
    parameters: list[str]      # required positional params (excluding optionals)
    is_read_only: bool


@dataclass(frozen=True)
class ResourceInfo:
    uri: str
    function_name: str
    description: str


def _server_source_path() -> Path:
    """Locate `orquestrum/mcp/server.py` regardless of where the package
    is installed. importlib.resources would be canonical but we need a
    file path for ast.parse."""
    return Path(__file__).resolve().parent / 'server.py'


def _extract_decorator_kwargs(decorator: ast.expr) -> dict[str, Any]:
    """Return the literal keyword arguments passed to a decorator call.
    Returns {} for non-call decorators (e.g. bare `@x`) or anything we
    can't safely literal_eval."""
    if not isinstance(decorator, ast.Call):
        return {}
    out: dict[str, Any] = {}
    for kw in decorator.keywords:
        if kw.arg is None:
            continue
        try:
            out[kw.arg] = ast.literal_eval(kw.value)
        except (ValueError, TypeError):
            continue
    return out


def _extract_decorator_first_arg(decorator: ast.expr) -> str | None:
    """For `@mcp.resource(URI)` style, return the URI string (first
    positional arg). Returns None if the decorator isn't a call or the
    arg isn't a literal string."""
    if not isinstance(decorator, ast.Call) or not decorator.args:
        return None
    arg = decorator.args[0]
    try:
        value = ast.literal_eval(arg)
    except (ValueError, TypeError):
        return None
    return value if isinstance(value, str) else None


def _is_decorator_for(decorator: ast.expr, attr: str) -> bool:
    """Check if a decorator targets `mcp.<attr>` (where `mcp` is the
    FastMCP instance). Matches both `@mcp.tool` and `@mcp.tool(...)`."""
    target = decorator.func if isinstance(decorator, ast.Call) else decorator
    if not isinstance(target, ast.Attribute):
        return False
    if target.attr != attr:
        return False
    return isinstance(target.value, ast.Name) and target.value.id == 'mcp'


def _required_params(func: ast.FunctionDef) -> list[str]:
    """Extract required positional/keyword arguments — i.e. those without
    a default value. The async/sync distinction doesn't matter here."""
    args = func.args
    defaults = args.defaults or []
    pos_count = len(args.args)
    required_pos = pos_count - len(defaults)
    return [a.arg for a in args.args[:required_pos]]


def list_orq_tools() -> list[ToolInfo]:
    """Parse server.py and return one ToolInfo per @mcp.tool function,
    sorted alphabetically by name. Pure file read — no module import."""
    source = _server_source_path().read_text(encoding='utf-8')
    tree = ast.parse(source)
    out: list[ToolInfo] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        for dec in node.decorator_list:
            if not _is_decorator_for(dec, 'tool'):
                continue
            kwargs = _extract_decorator_kwargs(dec)
            annotations = kwargs.get('annotations') or {}
            description = ast.get_docstring(node) or ''
            # Take the first sentence/line as the short description
            short = description.split('\n', 1)[0].strip().rstrip('.')
            out.append(ToolInfo(
                name=node.name,
                description=short,
                annotations=annotations,
                parameters=_required_params(node),
                is_read_only=bool(annotations.get('readOnlyHint', False)),
            ))
            break
    out.sort(key=lambda t: t.name)
    return out


def list_orq_resources() -> list[ResourceInfo]:
    """Parse server.py and return one ResourceInfo per @mcp.resource(URI)
    function. Sorted by URI."""
    source = _server_source_path().read_text(encoding='utf-8')
    tree = ast.parse(source)
    out: list[ResourceInfo] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        for dec in node.decorator_list:
            if not _is_decorator_for(dec, 'resource'):
                continue
            uri = _extract_decorator_first_arg(dec)
            if uri is None:
                continue
            description = ast.get_docstring(node) or ''
            short = description.split('\n', 1)[0].strip().rstrip('.')
            out.append(ResourceInfo(
                uri=uri,
                function_name=node.name,
                description=short,
            ))
            break
    out.sort(key=lambda r: r.uri)
    return out


def split_by_mode(tools: list[ToolInfo]) -> tuple[list[ToolInfo], list[ToolInfo]]:
    """Partition tools into (read_only, write). Used by the CLI listing."""
    read_only = [t for t in tools if t.is_read_only]
    write = [t for t in tools if not t.is_read_only]
    return read_only, write
