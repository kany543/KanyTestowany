"""Simple Tkinter-based GUI for managing scheduled scripts."""
from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Optional

from apscheduler.triggers.cron import CronTrigger

from .config import APP_NAME, default_data_dir, ensure_data_dir
from .db import Database


class ScriptManagerGUI:
    """Tkinter window that allows managing tasks stored in the database."""

    def __init__(self, root: tk.Tk, database: Database) -> None:
        self.root = root
        self.database = database
        self.root.title(f"{APP_NAME} - GUI")
        self.root.geometry("1000x600")

        self._build_widgets()
        self.refresh_tasks()

    # ------------------------------------------------------------------
    # UI construction helpers
    def _build_widgets(self) -> None:
        top_frame = ttk.Frame(self.root)
        top_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Tasks tree
        tasks_label = ttk.Label(top_frame, text="Zadania")
        tasks_label.pack(anchor=tk.W)

        columns = ("script", "cron", "python", "cwd", "created")
        self.tasks_tree = ttk.Treeview(
            top_frame,
            columns=columns,
            show="headings",
            height=10,
        )
        headings = {
            "script": "Skrypt",
            "cron": "Cron",
            "python": "Interpreter",
            "cwd": "Katalog roboczy",
            "created": "Utworzono",
        }
        for col, title in headings.items():
            self.tasks_tree.heading(col, text=title)
            self.tasks_tree.column(col, width=180, anchor=tk.W)

        self.tasks_tree.pack(fill=tk.BOTH, expand=True)
        self.tasks_tree.bind("<<TreeviewSelect>>", lambda event: self.refresh_runs())

        buttons_frame = ttk.Frame(top_frame)
        buttons_frame.pack(fill=tk.X, pady=(10, 0))

        add_btn = ttk.Button(buttons_frame, text="Dodaj", command=self.open_add_dialog)
        add_btn.pack(side=tk.LEFT)

        remove_btn = ttk.Button(buttons_frame, text="Usun", command=self.remove_selected_task)
        remove_btn.pack(side=tk.LEFT, padx=(5, 0))

        refresh_btn = ttk.Button(buttons_frame, text="Odswiez", command=self.refresh_tasks)
        refresh_btn.pack(side=tk.LEFT, padx=(5, 0))

        runs_frame = ttk.LabelFrame(self.root, text="Historia uruchomien")
        runs_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        runs_columns = ("task", "start", "finish", "status", "exit", "message")
        self.runs_tree = ttk.Treeview(
            runs_frame,
            columns=runs_columns,
            show="headings",
            height=8,
        )
        runs_headings = {
            "task": "Zadanie",
            "start": "Start",
            "finish": "Koniec",
            "status": "Status",
            "exit": "Kod wyjscia",
            "message": "Uwagi",
        }
        for col, title in runs_headings.items():
            self.runs_tree.heading(col, text=title)
            anchor = tk.W if col != "exit" else tk.CENTER
            self.runs_tree.column(col, width=150, anchor=anchor)

        self.runs_tree.pack(fill=tk.BOTH, expand=True)

    # ------------------------------------------------------------------
    # Task management
    def refresh_tasks(self) -> None:
        for item in self.tasks_tree.get_children():
            self.tasks_tree.delete(item)

        for task in self.database.list_tasks():
            python_exec = task.python_executable or Path(sys.executable)
            working_dir = task.working_directory or Path("-")
            created_at = task.created_at.strftime("%Y-%m-%d %H:%M:%S")
            self.tasks_tree.insert(
                "",
                tk.END,
                iid=task.name,
                values=(
                    str(task.script_path),
                    task.cron,
                    str(python_exec),
                    str(working_dir),
                    created_at,
                ),
            )

        self.refresh_runs()

    def open_add_dialog(self) -> None:
        dialog = tk.Toplevel(self.root)
        dialog.title("Dodaj zadanie")
        dialog.grab_set()

        form_fields = (
            ("Nazwa", "name"),
            ("Skrypt", "script"),
            ("Cron", "cron"),
            ("Interpreter", "python"),
            ("Katalog roboczy", "cwd"),
        )

        entries: dict[str, tk.Entry] = {}

        for idx, (label, key) in enumerate(form_fields):
            ttk.Label(dialog, text=label).grid(row=idx, column=0, sticky=tk.W, padx=5, pady=5)
            entry = ttk.Entry(dialog, width=60)
            entry.grid(row=idx, column=1, padx=5, pady=5)
            entries[key] = entry

        # Buttons for selecting files/directories
        script_btn = ttk.Button(
            dialog,
            text="Wybierz",
            command=lambda: self._choose_file(entries["script"]),
        )
        script_btn.grid(row=1, column=2, padx=5, pady=5)

        python_btn = ttk.Button(
            dialog,
            text="Wybierz",
            command=lambda: self._choose_file(entries["python"]),
        )
        python_btn.grid(row=3, column=2, padx=5, pady=5)

        cwd_btn = ttk.Button(
            dialog,
            text="Wybierz",
            command=lambda: self._choose_directory(entries["cwd"]),
        )
        cwd_btn.grid(row=4, column=2, padx=5, pady=5)

        buttons_frame = ttk.Frame(dialog)
        buttons_frame.grid(row=len(form_fields), column=0, columnspan=3, pady=10)

        submit_btn = ttk.Button(
            buttons_frame,
            text="Zapisz",
            command=lambda: self._create_task(dialog, entries),
        )
        submit_btn.pack(side=tk.LEFT, padx=5)

        cancel_btn = ttk.Button(buttons_frame, text="Anuluj", command=dialog.destroy)
        cancel_btn.pack(side=tk.LEFT)

    def _choose_file(self, entry: tk.Entry) -> None:
        file_path = filedialog.askopenfilename(parent=self.root)
        if file_path:
            entry.delete(0, tk.END)
            entry.insert(0, file_path)

    def _choose_directory(self, entry: tk.Entry) -> None:
        directory = filedialog.askdirectory(parent=self.root)
        if directory:
            entry.delete(0, tk.END)
            entry.insert(0, directory)

    def _create_task(self, dialog: tk.Toplevel, entries: dict[str, tk.Entry]) -> None:
        name = entries["name"].get().strip()
        script = entries["script"].get().strip()
        cron = entries["cron"].get().strip()
        python_exec = entries["python"].get().strip() or None
        working_dir = entries["cwd"].get().strip() or None

        if not name or not script or not cron:
            messagebox.showerror("Blad", "Nazwa, skrypt i cron sa wymagane.", parent=dialog)
            return

        script_path = Path(script).expanduser()
        if not script_path.exists():
            messagebox.showerror("Blad", "Wybrany skrypt nie istnieje.", parent=dialog)
            return

        try:
            CronTrigger.from_crontab(cron)
        except ValueError as exc:
            messagebox.showerror("Blad", f"Niepoprawne wyrazenie cron: {exc}", parent=dialog)
            return

        python_path = Path(python_exec).expanduser() if python_exec else None
        if python_path and not python_path.exists():
            messagebox.showerror("Blad", "Podany interpreter nie istnieje.", parent=dialog)
            return

        working_path = Path(working_dir).expanduser() if working_dir else None
        if working_path and not working_path.exists():
            messagebox.showerror("Blad", "Katalog roboczy nie istnieje.", parent=dialog)
            return

        try:
            self.database.add_task(
                name=name,
                script_path=script_path,
                cron=cron,
                python_executable=python_path,
                working_directory=working_path,
            )
        except Exception as exc:  # pragma: no cover - GUI feedback
            messagebox.showerror("Blad", f"Nie udalo sie dodac zadania: {exc}", parent=dialog)
            return

        dialog.destroy()
        self.refresh_tasks()

    def remove_selected_task(self) -> None:
        selection = self.tasks_tree.selection()
        if not selection:
            messagebox.showinfo("Informacja", "Wybierz zadanie do usuniecia.", parent=self.root)
            return

        task_name = selection[0]
        if messagebox.askyesno("Potwierdzenie", f"Czy na pewno usunac zadanie '{task_name}'?", parent=self.root):
            removed = self.database.remove_task(task_name)
            if not removed:
                messagebox.showerror("Blad", "Nie znaleziono zadania do usuniecia.", parent=self.root)
            self.refresh_tasks()

    # ------------------------------------------------------------------
    # Runs history
    def refresh_runs(self) -> None:
        for item in self.runs_tree.get_children():
            self.runs_tree.delete(item)

        selection = self.tasks_tree.selection()
        task_name = selection[0] if selection else None

        runs = self.database.recent_runs(limit=20, task_name=task_name)
        for run in runs:
            finished = run.finished_at.strftime("%Y-%m-%d %H:%M:%S") if run.finished_at else "-"
            exit_code = str(run.exit_code) if run.exit_code is not None else "-"
            message = run.message or ""
            started = run.started_at.strftime("%Y-%m-%d %H:%M:%S")
            task_label = run.task_name or str(run.task_id)
            self.runs_tree.insert(
                "",
                tk.END,
                values=(
                    task_label,
                    started,
                    finished,
                    run.status,
                    exit_code,
                    message,
                ),
            )


def _resolve_data_dir(custom: Optional[Path]) -> Path:
    if custom:
        return ensure_data_dir(custom.expanduser())
    return ensure_data_dir(default_data_dir())


def launch_gui(
    data_dir: Optional[Path] = None,
    *,
    database: Optional[Database] = None,
) -> None:
    """Initialise the database (if needed) and display the GUI."""

    db = database
    if db is None:
        resolved_dir = _resolve_data_dir(data_dir)
        db = Database(resolved_dir / "script-manager.db")
        db.initialise()

    root = tk.Tk()
    ScriptManagerGUI(root, db)
    root.mainloop()


__all__ = ["launch_gui", "ScriptManagerGUI"]
