"""catalog_loader.py — load agent + skill catalog from canonical source.

Reusable in both framework mode (the Orquestrum repo) and project mode
(read installed agents under .claude/agents/ or .opencode/agents/).
"""
from __future__ import annotations
import sys
from dataclasses import dataclass
from pathlib import Path

# Reuse the canonical parsers from scripts/lib/
_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_ROOT / 'scripts'))

try:
    from lib.frontmatter import parse_agent, parse_skill, AgentConfig, SkillConfig
    from lib.models import AGENT_TIERS
except ImportError:
    parse_agent = parse_skill = None
    AGENT_TIERS = {}


@dataclass(frozen=True)
class AgentRow:
    name:        str
    slug:        str
    description: str
    tier:        str
    max_tokens:  int | None
    temperature: float
    bash:        bool
    body_path:   Path


@dataclass(frozen=True)
class SkillRow:
    name:             str
    slug:             str
    description:      str
    inject_refs:      str
    inject_fewshot:   str
    chain_next:       str | None
    depends_on:       list[str]
    emits_confidence: bool
    body_path:        Path


def _slug_from_name(name: str) -> str:
    import re
    s = name.lower()
    s = re.sub(r'\s*[—–-]\s*', '-', s)
    s = s.replace(' & ', '-and-').replace(' ', '-')
    s = re.sub(r'[^a-z0-9-]', '', s)
    s = re.sub(r'-{2,}', '-', s)
    return s.strip('-')


def list_agents(agents_dir: Path) -> list[AgentRow]:
    if parse_agent is None or not agents_dir.is_dir():
        return []
    out: list[AgentRow] = []
    for f in sorted(agents_dir.glob('*.md')):
        try:
            cfg = parse_agent(f)
        except Exception:
            continue
        out.append(AgentRow(
            name=cfg.name,
            slug=_slug_from_name(cfg.name),
            description=cfg.description,
            tier=AGENT_TIERS.get(cfg.name, '?'),
            max_tokens=cfg.max_tokens,
            temperature=cfg.temperature,
            bash=cfg.bash,
            body_path=f,
        ))
    return out


def list_skills(skills_dir: Path) -> list[SkillRow]:
    if parse_skill is None or not skills_dir.is_dir():
        return []
    out: list[SkillRow] = []
    for d in sorted(skills_dir.iterdir()):
        if not d.is_dir():
            continue
        f = d / 'SKILL.md'
        if not f.exists():
            continue
        try:
            cfg = parse_skill(f)
        except Exception:
            continue
        # emits_confidence is a custom field — read raw frontmatter
        emits = False
        try:
            import frontmatter as fm
            emits = bool(fm.load(str(f)).get('emits_confidence', False))
        except Exception:
            pass
        out.append(SkillRow(
            name=cfg.name,
            slug=d.name,
            description=cfg.description,
            inject_refs=cfg.inject_refs,
            inject_fewshot=cfg.inject_fewshot,
            chain_next=cfg.chain_next,
            depends_on=cfg.depends_on,
            emits_confidence=emits,
            body_path=f,
        ))
    return out
