"""Unit tests for harness-gate.sh cold-start routing.

Skill discovery is host-owned; harness-gate only sets .routing-pending + planner advisory.
"""

import json
import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
HOOK = REPO_ROOT / "library" / "cursor" / "hooks" / "harness-gate.sh"

_PYENV_ROOT = os.environ.get("PYENV_ROOT", str(Path.home() / ".pyenv"))
_HOOK_PATH = (
    f"{_PYENV_ROOT}/shims:{_PYENV_ROOT}/bin:"
    "/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
)


def run_hook(prompt: str, cwd: Path) -> dict:
    env = {
        "PATH": _HOOK_PATH,
        "HOME": str(Path.home()),
    }
    if "PYENV_VERSION" in os.environ:
        env["PYENV_VERSION"] = os.environ["PYENV_VERSION"]
    result = subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps({"prompt": prompt}),
        capture_output=True,
        text=True,
        cwd=str(cwd),
        env=env,
    )
    assert result.returncode == 0, f"Hook exited non-zero:\n{result.stderr}"
    raw = result.stdout.strip()
    assert raw, f"Hook produced empty stdout\nstderr: {result.stderr}"
    return json.loads(raw)


def _write_state(path: Path) -> None:
    state = {
        "project": "test",
        "schema_version": 2,
        "vision": "v",
        "tasks": [{"id": "t1", "name": "x", "status": "pending"}],
    }
    harness = path / ".harness"
    harness.mkdir(parents=True, exist_ok=True)
    (harness / "state.json").write_text(json.dumps(state))


class TestColdStartRouting:
    def test_nontrivial_cold_start_routes_and_sets_marker(self, tmp_path):
        d = run_hook("migra o banco", tmp_path)
        assert "followup_message" in d
        assert "HARNESS ROUTING" in d["followup_message"]
        assert (tmp_path / ".harness" / ".routing-pending").is_file()

    def test_simple_pattern_cold_start_does_not_route(self, tmp_path):
        d = run_hook("review my code", tmp_path)
        assert d == {}
        assert not (tmp_path / ".harness" / ".routing-pending").exists()


class TestHarnessActiveSkipsRouting:
    def test_active_harness_no_routing(self, tmp_path):
        _write_state(tmp_path)
        d = run_hook("migra o banco agora por favor", tmp_path)
        assert d == {}
        assert "HARNESS ROUTING" not in d.get("followup_message", "")


class TestGlueAndOptOut:
    def test_ok_glue(self, tmp_path):
        assert run_hook("ok", tmp_path) == {}

    def test_skip_harness_opt_out(self, tmp_path):
        assert run_hook("skip harness and just fix the typo", tmp_path) == {}
