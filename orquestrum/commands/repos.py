"""orquestrum repos {list,add,remove} — manage ~/.orquestrum/registry.toml."""
from __future__ import annotations
import argparse


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser('repos', help='List / add / remove projects in the global registry.')
    repos_sub = p.add_subparsers(dest='repos_cmd', metavar='ACTION', required=True)

    pl = repos_sub.add_parser('list', help='Show all registered projects.')
    pl.set_defaults(handler=_list)

    pa = repos_sub.add_parser('add', help='Register a project path.')
    pa.add_argument('path', help='Path to a project directory')
    pa.add_argument('--name', help='Project name (default: basename of path)')
    pa.add_argument('--tool', choices=['claude-code', 'opencode', 'cursor', 'aider', 'windsurf'],
                    help='Tool installed in this project (optional)')
    pa.add_argument('--provider', choices=['claude', 'copilot', 'glm'],
                    help='Provider locked at install time (optional)')
    pa.set_defaults(handler=_add)

    pr = repos_sub.add_parser('remove', help='Unregister a project.')
    pr.add_argument('identifier',
                    help='Project name OR path (auto-detect: contains "/" → path)')
    pr.set_defaults(handler=_remove)


def _list(args: argparse.Namespace) -> int | None:
    from orquestrum.lib.registry import load_registry
    projects = load_registry()
    if not projects:
        print('No projects registered. Run `orquestrum init` in a project directory.')
        return 0
    print(f'{len(projects)} project(s) registered:')
    for proj in projects:
        tool = proj.get('tool') or '-'
        provider = proj.get('provider') or '-'
        linked = proj.get('linked_at') or '-'
        print(f"  {proj['name']:<24} {proj['path']:<50}"
              f" {tool:<12} provider={provider}  linked={linked}")
    return 0


def _add(args: argparse.Namespace) -> int | None:
    from orquestrum.lib.registry import register_project
    from pathlib import Path
    path = Path(args.path).expanduser().resolve()
    if not path.is_dir():
        print(f'error: not a directory: {path}')
        return 1
    name = args.name or path.name
    register_project(name=name, path=path, tool=args.tool, provider=args.provider)
    print(f'Registered: {name} → {path}')
    return 0


def _remove(args: argparse.Namespace) -> int | None:
    from orquestrum.lib.registry import unregister_project
    from pathlib import Path
    ident = args.identifier
    if '/' in ident:
        path = Path(ident).expanduser().resolve()
        removed = unregister_project(path=path)
    else:
        removed = unregister_project(name=ident)
    if removed:
        print(f'Unregistered: {removed["name"]} ({removed["path"]})')
        return 0
    print(f'No project matched: {ident}')
    return 1
