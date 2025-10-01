"""SQLite persistence for Script Manager."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterator, Optional

from .models import Task, TaskRun


class Database:
    """Wrapper around a SQLite database storing tasks and run history."""

    def __init__(self, path: Path) -> None:
        self.path = path

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def initialise(self) -> None:
        """Create tables if they do not exist."""

        with self.connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    script_path TEXT NOT NULL,
                    cron TEXT NOT NULL,
                    python_executable TEXT,
                    working_directory TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                    started_at TEXT NOT NULL,
                    finished_at TEXT,
                    status TEXT NOT NULL,
                    exit_code INTEGER,
                    stdout_path TEXT,
                    stderr_path TEXT,
                    message TEXT
                )
                """
            )

    def add_task(
        self,
        *,
        name: str,
        script_path: Path,
        cron: str,
        python_executable: Optional[Path],
        working_directory: Optional[Path],
    ) -> Task:
        """Insert a new task and return it."""

        with self.connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO tasks (name, script_path, cron, python_executable, working_directory, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    name,
                    str(script_path),
                    cron,
                    str(python_executable) if python_executable else None,
                    str(working_directory) if working_directory else None,
                    datetime.utcnow().isoformat(timespec="seconds"),
                ),
            )
            task_id = cursor.lastrowid
        return self.get_task_by_id(task_id)

    def get_task_by_id(self, task_id: int) -> Task:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if not row:
            raise ValueError(f"Task with id {task_id} not found")
        return self._row_to_task(row)

    def get_task(self, name: str) -> Optional[Task]:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM tasks WHERE name = ?", (name,)).fetchone()
        return self._row_to_task(row) if row else None

    def list_tasks(self) -> list[Task]:
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM tasks ORDER BY name").fetchall()
        return [self._row_to_task(row) for row in rows]

    def remove_task(self, name: str) -> bool:
        with self.connect() as conn:
            cursor = conn.execute("DELETE FROM tasks WHERE name = ?", (name,))
            removed = cursor.rowcount > 0
        return removed

    def record_run_start(
        self,
        *,
        task_id: int,
        started_at: datetime,
        stdout_path: Optional[Path],
        stderr_path: Optional[Path],
        message: Optional[str] = None,
    ) -> int:
        with self.connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO runs (task_id, started_at, status, stdout_path, stderr_path, message)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    task_id,
                    started_at.isoformat(timespec="seconds"),
                    "running",
                    str(stdout_path) if stdout_path else None,
                    str(stderr_path) if stderr_path else None,
                    message,
                ),
            )
            return cursor.lastrowid

    def record_run_end(
        self,
        run_id: int,
        *,
        finished_at: datetime,
        status: str,
        exit_code: Optional[int],
        message: Optional[str] = None,
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE runs
                   SET finished_at = ?, status = ?, exit_code = ?, message = COALESCE(?, message)
                 WHERE id = ?
                """,
                (
                    finished_at.isoformat(timespec="seconds"),
                    status,
                    exit_code,
                    message,
                    run_id,
                ),
            )

    def recent_runs(self, *, limit: int = 10, task_name: Optional[str] = None) -> list[TaskRun]:
        query = (
            "SELECT runs.*, tasks.name as task_name FROM runs JOIN tasks ON tasks.id = runs.task_id"
        )
        params: tuple[object, ...]
        if task_name:
            query += " WHERE tasks.name = ?"
            params = (task_name,)
        else:
            params = tuple()
        query += " ORDER BY runs.started_at DESC LIMIT ?"
        params = params + (limit,)

        with self.connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._row_to_run(row) for row in rows]

    @staticmethod
    def _row_to_task(row: sqlite3.Row) -> Task:
        return Task(
            id=row["id"],
            name=row["name"],
            script_path=Path(row["script_path"]),
            cron=row["cron"],
            python_executable=Path(row["python_executable"]) if row["python_executable"] else None,
            working_directory=Path(row["working_directory"]) if row["working_directory"] else None,
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    @staticmethod
    def _row_to_run(row: sqlite3.Row) -> TaskRun:
        task_name = row["task_name"] if "task_name" in row.keys() else None
        return TaskRun(
            id=row["id"],
            task_id=row["task_id"],
            task_name=task_name,
            started_at=datetime.fromisoformat(row["started_at"]),
            finished_at=datetime.fromisoformat(row["finished_at"]) if row["finished_at"] else None,
            status=row["status"],
            exit_code=row["exit_code"],
            stdout_path=Path(row["stdout_path"]) if row["stdout_path"] else None,
            stderr_path=Path(row["stderr_path"]) if row["stderr_path"] else None,
            message=row["message"],
        )


__all__ = ["Database"]
