"""Tests for ui.config (auto_detect_mode, resolve)."""
import pytest
from pathlib import Path
from ui.config import auto_detect_mode, resolve, UIConfig


class TestAutoDetectMode:
    def test_detects_framework_when_all_markers_present(self, tmp_path: Path):
        (tmp_path / 'agents').mkdir()
        (tmp_path / 'skills').mkdir()
        (tmp_path / 'orquestrum' / 'lib').mkdir(parents=True)
        (tmp_path / 'docs' / 'agent-context').mkdir(parents=True)
        assert auto_detect_mode(tmp_path) == 'framework'

    def test_detects_project_when_markers_absent(self, tmp_path: Path):
        assert auto_detect_mode(tmp_path) == 'project'

    def test_partial_markers_is_project(self, tmp_path: Path):
        (tmp_path / 'agents').mkdir()
        # Missing skills/, orquestrum/lib, docs/agent-context
        assert auto_detect_mode(tmp_path) == 'project'


class TestResolve:
    def test_project_mode_from_arg(self, tmp_path: Path):
        cfg = resolve(mode_arg='project', root_arg=str(tmp_path))
        assert cfg.mode == 'project'
        assert cfg.is_project

    def test_framework_mode_requires_dirs(self, tmp_path: Path):
        # framework mode on an empty dir should raise
        with pytest.raises(ValueError, match='agents'):
            resolve(mode_arg='framework', root_arg=str(tmp_path))

    def test_framework_mode_valid_when_dirs_exist(self, tmp_path: Path):
        (tmp_path / 'agents').mkdir()
        (tmp_path / 'skills').mkdir()
        (tmp_path / 'orquestrum').mkdir()
        cfg = resolve(mode_arg='framework', root_arg=str(tmp_path))
        assert cfg.is_framework

    def test_project_metrics_dir_set(self, tmp_path: Path):
        cfg = resolve(mode_arg='project', root_arg=str(tmp_path))
        assert cfg.metrics_dir == tmp_path / '.orquestrum' / 'metrics'

    def test_framework_targets_path_set(self, tmp_path: Path):
        (tmp_path / 'agents').mkdir()
        (tmp_path / 'skills').mkdir()
        (tmp_path / 'orquestrum').mkdir()
        cfg = resolve(mode_arg='framework', root_arg=str(tmp_path))
        assert cfg.targets_path is not None
        assert 'targets.json' in str(cfg.targets_path)

    def test_invalid_mode_raises(self, tmp_path: Path):
        with pytest.raises(ValueError, match='Invalid ORQ_MODE'):
            resolve(mode_arg='invalid', root_arg=str(tmp_path))

    def test_nonexistent_root_raises(self):
        with pytest.raises(ValueError, match='does not exist'):
            resolve(mode_arg='project', root_arg='/nonexistent/path/xyz')

    def test_port_arg_overrides_default(self, tmp_path: Path):
        cfg = resolve(mode_arg='project', root_arg=str(tmp_path), port_arg=9999)
        assert cfg.port == 9999

    def test_is_framework_property(self, tmp_path: Path):
        cfg = resolve(mode_arg='project', root_arg=str(tmp_path))
        assert not cfg.is_framework
        assert cfg.is_project

    def test_env_var_mode(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv('ORQ_MODE', 'project')
        cfg = resolve(root_arg=str(tmp_path))
        assert cfg.mode == 'project'

    def test_env_var_root(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv('ORQ_ROOT', str(tmp_path))
        cfg = resolve(mode_arg='project')
        assert cfg.root == tmp_path
