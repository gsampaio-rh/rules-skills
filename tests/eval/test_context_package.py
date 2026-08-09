"""Tests for library/cursor/hooks/context-package.py"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "library" / "cursor" / "hooks" / "context-package.py"


def run_pkg(*args, root: Path) -> subprocess.CompletedProcess:
    cmd = [sys.executable, str(SCRIPT), "--root", str(root), *args]
    return subprocess.run(cmd, capture_output=True, text=True)


def _setup(root: Path, state: dict | None = None, contract: dict | None = None,
           breadcrumbs: list[dict] | None = None, raw_breadcrumbs: str | None = None):
    harness = root / ".harness"
    harness.mkdir(parents=True, exist_ok=True)

    if state is not None:
        (harness / "state.json").write_text(json.dumps(state))
    if contract is not None:
        (harness / "contract.json").write_text(json.dumps(contract))
    if breadcrumbs is not None:
        (harness / "breadcrumbs.jsonl").write_text(
            "\n".join(json.dumps(b) for b in breadcrumbs) + "\n"
        )
    if raw_breadcrumbs is not None:
        (harness / "breadcrumbs.jsonl").write_text(raw_breadcrumbs)


def _state(tasks=None):
    return {
        "project": "test",
        "schema_version": 2,
        "vision": "v",
        "tasks": tasks or [],
    }


def _task(id_="feat-1", name="My feature", status="pending"):
    return {"id": id_, "name": name, "status": status}


def _contract(task_id="feat-1", ac=None, phase="building"):
    return {
        "task_id": task_id,
        "acceptance_criteria": ac or ["AC 1", "AC 2"],
        "phase": phase,
        "verified": False,
    }


def _bc(i: int):
    return {"ts": f"2026-06-01T0{i}:00:00+00:00", "role": "builder", "type": "build",
            "feat": "feat-1", "msg": f"breadcrumb {i}", "result": "pass"}


# --- JSON schema ---

class TestJsonSchema:
    def test_top_level_keys(self, tmp_path):
        _setup(tmp_path, state=_state(tasks=[_task()]), contract=_contract())
        result = run_pkg(root=tmp_path)
        assert result.returncode == 0
        d = json.loads(result.stdout)
        assert set(d) == {"task", "contract", "breadcrumbs"}

    def test_task_fields(self, tmp_path):
        _setup(tmp_path, state=_state(tasks=[_task("feat-2", "Do thing", "building")]))
        result = run_pkg(root=tmp_path)
        d = json.loads(result.stdout)
        assert d["task"] == {"id": "feat-2", "name": "Do thing", "status": "building"}

    def test_contract_fields(self, tmp_path):
        _setup(tmp_path, state=_state(tasks=[_task()]),
               contract=_contract(task_id="feat-1", ac=["C1"], phase="evaluating"))
        result = run_pkg(root=tmp_path)
        d = json.loads(result.stdout)
        assert d["contract"]["task_id"] == "feat-1"
        assert d["contract"]["acceptance_criteria"] == ["C1"]
        assert d["contract"]["phase"] == "evaluating"
        assert d["contract"]["verified"] is False

    def test_breadcrumbs_are_parsed_objects(self, tmp_path):
        bcs = [_bc(i) for i in range(3)]
        _setup(tmp_path, state=_state(tasks=[_task()]), breadcrumbs=bcs)
        result = run_pkg(root=tmp_path)
        d = json.loads(result.stdout)
        assert isinstance(d["breadcrumbs"], list)
        assert all(isinstance(b, dict) for b in d["breadcrumbs"])
        assert d["breadcrumbs"][0]["msg"] == "breadcrumb 0"


# --- Active task selection ---

class TestActiveTaskSelection:
    def test_first_pending_selected(self, tmp_path):
        tasks = [_task("feat-1", "one", "verified"), _task("feat-2", "two", "pending")]
        _setup(tmp_path, state=_state(tasks=tasks))
        result = run_pkg(root=tmp_path)
        d = json.loads(result.stdout)
        assert d["task"]["id"] == "feat-2"

    def test_evaluating_is_active(self, tmp_path):
        _setup(tmp_path, state=_state(tasks=[_task("feat-1", "x", "evaluating")]))
        result = run_pkg(root=tmp_path)
        d = json.loads(result.stdout)
        assert d["task"]["status"] == "evaluating"

    def test_no_active_task_is_null(self, tmp_path):
        tasks = [_task("feat-1", "done", "verified"), _task("feat-2", "done", "committed")]
        _setup(tmp_path, state=_state(tasks=tasks))
        result = run_pkg(root=tmp_path)
        assert result.returncode == 0
        d = json.loads(result.stdout)
        assert d["task"] is None

    def test_empty_tasks_task_null(self, tmp_path):
        _setup(tmp_path, state=_state(tasks=[]))
        result = run_pkg(root=tmp_path)
        assert result.returncode == 0
        d = json.loads(result.stdout)
        assert d["task"] is None


# --- Missing files ---

class TestMissingFiles:
    def test_missing_contract_is_null(self, tmp_path):
        _setup(tmp_path, state=_state(tasks=[_task()]))
        # No contract.json
        result = run_pkg(root=tmp_path)
        assert result.returncode == 0
        d = json.loads(result.stdout)
        assert d["contract"] is None

    def test_missing_breadcrumbs_empty_array(self, tmp_path):
        _setup(tmp_path, state=_state(tasks=[_task()]))
        result = run_pkg(root=tmp_path)
        assert result.returncode == 0
        d = json.loads(result.stdout)
        assert d["breadcrumbs"] == []

    def test_missing_state_exits_nonzero(self, tmp_path):
        (tmp_path / ".harness").mkdir(parents=True, exist_ok=True)
        # No state.json
        result = run_pkg(root=tmp_path)
        assert result.returncode != 0
        assert "ERROR" in result.stderr or "error" in result.stderr.lower()

    def test_invalid_state_json_exits_nonzero(self, tmp_path):
        harness = tmp_path / ".harness"
        harness.mkdir(parents=True, exist_ok=True)
        (harness / "state.json").write_text("{not valid json")
        result = run_pkg(root=tmp_path)
        assert result.returncode != 0


# --- Breadcrumb truncation and filtering ---

class TestBreadcrumbs:
    def test_last_3_of_many(self, tmp_path):
        bcs = [_bc(i) for i in range(15)]
        _setup(tmp_path, state=_state(tasks=[_task()]), breadcrumbs=bcs)
        result = run_pkg(root=tmp_path)
        d = json.loads(result.stdout)
        assert len(d["breadcrumbs"]) == 3
        # Last 3: indices 12..14
        assert d["breadcrumbs"][-1]["msg"] == "breadcrumb 14"
        assert d["breadcrumbs"][0]["msg"] == "breadcrumb 12"

    def test_fewer_than_window_all_included(self, tmp_path):
        bcs = [_bc(i) for i in range(2)]
        _setup(tmp_path, state=_state(tasks=[_task()]), breadcrumbs=bcs)
        result = run_pkg(root=tmp_path)
        d = json.loads(result.stdout)
        assert len(d["breadcrumbs"]) == 2

    def test_empty_breadcrumbs_file_returns_empty(self, tmp_path):
        _setup(tmp_path, state=_state(tasks=[_task()]), raw_breadcrumbs="")
        result = run_pkg(root=tmp_path)
        d = json.loads(result.stdout)
        assert d["breadcrumbs"] == []

    def test_invalid_jsonl_lines_skipped(self, tmp_path):
        raw = (
            json.dumps(_bc(1)) + "\n"
            + "NOT VALID JSON\n"
            + json.dumps(_bc(2)) + "\n"
        )
        _setup(tmp_path, state=_state(tasks=[_task()]), raw_breadcrumbs=raw)
        result = run_pkg(root=tmp_path)
        assert result.returncode == 0
        d = json.loads(result.stdout)
        assert len(d["breadcrumbs"]) == 2


# --- --format markdown ---

class TestMarkdownFormat:
    def test_headings_present_in_order(self, tmp_path):
        _setup(tmp_path, state=_state(tasks=[_task()]), contract=_contract(),
               breadcrumbs=[_bc(1)])
        result = run_pkg("--format", "markdown", root=tmp_path)
        assert result.returncode == 0
        lines = result.stdout.splitlines()
        headings = [l for l in lines if l.startswith("## ")]
        assert headings == [
            "## Current Task",
            "## Acceptance Criteria",
            "## Recent Breadcrumbs",
        ]
        assert "Open Questions" not in result.stdout

    def test_null_task_shows_none(self, tmp_path):
        _setup(tmp_path, state=_state(tasks=[]))
        result = run_pkg("--format", "markdown", root=tmp_path)
        assert "(none)" in result.stdout

    def test_empty_breadcrumbs_shows_none(self, tmp_path):
        _setup(tmp_path, state=_state(tasks=[_task()]))
        result = run_pkg("--format", "markdown", root=tmp_path)
        assert "(none)" in result.stdout


# --- --write flag ---

class TestWriteFlag:
    def test_write_byte_identical_to_stdout(self, tmp_path):
        _setup(tmp_path, state=_state(tasks=[_task()]), contract=_contract())
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            write_path = Path(f.name)

        result_stdout = run_pkg(root=tmp_path)
        run_pkg("--write", str(write_path), root=tmp_path)

        file_content = write_path.read_text().strip()
        stdout_content = result_stdout.stdout.strip()
        assert file_content == stdout_content
        write_path.unlink(missing_ok=True)


# --- --root fixture isolation ---

class TestRootFlag:
    def test_root_isolates_to_fixture(self, tmp_path, tmp_path_factory):
        """--root must NOT read from the real repo's .harness/."""
        fixture = tmp_path_factory.mktemp("fixture")
        _setup(fixture, state=_state(tasks=[_task("fixture-task", "Fixture", "pending")]))

        result = run_pkg(root=fixture)
        d = json.loads(result.stdout)
        assert d["task"]["id"] == "fixture-task"
