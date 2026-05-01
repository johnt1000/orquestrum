#!/usr/bin/env python3
"""lint.py — validates agent and skill files.

Checks:
  - YAML frontmatter present
  - Required fields: name, description
  - Agents: mode, temperature, emoji, tools.{write,edit,bash,question}
  - No tool-specific paths in canonical source
  - chain.next points to existing skill
  - depends_on entries exist
  - REGISTRY.md consistency
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from lib.log import ok, warn, err
from lib.frontmatter import parse_agent, parse_skill

ROOT       = Path(__file__).parent.parent
AGENTS_DIR = ROOT / 'agents'
SKILLS_DIR = ROOT / 'skills'

RED    = '\033[0;31m'
GREEN  = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE   = '\033[0;34m'
NC     = '\033[0m'

errors   = 0
warnings = 0

TOOL_PATHS = ['.opencode/', '.cursor/rules/', '.windsurfrules', '.sdd/']


def fail(msg: str) -> None:
    global errors
    print(f'  {RED}✗{NC} {msg}')
    errors += 1

def warn_(msg: str) -> None:
    global warnings
    print(f'  {YELLOW}!{NC} {msg}')
    warnings += 1

def pass_(msg: str) -> None:
    print(f'  {GREEN}✓{NC} {msg}')


def check_md_file(path: Path, required_fields: list[str] | None = None) -> bool:
    label = str(path.relative_to(ROOT))
    text  = path.read_text(encoding='utf-8')

    if required_fields:
        if not text.startswith('---'):
            fail(f'{label} — missing YAML frontmatter (no opening ---)')
            return False

    passed = True
    if required_fields:
        import frontmatter as fm
        try:
            post = fm.loads(text)
        except Exception as e:
            fail(f'{label} — YAML parse error: {e}')
            return False
        for field in required_fields:
            if field not in post:
                fail(f'{label} — missing required field: \'{field}\'')
                passed = False

    for pattern in TOOL_PATHS:
        if pattern in text:
            fail(f'{label} — contains tool-specific path \'{pattern}\' (use plain paths: docs/, skills/)')
            passed = False

    if passed:
        pass_(label)
    return passed


def check_agent_file(path: Path) -> None:
    label = str(path.relative_to(ROOT))

    if not check_md_file(path, ['name', 'description']):
        return

    import frontmatter as fm
    post = fm.load(str(path))

    for field in ('mode', 'temperature', 'emoji'):
        if field not in post:
            fail(f'{label} — missing frontmatter field: \'{field}\'')

    tools = post.get('tools') or {}
    for key in ('write', 'edit', 'bash', 'question'):
        if key not in tools:
            fail(f'{label} — missing tools.{key} in frontmatter')


def check_skill_chain(skill_file: Path) -> None:
    label = str(skill_file.relative_to(ROOT))
    try:
        skill = parse_skill(skill_file)
    except Exception as e:
        fail(f'{label} — parse error: {e}')
        return

    if skill.chain_next and not (SKILLS_DIR / skill.chain_next / 'SKILL.md').exists():
        fail(f'{label} — chain.next \'{skill.chain_next}\' does not exist in skills/')
        return

    for dep in skill.depends_on:
        if not (SKILLS_DIR / dep / 'SKILL.md').exists():
            fail(f'{label} — depends_on \'{dep}\' does not exist in skills/')
            return

    pass_(f'{label} — chain/deps OK')


def check_registry() -> None:
    registry = SKILLS_DIR / 'REGISTRY.md'
    if not registry.exists():
        warn_('skills/REGISTRY.md not found — skipping consistency check')
        return

    import re
    text = registry.read_text(encoding='utf-8')
    referenced = set(re.findall(r'`([a-z][a-z0-9-]+)`', text))

    for skill_ref in sorted(referenced):
        if not (SKILLS_DIR / skill_ref / 'SKILL.md').exists():
            warn_(f'REGISTRY.md references \'{skill_ref}\' but skills/{skill_ref}/SKILL.md not found')

    for skill_dir in sorted(SKILLS_DIR.iterdir()):
        if skill_dir.is_dir() and skill_dir.name not in referenced:
            warn_(f'skills/{skill_dir.name}/ exists but is not referenced in REGISTRY.md')

    pass_('REGISTRY.md checked')


def main() -> None:
    global errors, warnings

    print()
    print(f'{BLUE}=== Agents ==={NC}')
    for f in sorted(AGENTS_DIR.glob('*.md')):
        check_agent_file(f)

    print()
    print(f'{BLUE}=== Skills ==={NC}')
    for f in sorted(SKILLS_DIR.glob('*/SKILL.md')):
        check_md_file(f, ['name', 'description'])

    print()
    print(f'{BLUE}=== Skill assets ==={NC}')
    for f in sorted(SKILLS_DIR.glob('*/assets/*.md')):
        check_md_file(f)

    print()
    print(f'{BLUE}=== Skill chain & dependency integrity ==={NC}')
    for skill_dir in sorted(SKILLS_DIR.iterdir()):
        skill_file = skill_dir / 'SKILL.md'
        if skill_file.exists():
            check_skill_chain(skill_file)

    print()
    print(f'{BLUE}=== REGISTRY.md consistency ==={NC}')
    check_registry()

    print()
    if errors > 0:
        suffix = f', {warnings} warning(s)' if warnings > 0 else ''
        print(f'{RED}✗ {errors} error(s){NC}{suffix}')
        sys.exit(1)
    else:
        suffix = f' ({warnings} warning(s))' if warnings > 0 else ''
        print(f'{GREEN}✓ All checks passed{NC}{suffix}')


if __name__ == '__main__':
    main()
