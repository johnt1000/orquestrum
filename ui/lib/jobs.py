"""ui/lib/jobs.py — tiny async job runner for the local single-user console.

Replaces the synchronous-blocking subprocess pattern in convert/install/
compact/audits. Operations submit a Job, immediately return its id, and
the HTMX `/jobs/{id}` polling endpoint reads progress until terminal.

Single-user, single-process: a global OrderedDict registry is fine. Jobs
older than _MAX_JOBS get evicted to keep memory bounded.
"""
from __future__ import annotations
import asyncio
import time
import uuid
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path

_MAX_JOBS        = 50
_DEFAULT_TIMEOUT = 300

State = str  # one of: 'running', 'done', 'failed', 'timed_out'


@dataclass
class Job:
    id:           str
    label:        str
    cmd:          list[str]
    cwd:          str
    started_at:   float
    timeout_s:    int                  = _DEFAULT_TIMEOUT
    render_md:    bool                 = False  # render stdout as markdown when terminal
    completed_at: float | None         = None
    exit_code:    int | None           = None
    stdout:       str                  = ''
    stderr:       str                  = ''
    state:        State                = 'running'
    extra:        dict                 = field(default_factory=dict)

    @property
    def is_terminal(self) -> bool:
        return self.state != 'running'

    @property
    def duration_s(self) -> float:
        end = self.completed_at or time.time()
        return end - self.started_at


_jobs: 'OrderedDict[str, Job]' = OrderedDict()


def submit(
    *,
    label:     str,
    cmd:       list[str],
    cwd:       str | Path,
    timeout_s: int               = _DEFAULT_TIMEOUT,
    render_md: bool              = False,
    extra:     dict | None       = None,
) -> Job:
    """Spawn the subprocess on the running event loop and return Job immediately."""
    job_id = uuid.uuid4().hex[:12]
    job = Job(
        id=job_id, label=label, cmd=list(cmd), cwd=str(cwd),
        started_at=time.time(), timeout_s=timeout_s,
        render_md=render_md, extra=extra or {},
    )
    _jobs[job_id] = job
    while len(_jobs) > _MAX_JOBS:
        _jobs.popitem(last=False)  # evict oldest
    asyncio.create_task(_run(job))
    return job


def get(job_id: str) -> Job | None:
    return _jobs.get(job_id)


async def _run(job: Job) -> None:
    try:
        proc = await asyncio.create_subprocess_exec(
            *job.cmd,
            cwd=job.cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=job.timeout_s
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            job.stderr += f'\ntimed out after {job.timeout_s}s\n'
            job.state = 'timed_out'
            return
        job.stdout    = (stdout or b'').decode('utf-8', errors='replace')
        job.stderr    = (stderr or b'').decode('utf-8', errors='replace')
        job.exit_code = proc.returncode
        job.state     = 'done' if proc.returncode == 0 else 'failed'
    except Exception as e:
        job.state  = 'failed'
        job.stderr = (job.stderr + '\n' + repr(e)).strip()
    finally:
        job.completed_at = time.time()
