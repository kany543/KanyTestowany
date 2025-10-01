"""Task execution utilities."""
from __future__ import annotations

import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from .db import Database
from .models import Task


class TaskExecutionError(RuntimeError):
    """Raised when a task fails before it can start."""


def run_task(database: Database, task: Task, data_dir: Path) -> None:
    """Execute a task and record the result in the database."""

    logs_dir = data_dir / "logs" / task.name
    logs_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    stdout_path = logs_dir / f"{timestamp}.stdout.log"
    stderr_path = logs_dir / f"{timestamp}.stderr.log"

    run_id = database.record_run_start(
        task_id=task.id,
        started_at=datetime.utcnow(),
        stdout_path=stdout_path,
        stderr_path=stderr_path,
    )

    executable = str(task.python_executable) if task.python_executable else sys.executable
    script_path = str(task.script_path)
    cwd: Optional[str] = str(task.working_directory) if task.working_directory else None

    try:
        with stdout_path.open("w", encoding="utf-8") as stdout_file, stderr_path.open(
            "w", encoding="utf-8"
        ) as stderr_file:
            process = subprocess.Popen(
                [executable, script_path],
                stdout=stdout_file,
                stderr=stderr_file,
                cwd=cwd,
            )
            exit_code = process.wait()
    except Exception as exc:  # noqa: BLE001 - we want to capture all exceptions
        database.record_run_end(
            run_id,
            finished_at=datetime.utcnow(),
            status="failed",
            exit_code=None,
            message=str(exc),
        )
        raise TaskExecutionError(str(exc)) from exc

    status = "success" if exit_code == 0 else "failed"
    database.record_run_end(
        run_id,
        finished_at=datetime.utcnow(),
        status=status,
        exit_code=exit_code,
        message=None,
    )


__all__ = ["run_task", "TaskExecutionError"]
