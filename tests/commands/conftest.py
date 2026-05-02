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
    """Point ORQUESTRUM_HOME at a tmp dir so registry writes stay isolated."""
    home = tmp_path / 'orq-home'
    home.mkdir()
    monkeypatch.setenv('ORQUESTRUM_HOME', str(home))
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
    """A project_root that already has .orquestrum/ + ORQUESTRUM.md."""
    (project_root / '.orquestrum').mkdir()
    (project_root / '.orquestrum' / 'config.toml').write_text(
        '[project]\nname = "sample-project"\n', encoding='utf-8',
    )
    (project_root / 'ORQUESTRUM.md').write_text(
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
