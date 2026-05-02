"""update_impl — implementation of `orquestrum update`."""
from __future__ import annotations
import datetime as dt
import os
import shutil
import sys
import tomllib
from pathlib import Path

from orquestrum.lib import manifest, paths, registry


def _read_project_config(project_root: Path) -> dict:
    cfg = project_root / '.orquestrum' / 'config.toml'
    if not cfg.exists():
        return {}
    try:
        return tomllib.loads(cfg.read_text(encoding='utf-8'))
    except tomllib.TOMLDecodeError:
        return {}


def _project_tool(project_root: Path) -> tuple[str | None, str | None]:
    cfg = _read_project_config(project_root)
    proj = cfg.get('project') or {}
    return proj.get('tool'), proj.get('provider')


def _cleanup_old_tool(project_root: Path, old_tool: str) -> list[str]:
    """Remove integration files of a previous tool. Conservative: only removes
    canonical install paths; leaves user files alone.
    Returns a list of removed paths for the report.
    """
    removed: list[str] = []
    if old_tool == 'claude-code':
        for rel in ('.claude/agents', '.sdd'):
            p = project_root / rel
            if p.is_dir():
                shutil.rmtree(p, ignore_errors=True)
                removed.append(rel)
        # settings.json: remove only OUR hook entries, preserve user keys
        settings = project_root / '.claude' / 'settings.json'
        if settings.exists():
            _scrub_claude_settings_hooks(settings)
            removed.append('.claude/settings.json (orquestrum hooks)')
    elif old_tool == 'opencode':
        for rel in ('.opencode/agents', '.opencode/skills', '.opencode/docs'):
            p = project_root / rel
            if p.is_dir():
                shutil.rmtree(p, ignore_errors=True)
                removed.append(rel)
    elif old_tool == 'cursor':
        p = project_root / '.cursor' / 'rules'
        if p.is_dir():
            shutil.rmtree(p, ignore_errors=True)
            removed.append('.cursor/rules')
    elif old_tool == 'aider':
        p = project_root / 'CONVENTIONS.md'
        if p.exists():
            p.unlink()
            removed.append('CONVENTIONS.md')
    elif old_tool == 'windsurf':
        p = project_root / '.windsurfrules'
        if p.exists():
            p.unlink()
            removed.append('.windsurfrules')
    return removed


def _scrub_claude_settings_hooks(settings_path: Path) -> None:
    """Remove orquestrum hook entries from a Claude Code settings.json,
    preserve user keys / other hooks."""
    import json
    try:
        data = json.loads(settings_path.read_text(encoding='utf-8'))
    except (json.JSONDecodeError, OSError):
        return
    hooks = data.get('hooks') or {}
    target_cmd = 'uv run .sdd/scripts/hooks/emit_metrics.py'
    for event, blocks in list(hooks.items()):
        if not isinstance(blocks, list):
            continue
        new_blocks = []
        for block in blocks:
            inner = block.get('hooks') or []
            kept = [h for h in inner if h.get('command') != target_cmd]
            if kept:
                new_blocks.append({**block, 'hooks': kept})
        if new_blocks:
            hooks[event] = new_blocks
        else:
            hooks.pop(event, None)
    if hooks:
        data['hooks'] = hooks
    else:
        data.pop('hooks', None)
    settings_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def _install_tool(project_root: Path, tool: str, provider: str | None) -> bool:
    canonical = paths.canonical_root()
    if canonical is None:
        print('warning: canonical Orquestrum source not found — install skipped.', file=sys.stderr)
        return False
    integration_dir = canonical / 'integrations' / tool
    if not integration_dir.is_dir():
        from scripts.convert import main as convert_main
        prev_cwd = os.getcwd()
        try:
            os.chdir(canonical)
            args = ['--tool', tool]
            if provider:
                args += ['--provider', provider]
            convert_main(args)
        finally:
            os.chdir(prev_cwd)
    from scripts.install import main as install_main
    prev_cwd = os.getcwd()
    try:
        os.chdir(canonical)
        install_main(['--tool', tool, '--target', str(project_root)])
    finally:
        os.chdir(prev_cwd)
    return True


def _update_one(project_root: Path, *, new_tool: str | None, check: bool) -> tuple[bool, str]:
    """Update one project. Returns (success, message)."""
    if not (project_root / '.orquestrum').is_dir():
        return False, 'not initialized (run `orquestrum init` here)'

    cur_tool, cur_provider = _project_tool(project_root)
    state = manifest.read_manifest_state(project_root)

    if check:
        if new_tool and new_tool != cur_tool:
            return True, f'(check) would switch from {cur_tool!r} → {new_tool!r}'
        if cur_tool:
            return True, f'(check) would re-install {cur_tool}'
        return True, '(check) no tool configured; would do nothing'

    target_tool = new_tool or cur_tool
    if not target_tool:
        return False, 'no tool configured (use --tool to set one)'

    # Tool switch?
    if cur_tool and new_tool and new_tool != cur_tool:
        removed = _cleanup_old_tool(project_root, cur_tool)
        msg_remove = f' removed: {", ".join(removed)}' if removed else ''
        if state:
            manifest.append_history(state, f'switched from `{cur_tool}` to `{new_tool}`')
            state.tool = new_tool
            state.last_sync = dt.date.today().isoformat()
            manifest.write_manifest(project_root, state)
        # Update config.toml
        _set_project_tool(project_root, new_tool, cur_provider)
        # Update registry tool field too
        proj_name = state.name if state else project_root.name
        registry.register_project(name=proj_name, path=project_root,
                                  tool=new_tool, provider=cur_provider)
        ok = _install_tool(project_root, new_tool, cur_provider)
        msg = f'switched {cur_tool} → {new_tool}{msg_remove}'
        return ok, msg

    # Same tool: re-install + bump last_sync
    ok = _install_tool(project_root, target_tool, cur_provider)
    if state:
        state.last_sync = dt.date.today().isoformat()
        if not state.tool and target_tool:
            state.tool = target_tool
        manifest.write_manifest(project_root, state)
    proj_name = state.name if state else project_root.name
    registry.register_project(name=proj_name, path=project_root,
                              tool=target_tool, provider=cur_provider)
    return ok, f're-installed {target_tool}'


def _set_project_tool(project_root: Path, tool: str, provider: str | None) -> None:
    """Rewrite [project].tool in .orquestrum/config.toml. Best-effort regex."""
    cfg = project_root / '.orquestrum' / 'config.toml'
    if not cfg.exists():
        return
    text = cfg.read_text(encoding='utf-8')
    import re
    if 'tool' in text:
        text = re.sub(r'^tool\s*=\s*".*"', f'tool      = "{tool}"', text, count=1, flags=re.MULTILINE)
    else:
        # Insert after [project] header
        text = re.sub(r'(\[project\][^\[]*)', rf'\1tool      = "{tool}"\n', text, count=1)
    cfg.write_text(text, encoding='utf-8')


def run_update(*, tool: str | None = None, all_: bool = False,
               check: bool = False, self_update: bool = False) -> int:
    if self_update:
        print('To upgrade the orquestrum CLI itself, run one of:')
        print('  uv tool upgrade orquestrum')
        print('  pip install --upgrade git+https://github.com/johnt1000/orquestrum')
        print('Or, if installed --editable, run `git pull` in the source repo.')
        return 0

    if all_:
        projects = registry.load_registry()
        if not projects:
            print('No projects registered.')
            return 0
        print(f'{len(projects)} project(s) to update:')
        ok_count = skip_count = fail_count = 0
        for i, proj in enumerate(projects, 1):
            path = Path(proj['path'])
            print(f'  [{i}/{len(projects)}] {proj["name"]:<24} ({path})')
            if not path.is_dir():
                print('    skipped (path no longer exists)')
                skip_count += 1
                continue
            ok, msg = _update_one(path, new_tool=tool, check=check)
            print(f'    {"✓" if ok else "✗"} {msg}')
            if ok:
                ok_count += 1
            else:
                fail_count += 1
        print()
        print(f'{ok_count} succeeded, {skip_count} skipped, {fail_count} failed.')
        return 0 if fail_count == 0 else 1

    # Default: current project
    project_root = paths.find_project_root() or Path.cwd()
    if not (project_root / '.orquestrum').is_dir():
        print('error: not in an Orquestrum project. Run `orquestrum init` here first.', file=sys.stderr)
        return 1
    ok, msg = _update_one(project_root, new_tool=tool, check=check)
    print(msg)
    return 0 if ok else 1
