"""Entry point for the ``script-manager`` command."""
from __future__ import annotations

from .cli import app

__all__ = ["app"]


if __name__ == "__main__":
    app()
