#!/usr/bin/env python3
"""install.py — copies an integration package into a target project.

Usage:
    orquestrum install --tool <tool> --target <path>
    orquestrum install --auto --target <path>

    Tools: claude-code, opencode, cursor, aider, windsurf

    Run `orquestrum convert` first to generate integrations/.
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

from orquestrum.lib.log import log, ok, warn, err, set_prefix
from orquestrum.lib.models import VALID_TOOLS
from orquestrum.lib.paths import convert_output_root

set_prefix('install')

# INTEGRATIONS is the directory holding `orquestrum convert`'s output.
# It's the dev repo's `integrations/` in dev mode and the user cache
# (`~/.orquestrum/cache/integrations/`) in wheel mode. Stays a module-level
# attribute because tests/core/test_install.py monkeypatches it.
INTEGRATIONS = convert_output_root()


def _merge_claude_settings(template_path: Path, target_path: Path) -> None:
    """Merge our hooks into target settings.json without clobbering user keys.

    Strategy:
      - If target does not exist → copy template verbatim.
      - If target exists → load both, deep-merge hooks.{Stop,SubagentStop}
        as additional entries; never overwrite existing user hooks at the
        same matcher; refuse if structure incompatible.
    """
    if not target_path.exists():
        shutil.copy(template_path, target_path)
        ok(f'  settings.json: created at {target_path}')
        return

    try:
        template_data = json.loads(template_path.read_text(encoding='utf-8'))
        target_data   = json.loads(target_path.read_text(encoding='utf-8'))
    except json.JSONDecodeError as e:
        warn(f'  settings.json: target is not valid JSON ({e}); leaving untouched.')
        warn(f'  Manually merge hooks from: {template_path}')
        return

    target_hooks   = target_data.setdefault('hooks', {})
    template_hooks = template_data.get('hooks', {})

    added: list[str] = []
    skipped: list[str] = []

    for event_name, blocks in template_hooks.items():
        existing = target_hooks.setdefault(event_name, [])
        if not isinstance(existing, list):
            warn(f'  settings.json: hooks.{event_name} exists but is not a list; skipping.')
            continue
        for block in blocks:
            block_command = next(
                (h.get('command') for h in block.get('hooks', []) if h.get('command')),
                None,
            )
            # Skip if any existing entry already runs the same command
            duplicate = any(
                h.get('command') == block_command
                for ex in existing
                for h in ex.get('hooks', [])
                if isinstance(h, dict)
            )
            if duplicate:
                skipped.append(f'{event_name}: {block_command}')
            else:
                existing.append(block)
                added.append(f'{event_name}: {block_command}')

    target_path.write_text(json.dumps(target_data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    if added:
        ok(f'  settings.json: added {len(added)} hook(s)')
        for entry in added:
            print(f'    + {entry}')
    if skipped:
        log(f'  settings.json: {len(skipped)} hook(s) already present; skipped')


def detect_tools(target: Path) -> list[str]:
    found: list[str] = []
    home = Path.home()
    if (home / '.claude').is_dir() or shutil.which('claude'):
        found.append('claude-code')
    if ((home / '.config' / 'opencode').is_dir() or
            (target / '.opencode').is_dir() or shutil.which('opencode')):
        found.append('opencode')
    if (target / '.cursor').is_dir() or shutil.which('cursor'):
        found.append('cursor')
    if shutil.which('aider'):
        found.append('aider')
    if (target / '.windsurfrules').exists() or shutil.which('windsurf'):
        found.append('windsurf')
    return found


def install_tool(tool: str, target: Path) -> bool:
    if tool not in VALID_TOOLS:
        err(f'Unknown tool: {tool}')
        if tool == 'claude':
            err('  Did you mean: claude-code?')
        return False

    src = INTEGRATIONS / tool
    if not src.is_dir():
        err(f'Integration package not found: {src}')
        err(f'Run first: orquestrum convert --tool {tool}')
        return False

    abs_target = target.expanduser().resolve()
    log(f'Installing {tool} → {abs_target}')
    abs_target.mkdir(parents=True, exist_ok=True)

    # Special handling: claude-code settings.json — merge instead of overwrite
    if tool == 'claude-code':
        template_settings = src / '.claude' / 'settings.json'
        target_settings   = abs_target / '.claude' / 'settings.json'
        target_settings.parent.mkdir(parents=True, exist_ok=True)
        # Copy everything else first
        shutil.copytree(src, abs_target, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns('settings.json'))
        # Then merge settings.json
        if template_settings.exists():
            _merge_claude_settings(template_settings, target_settings)
    else:
        shutil.copytree(src, abs_target, dirs_exist_ok=True)

    # Make any bundled shell scripts executable
    scripts_dir = abs_target / 'scripts'
    if scripts_dir.is_dir():
        for sh in scripts_dir.glob('*.sh'):
            sh.chmod(sh.stat().st_mode | 0o111)

    # Hook scripts (claude-code) need execute bit too
    sdd_hooks = abs_target / '.sdd' / 'scripts' / 'hooks'
    if sdd_hooks.is_dir():
        for py in sdd_hooks.glob('*.py'):
            py.chmod(py.stat().st_mode | 0o111)

    # OpenCode: resolve __OPENCODE_ROOT__ placeholder
    if tool == 'opencode':
        for md in abs_target.rglob('*.md'):
            try:
                content = md.read_text(encoding='utf-8')
                if '__OPENCODE_ROOT__' in content:
                    md.write_text(
                        content.replace('__OPENCODE_ROOT__', str(abs_target)),
                        encoding='utf-8',
                    )
            except (OSError, UnicodeDecodeError):
                pass

    ok(f'{tool} installed into {abs_target}')
    return True


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog='orquestrum install',
        description='Install a generated integration package into a target project.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            'Examples:\n'
            '  orquestrum install --tool claude-code --target /path/to/project\n'
            '  orquestrum install --tool opencode --target ~/.config/opencode\n'
            '  orquestrum install --auto --target /path/to/project'
        ),
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--tool', metavar='TOOL',
                       help='Tool to install (claude-code | opencode | cursor | aider | windsurf)')
    group.add_argument('--auto', action='store_true',
                       help='Auto-detect installed tools and install all')
    parser.add_argument('--target', required=True, metavar='PATH',
                        help='Target directory (project root or tool config dir)')
    args = parser.parse_args(argv)

    target = Path(args.target).expanduser()
    if not target.exists():
        err(f'Target directory does not exist: {target}')
        sys.exit(1)

    print()

    if args.auto:
        tools = detect_tools(target)
        if not tools:
            warn(f'No supported tools detected in {target}')
            warn('Install one of: claude-code, opencode, cursor, aider, windsurf')
            sys.exit(1)
        log(f'Detected tools: {", ".join(tools)}')
        print()
        total = len(tools)
        for idx, tool in enumerate(tools, 1):
            if total > 1:
                print(f'\033[1m[{idx}/{total}] {tool}\033[0m')
            if not install_tool(tool, target):
                sys.exit(1)
    else:
        if not install_tool(args.tool, target):
            sys.exit(1)

    print()


if __name__ == '__main__':
    main()
