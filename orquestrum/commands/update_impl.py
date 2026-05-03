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


def _orquestrum_agent_filenames() -> list[str]:
    """Return the exact filenames Orquestrum installs for its 8 agents."""
    from orquestrum.lib.models import AGENT_TIERS
    from orquestrum.lib.rewrite import name_to_kebab
    return [f'{name_to_kebab(name)}.md' for name in AGENT_TIERS]


def _remove_only_framework_files(directory: Path, filenames: list[str]) -> list[str]:
    """Delete only the specific files Orquestrum owns. Never removes the directory."""
    removed: list[str] = []
    for fname in filenames:
        f = directory / fname
        if f.exists():
            f.unlink()
            removed.append(str(f.relative_to(directory.parent.parent)))
    return removed


def _cleanup_old_tool(project_root: Path, old_tool: str) -> list[str]:
    """Remove only the files Orquestrum installed for the given tool.

    Strategy:
      1. If a manifest entry exists at `~/.orquestrum/installs.json` for
         (target=project_root, tool=old_tool), use it as source of truth —
         orquestrum removes ONLY the files/dirs it recorded. User-added
         content in shared dirs is preserved (the rmdir of those dirs
         fails if non-empty, leaving user files untouched).
      2. Otherwise, fall back to the legacy heuristic for installs that
         predate the manifest. The heuristic uses uniqueness of agent
         filenames + `.sdd/` being orquestrum-exclusive by convention,
         which is correct for the canonical install but cannot defend
         against user files dropped under those dirs.

    The manifest path is the future-proof one; the heuristic remains so
    upgrades from older CLIs don't regress.
    """
    from orquestrum.lib import installs_manifest

    record = installs_manifest.get_install(old_tool, project_root)
    if record is not None:
        removed_files, removed_dirs = installs_manifest.surgical_uninstall(
            old_tool, project_root,
        )
        # claude-code: hooks live inside settings.json, not as a separate file
        if old_tool == 'claude-code':
            settings = project_root / '.claude' / 'settings.json'
            if settings.exists():
                _scrub_claude_settings_hooks(settings)
        return removed_files + [f'{d}/' for d in removed_dirs]

    # ── legacy heuristic (no manifest entry) ────────────────────────────
    removed: list[str] = []
    agent_files = _orquestrum_agent_filenames()

    if old_tool == 'claude-code':
        # .claude/agents/ is shared — remove only Orquestrum's agent files
        agents_dir = project_root / '.claude' / 'agents'
        if agents_dir.is_dir():
            removed += _remove_only_framework_files(agents_dir, agent_files)
        # .claude/skills/ is shared — remove only Orquestrum-installed skills
        skills_dir = project_root / '.claude' / 'skills'
        if skills_dir.is_dir():
            from orquestrum.lib.paths import canonical_assets_root
            try:
                canonical_skills = canonical_assets_root() / 'skills'
                orq_skill_names = {d.name for d in canonical_skills.iterdir()
                                   if d.is_dir()}
                for name in orq_skill_names:
                    target_skill = skills_dir / name
                    if target_skill.is_dir():
                        shutil.rmtree(target_skill, ignore_errors=True)
                        removed.append(f'.claude/skills/{name}')
            except OSError:
                pass
        # .claude/sdd/ is exclusively Orquestrum's — safe to remove entirely
        sdd = project_root / '.claude' / 'sdd'
        if sdd.is_dir():
            shutil.rmtree(sdd, ignore_errors=True)
            removed.append('.claude/sdd')
        # Legacy layout (pre-v0.3.1): .sdd/ at the project root
        legacy_sdd = project_root / '.sdd'
        if legacy_sdd.is_dir():
            shutil.rmtree(legacy_sdd, ignore_errors=True)
            removed.append('.sdd (legacy)')
        # settings.json: remove only OUR hook entries, preserve user keys
        settings = project_root / '.claude' / 'settings.json'
        if settings.exists():
            _scrub_claude_settings_hooks(settings)
            removed.append('.claude/settings.json (orquestrum hooks)')
    elif old_tool == 'opencode':
        # agents/ and skills/ are shared — remove only Orquestrum's files
        agents_dir = project_root / '.opencode' / 'agents'
        if agents_dir.is_dir():
            removed += _remove_only_framework_files(agents_dir, agent_files)
        # docs/ is exclusively Orquestrum's — safe to remove entirely
        for rel in ('.opencode/docs',):
            p = project_root / rel
            if p.is_dir():
                shutil.rmtree(p, ignore_errors=True)
                removed.append(rel)
    return removed


def _detect_install_mode() -> str:
    """Returns 'source', 'uv-tool', or 'unknown'."""
    canonical = paths.canonical_root()
    if canonical and (canonical / '.git').is_dir():
        return 'source'
    import shutil
    exe = shutil.which('orquestrum')
    if exe:
        exe_path = Path(exe).resolve()
        for uv_tools in (
            Path.home() / '.local' / 'share' / 'uv' / 'tools',
            Path.home() / 'Library' / 'Application Support' / 'uv' / 'tools',
        ):
            try:
                exe_path.relative_to(uv_tools)
                return 'uv-tool'
            except ValueError:
                pass
    return 'unknown'


def _run_self_upgrade() -> int:
    import subprocess
    mode = _detect_install_mode()

    if mode == 'source':
        canonical = paths.canonical_root()
        print(f'Source install detected at {canonical}')
        print('Running: git pull ...')
        result = subprocess.run(['git', 'pull'], cwd=canonical)
        if result.returncode != 0:
            return result.returncode
        print('\nRegenerating integration packages...')
        from orquestrum.core.convert import main as convert_main
        prev = os.getcwd()
        try:
            os.chdir(canonical)
            convert_main(['--all'])
        finally:
            os.chdir(prev)
        print('\nOrquestrum updated.')
        return 0

    if mode == 'uv-tool':
        print('uv tool install detected.')
        print('Running: uv tool upgrade orquestrum ...')
        result = subprocess.run(['uv', 'tool', 'upgrade', 'orquestrum'])
        return result.returncode

    print('Could not detect install method automatically. Run one of:')
    print('  uv tool upgrade orquestrum')
    print('  pip install --upgrade git+https://github.com/johnt1000/orquestrum')
    print('Or, if installed --editable, run `git pull` in the source repo.')
    return 0


def _scrub_claude_settings_hooks(settings_path: Path) -> None:
    """Remove orquestrum hook entries from a Claude Code settings.json,
    preserve user keys / other hooks.

    Recognises every form orquestrum has emitted historically:
      - `orquestrum hook`                          (≥0.5.1, current)
      - `uv run .claude/sdd/scripts/...`           (0.3.1–0.5.0)
      - `uv run .sdd/scripts/...`                  (≤0.3.0)
    so old installs scrub cleanly regardless of which version put the
    entry there.
    """
    import json
    try:
        data = json.loads(settings_path.read_text(encoding='utf-8'))
    except (json.JSONDecodeError, OSError):
        return
    hooks = data.get('hooks') or {}

    def _is_orq(cmd: str | None) -> bool:
        if not cmd:
            return False
        if 'orquestrum hook' in cmd:
            return True
        return 'sdd/scripts/hooks/emit_metrics.py' in cmd

    for event, blocks in list(hooks.items()):
        if not isinstance(blocks, list):
            continue
        new_blocks = []
        for block in blocks:
            inner = block.get('hooks') or []
            kept = [h for h in inner if not _is_orq(h.get('command'))]
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
    """Generate (if needed) and install an integration into the target project.

    Works equally in dev mode and wheel mode — convert resolves source/output
    paths internally, no chdir required.
    """
    from orquestrum.core.convert import main as convert_main
    from orquestrum.core.install import main as install_main

    integration_dir = paths.convert_output_root() / tool
    if not integration_dir.is_dir():
        args = ['--tool', tool]
        if provider:
            args += ['--provider', provider]
        convert_main(args)

    install_main(['--tool', tool, '--target', str(project_root)])
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
        return _run_self_upgrade()

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
