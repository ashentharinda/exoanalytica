"""Runs the analysis worker in a resource-limited child process inside the job's own directory."""
import json
import os
import resource
import subprocess
import sys
from pathlib import Path

from ..config import settings


def _limits():
    mem = settings.worker_mem_mb * 1024 * 1024
    resource.setrlimit(resource.RLIMIT_AS, (mem, mem))
    resource.setrlimit(resource.RLIMIT_CPU, (settings.worker_timeout_s, settings.worker_timeout_s))
    resource.setrlimit(resource.RLIMIT_FSIZE, (300 * 1024 * 1024,) * 2)
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    os.setsid()


def run_worker(job_dir: Path) -> dict:
    # Minimal environment: the worker never sees JWT_SECRET, the DB URL or cloud credentials.
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin"),
        "HOME": str(job_dir),
        "PYTHONPATH": "/app",
        "MODEL_PATH": settings.model_path,
        "OMP_NUM_THREADS": "2",
        "MPLCONFIGDIR": str(job_dir),
    }
    try:
        subprocess.run([sys.executable, "-m", "app.worker", str(job_dir)], cwd=job_dir, env=env,
                       preexec_fn=_limits, timeout=settings.worker_timeout_s + 30,
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=False)
    except subprocess.TimeoutExpired:
        return {"error": "Analysis timed out. Try a shorter light curve."}
    out = job_dir / "result.json"
    if out.exists():
        return json.loads(out.read_text())
    return {"error": "Analysis failed unexpectedly."}
