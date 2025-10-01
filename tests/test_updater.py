from pathlib import Path

import pytest

from script_manager import updater


def _fake_git_available(monkeypatch) -> None:
    monkeypatch.setattr(updater.shutil, "which", lambda _: "/usr/bin/git")


def test_update_repository_runs_expected_commands(tmp_path, monkeypatch):
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    (repo_dir / ".git").mkdir()

    _fake_git_available(monkeypatch)

    executed = []

    def fake_run(cmd, cwd):
        executed.append((tuple(cmd), Path(cwd)))
        if cmd == ["git", "status", "--porcelain"]:
            return ""
        return "ok"

    monkeypatch.setattr(updater, "_run_git_command", fake_run)

    updater.update_repository(repo_dir, branch="main", force=False)

    assert executed == [
        (("git", "status", "--porcelain"), repo_dir),
        (("git", "fetch", "origin", "main"), repo_dir),
        (("git", "checkout", "main"), repo_dir),
        (("git", "pull", "--ff-only", "origin", "main"), repo_dir),
    ]


def test_update_repository_requires_clean_state(tmp_path, monkeypatch):
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    (repo_dir / ".git").mkdir()

    _fake_git_available(monkeypatch)

    def fake_run(cmd, cwd):
        if cmd == ["git", "status", "--porcelain"]:
            return " M file.py"
        return ""

    monkeypatch.setattr(updater, "_run_git_command", fake_run)

    with pytest.raises(updater.UpdateError):
        updater.update_repository(repo_dir)


def test_update_repository_checks_git_available(tmp_path, monkeypatch):
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    (repo_dir / ".git").mkdir()

    monkeypatch.setattr(updater.shutil, "which", lambda _: None)

    with pytest.raises(updater.UpdateError):
        updater.update_repository(repo_dir)
