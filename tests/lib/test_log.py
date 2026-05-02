"""Tests for orquestrum.lib.log."""
import sys
import pytest
from orquestrum.lib import log as log_mod


@pytest.fixture(autouse=True)
def reset_prefix():
    """Reset global prefix between tests."""
    original = log_mod._prefix
    yield
    log_mod._prefix = original


class TestSetPrefix:
    def test_sets_prefix(self):
        log_mod.set_prefix('myprefix')
        assert log_mod._prefix == 'myprefix'

    def test_empty_string_clears_prefix(self):
        log_mod.set_prefix('foo')
        log_mod.set_prefix('')
        assert log_mod._prefix == ''


class TestLog:
    def test_log_prints_to_stdout(self, capsys):
        log_mod.set_prefix('')
        log_mod.log('hello world')
        out = capsys.readouterr().out
        assert 'hello world' in out
        assert '[*]' in out

    def test_log_uses_prefix_when_set(self, capsys):
        log_mod.set_prefix('STEP')
        log_mod.log('doing something')
        out = capsys.readouterr().out
        assert '[STEP]' in out


class TestOk:
    def test_prints_checkmark(self, capsys):
        log_mod.ok('all good')
        out = capsys.readouterr().out
        assert 'all good' in out
        assert '[✓]' in out


class TestWarn:
    def test_prints_warning(self, capsys):
        log_mod.warn('be careful')
        out = capsys.readouterr().out
        assert 'be careful' in out
        assert '[!]' in out


class TestErr:
    def test_prints_to_stderr(self, capsys):
        log_mod.err('something broke')
        captured = capsys.readouterr()
        assert 'something broke' in captured.err
        assert '[✗]' in captured.err

    def test_not_in_stdout(self, capsys):
        log_mod.err('error msg')
        captured = capsys.readouterr()
        assert 'error msg' not in captured.out
