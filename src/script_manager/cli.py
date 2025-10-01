"""Typer commands exposed to the user."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import typer
from apscheduler.triggers.cron import CronTrigger
from rich.console import Console
from rich.table import Table

from .config import APP_NAME, default_data_dir, ensure_data_dir
from .db import Database
from .runner import run_task
from .scheduler_service import run_scheduler_loop
from .updater import UpdateError, default_repository_root, update_repository

console = Console()
app = typer.Typer(help="Zarzadzanie harmonogramem uruchamiania skryptow Python.")


def _resolve_data_dir(custom: Optional[Path]) -> Path:
    if custom:
        return ensure_data_dir(custom.expanduser())
    return ensure_data_dir(default_data_dir())


def _get_database(data_dir: Path) -> Database:
    db_path = data_dir / "script-manager.db"
    database = Database(db_path)
    database.initialise()
    return database


@app.callback()
def main(
    ctx: typer.Context,
    data_dir: Optional[Path] = typer.Option(
        None,
        "--data-dir",
        help="Sciezka do katalogu z danymi aplikacji (domyslnie systemowy katalog aplikacji).",
    ),
) -> None:
    data_dir_resolved = _resolve_data_dir(data_dir)
    ctx.obj = {
        "data_dir": data_dir_resolved,
        "db": _get_database(data_dir_resolved),
    }
    console.print(f"[green]{APP_NAME} bedzie korzystal z katalogu: {data_dir_resolved}[/green]")


@app.command("add")
def add_task(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Nazwa zadania"),
    script: Path = typer.Argument(..., help="Sciezka do skryptu Python"),
    cron: str = typer.Option(..., help="Wyrazenie cron okreslajace harmonogram"),
    python: Optional[Path] = typer.Option(
        None,
        "--python",
        help="Opcjonalna sciezka do interpretera Python (domyslnie aktualny interpreter)",
    ),
    working_dir: Optional[Path] = typer.Option(
        None,
        "--cwd",
        help="Katalog roboczy, w ktorym bedzie uruchamiany skrypt",
    ),
) -> None:
    """Dodaj nowe zadanie."""

    database: Database = ctx.obj["db"]
    script_path = script.expanduser().resolve()
    if not script_path.exists():
        typer.echo(f"Blad: skrypt {script_path} nie istnieje.")
        raise typer.Exit(code=1)

    try:
        CronTrigger.from_crontab(cron)
    except ValueError as exc:  # pragma: no cover - cron validation is deterministic
        typer.echo(f"Blad: niepoprawne wyrazenie cron ({exc}).")
        raise typer.Exit(code=1)

    python_exec = python.expanduser().resolve() if python else None
    working_directory = working_dir.expanduser().resolve() if working_dir else None

    if python_exec and not python_exec.exists():
        typer.echo(f"Blad: interpreter {python_exec} nie istnieje.")
        raise typer.Exit(code=1)

    if working_directory and not working_directory.exists():
        typer.echo(f"Blad: katalog roboczy {working_directory} nie istnieje.")
        raise typer.Exit(code=1)

    task = database.add_task(
        name=name,
        script_path=script_path,
        cron=cron,
        python_executable=python_exec,
        working_directory=working_directory,
    )
    console.print(f"[green]Dodano zadanie '{task.name}'.[/green]")


@app.command("list")
def list_tasks(ctx: typer.Context) -> None:
    """Wyswietl wszystkie zadania."""

    database: Database = ctx.obj["db"]
    tasks = database.list_tasks()
    if not tasks:
        console.print("[yellow]Brak zadan w bazie danych.[/yellow]")
        return

    table = Table(title="Zadania", header_style="bold blue")
    table.add_column("Nazwa")
    table.add_column("Skrypt")
    table.add_column("Cron")
    table.add_column("Interpreter")
    table.add_column("Katalog roboczy")
    table.add_column("Utworzono")

    for task in tasks:
        table.add_row(
            task.name,
            str(task.script_path),
            task.cron,
            str(task.python_executable) if task.python_executable else sys.executable,
            str(task.working_directory) if task.working_directory else "-",
            task.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        )

    console.print(table)


@app.command("remove")
def remove_task(ctx: typer.Context, name: str = typer.Argument(..., help="Nazwa zadania")) -> None:
    """Usun zadanie."""

    database: Database = ctx.obj["db"]
    if database.remove_task(name):
        console.print(f"[green]Usunieto zadanie '{name}'.[/green]")
    else:
        console.print(f"[yellow]Zadanie '{name}' nie zostalo znalezione.[/yellow]")


@app.command("runs")
def show_runs(
    ctx: typer.Context,
    name: Optional[str] = typer.Option(None, "--name", help="Filtruj po nazwie zadania"),
    limit: int = typer.Option(10, "--limit", help="Limit historii"),
) -> None:
    """Pokaz ostatnie uruchomienia."""

    database: Database = ctx.obj["db"]
    runs = database.recent_runs(limit=limit, task_name=name)
    if not runs:
        console.print("[yellow]Brak historii uruchomien.[/yellow]")
        return

    table = Table(title="Historia uruchomien", header_style="bold magenta")
    table.add_column("ID")
    table.add_column("Zadanie")
    table.add_column("Start")
    table.add_column("Koniec")
    table.add_column("Status")
    table.add_column("Kod wyjscia")
    table.add_column("stdout")
    table.add_column("stderr")
    table.add_column("Uwagi")

    for run in runs:
        task_label = run.task_name if run.task_name else str(run.task_id)
        table.add_row(
            str(run.id),
            task_label,
            run.started_at.strftime("%Y-%m-%d %H:%M:%S"),
            run.finished_at.strftime("%Y-%m-%d %H:%M:%S") if run.finished_at else "-",
            run.status,
            str(run.exit_code) if run.exit_code is not None else "-",
            str(run.stdout_path) if run.stdout_path else "-",
            str(run.stderr_path) if run.stderr_path else "-",
            run.message or "-",
        )

    console.print(table)


@app.command("run-once")
def run_once(ctx: typer.Context, name: str = typer.Argument(..., help="Nazwa zadania")) -> None:
    """Uruchom zadanie jednorazowo."""

    database: Database = ctx.obj["db"]
    task = database.get_task(name)
    if not task:
        console.print(f"[red]Zadanie '{name}' nie istnieje.[/red]")
        raise typer.Exit(code=1)

    console.print(f"[blue]Uruchamiam zadanie '{name}'...[/blue]")
    run_task(database, task, ctx.obj["data_dir"])


codex/add-update-script-for-main-branch
@app.command("update")
def update_application(
    repo_dir: Optional[Path] = typer.Option(
        None,
        "--repo-dir",
        help="Sciezka do repozytorium aplikacji (domyslnie katalog projektu)",
    ),
    branch: str = typer.Option("main", "--branch", help="Nazwa brancha do pobrania"),
    force: bool = typer.Option(
        False,
        "--force",
        help="Wymus nadpisanie lokalnych zmian (git reset --hard).",
    ),
) -> None:
    """Zaktualizuj aplikacje do najnowszej wersji z wybranego brancha."""

    target_dir = repo_dir.expanduser().resolve() if repo_dir else default_repository_root()
    console.print(
        f"[blue]Aktualizuje repozytorium {target_dir} z brancha '{branch}'...[/blue]"
    )

    try:
        output = update_repository(target_dir, branch=branch, force=force)
    except UpdateError as exc:
        console.print(f"[red]Aktualizacja nie powiodla sie: {exc}[/red]")
        raise typer.Exit(code=1)

    if output:
        console.print(f"[dim]{output}[/dim]")
    console.print("[green]Aktualizacja zakonczona sukcesem.[/green]")
=======
@app.command("gui")
def open_gui(ctx: typer.Context) -> None:
    """Uruchom interfejs graficzny do zarzadzania zadaniami."""

    from .gui import launch_gui

    database: Database = ctx.obj["db"]
    launch_gui(ctx.obj["data_dir"], database=database)
main


@app.command("start")
def start_scheduler(
    ctx: typer.Context,
    refresh: int = typer.Option(30, "--refresh", help="Co ile sekund aktualizowac harmonogram"),
) -> None:
    """Uruchom serwis harmonogramu."""

    database: Database = ctx.obj["db"]
    data_dir: Path = ctx.obj["data_dir"]
    run_scheduler_loop(database, data_dir, refresh_interval=refresh)


__all__ = ["app"]
