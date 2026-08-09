"""Pytest coverage for evaluator-guard.sh (sacred deny spine)."""

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
HOOK = REPO_ROOT / "library" / "cursor" / "hooks" / "evaluator-guard.sh"

_PYENV_ROOT = os.environ.get("PYENV_ROOT", str(Path.home() / ".pyenv"))
_HOOK_PATH = (
    f"{_PYENV_ROOT}/shims:{_PYENV_ROOT}/bin:"
    "/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
)


def _env(cwd: Path) -> dict:
    env = {
        "PATH": _HOOK_PATH,
        "HOME": str(Path.home()),
    }
    if "PYENV_VERSION" in os.environ:
        env["PYENV_VERSION"] = os.environ["PYENV_VERSION"]
    return env


def _run(cwd: Path, stdin: str) -> dict:
    result = subprocess.run(
        ["bash", str(HOOK)],
        input=stdin,
        capture_output=True,
        text=True,
        cwd=str(cwd),
        env=_env(cwd),
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout.strip() or "{}")


def _flag(cwd: Path, *, age_sec: int | None = None) -> Path:
    d = cwd / ".cursor" / "hooks"
    d.mkdir(parents=True, exist_ok=True)
    p = d / ".evaluator-active"
    p.write_text("")
    if age_sec is not None:
        past = time.time() - age_sec
        os.utime(p, (past, past))
    return p


class TestEvaluatorGuard:
    def test_no_flag_allows_impl_write(self, tmp_path: Path) -> None:
        out = _run(tmp_path, json.dumps({"input": {"path": "src/app.py"}}))
        assert out.get("permission") != "deny"
        assert out == {} or out.get("permission") == "allow"

    def test_active_denies_impl_write(self, tmp_path: Path) -> None:
        _flag(tmp_path)
        out = _run(tmp_path, json.dumps({"input": {"path": "src/app.py"}}))
        assert out.get("permission") == "deny"
        assert "EVALUATOR" in out.get("agent_message", "").upper()

    def test_active_allows_harness_write(self, tmp_path: Path) -> None:
        _flag(tmp_path)
        out = _run(
            tmp_path,
            json.dumps({"input": {"path": ".harness/breadcrumbs.jsonl"}}),
        )
        assert out.get("permission") != "deny"

    def test_stale_flag_allows_impl_write(self, tmp_path: Path) -> None:
        _flag(tmp_path, age_sec=1801)
        out = _run(tmp_path, json.dumps({"input": {"path": "src/app.py"}}))
        assert out.get("permission") != "deny"
        assert not (tmp_path / ".cursor" / "hooks" / ".evaluator-active").exists()

    def test_tool_input_filepath_denied(self, tmp_path: Path) -> None:
        _flag(tmp_path)
        out = _run(
            tmp_path,
            json.dumps({"toolInput": {"filePath": "src/app.py"}}),
        )
        assert out.get("permission") == "deny"
