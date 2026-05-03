"""Tests for orquestrum.lib.prompts — interactive helpers for `init`."""
from __future__ import annotations

import pytest

from orquestrum.lib import prompts


@pytest.fixture()
def force_interactive(monkeypatch: pytest.MonkeyPatch):
    """Pretend stdin is a TTY for the test, regardless of the test runner."""
    monkeypatch.setattr(prompts, '_is_interactive', lambda: True)
    monkeypatch.delenv('ORQUESTRUM_NONINTERACTIVE', raising=False)


@pytest.fixture()
def force_noninteractive(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(prompts, '_is_interactive', lambda: False)


def _scripted_input(answers: list[str], monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Feed `answers` into _read_line one at a time, return the prompts received
    so tests can assert on what the user saw."""
    received: list[str] = []
    iterator = iter(answers)

    def fake(prompt: str) -> str:
        received.append(prompt)
        return next(iterator, '')

    monkeypatch.setattr(prompts, '_read_line', fake)
    return received


# ─── ask_yn ─────────────────────────────────────────────────────────────────


class TestAskYn:
    def test_default_yes_on_blank(
        self, force_interactive, monkeypatch: pytest.MonkeyPatch,
    ):
        _scripted_input([''], monkeypatch)
        assert prompts.ask_yn('Enable foo?', default=True) is True

    def test_default_no_on_blank(
        self, force_interactive, monkeypatch: pytest.MonkeyPatch,
    ):
        _scripted_input([''], monkeypatch)
        assert prompts.ask_yn('Enable foo?', default=False) is False

    def test_explicit_y_returns_true(
        self, force_interactive, monkeypatch: pytest.MonkeyPatch,
    ):
        _scripted_input(['y'], monkeypatch)
        assert prompts.ask_yn('?', default=False) is True

    def test_explicit_no(
        self, force_interactive, monkeypatch: pytest.MonkeyPatch,
    ):
        _scripted_input(['n'], monkeypatch)
        assert prompts.ask_yn('?', default=True) is False

    def test_portuguese_sim(
        self, force_interactive, monkeypatch: pytest.MonkeyPatch,
    ):
        _scripted_input(['sim'], monkeypatch)
        assert prompts.ask_yn('?', default=False) is True

    def test_portuguese_nao(
        self, force_interactive, monkeypatch: pytest.MonkeyPatch,
    ):
        _scripted_input(['nao'], monkeypatch)
        assert prompts.ask_yn('?', default=True) is False

    def test_invalid_then_valid(
        self, force_interactive, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
    ):
        _scripted_input(['maybe', 'y'], monkeypatch)
        assert prompts.ask_yn('?', default=False) is True
        out = capsys.readouterr().out
        assert 'please answer y or n' in out

    def test_noninteractive_returns_default(self, force_noninteractive):
        assert prompts.ask_yn('?', default=True) is True
        assert prompts.ask_yn('?', default=False) is False

    def test_explicit_interactive_false_skips_input(self):
        # Even if stdin would be a TTY, interactive=False short-circuits.
        assert prompts.ask_yn('?', default=False, interactive=False) is False


# ─── ask_choice ─────────────────────────────────────────────────────────────


class TestAskChoice:
    def test_default_returned_on_blank(
        self, force_interactive, monkeypatch: pytest.MonkeyPatch,
    ):
        _scripted_input([''], monkeypatch)
        result = prompts.ask_choice('Pick:',
                                    [('g', 'global'), ('p', 'project'), ('s', 'skip')],
                                    default='g')
        assert result == 'g'

    def test_explicit_pick(
        self, force_interactive, monkeypatch: pytest.MonkeyPatch,
    ):
        _scripted_input(['p'], monkeypatch)
        result = prompts.ask_choice('Pick:',
                                    [('g', 'global'), ('p', 'project')],
                                    default='g')
        assert result == 'p'

    def test_invalid_then_valid(
        self, force_interactive, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
    ):
        _scripted_input(['x', 's'], monkeypatch)
        result = prompts.ask_choice('?',
                                    [('g', 'global'), ('s', 'skip')],
                                    default='g')
        assert result == 's'
        out = capsys.readouterr().out
        assert 'pick one of' in out

    def test_case_and_whitespace_tolerated(
        self, force_interactive, monkeypatch: pytest.MonkeyPatch,
    ):
        _scripted_input(['  G  '], monkeypatch)
        result = prompts.ask_choice('?',
                                    [('g', 'global'), ('p', 'project')],
                                    default='p')
        assert result == 'g'

    def test_noninteractive_returns_default(self, force_noninteractive):
        result = prompts.ask_choice('?',
                                    [('a', 'A'), ('b', 'B')],
                                    default='b')
        assert result == 'b'

    def test_noninteractive_without_default_raises(self, force_noninteractive):
        with pytest.raises(RuntimeError):
            prompts.ask_choice('?', [('a', 'A')])

    def test_default_must_match_a_key(self, force_interactive):
        with pytest.raises(ValueError):
            prompts.ask_choice('?', [('a', 'A')], default='z')


# ─── ask_text ───────────────────────────────────────────────────────────────


class TestAskText:
    def test_default_on_blank(
        self, force_interactive, monkeypatch: pytest.MonkeyPatch,
    ):
        _scripted_input([''], monkeypatch)
        assert prompts.ask_text('Name?', default='alpha') == 'alpha'

    def test_returns_user_input(
        self, force_interactive, monkeypatch: pytest.MonkeyPatch,
    ):
        _scripted_input(['my-project'], monkeypatch)
        assert prompts.ask_text('Name?', default='') == 'my-project'

    def test_trims_whitespace(
        self, force_interactive, monkeypatch: pytest.MonkeyPatch,
    ):
        _scripted_input(['  spaced  '], monkeypatch)
        assert prompts.ask_text('?', default='') == 'spaced'

    def test_noninteractive_returns_default(self, force_noninteractive):
        assert prompts.ask_text('?', default='from-flag') == 'from-flag'


# ─── env opt-out ────────────────────────────────────────────────────────────


class TestEnvOptOut:
    def test_orq_noninteractive_env_disables_prompts(
        self, monkeypatch: pytest.MonkeyPatch,
    ):
        monkeypatch.setenv('ORQUESTRUM_NONINTERACTIVE', '1')
        # Even with a TTY, the env var wins
        assert prompts._is_interactive() is False
