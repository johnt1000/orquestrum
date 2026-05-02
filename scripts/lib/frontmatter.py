from dataclasses import dataclass, field
from pathlib import Path
import frontmatter as fm


@dataclass
class AgentConfig:
    name:                str
    description:         str
    mode:                str
    temperature:         float
    emoji:               str
    bash:                bool
    write:               bool
    edit:                bool
    body:                str
    max_tokens:          int | None = None   # P1: output cap per call
    model_tier_override: str | None = None  # P3: overrides AGENT_TIERS for this agent


@dataclass
class SkillConfig:
    name:          str
    description:   str
    chain_next:    str | None
    depends_on:    list[str]
    inject_refs:   str        # "false" | "full" | "compact"
    inject_fewshot:str        # "false" | "full" | "compact"
    body:          str


def parse_agent(path: Path) -> AgentConfig:
    post = fm.load(str(path))
    tools = post.get('tools') or {}
    raw_mt = post.get('max_tokens')
    raw_ov = post.get('model_tier_override')
    return AgentConfig(
        name=post['name'],
        description=post['description'],
        mode=str(post.get('mode', 'primary')),
        temperature=float(post.get('temperature', 0.2)),
        emoji=str(post.get('emoji', '')),
        bash=bool(tools.get('bash', False)),
        write=bool(tools.get('write', True)),
        edit=bool(tools.get('edit', True)),
        body=post.content,
        max_tokens=int(raw_mt) if raw_mt is not None else None,
        model_tier_override=str(raw_ov) if raw_ov is not None else None,
    )


def parse_skill(path: Path) -> SkillConfig:
    post = fm.load(str(path))
    chain = post.get('chain') or {}
    raw_deps = post.get('depends_on')
    if isinstance(raw_deps, list):
        deps = [str(d) for d in raw_deps]
    elif isinstance(raw_deps, str):
        # Handle inline format "skill1, skill2" (legacy)
        deps = [d.strip() for d in raw_deps.split(',') if d.strip()]
    else:
        deps = []
    return SkillConfig(
        name=post['name'],
        description=post['description'],
        chain_next=chain.get('next'),
        depends_on=deps,
        # Normalize to lowercase so YAML bool `false` (→ Python 'False') matches the
        # 'false' literal used downstream in paths.py / convert.py / audit.
        inject_refs=str(post.get('inject_references', 'false')).lower(),
        inject_fewshot=str(post.get('inject_fewshot', 'false')).lower(),
        body=post.content,
    )
