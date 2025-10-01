from __future__ import annotations

from datetime import datetime
from pathlib import Path

from script_manager.db import Database


def create_db(tmp_path: Path) -> Database:
    db = Database(tmp_path / "test.db")
    db.initialise()
    return db


def test_add_and_get_task(tmp_path: Path) -> None:
    db = create_db(tmp_path)
    task = db.add_task(
        name="demo",
        script_path=Path("/tmp/demo.py"),
        cron="0 0 * * *",
        python_executable=None,
        working_directory=None,
    )

    fetched = db.get_task("demo")
    assert fetched is not None
    assert fetched.id == task.id
    assert fetched.name == "demo"
    assert fetched.cron == "0 0 * * *"


def test_record_run_history(tmp_path: Path) -> None:
    db = create_db(tmp_path)
    task = db.add_task(
        name="demo",
        script_path=Path("/tmp/demo.py"),
        cron="0 0 * * *",
        python_executable=None,
        working_directory=None,
    )

    run_id = db.record_run_start(
        task_id=task.id,
        started_at=datetime.utcnow(),
        stdout_path=None,
        stderr_path=None,
    )

    db.record_run_end(
        run_id,
        finished_at=datetime.utcnow(),
        status="success",
        exit_code=0,
    )

    runs = db.recent_runs(limit=5)
    assert len(runs) == 1
    assert runs[0].status == "success"
    assert runs[0].exit_code == 0
    assert runs[0].task_id == task.id
    assert runs[0].task_name == "demo"
