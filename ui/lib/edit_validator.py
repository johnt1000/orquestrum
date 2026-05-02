"""edit_validator.py — preflight validation for frontmatter edits.

Mirrors the rules in scripts/lint.py:check_agent_file but operates on a dict
in-memory (no subprocess, no file I/O). Used by /agents/{slug}/edit to gate
writes BEFORE they touch disk.

Single source of truth for the rules:
  - max_tokens: required, int, 1 <= value <= 16384
  - mode, temperature, emoji: required and present
  - tools.{write, edit, bash, question}: all four required as booleans
  - name, description: required, non-empty strings
"""
from __future__ import annotations
from typing import Any


MAX_TOKENS_CEILING = 16384

VALID_MODES = {'primary', 'agent', 'subagent'}


def validate_agent_frontmatter(fm: dict[str, Any]) -> list[str]:
    """Return a list of human-readable error strings. Empty list = OK."""
    errors: list[str] = []

    for field in ('name', 'description'):
        if field not in fm:
            errors.append(f'missing required field: {field!r}')
        elif not isinstance(fm[field], str) or not fm[field].strip():
            errors.append(f'{field}: must be a non-empty string')

    if 'mode' not in fm:
        errors.append('missing required field: \'mode\'')
    elif str(fm['mode']) not in VALID_MODES:
        errors.append(f'mode: must be one of {sorted(VALID_MODES)}, got {fm["mode"]!r}')

    if 'temperature' not in fm:
        errors.append('missing required field: \'temperature\'')
    else:
        try:
            t = float(fm['temperature'])
            if not (0.0 <= t <= 2.0):
                errors.append(f'temperature: must be in [0.0, 2.0], got {t}')
        except (TypeError, ValueError):
            errors.append(f'temperature: not a number ({fm["temperature"]!r})')

    if 'max_tokens' not in fm:
        errors.append('missing required field: \'max_tokens\' (output cap)')
    else:
        mt = fm['max_tokens']
        if isinstance(mt, bool) or not isinstance(mt, int):
            errors.append(f'max_tokens: must be int, got {type(mt).__name__}')
        elif mt <= 0 or mt > MAX_TOKENS_CEILING:
            errors.append(f'max_tokens: must be a positive int ≤ {MAX_TOKENS_CEILING}, got {mt}')

    if 'emoji' not in fm or not str(fm.get('emoji', '')).strip():
        errors.append('missing required field: \'emoji\' (non-empty)')

    tools = fm.get('tools')
    if not isinstance(tools, dict):
        errors.append('tools: must be a mapping with keys write/edit/bash/question')
    else:
        for key in ('write', 'edit', 'bash', 'question'):
            if key not in tools:
                errors.append(f'tools.{key}: missing (must be true|false)')
            elif not isinstance(tools[key], bool):
                errors.append(f'tools.{key}: must be boolean, got {type(tools[key]).__name__}')

    return errors


def diff_frontmatter(old: dict[str, Any], new: dict[str, Any]) -> list[tuple[str, Any, Any]]:
    """Return list of (key, old_value, new_value) for changed top-level keys.
    Special-cases tools.* and chain.* changes.
    """
    changes: list[tuple[str, Any, Any]] = []
    keys = set(old) | set(new)
    for k in sorted(keys):
        if k == 'tools':
            old_tools = old.get('tools') or {}
            new_tools = new.get('tools') or {}
            for tk in sorted(set(old_tools) | set(new_tools)):
                if old_tools.get(tk) != new_tools.get(tk):
                    changes.append((f'tools.{tk}', old_tools.get(tk), new_tools.get(tk)))
        elif k == 'chain':
            old_chain = old.get('chain') or {}
            new_chain = new.get('chain') or {}
            for ck in sorted(set(old_chain) | set(new_chain)):
                if old_chain.get(ck) != new_chain.get(ck):
                    changes.append((f'chain.{ck}', old_chain.get(ck), new_chain.get(ck)))
        else:
            if old.get(k) != new.get(k):
                changes.append((k, old.get(k), new.get(k)))
    return changes


# ─── Skill validation ─────────────────────────────────────────────────────────

VALID_INJECT_VALUES = {'false', 'full', 'compact'}


def validate_skill_frontmatter(fm: dict[str, Any], skills_dir_existing: list[str]) -> list[str]:
    """Mirror scripts/lint.py:check_skill_fields. Empty list = OK.

    skills_dir_existing: list of existing skill slugs (for chain.next + depends_on
    cross-reference validation).
    """
    errors: list[str] = []

    for field in ('name', 'description'):
        if field not in fm:
            errors.append(f'missing required field: {field!r}')
        elif not isinstance(fm[field], str) or not fm[field].strip():
            errors.append(f'{field}: must be a non-empty string')

    for field in ('inject_references', 'inject_fewshot'):
        if field in fm:
            normalized = str(fm[field]).lower()
            if normalized not in VALID_INJECT_VALUES:
                errors.append(f'{field}: must be one of {sorted(VALID_INJECT_VALUES)}, '
                              f'got {fm[field]!r}')

    if 'emits_confidence' in fm and not isinstance(fm['emits_confidence'], bool):
        errors.append(f'emits_confidence: must be true|false, got {fm["emits_confidence"]!r}')

    chain = fm.get('chain') or {}
    if chain:
        if not isinstance(chain, dict):
            errors.append(f'chain: must be a mapping, got {type(chain).__name__}')
        else:
            chain_next = chain.get('next')
            if chain_next and chain_next not in skills_dir_existing:
                errors.append(f'chain.next: \'{chain_next}\' not in skills/')

    deps = fm.get('depends_on')
    if deps is not None:
        if isinstance(deps, str):
            deps_list = [d.strip() for d in deps.split(',') if d.strip()]
        elif isinstance(deps, list):
            deps_list = [str(d) for d in deps]
        else:
            errors.append(f'depends_on: must be list or comma-separated string, got {type(deps).__name__}')
            deps_list = []
        for d in deps_list:
            if d not in skills_dir_existing:
                errors.append(f'depends_on: \'{d}\' not in skills/')

    return errors
