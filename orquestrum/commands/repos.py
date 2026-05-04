"""orquestrum repos {list,add,remove} — manage ~/.orquestrum/registry.toml."""
from __future__ import annotations
import argparse


def register(sub: argparse._SubParsersAction) -> None:
    p = sub.add_parser(
        'repos',
        help='Manage the global registry of orquestrum-linked projects.',
        description=(
            'Read/modify `~/.orquestrum/registry.toml` — the central list of '
            'projects connected to orquestrum (created automatically when '
            '`orquestrum init` runs in a project).\n\n'
            'Use `repos list` to see what `update --all` and `web --mode '
            'framework` will touch. Use `repos add` to manually register a '
            'project that was set up before the registry existed (legacy '
            'v0.4 projects). Use `repos remove` to unlink a project without '
            'deleting its files.'
        ),
        epilog=(
            'Examples:\n'
            '  orquestrum repos list                              # show all\n'
            '  orquestrum repos add /path/to/project              # register manually\n'
            '  orquestrum repos add . --tool claude-code          # current dir + metadata\n'
            '  orquestrum repos add ~/work/api --provider glm     # lock provider\n'
            '  orquestrum repos remove my-project                 # unlink by name\n'
            '  orquestrum repos remove /path/to/project           # unlink by path\n'
            '\n'
            'See also:\n'
            '  orquestrum init --help     Auto-registers when run in a project\n'
            '  orquestrum doctor --help   Detects stale registry entries'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    repos_sub = p.add_subparsers(dest='repos_cmd', metavar='ACTION', required=True)

    pl = repos_sub.add_parser(
        'list',
        help='Show all registered projects (name, path, tool, provider).',
        description='Print every project in ~/.orquestrum/registry.toml with its metadata.',
    )
    pl.set_defaults(handler=_list)

    pa = repos_sub.add_parser(
        'add',
        help='Manually register a project path in the registry.',
        description=(
            'Add a project to ~/.orquestrum/registry.toml. Normally this happens '
            'automatically when `orquestrum init` runs — use this command only '
            'for legacy projects or to register without touching project files.'
        ),
        epilog=(
            'Examples:\n'
            '  orquestrum repos add .\n'
            '  orquestrum repos add /path/to/project --name myapp --tool claude-code'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    pa.add_argument('path', help='Path to a project directory')
    pa.add_argument('--name', help='Project name (default: basename of path)')
    pa.add_argument('--tool', choices=['claude-code', 'opencode'],
                    help='Tool installed in this project (optional)')
    pa.add_argument('--provider', choices=['claude', 'copilot', 'glm'],
                    help='Provider locked at install time (optional)')
    pa.set_defaults(handler=_add)

    pr = repos_sub.add_parser(
        'remove',
        help='Unregister a project (does not delete files).',
        description=(
            'Remove a project from ~/.orquestrum/registry.toml. Does NOT '
            'delete .orquestrum/ or any project files — see `orquestrum '
            'uninstall` for that.'
        ),
        epilog=(
            'Examples:\n'
            '  orquestrum repos remove my-project        # by name\n'
            '  orquestrum repos remove /path/to/project  # by path (auto-detect: has /)'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
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
