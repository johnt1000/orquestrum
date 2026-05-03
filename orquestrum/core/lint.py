#!/usr/bin/env python3
"""lint.py — validates agent and skill files.

Checks:
  - YAML frontmatter present
  - Required fields: name, description
  - Agents: mode, temperature, max_tokens, emoji, tools.{write,edit,bash,question}
  - max_tokens must be a positive int ≤ 16384 (output cap; runaway-generation guard)
  - No tool-specific paths in canonical source
  - chain.next points to existing skill
  - depends_on entries exist
  - inject_references / inject_fewshot ∈ {false, true, compact}
  - emits_confidence (when present) must be boolean
  - REGISTRY.md consistency
  - docs/ structure: no .md files at root; only under agent-context/, governance/, baselines/
"""
import sys
from pathlib import Path

from orquestrum.lib.log import ok, warn, err
from orquestrum.lib.frontmatter import parse_agent, parse_skill
from orquestrum.lib.paths import canonical_assets_root

# Read canonical SDD content from the dev repo (when available) or the
# wheel-bundled `_assets/` tree. lint never writes anything, so it works
# identically in both modes.
ROOT       = canonical_assets_root()
AGENTS_DIR = ROOT / 'agents'
SKILLS_DIR = ROOT / 'skills'
DOCS_DIR   = ROOT / 'docs'

DOCS_ALLOWED_SUBDIRS = {'agent-context', 'governance', 'baselines'}

RED    = '\033[0;31m'
GREEN  = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE   = '\033[0;34m'
NC     = '\033[0m'

errors   = 0
warnings = 0

TOOL_PATHS = ['.opencode/', '.sdd/']


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


MAX_TOKENS_CEILING = 16384


def check_agent_file(path: Path) -> None:
    label = str(path.relative_to(ROOT))

    if not check_md_file(path, ['name', 'description']):
        return

    import frontmatter as fm
    post = fm.load(str(path))

    for field in ('mode', 'temperature', 'emoji'):
        if field not in post:
            fail(f'{label} — missing frontmatter field: \'{field}\'')

    if 'max_tokens' not in post:
        fail(f'{label} — missing required field \'max_tokens\' (see docs/governance/MODELS.md → Output Cap)')
    else:
        mt = post.get('max_tokens')
        if not isinstance(mt, int) or isinstance(mt, bool) or mt <= 0 or mt > MAX_TOKENS_CEILING:
            fail(f'{label} — max_tokens must be a positive int ≤ {MAX_TOKENS_CEILING}, got {mt!r}')

    tools = post.get('tools') or {}
    for key in ('write', 'edit', 'bash', 'question'):
        if key not in tools:
            fail(f'{label} — missing tools.{key} in frontmatter')


VALID_INJECT_VALUES = {'false', 'full', 'compact'}


def check_skill_fields(path: Path) -> None:
    """Validate skill frontmatter fields beyond name/description."""
    label = str(path.relative_to(ROOT))
    import frontmatter as fm
    try:
        post = fm.load(str(path))
    except Exception:
        return  # already reported by check_md_file

    for field in ('inject_references', 'inject_fewshot'):
        if field in post:
            normalized = str(post[field]).lower()
            if normalized not in VALID_INJECT_VALUES:
                fail(f'{label} — {field} must be one of {sorted(VALID_INJECT_VALUES)}, '
                     f'got {post[field]!r}')

    if 'emits_confidence' in post:
        if not isinstance(post['emits_confidence'], bool):
            fail(f'{label} — emits_confidence must be true|false, got {post["emits_confidence"]!r}')


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


def check_docs_structure() -> None:
    """Reject .md files at docs/ root. Force categorization under
    agent-context/, governance/, or baselines/.
    """
    if not DOCS_DIR.is_dir():
        return
    for entry in sorted(DOCS_DIR.iterdir()):
        if entry.is_file() and entry.suffix == '.md':
            fail(f'docs/{entry.name} — forbidden at docs/ root; '
                 f'place under one of: {sorted(DOCS_ALLOWED_SUBDIRS)}')
        elif entry.is_dir() and entry.name not in DOCS_ALLOWED_SUBDIRS:
            warn_(f'docs/{entry.name}/ — unknown subdirectory '
                  f'(expected: {sorted(DOCS_ALLOWED_SUBDIRS)})')
    pass_('docs/ structure checked')


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


def main(argv: list[str] | None = None) -> None:
    global errors, warnings
    # lint.py takes no flags today; argv accepted for CLI wrapper symmetry
    if argv is not None and argv:
        import argparse
        argparse.ArgumentParser(prog='orquestrum lint',
                                description='Validate agent and skill files.').parse_args(argv)

    n_agents = n_skills = n_assets = 0

    print()
    print(f'{BLUE}=== Agents ==={NC}')
    for f in sorted(AGENTS_DIR.glob('*.md')):
        check_agent_file(f)
        n_agents += 1

    print()
    print(f'{BLUE}=== Skills ==={NC}')
    for f in sorted(SKILLS_DIR.glob('*/SKILL.md')):
        if check_md_file(f, ['name', 'description']):
            check_skill_fields(f)
        n_skills += 1

    print()
    print(f'{BLUE}=== Skill assets ==={NC}')
    for f in sorted(SKILLS_DIR.glob('*/assets/*.md')):
        check_md_file(f)
        n_assets += 1

    print()
    print(f'{BLUE}=== Skill chain & dependency integrity ==={NC}')
    for skill_dir in sorted(SKILLS_DIR.iterdir()):
        skill_file = skill_dir / 'SKILL.md'
        if skill_file.exists():
            check_skill_chain(skill_file)

    print()
    print(f'{BLUE}=== docs/ structure ==={NC}')
    check_docs_structure()

    print()
    print(f'{BLUE}=== REGISTRY.md consistency ==={NC}')
    check_registry()

    print()
    counts = f'{n_agents} agents, {n_skills} skills, {n_assets} assets'
    if errors > 0:
        suffix = f', {warnings} warning(s)' if warnings > 0 else ''
        print(f'{RED}✗ {errors} error(s){NC} in {counts}{suffix}')
        sys.exit(1)
    else:
        suffix = f', {warnings} warning(s)' if warnings > 0 else ''
        print(f'{GREEN}✓ {counts}, 0 errors{NC}{suffix}')


if __name__ == '__main__':
    main()
