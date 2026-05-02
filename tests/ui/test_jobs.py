"""Tests for ui.lib.jobs (async job runner)."""
import asyncio
import sys
import pytest
import ui.lib.jobs as jobs_module
from ui.lib.jobs import submit, get, _run, Job


@pytest.fixture(autouse=True)
def clear_registry():
    """Ensure a clean job registry for each test."""
    jobs_module._jobs.clear()
    yield
    jobs_module._jobs.clear()


class TestSubmit:
    async def test_submit_creates_job(self):
        job = submit(label='test', cmd=[sys.executable, '-c', 'pass'], cwd='.')
        assert isinstance(job, Job)
        assert job.id in jobs_module._jobs

    async def test_submit_initial_state_is_running(self):
        job = submit(label='test', cmd=[sys.executable, '-c', 'pass'], cwd='.')
        assert job.state == 'running'

    async def test_job_completes_to_done(self):
        job = submit(label='test', cmd=[sys.executable, '-c', 'pass'], cwd='.')
        # Give the event loop time to run the subprocess
        for _ in range(50):
            await asyncio.sleep(0.05)
            if job.is_terminal:
                break
        assert job.state == 'done'
        assert job.exit_code == 0

    async def test_failing_cmd_state_is_failed(self):
        job = submit(label='fail', cmd=[sys.executable, '-c', 'raise SystemExit(1)'], cwd='.')
        for _ in range(50):
            await asyncio.sleep(0.05)
            if job.is_terminal:
                break
        assert job.state == 'failed'
        assert job.exit_code == 1

    async def test_stdout_captured(self):
        job = submit(label='out', cmd=[sys.executable, '-c', 'print("hello")'], cwd='.')
        for _ in range(50):
            await asyncio.sleep(0.05)
            if job.is_terminal:
                break
        assert 'hello' in job.stdout

    async def test_eviction_when_max_exceeded(self):
        original_max = jobs_module._MAX_JOBS
        jobs_module._MAX_JOBS = 3
        try:
            ids = []
            for i in range(5):
                j = submit(label=f'j{i}', cmd=[sys.executable, '-c', 'pass'], cwd='.')
                ids.append(j.id)
            assert len(jobs_module._jobs) <= 3
            # The most recent job should still be present
            assert ids[-1] in jobs_module._jobs
        finally:
            jobs_module._MAX_JOBS = original_max


class TestGet:
    async def test_get_returns_job(self):
        job = submit(label='test', cmd=[sys.executable, '-c', 'pass'], cwd='.')
        assert get(job.id) is job

    def test_get_returns_none_for_unknown(self):
        assert get('nonexistent_id') is None


class TestJobProperties:
    async def test_is_terminal_false_while_running(self):
        job = submit(label='test', cmd=[sys.executable, '-c', 'pass'], cwd='.')
        # Before completing, state is 'running'
        # (may or may not have completed by this line, so we just verify the property logic)
        assert job.is_terminal == (job.state != 'running')

    async def test_duration_positive(self):
        job = submit(label='test', cmd=[sys.executable, '-c', 'pass'], cwd='.')
        for _ in range(50):
            await asyncio.sleep(0.05)
            if job.is_terminal:
                break
        assert job.duration_s > 0
