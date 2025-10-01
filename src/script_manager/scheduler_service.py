"""Scheduler loop for running tasks based on cron expressions."""
from __future__ import annotations

import signal
import threading
from pathlib import Path
from typing import Dict

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from rich.console import Console

from .db import Database
from .models import Task
from .runner import run_task

console = Console()


class SchedulerService:
    """Manages APScheduler jobs and synchronises them with the database."""

    def __init__(self, database: Database, data_dir: Path, refresh_interval: int = 30) -> None:
        self.database = database
        self.data_dir = data_dir
        self.refresh_interval = refresh_interval
        self.scheduler = BackgroundScheduler()
        self._stop_event = threading.Event()
        self._scheduled_cron: Dict[str, str] = {}

    def start(self) -> None:
        console.print("[bold green]Starting Script Manager scheduler...[/bold green]")
        self.database.initialise()
        self.scheduler.start()
        self._install_signal_handlers()
        try:
            while not self._stop_event.is_set():
                self._synchronise_jobs()
                self._stop_event.wait(self.refresh_interval)
        finally:
            self.scheduler.shutdown(wait=True)
            console.print("[bold yellow]Scheduler stopped.[/bold yellow]")

    def stop(self) -> None:
        self._stop_event.set()

    def _install_signal_handlers(self) -> None:
        try:
            signal.signal(signal.SIGINT, self._handle_signal)
            signal.signal(signal.SIGTERM, self._handle_signal)
        except ValueError:
            # Signal handling can fail on certain platforms/threads.
            pass

    def _handle_signal(self, signum, frame) -> None:  # type: ignore[override]
        console.print(f"[yellow]Received signal {signum}, shutting down...[/yellow]")
        self.stop()

    def _synchronise_jobs(self) -> None:
        tasks = {task.name: task for task in self.database.list_tasks()}

        # Remove jobs for deleted tasks
        for name in list(self._scheduled_cron.keys()):
            if name not in tasks:
                console.print(f"[cyan]Removing job for deleted task '{name}'.[/cyan]")
                self.scheduler.remove_job(name)
                del self._scheduled_cron[name]

        # Add or update jobs
        for name, task in tasks.items():
            cron_expression = task.cron
            if name not in self._scheduled_cron:
                self._add_job(task)
                self._scheduled_cron[name] = cron_expression
            elif self._scheduled_cron[name] != cron_expression:
                console.print(
                    f"[cyan]Updating schedule for task '{name}' to '{cron_expression}'.[/cyan]"
                )
                trigger = CronTrigger.from_crontab(cron_expression)
                self.scheduler.reschedule_job(name, trigger=trigger)
                self._scheduled_cron[name] = cron_expression

    def _add_job(self, task: Task) -> None:
        console.print(
            f"[green]Scheduling task '{task.name}' with cron '{task.cron}'.[/green]"
        )
        trigger = CronTrigger.from_crontab(task.cron)
        self.scheduler.add_job(
            self._run_task_job,
            trigger=trigger,
            id=task.name,
            args=[task.name],
            replace_existing=True,
            max_instances=1,
        )

    def _run_task_job(self, task_name: str) -> None:
        # Each job reconnects to the database to fetch the latest task definition
        task = self.database.get_task(task_name)
        if not task:
            console.print(f"[red]Task '{task_name}' no longer exists, skipping run.[/red]")
            return
        console.print(f"[blue]Running task '{task.name}'.[/blue]")
        try:
            run_task(self.database, task, self.data_dir)
            console.print(f"[green]Task '{task.name}' finished successfully.[/green]")
        except Exception as exc:  # noqa: BLE001 - intentionally broad
            console.print(f"[red]Task '{task.name}' failed: {exc}[/red]")


def run_scheduler_loop(database: Database, data_dir: Path, refresh_interval: int = 30) -> None:
    service = SchedulerService(database, data_dir, refresh_interval)
    service.start()


__all__ = ["SchedulerService", "run_scheduler_loop"]
