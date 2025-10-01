"""Utility classes for managing script metadata stored in JSON."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, List


@dataclass(slots=True)
class Script:
    """Represents a user-defined script entry."""

    name: str
    command: str
    description: str = ""


class ScriptRepository:
    """Stores and retrieves scripts from a JSON file."""

    def __init__(self, storage_path: str | Path = "scripts.json") -> None:
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_storage_exists()

    def _ensure_storage_exists(self) -> None:
        if not self.storage_path.exists():
            self.storage_path.write_text("[]\n", encoding="utf-8")

    def load_scripts(self) -> List[Script]:
        data = json.loads(self.storage_path.read_text(encoding="utf-8"))
        scripts: List[Script] = []
        for item in data:
            scripts.append(
                Script(
                    name=item.get("name", ""),
                    command=item.get("command", ""),
                    description=item.get("description", ""),
                )
            )
        return scripts

    def save_scripts(self, scripts: Iterable[Script]) -> None:
        payload = [asdict(script) for script in scripts]
        self.storage_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def add_script(self, script: Script) -> None:
        scripts = self.load_scripts()
        if any(existing.name.lower() == script.name.lower() for existing in scripts):
            raise ValueError(f"Script '{script.name}' already exists.")
        scripts.append(script)
        self.save_scripts(scripts)

    def remove_script(self, name: str) -> None:
        name = name.lower()
        scripts = [script for script in self.load_scripts() if script.name.lower() != name]
        self.save_scripts(scripts)


__all__ = ["Script", "ScriptRepository"]
