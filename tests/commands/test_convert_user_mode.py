"""End-to-end test of `orquestrum convert` in wheel/user mode.

The CLI normally finds `agents/`, `skills/`, `docs/`, `bundle/` either via
the dev repo (cwd-walk) or via the wheel-bundled `_assets/`. This test
simulates the wheel-install scenario by:

  1. Running the CLI as a subprocess from a tmp cwd OUTSIDE the dev repo
     (so `find_canonical_root()` returns None).
  2. Pointing `$ORQUESTRUM_ASSETS_ROOT` at the dev repo (mimics `_assets/`
     materialized by `uv build --wheel`).
  3. Pointing `$ORQUESTRUM_HOME` and `$ORQUESTRUM_CACHE` at tmp dirs so
     the user's real `~/.orquestrum/` is never touched.

Validates that convert + install work end-to-end without `os.chdir` and
without requiring the user to be inside the canonical repo.
"""
from __future__ import annotations
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _run_in_user_mode(
    args: list[str], *, cwd: Path, home: Path, cache: Path,
) -> subprocess.CompletedProcess:
    """Run the orquestrum CLI as if installed via wheel from outside the repo."""
    env = os.environ.copy()
    env['ORQUESTRUM_HOME'] = str(home)
    env['ORQUESTRUM_CACHE'] = str(cache)
    # Simulate wheel mode by exposing the repo's content tree as bundled assets.
    env['ORQUESTRUM_ASSETS_ROOT'] = str(REPO_ROOT)
    return subprocess.run(
        [sys.executable, '-m', 'orquestrum.cli', *args],
        cwd=str(cwd), capture_output=True, text=True, env=env,
    )


class TestConvertWritesToCache:
    def test_writes_into_explicit_cache_dir(self, tmp_path: Path):
        cwd = tmp_path / 'outside-the-repo'
        cwd.mkdir()
        home = tmp_path / 'orq-home'
        cache = tmp_path / 'orq-cache'
        result = _run_in_user_mode(
            ['convert', '--tool', 'cursor'],
            cwd=cwd, home=home, cache=cache,
        )
        assert result.returncode == 0, (
            f'convert failed:\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}'
        )
        # Output landed in the cache, not in the repo
        assert (cache / 'cursor').is_dir()
        rules = list((cache / 'cursor').rglob('*.mdc'))
        assert rules, 'expected at least one .mdc rule file'

    def test_does_not_pollute_repo_integrations(self, tmp_path: Path):
        cwd = tmp_path / 'far-away'
        cwd.mkdir()
        home = tmp_path / 'orq-home'
        cache = tmp_path / 'orq-cache'
        before = sorted((REPO_ROOT / 'integrations').rglob('*')) \
            if (REPO_ROOT / 'integrations').exists() else []
        _run_in_user_mode(
            ['convert', '--tool', 'cursor'],
            cwd=cwd, home=home, cache=cache,
        )
        after = sorted((REPO_ROOT / 'integrations').rglob('*')) \
            if (REPO_ROOT / 'integrations').exists() else []
        assert before == after, 'user-mode convert must not touch the repo'

    def test_default_cache_falls_under_orquestrum_home(self, tmp_path: Path):
        cwd = tmp_path / 'somewhere'
        cwd.mkdir()
        home = tmp_path / 'orq-home'
        # No ORQUESTRUM_CACHE — should default to home/cache/integrations
        env = os.environ.copy()
        env['ORQUESTRUM_HOME'] = str(home)
        env['ORQUESTRUM_ASSETS_ROOT'] = str(REPO_ROOT)
        env.pop('ORQUESTRUM_CACHE', None)
        result = subprocess.run(
            [sys.executable, '-m', 'orquestrum.cli', 'convert', '--tool', 'aider'],
            cwd=str(cwd), capture_output=True, text=True, env=env,
        )
        assert result.returncode == 0, result.stderr
        assert (home / 'cache' / 'integrations' / 'aider').is_dir()

    def test_prints_install_hint_in_user_mode(self, tmp_path: Path):
        cwd = tmp_path / 'noplace'
        cwd.mkdir()
        home = tmp_path / 'orq-home'
        cache = tmp_path / 'orq-cache'
        result = _run_in_user_mode(
            ['convert', '--tool', 'cursor'],
            cwd=cwd, home=home, cache=cache,
        )
        assert result.returncode == 0
        # The CLI should suggest `orquestrum install` next
        assert 'orquestrum install' in result.stdout


class TestInstallFromCache:
    def test_full_pipeline_convert_then_install(self, tmp_path: Path):
        cwd = tmp_path / 'work'
        cwd.mkdir()
        home = tmp_path / 'orq-home'
        cache = tmp_path / 'orq-cache'
        target = tmp_path / 'my-project'
        target.mkdir()

        # Step 1: convert
        r1 = _run_in_user_mode(
            ['convert', '--tool', 'cursor'],
            cwd=cwd, home=home, cache=cache,
        )
        assert r1.returncode == 0, r1.stderr

        # Step 2: install — uses cache as source, copies to target
        r2 = _run_in_user_mode(
            ['install', '--tool', 'cursor', '--target', str(target)],
            cwd=cwd, home=home, cache=cache,
        )
        assert r2.returncode == 0, r2.stderr
        assert (target / '.cursor' / 'rules').is_dir()
        rules = list((target / '.cursor' / 'rules').glob('*.mdc'))
        assert rules


class TestVersionStamp:
    def test_cache_gets_version_stamp(self, tmp_path: Path):
        cwd = tmp_path / 'tmp'
        cwd.mkdir()
        home = tmp_path / 'orq-home'
        cache = tmp_path / 'orq-cache'
        _run_in_user_mode(
            ['convert', '--tool', 'aider'],
            cwd=cwd, home=home, cache=cache,
        )
        stamp = cache / '.version'
        assert stamp.is_file()
        from orquestrum import __version__
        assert stamp.read_text(encoding='utf-8').strip() == __version__

    def test_stale_cache_is_invalidated(self, tmp_path: Path):
        cwd = tmp_path / 'tmp'
        cwd.mkdir()
        home = tmp_path / 'orq-home'
        cache = tmp_path / 'orq-cache'
        cache.mkdir()
        # Pre-populate the cache with a fake stale version + leftover files
        (cache / '.version').write_text('0.0.0-old\n', encoding='utf-8')
        (cache / 'leftover-from-old-version').mkdir()
        result = _run_in_user_mode(
            ['convert', '--tool', 'cursor'],
            cwd=cwd, home=home, cache=cache,
        )
        assert result.returncode == 0
        # Stale leftover gone, current version stamped
        assert not (cache / 'leftover-from-old-version').exists()
        from orquestrum import __version__
        assert (cache / '.version').read_text(encoding='utf-8').strip() == __version__
