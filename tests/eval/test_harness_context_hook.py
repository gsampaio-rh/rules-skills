"""Integration tests for library/cursor/hooks/harness-context.sh.

Invokes the hook directly with HARNESS_ROOT pointing at a fixture directory.
"""

import json
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
HOOK = REPO_ROOT / "library" / "cursor" / "hooks" / "harness-context.sh"

import os as _os
_PYENV_ROOT = _os.environ.get("PYENV_ROOT", str(Path.home() / ".pyenv"))
_HOOK_PATH = (
    f"{_PYENV_ROOT}/shims:{_PYENV_ROOT}/bin:"
    "/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
)


def run_hook(harness_root: Path) -> dict:
    """Run harness-context.sh with HARNESS_ROOT set, pipe stdin='{}', return parsed JSON."""
    env = {
        "HARNESS_ROOT": str(harness_root),
        "PATH": _HOOK_PATH,
        "HOME": str(Path.home()),
    }
    if "PYENV_VERSION" in _os.environ:
        env["PYENV_VERSION"] = _os.environ["PYENV_VERSION"]
    result = subprocess.run(
        ["bash", str(HOOK)],
        input="{}",
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0, f"Hook exited non-zero:\n{result.stderr}"
    raw = result.stdout.strip()
    assert raw, f"Hook produced empty stdout\nstderr: {result.stderr}"
    return json.loads(raw)


def _harness_dir(root: Path) -> Path:
    d = root / ".harness"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _write_state(root: Path, tasks: list, open_questions: list | None = None) -> None:
    state = {
        "project": "test", "schema_version": 2, "vision": "v", "direction": "d",
        "trade_offs": [], "open_questions": open_questions or [], "tasks": tasks,
    }
    (_harness_dir(root) / "state.json").write_text(json.dumps(state))


def _write_breadcrumbs(root: Path, entries: list[dict]) -> None:
    content = "\n".join(json.dumps(e) for e in entries) + "\n"
    (_harness_dir(root) / "breadcrumbs.jsonl").write_text(content)


def _session_start(ts: str) -> dict:
    return {"ts": ts, "role": "system", "type": "session_start",
            "feat": None, "msg": "New session", "result": "pass"}


def _build_pass(feat: str, ts: str = "2026-01-01T01:00:00Z") -> dict:
    return {"ts": ts, "role": "builder", "type": "build",
            "feat": feat, "msg": f"built {feat}", "result": "pass"}


# --- Core criteria ---

class TestCoreContext:
    def test_output_is_valid_json_with_additional_context(self, tmp_path):
        _write_state(tmp_path, tasks=[{"id": "feat-1", "name": "Test", "status": "pending"}])
        d = run_hook(tmp_path)
        assert "additional_context" in d
        assert isinstance(d["additional_context"], str)

    def test_additional_context_has_current_task_heading(self, tmp_path):
        _write_state(tmp_path, tasks=[{"id": "feat-1", "name": "Test", "status": "pending"}])
        d = run_hook(tmp_path)
        assert "## Current Task" in d["additional_context"]

    def test_additional_context_has_recent_breadcrumbs_heading(self, tmp_path):
        _write_state(tmp_path, tasks=[{"id": "feat-1", "name": "Test", "status": "pending"}])
        d = run_hook(tmp_path)
        assert "## Recent Breadcrumbs" in d["additional_context"]

    def test_inject_has_no_novel_session_advisories(self, tmp_path):
        """Slim: inject is context-package only — no SESSION BOUNDARY / overload prose."""
        _write_state(tmp_path, tasks=[{"id": "feat-1", "name": "Test", "status": "pending"}])
        entries = [
            _session_start("2026-01-01T00:00:00Z"),
            _build_pass("feat-1", "2026-01-01T01:00:00Z"),
            _build_pass("feat-2", "2026-01-01T02:00:00Z"),
            _build_pass("feat-3", "2026-01-01T03:00:00Z"),
        ]
        _write_breadcrumbs(tmp_path, entries)
        ctx = run_hook(tmp_path)["additional_context"]
        banned = ("SESSION BOUNDARY", "TASK OVERLOAD", "CONTRACT REQUIRED")
        for needle in banned:
            assert needle not in ctx, f"unexpected advisory: {needle}"
        assert "## Current Task" in ctx


# --- Prune advisory (>40 non-empty lines) ---

class TestAutoTruncation:
    def test_41_lines_gets_truncated_to_30(self, tmp_path):
        """Seed 40 entries → hook auto-truncates to last 30 + appends session_start."""
        _write_state(tmp_path, tasks=[])
        entries = [{"ts": f"2026-01-01T00:00:00Z", "role": "builder",
                    "type": "build", "msg": f"entry {i}", "result": "pass"}
                   for i in range(40)]
        _write_breadcrumbs(tmp_path, entries)
        d = run_hook(tmp_path)
        # After hook runs, breadcrumbs should be truncated (30 kept + 1 new session_start)
        bc_path = tmp_path / ".harness" / "breadcrumbs.jsonl"
        lines = [l for l in bc_path.read_text().splitlines() if l.strip()]
        assert len(lines) <= 31, f"Expected <=31 lines after truncation, got {len(lines)}"

    def test_30_lines_no_truncation(self, tmp_path):
        """Seed 29 lines → hook appends 1 session_start → 30 total → no truncation needed."""
        _write_state(tmp_path, tasks=[])
        entries = [{"ts": f"2026-01-01T00:00:00Z", "role": "builder",
                    "type": "build", "msg": f"entry {i}", "result": "pass"}
                   for i in range(29)]
        _write_breadcrumbs(tmp_path, entries)
        d = run_hook(tmp_path)
        bc_path = tmp_path / ".harness" / "breadcrumbs.jsonl"
        lines = [l for l in bc_path.read_text().splitlines() if l.strip()]
        assert len(lines) == 30, f"Expected 30 lines (29 + session_start), got {len(lines)}"


# --- Fallback / robustness ---

class TestFallback:
    def test_context_package_missing_still_exits_zero_with_fallback(self, tmp_path):
        """When context-package.py is missing/fails, hook exits 0 with lean fallback."""
        _write_state(tmp_path, tasks=[{"id": "feat-1", "name": "x", "status": "pending"}])
        _write_breadcrumbs(tmp_path, [])

        hook_src = HOOK.read_text()
        broken_hook = tmp_path / "broken-harness-context.sh"
        patched = hook_src.replace(
            'CONTEXT_PKG="$SCRIPT_DIR/context-package.py"',
            'CONTEXT_PKG="/nonexistent/path/context-package.py"',
        )
        broken_hook.write_text(patched)
        broken_hook.chmod(0o755)

        env = {
            "HARNESS_ROOT": str(tmp_path),
            "PATH": _HOOK_PATH,
            "HOME": str(Path.home()),
        }
        if "PYENV_VERSION" in _os.environ:
            env["PYENV_VERSION"] = _os.environ["PYENV_VERSION"]

        result = subprocess.run(
            ["bash", str(broken_hook)], input="{}", capture_output=True, text=True, env=env
        )
        assert result.returncode == 0, f"Non-zero exit:\n{result.stderr}"
        d = json.loads(result.stdout.strip())
        ctx = d["additional_context"]
        assert "Traceback" not in result.stdout, "No Python traceback on stdout"
        assert "context-package unavailable" in ctx, "Fallback text must indicate pkg unavailable"
        assert "SESSION BOUNDARY" not in ctx

    def test_cold_start_no_harness_files(self, tmp_path):
        """No state.json or contract.json → free-default / opt-in message, exit 0."""
        (tmp_path / ".harness").mkdir(parents=True, exist_ok=True)
        result = subprocess.run(
            ["bash", str(HOOK)],
            input="{}",
            capture_output=True,
            text=True,
            env={"HARNESS_ROOT": str(tmp_path),
                 "PATH": "/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin",
                 "HOME": str(Path.home())},
        )
        assert result.returncode == 0
        d = json.loads(result.stdout.strip())
        assert "additional_context" in d
        ctx = d["additional_context"].lower()
        assert "work freely" in ctx or "opt in" in ctx
