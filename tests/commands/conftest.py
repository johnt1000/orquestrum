"""Shared fixtures for orquestrum CLI command tests.

These tests must never read or write the real `~/.orquestrum/` directory.
Every fixture redirects ORQUESTRUM_HOME to an isolated tmp directory and
runs each test in a sandboxed cwd that mimics a target project.
"""
from __future__ import annotations
from pathlib import Path

import pytest


@pytest.fixture()
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point ORQUESTRUM_HOME at a tmp dir so registry writes stay isolated.

    Also overrides `Path.home()` to a tmp dir so any code that consults the
    real `~/.claude/settings.json` (e.g. `_detect_global_state` in init,
    `_claude_code_target` in setup) sees a fresh empty environment instead
    of the developer's actual install state. Without this, init tests run
    on a machine with global orquestrum installed would skip prompts that
    the test expects to fire.
    """
    home = tmp_path / 'orq-home'
    home.mkdir()
    monkeypatch.setenv('ORQUESTRUM_HOME', str(home))
    fake = tmp_path / 'fake-user-home'
    fake.mkdir()
    monkeypatch.setattr(Path, 'home', staticmethod(lambda: fake))
    return home


@pytest.fixture()
def project_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A bare directory that mimics a target project; cwd is moved inside it."""
    root = tmp_path / 'sample-project'
    root.mkdir()
    monkeypatch.chdir(root)
    return root


@pytest.fixture()
def initialized_project(project_root: Path, isolated_home: Path) -> Path:
    """A project_root with the v0.5 layout: `.orquestrum/{config.toml, manifest.md}`."""
    (project_root / '.orquestrum').mkdir()
    (project_root / '.orquestrum' / 'config.toml').write_text(
        '[project]\nname = "sample-project"\n', encoding='utf-8',
    )
    (project_root / '.orquestrum' / 'manifest.md').write_text(
        '# Orquestrum — Project Manifest\n\n'
        '## Configuration\n\n'
        '| Field | Value |\n|-------|-------|\n'
        '| Project name | `sample-project` |\n'
        '| Tool         | `—` |\n'
        '| Provider     | `—` |\n'
        '| Default tier | `balanced` |\n'
        '| Initialized  | 2026-05-02 |\n'
        '| Last sync    | 2026-05-02 |\n'
        '\n'
        '## History\n\n- 2026-05-02 — initialized\n\n'
        '<!-- ===== orquestrum:auto-managed-above ===== -->\n\n'
        '## Notes\n\n(your notes here)\n',
        encoding='utf-8',
    )
    return project_root
