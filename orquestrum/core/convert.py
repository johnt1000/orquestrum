#!/usr/bin/env python3
"""convert.py — generates integrations/<tool>/ from canonical source.

Usage:
    orquestrum convert --tool <tool>
    orquestrum convert --all
    orquestrum convert --tool claude-code --provider claude

    Tools:     claude-code, opencode, cursor, aider, windsurf
    Providers: claude (default for claude-code), copilot, glm
"""
import argparse
import re
import shutil
import sys
from abc import ABC, abstractmethod
from pathlib import Path

from orquestrum.lib.log import log, ok, warn, err, set_prefix
from orquestrum.lib.models import (
    VALID_PROVIDERS, VALID_TOOLS, PROVIDER_MODELS,
    CANONICAL_MODELS, HELM_NAME, ORCHESTRATOR_NAMES,
    AGENT_TIERS, resolve_model, apply_provider_models, tier_collapse,
    estimate_cost,
)
from orquestrum.lib.frontmatter import parse_agent, parse_skill, AgentConfig
from orquestrum.lib.rewrite import rewrite_paths, name_to_kebab

set_prefix('convert')

# These are resolved once at the start of main() via _init_paths().
# They remain None only when the module is imported without calling main
# (e.g. from tests or init_impl) — callers that need the actual paths
# must go through main().
ROOT:         Path | None = None
INTEGRATIONS: Path | None = None
AGENTS_DIR:   Path | None = None
SKILLS_DIR:   Path | None = None
DOCS_DIR:     Path | None = None
CORE_DIR:     Path | None = None
LIB_DIR:      Path | None = None
BUNDLE_DIR:   Path | None = None


def _init_paths() -> None:
    """Resolve source + output paths. Called once at the top of main().

    SOURCE (canonical SDD content) comes from the dev repo when available,
    otherwise from the wheel-bundled `_assets/` tree — never None.

    OUT (generated `integrations/<tool>/`) defaults to the dev repo's
    `integrations/` in dev mode and `~/.orquestrum/cache/integrations/`
    in wheel mode. Override via `$ORQUESTRUM_CACHE`.

    CORE_DIR/LIB_DIR are always satisfied from the installed `orquestrum`
    package itself — they live next to this file.
    """
    global ROOT, INTEGRATIONS, AGENTS_DIR, SKILLS_DIR, DOCS_DIR, CORE_DIR, LIB_DIR, BUNDLE_DIR
    from orquestrum.lib.paths import canonical_assets_root, convert_output_root
    import orquestrum

    source = canonical_assets_root()
    out    = convert_output_root()

    ROOT         = source
    INTEGRATIONS = out
    AGENTS_DIR   = source / 'agents'
    SKILLS_DIR   = source / 'skills'
    DOCS_DIR     = source / 'docs'
    BUNDLE_DIR   = source / 'bundle'

    # Hooks + lib are part of the Python package, not the SDD content tree —
    # always available regardless of dev/wheel mode.
    pkg_root     = Path(orquestrum.__file__).resolve().parent
    CORE_DIR     = pkg_root / 'core'
    LIB_DIR      = pkg_root / 'lib'

    _maybe_invalidate_cache(out)


def _maybe_invalidate_cache(out: Path) -> None:
    """If the cache is stamped for a different orquestrum version, wipe it.

    Avoids silent staleness after `uv tool upgrade orquestrum`. Only fires
    in user/cache mode — dev mode's `<repo>/integrations/` is the working
    directory of the contributor and must never be auto-deleted.
    """
    from orquestrum.lib.paths import is_dev_mode
    if is_dev_mode():
        return
    from orquestrum import __version__
    stamp = out / '.version'
    if out.exists() and stamp.exists():
        try:
            existing = stamp.read_text(encoding='utf-8').strip()
        except OSError:
            existing = ''
        if existing == __version__:
            return
        # Version mismatch — start fresh.
        shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True, exist_ok=True)
    try:
        stamp.write_text(__version__ + '\n', encoding='utf-8')
    except OSError:
        pass

# Settings.json template for Claude Code: metrics hook + MCP server.
# Hooks remain the canonical source of token counts (Claude Code's API
# counters are authoritative). The orquestrum MCP server adds rich domain
# events + real-time queries that the hook cannot capture.
_CLAUDE_SETTINGS_TEMPLATE = '''{
  "hooks": {
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "uv run .claude/sdd/scripts/hooks/emit_metrics.py"
          }
        ]
      }
    ],
    "SubagentStop": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "uv run .claude/sdd/scripts/hooks/emit_metrics.py"
          }
        ]
      }
    ]
  },
  "mcpServers": {
    "orquestrum": {
      "command": "orquestrum",
      "args": ["mcp"],
      "type": "stdio"
    }
  }
}
'''


# ─── Adapters ─────────────────────────────────────────────────────────────────

_CACHE_MARKER_RE = re.compile(
    r'<!--\s*/?cache:(?:stable|volatile)\s*-->\n?',
    re.IGNORECASE,
)


def _yaml_quote(value: str) -> str:
    """Quote a YAML scalar so colons / quotes / hashes don't break parsing.

    Always uses double quotes; escapes embedded double-quotes and backslashes.
    """
    if not isinstance(value, str):
        return str(value)
    escaped = value.replace('\\', '\\\\').replace('"', '\\"')
    return f'"{escaped}"'


class ToolAdapter(ABC):
    docs_prefix:   str
    skills_prefix: str

    @abstractmethod
    def convert(self, provider: str | None) -> None: ...

    def _apply(self, body: str, provider: str | None) -> str:
        body = self._segment_for_cache(body)
        return apply_provider_models(rewrite_paths(body, self.docs_prefix, self.skills_prefix), provider)

    def _segment_for_cache(self, body: str) -> str:
        """Default: strip cache:stable/cache:volatile markers (no segmented cache).

        Adapters that support segmented prompt caching (e.g. native cache_control
        injection) override this to emit per-segment directives. See
        docs/agent-context/CONVENTIONS.md → Cache Segmentation Markers.
        """
        return _CACHE_MARKER_RE.sub('', body)

    def _check_canonical(self, content: str, filename: str, provider: str | None) -> None:
        if not provider:
            return
        import re
        for canonical in CANONICAL_MODELS:
            if re.search(rf'^model:\s+{re.escape(canonical)}\s*$', content, re.MULTILINE):
                warn(f'{filename}: model field is bare canonical \'{canonical}\' — provider={provider} may be incomplete')


class ClaudeCodeAdapter(ToolAdapter):
    # Everything orquestrum installs lives under .claude/ for total isolation
    # — opencode-style. Hook scripts and governance docs go to .claude/sdd/
    # so a single `rm -rf ~/.claude` (or scoped uninstall) reclaims it cleanly.
    docs_prefix   = '.claude/sdd/docs'
    # Skills go where Claude Code looks: ~/.claude/skills/ or
    # <project>/.claude/skills/. The .sdd/ prefix was OpenCode-style and
    # made Claude Code's /skills + auto-discovery blind to them.
    skills_prefix = '.claude/skills'

    # Map orquestrum tiers → Claude Code model aliases. Aliases (opus/sonnet/
    # haiku) are guaranteed-stable across Claude Code versions; full IDs
    # (claude-opus-4-7) work in current versions but have been observed to
    # fail-silently with "0 tool uses · 0 tokens · 1s" on certain plan
    # configurations. Aliases sidestep that entirely.
    _CLAUDE_TIER_ALIAS = {
        'deep':       'opus',
        'sharp':      'sonnet',   # collapsed (no intermediate Claude model)
        'balanced':   'sonnet',
        'mechanical': 'haiku',
    }

    # Per-agent tools allowlist for Claude Code subagents.
    # Without `tools:`, the subagent inherits ALL tools, including Edit/Bash/
    # Glob/Grep — which has been observed to trigger overreach (orchestrator
    # editing user settings.json mid-task). Omitting an entry here means
    # "no restriction" (all tools available); list it to constrain.
    #
    # Helm and Flux are pure coordinators: they classify, route via Task,
    # read CHECKPOINT.md and write it back. They have no business writing
    # to project files, running shell commands, or scanning code with grep.
    #
    # The mcp__orquestrum__orq_* entries grant access to the READ-ONLY tools
    # of the orquestrum MCP server (session_summary, budget_status, etc.).
    # Write MCP tools (orq_record_event, orq_skill_completed) are
    # intentionally excluded — coordinators don't author metric events;
    # the executors (Forge/Ward/etc., which have no allowlist) do.
    _CLAUDE_TOOLS_ALLOWLIST = {
        'Helm - The Architect': (
            'Task, Read, Write, '
            'mcp__orquestrum__orq_session_summary, '
            'mcp__orquestrum__orq_budget_status, '
            'mcp__orquestrum__orq_recent_events, '
            'mcp__orquestrum__orq_list_projects, '
            'mcp__orquestrum__orq_project_summary, '
            'mcp__orquestrum__orq_cost_today'
        ),
        'Flux - Support Lead': (
            'Task, Read, Grep, Glob, '
            'mcp__orquestrum__orq_session_summary, '
            'mcp__orquestrum__orq_recent_events, '
            'mcp__orquestrum__orq_list_projects, '
            'mcp__orquestrum__orq_cost_today'
        ),
    }

    def _frontmatter(self, agent: AgentConfig, provider: str | None) -> str:
        # Claude Code recognises only `name`, `description`, `model`, and
        # `tools` in subagent frontmatter. Custom fields like `temperature`,
        # `maxTokens`, `disallowedTools` are NOT honoured and have been
        # observed to confuse the picker / cause unrelated agent overreach
        # (e.g. a status-query agent suddenly editing settings.json). We
        # emit only the standard fields and let Claude Code's defaults apply.
        from orquestrum.lib.models import AGENT_TIERS
        tier = agent.model_tier_override or AGENT_TIERS.get(agent.name, 'balanced')
        model = self._CLAUDE_TIER_ALIAS.get(tier, 'sonnet')
        lines = ['---',
                 f'name: {_yaml_quote(agent.name)}',
                 f'description: {_yaml_quote(agent.description)}',
                 f'model: {model}']
        tools_allowed = self._CLAUDE_TOOLS_ALLOWLIST.get(agent.name)
        if tools_allowed:
            lines.append(f'tools: {tools_allowed}')
        lines.append('---\n')
        return '\n'.join(lines) + '\n'

    def convert(self, provider: str | None) -> None:
        out = INTEGRATIONS / 'claude-code'
        shutil.rmtree(out, ignore_errors=True)
        # All orquestrum content under .claude/ for total isolation:
        #   .claude/agents/       (subagents — Claude Code shift+tab + /agents)
        #   .claude/skills/       (skills — Claude Code /skills + auto-load)
        #   .claude/settings.json (hooks merged into existing user settings)
        #   .claude/sdd/docs/     (orquestrum governance docs, agent refs)
        #   .claude/sdd/scripts/  (metrics hook + lib)
        agents_out = out / '.claude' / 'agents'
        skills_out = out / '.claude' / 'skills'
        sdd_root   = out / '.claude' / 'sdd'
        agents_out.mkdir(parents=True)
        skills_out.mkdir(parents=True)
        (sdd_root / 'scripts').mkdir(parents=True)

        for agent_file in sorted(AGENTS_DIR.glob('*.md')):
            agent = parse_agent(agent_file)
            slug  = name_to_kebab(agent.name)
            content = self._frontmatter(agent, provider) + self._apply(agent.body, provider)
            out_file = agents_out / f'{slug}.md'
            out_file.write_text(content, encoding='utf-8')
            self._check_canonical(content, out_file.name, provider)

        shutil.copytree(DOCS_DIR, sdd_root / 'docs', dirs_exist_ok=True)
        shutil.copytree(SKILLS_DIR, skills_out, dirs_exist_ok=True)
        for bak in skills_out.rglob('*.bak'):
            bak.unlink()

        # Hook + lib copy: metrics hook needs orquestrum/lib/models for estimate_cost
        shutil.copytree(CORE_DIR / 'hooks', sdd_root / 'scripts' / 'hooks', dirs_exist_ok=True)
        shutil.copytree(LIB_DIR,            sdd_root / 'scripts' / 'lib',   dirs_exist_ok=True)
        shutil.copy(BUNDLE_DIR / 'archive-cleanup.sh', sdd_root / 'scripts')

        # Claude Code settings.json template — install.py merges with user's existing
        (out / '.claude' / 'settings.json').write_text(_CLAUDE_SETTINGS_TEMPLATE, encoding='utf-8')

        ok(f'claude-code → {out}')
        print(f'    .claude/agents/        ← Claude Code subagents (shift+tab picker)')
        print(f'    .claude/skills/        ← Claude Code skills (/skills, auto-loaded)')
        print(f'    .claude/settings.json  ← merged hooks for orquestrum metrics')
        print(f'    .claude/sdd/           ← orquestrum docs + hook scripts (isolated)')


class OpenCodeAdapter(ToolAdapter):
    docs_prefix   = '__OPENCODE_ROOT__/docs'
    skills_prefix = '__OPENCODE_ROOT__/skills'

    def _frontmatter(self, agent: AgentConfig, provider: str | None) -> str:
        model_line = ''
        if provider:
            model = resolve_model(agent.name, provider, agent.model_tier_override)
            model_line = f'model: {model}\n'
        max_tokens_line = f'maxTokens: {agent.max_tokens}\n' if agent.max_tokens is not None else ''
        bash_perm = 'allow' if agent.bash else 'deny'
        if agent.name == HELM_NAME:
            task = '    "*": deny\n' + ''.join(f'    "{o}": allow\n' for o in ORCHESTRATOR_NAMES)
        else:
            task = '    "*": allow\n'
        return (
            f'---\nname: {_yaml_quote(agent.name)}\ndescription: {_yaml_quote(agent.description)}\n'
            f'mode: primary\n{model_line}temperature: {agent.temperature}\n'
            f'{max_tokens_line}'
            f'emoji: {agent.emoji}\npermission:\n  edit: allow\n'
            f'  bash: {bash_perm}\n  task:\n{task}---\n\n'
        )

    def convert(self, provider: str | None) -> None:
        out = INTEGRATIONS / 'opencode'
        shutil.rmtree(out, ignore_errors=True)
        (out / 'agents').mkdir(parents=True)
        (out / 'docs').mkdir(parents=True)
        (out / 'skills').mkdir(parents=True)
        (out / 'scripts').mkdir(parents=True)

        for agent_file in sorted(AGENTS_DIR.glob('*.md')):
            agent = parse_agent(agent_file)
            slug  = name_to_kebab(agent.name)
            content = self._frontmatter(agent, provider) + self._apply(agent.body, provider)
            out_file = out / 'agents' / f'{slug}.md'
            out_file.write_text(content, encoding='utf-8')
            self._check_canonical(content, out_file.name, provider)

        # docs/ has subdirectories now (agent-context, governance, baselines)
        shutil.copytree(DOCS_DIR, out / 'docs', dirs_exist_ok=True)
        shutil.copytree(SKILLS_DIR, out / 'skills', dirs_exist_ok=True)
        for bak in (out / 'skills').rglob('*.bak'):
            bak.unlink()

        # Rewrite governance paths in all skill files
        for md in (out / 'skills').rglob('*.md'):
            text = md.read_text(encoding='utf-8')
            rewritten = rewrite_paths(text, self.docs_prefix, self.skills_prefix)
            if rewritten != text:
                md.write_text(rewritten, encoding='utf-8')

        shutil.copy(BUNDLE_DIR / 'archive-cleanup.sh', out / 'scripts')

        ok(f'opencode → {out}')
        print(f'    Install global:   orquestrum install --tool opencode --target ~/.config/opencode')
        print(f'    Install local:    orquestrum install --tool opencode --target /your/project/.opencode')


ADAPTERS: dict[str, ToolAdapter] = {
    'claude-code': ClaudeCodeAdapter(),
    'opencode':    OpenCodeAdapter(),
}


# ─── Dry run ──────────────────────────────────────────────────────────────────

# Approximate session shapes (tier → (avg input, avg output) per LLM call) and
# call counts. Source: docs/agent-context/TIERS.md (~2 / ~5 / ~13 calls per tier).
# Conservative; prefer over-estimation for budgeting.
SESSION_SHAPES: dict[str, dict] = {
    'tier-0': {
        'calls':  [('mechanical', 2, 1500, 400)],   # 2 mechanical calls
        'label':  'Tier 0 — Micro (typo, config, single-file edit)',
    },
    'tier-1': {
        'calls':  [('balanced', 5, 1800, 500)],
        'label':  'Tier 1 — Standard (epic + tasks + QA)',
    },
    'tier-2': {
        'calls':  [
            ('deep',       2, 4500, 1200),    # spec + adr (heavy reasoning)
            ('balanced',   9, 2200, 600),     # architecture, epic, task, review, qa, learning, etc.
            ('mechanical', 2, 1500, 400),     # changelog, runbook
        ],
        'label':  'Tier 2 — Full pipeline (greenfield feature)',
    },
}


def _session_cost(provider: str, shape: dict) -> tuple[int, int, float]:
    """Return (total_in_tokens, total_out_tokens, total_cost_usd) for one session shape."""
    total_in = 0
    total_out = 0
    total_cost = 0.0
    for tier, calls, in_per_call, out_per_call in shape['calls']:
        model = PROVIDER_MODELS[provider][tier]
        in_t  = calls * in_per_call
        out_t = calls * out_per_call
        total_in  += in_t
        total_out += out_t
        total_cost += estimate_cost(model, in_t, out_t)
    return total_in, total_out, round(total_cost, 4)


def _count_canonical_inventory() -> dict:
    agents = [parse_agent(f) for f in sorted(AGENTS_DIR.glob('*.md'))]
    skills = []
    for d in sorted(SKILLS_DIR.iterdir()):
        if d.is_dir() and (d / 'SKILL.md').exists():
            skills.append(parse_skill(d / 'SKILL.md'))
    docs_count = sum(1 for _ in DOCS_DIR.rglob('*.md'))
    return {
        'agents':           agents,
        'skills':           skills,
        'docs_count':       docs_count,
        'agent_total_b':    sum(len(a.body.encode('utf-8')) for a in agents),
        'skill_total_b':    sum(len(s.body.encode('utf-8')) for s in skills),
    }


def _count_cache_markers() -> int:
    pattern = re.compile(r'<!--\s*/?cache:(?:stable|volatile)\s*-->', re.IGNORECASE)
    total = 0
    for f in list(AGENTS_DIR.rglob('*.md')) + list(SKILLS_DIR.rglob('*.md')) + list(DOCS_DIR.rglob('*.md')):
        try:
            total += len(pattern.findall(f.read_text(encoding='utf-8')))
        except OSError:
            continue
    return total


def dry_run_report(tools: list[str], provider: str | None) -> None:
    inv = _count_canonical_inventory()

    print(f'{"─" * 72}')
    print(f'  Orquestrum — convert dry-run')
    print(f'{"─" * 72}')
    print(f'  Canonical inventory')
    print(f'    agents:      {len(inv["agents"])} ({inv["agent_total_b"]:,} bytes total)')
    print(f'    skills:      {len(inv["skills"])} ({inv["skill_total_b"]:,} bytes total)')
    print(f'    docs:        {inv["docs_count"]} files under docs/')
    print(f'    cache markers: {_count_cache_markers()}')
    print()

    if provider:
        print(f'  Provider: {provider}')
        for tier in ('deep', 'sharp', 'balanced', 'mechanical'):
            print(f'    {tier:11}: {PROVIDER_MODELS[provider][tier]}')
        collapses = [(n, t, tier_collapse(provider, t)) for n, t in AGENT_TIERS.items()
                     if tier_collapse(provider, t)]
        if collapses:
            print()
            print(f'  ⚠ Tier collapses on \'{provider}\':')
            for name, tier, to in collapses:
                print(f'    {name}: {tier!r} → {to!r}')
        print()
        print(f'  Projected session cost (provider={provider}):')
        print(f'    {"Tier":<8} {"Calls":>5}  {"Input tk":>10}  {"Output tk":>10}  {"USD":>8}  Description')
        print(f'    {"-"*8} {"-"*5}  {"-"*10}  {"-"*10}  {"-"*8}  {"-"*40}')
        for key in ('tier-0', 'tier-1', 'tier-2'):
            shape = SESSION_SHAPES[key]
            in_t, out_t, cost = _session_cost(provider, shape)
            calls = sum(c[1] for c in shape['calls'])
            print(f'    {key:<8} {calls:>5}  {in_t:>10,}  {out_t:>10,}  ${cost:>7.4f}  {shape["label"]}')
        print()
    else:
        print('  Provider: not set — costs not computed (use --provider claude|copilot|glm to project)')
        print()

    print(f'  Tools to generate: {", ".join(tools)}')
    print(f'  → would write to: {INTEGRATIONS}/{{{",".join(tools)}}}/')
    print(f'  → no files written (dry-run)')
    print(f'{"─" * 72}')


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> None:
    _init_paths()
    parser = argparse.ArgumentParser(
        prog='orquestrum convert',
        description='Generate integration packages from canonical source.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            'Tools:     claude-code, opencode, cursor, aider, windsurf\n'
            'Providers: claude (default for claude-code), copilot, glm\n'
            '\n'
            'Examples:\n'
            '  orquestrum convert --all\n'
            '  orquestrum convert --tool opencode --provider claude\n'
            '  orquestrum convert --all --provider claude --dry-run'
        ),
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--tool', choices=list(ADAPTERS), metavar='TOOL',
                       help='Single tool to generate')
    group.add_argument('--all', action='store_true', help='Generate all tools')
    parser.add_argument('--provider', choices=list(VALID_PROVIDERS), metavar='PROVIDER',
                        help='Model provider (claude | copilot | glm)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Print summary (inventory, cost projection, tier collapses) without writing files')
    args = parser.parse_args(argv)

    provider = args.provider or None
    tools = list(ADAPTERS) if args.all else [args.tool]

    if args.dry_run:
        dry_run_report(tools, provider)
        return

    if provider:
        log(f'Provider: {provider}')
        models = PROVIDER_MODELS[provider]
        log(f'  deep:       {models["deep"]}')
        log(f'  sharp:      {models["sharp"]}')
        log(f'  balanced:   {models["balanced"]}')
        log(f'  mechanical: {models["mechanical"]}')

        collapses = []
        for agent_name, tier in AGENT_TIERS.items():
            collapsed_to = tier_collapse(provider, tier)
            if collapsed_to:
                collapses.append((agent_name, tier, collapsed_to))
        if collapses:
            warn(f'Tier collapse for provider \'{provider}\' — these agents run on a lower tier than declared:')
            for agent_name, tier, target in collapses:
                target_model = PROVIDER_MODELS[provider][target]
                warn(f'  {agent_name}: \'{tier}\' → \'{target}\' ({target_model})')
            warn('See docs/governance/MODELS.md → Provider Parity Caveats for rationale.')
    else:
        log('Provider: none (model not set — user chooses at runtime; claude-code defaults to claude)')

    # Friendly preflight banner — tells the user where reads come from and
    # where output is going BEFORE we start writing files.
    from orquestrum.lib.paths import is_dev_mode
    source_label = 'dev repo' if is_dev_mode() else 'bundled (wheel)'
    log(f'Source: {source_label} — {ROOT}')
    log(f'Output: {INTEGRATIONS}')
    print()

    total = len(tools)
    skill_count = sum(1 for d in SKILLS_DIR.iterdir()
                      if d.is_dir() and (d / 'SKILL.md').exists())

    from orquestrum.lib.verify import (
        verify_convert_output, render_summary, render_listing, VerifyReport,
    )
    reports: list[VerifyReport] = []

    for idx, tool in enumerate(tools, 1):
        if total > 1:
            print(f'\033[1m[{idx}/{total}] {tool}\033[0m')
        ADAPTERS[tool].convert(provider)

        # Verify the tool's output before moving on. A failed verification
        # surfaces immediately so users see the specific check that failed
        # rather than a "works on my machine" surprise later.
        report = verify_convert_output(tool, INTEGRATIONS / tool,
                                       expected_skill_count=skill_count)
        print(report.render())
        # Show what's actually on disk — particularly important for tools
        # whose integration consists entirely of dot-dirs (claude-code, cursor)
        # which a plain `ls` won't surface.
        print(render_listing(INTEGRATIONS / tool))
        reports.append(report)
        print()

    # Aggregate summary — one line per tool
    print(render_summary(reports))

    failed = [r for r in reports if not r.passed]
    if failed:
        err(f'{len(failed)} tool(s) failed verification — output may be incomplete.')
        sys.exit(1)

    if args.all:
        ok(f'All {total} integrations generated and verified in {INTEGRATIONS}')

    # In wheel/cache mode the user almost always wants `orquestrum install`
    # next — point the way.
    if not is_dev_mode():
        print()
        print(f'  Cached at {INTEGRATIONS}')
        if len(tools) == 1:
            print(f'  Next: orquestrum install --tool {tools[0]} --target /your/project')
        else:
            print(f'  Next: orquestrum install --tool <tool> --target /your/project')


if __name__ == '__main__':
    main()
