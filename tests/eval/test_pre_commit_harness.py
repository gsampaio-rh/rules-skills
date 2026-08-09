"""Pytest coverage for pre-commit-harness.sh (commit gate + secrets deny)."""

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
HOOK = REPO_ROOT / "library" / "cursor" / "hooks" / "pre-commit-harness.sh"

_PYENV_ROOT = os.environ.get("PYENV_ROOT", str(Path.home() / ".pyenv"))
_HOOK_PATH = (
    f"{_PYENV_ROOT}/shims:{_PYENV_ROOT}/bin:"
    "/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
)


def _env(cwd: Path) -> dict:
    env = {
        "PATH": _HOOK_PATH,
        "HOME": str(Path.home()),
        "GIT_AUTHOR_NAME": "Test",
        "GIT_AUTHOR_EMAIL": "test@example.com",
        "GIT_COMMITTER_NAME": "Test",
        "GIT_COMMITTER_EMAIL": "test@example.com",
    }
    if "PYENV_VERSION" in os.environ:
        env["PYENV_VERSION"] = os.environ["PYENV_VERSION"]
    return env


def _git_init(cwd: Path) -> None:
    subprocess.run(["git", "init"], cwd=cwd, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=cwd,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=cwd,
        check=True,
        capture_output=True,
    )


def _run(cwd: Path, command: str) -> dict:
    result = subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps({"command": command}),
        capture_output=True,
        text=True,
        cwd=str(cwd),
        env=_env(cwd),
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout.strip() or "{}")


def _approve(cwd: Path, *, age_sec: int | None = None) -> Path:
    d = cwd / ".cursor" / "hooks"
    d.mkdir(parents=True, exist_ok=True)
    p = d / ".commit-approved"
    p.write_text("ok\n")
    if age_sec is not None:
        past = time.time() - age_sec
        os.utime(p, (past, past))
    return p


class TestPreCommitHarness:
    def test_non_commit_allows(self, tmp_path: Path) -> None:
        _git_init(tmp_path)
        out = _run(tmp_path, "git status")
        assert out.get("permission") == "allow"

    def test_deny_without_commit_approved(self, tmp_path: Path) -> None:
        _git_init(tmp_path)
        out = _run(tmp_path, 'git commit -m "sneaky"')
        assert out.get("permission") == "deny"
        assert "approval" in out.get("agent_message", "").lower() or "COMMIT BLOCKED" in out.get(
            "agent_message", ""
        )

    def test_allow_with_fresh_flag(self, tmp_path: Path) -> None:
        _git_init(tmp_path)
        (tmp_path / "f.txt").write_text("x\n")
        subprocess.run(["git", "add", "f.txt"], cwd=tmp_path, check=True, capture_output=True)
        _approve(tmp_path)
        out = _run(tmp_path, 'git commit -m "ok commit"')
        assert out.get("permission") == "allow"
        assert not (tmp_path / ".cursor" / "hooks" / ".commit-approved").exists()

    def test_deny_stale_flag(self, tmp_path: Path) -> None:
        _git_init(tmp_path)
        _approve(tmp_path, age_sec=301)
        out = _run(tmp_path, 'git commit -m "stale"')
        assert out.get("permission") == "deny"
        assert "stale" in out.get("agent_message", "").lower()

    def test_deny_staged_dotenv(self, tmp_path: Path) -> None:
        _git_init(tmp_path)
        env_file = tmp_path / ".env"
        env_file.write_text("SECRET=1\n")
        subprocess.run(["git", "add", ".env"], cwd=tmp_path, check=True, capture_output=True)
        _approve(tmp_path)  # even with approval, secrets must deny
        out = _run(tmp_path, 'git commit -m "leak"')
        assert out.get("permission") == "deny"
        msg = out.get("agent_message", "").lower()
        assert "secret" in msg or ".env" in msg
