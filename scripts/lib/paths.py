import re
from pathlib import Path


def name_to_kebab(name: str) -> str:
    """'Helm - The Architect' → 'helm-the-architect'"""
    s = name.lower()
    s = re.sub(r'\s*[—–-]\s*', '-', s)   # em-dash, en-dash, hyphen with optional spaces
    s = s.replace(' & ', '-and-').replace(' ', '-')
    s = re.sub(r'[^a-z0-9-]', '', s)
    s = re.sub(r'-{2,}', '-', s)
    return s.strip('-')


_PATH_PATTERNS: list[tuple[str, str]] = [
    (r'docs/SDLC\.md',              '{docs}/SDLC.md'),
    (r'docs/TIERS\.md',             '{docs}/TIERS.md'),
    (r'docs/MODELS\.md',            '{docs}/MODELS.md'),
    (r'docs/CONVENTIONS\.md',       '{docs}/CONVENTIONS.md'),
    (r'skills/([a-zA-Z_-]+)/SKILL\.md',      '{skills}/\\1/SKILL.md'),
    (r'skills/([a-zA-Z_-]+)/references/',    '{skills}/\\1/references/'),
    (r'skills/([a-zA-Z_-]+)/assets/',        '{skills}/\\1/assets/'),
]


def rewrite_paths(content: str, docs_prefix: str, skills_prefix: str) -> str:
    for pattern, template in _PATH_PATTERNS:
        repl = template.replace('{docs}', docs_prefix).replace('{skills}', skills_prefix)
        content = re.sub(pattern, repl, content)
    return content


def extract_inject_blocks(content: str) -> str:
    """Extract only content between <!-- inject:start --> and <!-- inject:end --> markers."""
    blocks: list[str] = []
    for match in re.finditer(
        r'<!--\s*inject:start\s*-->(.*?)<!--\s*inject:end\s*-->',
        content, re.DOTALL
    ):
        blocks.append(match.group(1).strip())
    return '\n\n'.join(blocks)


def skill_reference_content(skill_dir: Path) -> str:
    """Return injected reference + fewshot content for tools that can't read files at runtime."""
    from .frontmatter import parse_skill

    skill_file = skill_dir / 'SKILL.md'
    if not skill_file.exists():
        return ''

    skill = parse_skill(skill_file)
    parts: list[str] = []

    if skill.inject_refs and skill.inject_refs != 'false':
        refs_dir = skill_dir / 'references'
        ref_file = next(refs_dir.glob('*-references.md'), None) or \
                   next(refs_dir.glob('*-index.md'), None) if refs_dir.is_dir() else None
        if ref_file:
            raw = ref_file.read_text(encoding='utf-8')
            content = extract_inject_blocks(raw) if skill.inject_refs == 'compact' else raw
            parts.append('\n---\n\n## Reference Knowledge\n\n' + content)

    if skill.inject_fewshot and skill.inject_fewshot != 'false':
        refs_dir = skill_dir / 'references'
        fs_file = next(refs_dir.glob('*-fewshot.md'), None) if refs_dir.is_dir() else None
        if fs_file:
            raw = fs_file.read_text(encoding='utf-8')
            content = extract_inject_blocks(raw) if skill.inject_fewshot == 'compact' else raw
            parts.append('\n---\n\n## Examples\n\n' + content)

    return ''.join(parts)
