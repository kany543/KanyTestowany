"""Dataclasses describing tasks and run history."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass(slots=True)
class Task:
    """A scheduled Python script."""

    id: int
    name: str
    script_path: Path
    cron: str
    python_executable: Optional[Path]
    working_directory: Optional[Path]
    created_at: datetime


@dataclass(slots=True)
class TaskRun:
    """Represents a single execution of a task."""

    id: int
    task_id: int
    task_name: Optional[str]
    started_at: datetime
    finished_at: Optional[datetime]
    status: str
    exit_code: Optional[int]
    stdout_path: Optional[Path]
    stderr_path: Optional[Path]
    message: Optional[str]


__all__ = ["Task", "TaskRun"]
