"""Tkinter GUI for managing custom scripts."""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

from script_store import Script, ScriptRepository


class ScriptManagerApp(tk.Tk):
    """Main window that allows users to manage scripts."""

    def __init__(self) -> None:
        super().__init__()
        self.title("Script Manager")
        self.geometry("640x400")
        self.resizable(True, True)

        self.repository = ScriptRepository()

        self.name_var = tk.StringVar()
        self.command_var = tk.StringVar()
        self.description_text: tk.Text | None = None

        self.script_listbox: tk.Listbox | None = None

        self._build_layout()
        self.refresh_script_list()

    # Layout -----------------------------------------------------------------
    def _build_layout(self) -> None:
        self.columnconfigure(0, weight=3)
        self.columnconfigure(1, weight=2)
        self.rowconfigure(0, weight=1)

        list_frame = tk.Frame(self, padx=10, pady=10)
        list_frame.grid(row=0, column=0, sticky="nsew")
        list_frame.rowconfigure(1, weight=1)

        tk.Label(list_frame, text="Zdefiniowane skrypty", font=("TkDefaultFont", 12, "bold")).grid(
            row=0, column=0, sticky="w"
        )

        self.script_listbox = tk.Listbox(list_frame, height=15)
        self.script_listbox.grid(row=1, column=0, sticky="nsew", pady=(5, 0))

        scrollbar = tk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.script_listbox.yview)
        scrollbar.grid(row=1, column=1, sticky="ns")
        self.script_listbox.configure(yscrollcommand=scrollbar.set)

        form_frame = tk.LabelFrame(self, text="Dodaj nowy skrypt", padx=10, pady=10)
        form_frame.grid(row=0, column=1, sticky="nsew", padx=(0, 10), pady=10)
        form_frame.columnconfigure(1, weight=1)

        tk.Label(form_frame, text="Nazwa:").grid(row=0, column=0, sticky="w", pady=5)
        name_entry = tk.Entry(form_frame, textvariable=self.name_var)
        name_entry.grid(row=0, column=1, sticky="ew", pady=5)

        tk.Label(form_frame, text="Polecenie:").grid(row=1, column=0, sticky="w", pady=5)
        command_entry = tk.Entry(form_frame, textvariable=self.command_var)
        command_entry.grid(row=1, column=1, sticky="ew", pady=5)

        tk.Label(form_frame, text="Opis (opcjonalny):").grid(row=2, column=0, sticky="nw", pady=5)
        self.description_text = tk.Text(form_frame, height=6, wrap=tk.WORD)
        self.description_text.grid(row=2, column=1, sticky="nsew", pady=5)
        form_frame.rowconfigure(2, weight=1)

        add_button = tk.Button(form_frame, text="Dodaj skrypt", command=self.add_script)
        add_button.grid(row=3, column=0, columnspan=2, pady=(10, 0), sticky="ew")

        name_entry.focus_set()

    # Data handling ----------------------------------------------------------
    def refresh_script_list(self) -> None:
        scripts = self.repository.load_scripts()
        if not self.script_listbox:
            return

        self.script_listbox.delete(0, tk.END)
        for script in scripts:
            description = f" – {script.description}" if script.description else ""
            self.script_listbox.insert(tk.END, f"{script.name}: {script.command}{description}")

    def add_script(self) -> None:
        name = self.name_var.get().strip()
        command = self.command_var.get().strip()
        description = self.description_text.get("1.0", tk.END).strip() if self.description_text else ""

        if not name:
            messagebox.showerror("Błąd", "Nazwa skryptu jest wymagana.")
            return

        if not command:
            messagebox.showerror("Błąd", "Polecenie skryptu jest wymagane.")
            return

        script = Script(name=name, command=command, description=description)

        try:
            self.repository.add_script(script)
        except ValueError as exc:
            messagebox.showerror("Błąd", str(exc))
            return

        self.refresh_script_list()
        self._clear_form()
        messagebox.showinfo("Sukces", f"Dodano skrypt '{script.name}'.")

    def _clear_form(self) -> None:
        self.name_var.set("")
        self.command_var.set("")
        if self.description_text:
            self.description_text.delete("1.0", tk.END)


def main() -> None:
    app = ScriptManagerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
