"""Tests for optional agents-md-nudge.sh (sessionStart)."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
HOOK = REPO_ROOT / "library" / "cursor" / "hooks" / "agents-md-nudge.sh"

_PYENV_ROOT = os.environ.get("PYENV_ROOT", str(Path.home() / ".pyenv"))
_HOOK_PATH = (
    f"{_PYENV_ROOT}/shims:{_PYENV_ROOT}/bin:"
    "/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
)


def _run(root: Path) -> tuple[dict, int]:
    env = {
        "PATH": _HOOK_PATH,
        "HOME": str(Path.home()),
        "HARNESS_ROOT": str(root),
    }
    if "PYENV_VERSION" in os.environ:
        env["PYENV_VERSION"] = os.environ["PYENV_VERSION"]
    result = subprocess.run(
        ["bash", str(HOOK)],
        input="{}",
        capture_output=True,
        text=True,
        cwd=str(root),
        env=env,
        check=False,
    )
    out = json.loads(result.stdout.strip() or "{}")
    return out, result.returncode


class TestAgentsMdNudge:
    def test_absent_agents_md_nudges(self, tmp_path: Path) -> None:
        out, code = _run(tmp_path)
        assert code == 0
        ctx = out.get("additional_context") or ""
        assert "adopt-agents-md" in ctx
        assert "agents-bootstrap" in ctx
        assert len(ctx) <= 200
        assert "\n\n" not in ctx
        assert not (tmp_path / "AGENTS.md").exists()

    def test_present_agents_md_silent(self, tmp_path: Path) -> None:
        agents = tmp_path / "AGENTS.md"
        agents.write_text("ok\n")
        out, code = _run(tmp_path)
        assert code == 0
        assert not out.get("additional_context")
        assert agents.read_text() == "ok\n"

    def test_exit_zero_when_nudging(self, tmp_path: Path) -> None:
        _, code = _run(tmp_path)
        assert code == 0
