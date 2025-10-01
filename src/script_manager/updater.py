"""Utilities for updating the local installation from the Git repository."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Iterable, List


class UpdateError(RuntimeError):
    """Raised when the application update process cannot be completed."""


def default_repository_root() -> Path:
    """Return the project root directory (the git repository).

    The function assumes the package uses the ``src`` layout and therefore the
    repository root is two levels above this module.
    """

    return Path(__file__).resolve().parents[2]


def _ensure_git_available() -> None:
    if shutil.which("git") is None:
        raise UpdateError("Polecenie 'git' nie jest dostepne w systemie.")


def _run_git_command(args: Iterable[str], cwd: Path) -> str:
    result = subprocess.run(
        list(args),
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise UpdateError(result.stdout.strip() or "Niepowodzenie polecenia git.")
    return result.stdout


def _ensure_repository(repo_dir: Path) -> None:
    if not repo_dir.exists():
        raise UpdateError(f"Katalog {repo_dir} nie istnieje.")
    if not (repo_dir / ".git").exists():
        raise UpdateError(f"Katalog {repo_dir} nie jest repozytorium git.")


def update_repository(repo_dir: Path, branch: str = "main", force: bool = False) -> str:
    """Update the repository to the newest commit from ``branch``.

    Args:
        repo_dir: Path to the repository root directory.
        branch: Name of the branch to update from (defaults to ``main``).
        force: When ``True`` discard any local changes by performing
            ``git reset --hard``.

    Returns:
        Aggregated textual output of the executed git commands.

    Raises:
        UpdateError: When the repository cannot be updated.
    """

    repo_dir = repo_dir.expanduser().resolve()
    _ensure_git_available()
    _ensure_repository(repo_dir)

    output: List[str] = []

    status_output = _run_git_command(["git", "status", "--porcelain"], repo_dir)
    if status_output.strip() and not force:
        raise UpdateError(
            "Repozytorium zawiera lokalne zmiany. Uzyj opcji --force aby je nadpisac."
        )
    output.append(status_output)

    output.append(_run_git_command(["git", "fetch", "origin", branch], repo_dir))
    output.append(_run_git_command(["git", "checkout", branch], repo_dir))

    if force:
        output.append(
            _run_git_command(["git", "reset", "--hard", f"origin/{branch}"], repo_dir)
        )
    else:
        output.append(
            _run_git_command(["git", "pull", "--ff-only", "origin", branch], repo_dir)
        )

    return "\n".join(filter(None, (part.strip() for part in output)))


__all__ = ["UpdateError", "default_repository_root", "update_repository"]

