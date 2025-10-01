"""Configuration helpers for Script Manager."""
from __future__ import annotations

import os
import platform
from pathlib import Path

APP_NAME = "ScriptManager"


def default_data_dir() -> Path:
    """Return the default directory for storing persistent data.

    On Windows the data directory is created inside ``%ProgramData%`` so that it
    can be shared between users. On other platforms the directory lives inside
    the user's home folder.
    """

    system = platform.system()
    if system == "Windows":
        base = os.environ.get("PROGRAMDATA")
        if base:
            return Path(base) / APP_NAME
        # Fallback for environments where PROGRAMDATA is not defined
        return Path.home() / APP_NAME
    return Path.home() / f".{APP_NAME.lower()}"


def ensure_data_dir(path: Path) -> Path:
    """Create the data directory if it does not exist and return it."""

    path.mkdir(parents=True, exist_ok=True)
    return path


__all__ = ["default_data_dir", "ensure_data_dir", "APP_NAME"]
