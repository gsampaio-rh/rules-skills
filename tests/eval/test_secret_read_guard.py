"""Tests for optional secret-read-guard.sh (beforeReadFile)."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
HOOK = REPO_ROOT / "library" / "cursor" / "hooks" / "secret-read-guard.sh"

_PYENV_ROOT = os.environ.get("PYENV_ROOT", str(Path.home() / ".pyenv"))
_HOOK_PATH = (
    f"{_PYENV_ROOT}/shims:{_PYENV_ROOT}/bin:"
    "/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
)


def _run(file_path: str) -> dict:
    env = {"PATH": _HOOK_PATH, "HOME": str(Path.home())}
    if "PYENV_VERSION" in os.environ:
        env["PYENV_VERSION"] = os.environ["PYENV_VERSION"]
    result = subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps({"file_path": file_path}),
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        env=env,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout.strip() or "{}")


class TestSecretReadGuard:
    def test_denies_dotenv(self) -> None:
        out = _run("/tmp/project/.env")
        assert out.get("permission") == "deny"

    def test_denies_dotenv_local(self) -> None:
        out = _run("/tmp/project/.env.local")
        assert out.get("permission") == "deny"

    def test_allows_env_example(self) -> None:
        out = _run("/tmp/project/.env.example")
        assert out.get("permission") != "deny"

    def test_denies_pem(self) -> None:
        out = _run("/tmp/project/certs/server.pem")
        assert out.get("permission") == "deny"

    def test_denies_id_rsa(self) -> None:
        out = _run("/home/u/.ssh/id_rsa")
        assert out.get("permission") == "deny"

    def test_allows_source(self) -> None:
        out = _run("/tmp/project/library/cursor/hooks/secret-read-guard.sh")
        assert out.get("permission") != "deny"

    def test_missing_path_fail_closed(self) -> None:
        env = {"PATH": _HOOK_PATH, "HOME": str(Path.home())}
        result = subprocess.run(
            ["bash", str(HOOK)],
            input="{}",
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            env=env,
            check=False,
        )
        assert result.returncode == 0
        out = json.loads(result.stdout.strip() or "{}")
        assert out.get("permission") == "deny"
