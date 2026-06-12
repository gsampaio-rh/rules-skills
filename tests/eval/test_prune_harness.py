"""Tests for library/cursor/hooks/prune-harness.py"""

import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PRUNE_SCRIPT = REPO_ROOT / "library" / "cursor" / "hooks" / "prune-harness.py"


def run_prune(*args, root: Path) -> subprocess.CompletedProcess:
    cmd = [sys.executable, str(PRUNE_SCRIPT), "--root", str(root), *args]
    return subprocess.run(cmd, capture_output=True, text=True)


def _make_state(root: Path, open_questions: list[str], tasks: list[dict] | None = None) -> Path:
    state = {
        "project": "test",
        "schema_version": 2,
        "vision": "test vision",
        "direction": "test direction",
        "trade_offs": [],
        "open_questions": open_questions,
        "tasks": tasks or [],
    }
    state_path = root / ".harness" / "state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, indent=2))
    return state_path


def _make_breadcrumbs(root: Path, entries: list[dict]) -> Path:
    bc_path = root / ".harness" / "breadcrumbs.jsonl"
    bc_path.parent.mkdir(parents=True, exist_ok=True)
    bc_path.write_text("\n".join(json.dumps(e) for e in entries) + "\n")
    return bc_path


def _bc_entry(ts: datetime, msg: str = "test") -> dict:
    return {"ts": ts.isoformat(), "role": "builder", "type": "build", "msg": msg}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _age(days: float = 0, hours: float = 0, minutes: float = 0) -> datetime:
    return _now() - timedelta(days=days, hours=hours, minutes=minutes)


# --- Dry-run: byte-identical guarantee ---

class TestDryRun:
    def test_dry_run_no_op_on_files(self, tmp_path):
        """Dry-run must not modify any harness files."""
        state_path = _make_state(tmp_path, ["RESOLVED: thing one"])
        bc_path = _make_breadcrumbs(tmp_path, [_bc_entry(_now(), "recent")])

        orig_state = state_path.read_bytes()
        orig_bc = bc_path.read_bytes()

        result = run_prune(root=tmp_path)
        assert result.returncode == 0, result.stderr

        assert state_path.read_bytes() == orig_state, "state.json was modified by dry-run"
        assert bc_path.read_bytes() == orig_bc, "breadcrumbs.jsonl was modified by dry-run"
        assert not (tmp_path / ".harness" / ".archive" / "questions.jsonl").exists()

    def test_dry_run_prints_plan(self, tmp_path):
        _make_state(tmp_path, ["RESOLVED: something", "DEFERRED: another"])
        _make_breadcrumbs(tmp_path, [])

        result = run_prune(root=tmp_path)
        assert result.returncode == 0
        assert "RESOLVED" in result.stdout or "open_questions" in result.stdout


# --- Questions archiving ---

class TestQuestionsArchive:
    def test_apply_archives_resolved_and_deferred(self, tmp_path):
        qs = [
            "RESOLVED: thing one",
            "DEFERRED: thing two",
            "Still open question — keep this",
        ]
        _make_state(tmp_path, qs)
        _make_breadcrumbs(tmp_path, [])

        result = run_prune("--apply", root=tmp_path)
        assert result.returncode == 0, result.stderr

        state = json.loads((tmp_path / ".harness" / "state.json").read_text())
        assert len(state["open_questions"]) == 1
        assert state["open_questions"][0] == "Still open question — keep this"

        archive = (tmp_path / ".harness" / ".archive" / "questions.jsonl").read_text().strip().splitlines()
        assert len(archive) == 2
        archived_qs = {json.loads(ln)["question"] for ln in archive}
        assert "RESOLVED: thing one" in archived_qs
        assert "DEFERRED: thing two" in archived_qs

    def test_apply_archive_format_has_archived_at(self, tmp_path):
        _make_state(tmp_path, ["RESOLVED: x"])
        _make_breadcrumbs(tmp_path, [])

        run_prune("--apply", root=tmp_path)

        archive_lines = (tmp_path / ".harness" / ".archive" / "questions.jsonl").read_text().strip().splitlines()
        obj = json.loads(archive_lines[0])
        assert "question" in obj
        assert "archived_at" in obj
        datetime.fromisoformat(obj["archived_at"])  # must parse

    def test_no_resolved_questions_no_archive_created(self, tmp_path):
        _make_state(tmp_path, ["Still open", "Another open"])
        _make_breadcrumbs(tmp_path, [])

        run_prune("--apply", root=tmp_path)

        assert not (tmp_path / ".harness" / ".archive" / "questions.jsonl").exists()

    def test_unresolved_superseded_stay_in_state(self, tmp_path):
        _make_state(tmp_path, ["UNRESOLVED: keep me", "SUPERSEDED: also keep", "RESOLVED: archive me"])
        _make_breadcrumbs(tmp_path, [])

        run_prune("--apply", root=tmp_path)

        state = json.loads((tmp_path / ".harness" / "state.json").read_text())
        kept = state["open_questions"]
        assert "UNRESOLVED: keep me" in kept
        assert "SUPERSEDED: also keep" in kept
        assert not any(q.startswith("RESOLVED") for q in kept)

    def test_idempotent_no_duplicate_archive_lines(self, tmp_path):
        _make_state(tmp_path, ["RESOLVED: idempotent test"])
        _make_breadcrumbs(tmp_path, [])

        run_prune("--apply", root=tmp_path)
        # state.json now has 0 RESOLVED — second run archives nothing new
        run_prune("--apply", root=tmp_path)

        archive_lines = (tmp_path / ".harness" / ".archive" / "questions.jsonl").read_text().strip().splitlines()
        assert len(archive_lines) == 1


# --- Breadcrumb retention policy ---

class TestBreadcrumbRetention:
    def test_recent_within_7days_and_under_50_not_archived(self, tmp_path):
        _make_state(tmp_path, [])
        entries = [_bc_entry(_age(days=1), f"entry {i}") for i in range(30)]
        bc_path = _make_breadcrumbs(tmp_path, entries)
        orig = bc_path.read_bytes()

        run_prune("--apply", root=tmp_path)

        assert bc_path.read_bytes() == orig
        assert not (tmp_path / ".harness" / ".archive" / "breadcrumbs.jsonl").exists()

    def test_100_recent_entries_archives_0(self, tmp_path):
        """100 lines within 7 days — age policy keeps all 100 > last-50 → archive 0."""
        _make_state(tmp_path, [])
        entries = [_bc_entry(_age(hours=1), f"recent {i}") for i in range(100)]
        bc_path = _make_breadcrumbs(tmp_path, entries)

        run_prune("--apply", root=tmp_path)

        assert not (tmp_path / ".harness" / ".archive" / "breadcrumbs.jsonl").exists()
        kept = [ln for ln in bc_path.read_text().splitlines() if ln.strip()]
        assert len(kept) == 100

    def test_100_old_entries_archives_50(self, tmp_path):
        """100 lines all >7 days — last-50 policy (50) >= age-policy (0) → archive 50."""
        _make_state(tmp_path, [])
        entries = [_bc_entry(_age(days=10), f"old {i}") for i in range(100)]
        _make_breadcrumbs(tmp_path, entries)

        run_prune("--apply", root=tmp_path)

        bc_path = tmp_path / ".harness" / "breadcrumbs.jsonl"
        kept = [ln for ln in bc_path.read_text().splitlines() if ln.strip()]
        assert len(kept) == 50

        archive = tmp_path / ".harness" / ".archive" / "breadcrumbs.jsonl"
        archived = [ln for ln in archive.read_text().splitlines() if ln.strip()]
        assert len(archived) == 50

    def test_missing_breadcrumbs_no_crash(self, tmp_path):
        _make_state(tmp_path, [])
        # No breadcrumbs.jsonl created

        result = run_prune("--apply", root=tmp_path)
        assert result.returncode == 0
        assert "breadcrumb" in result.stderr.lower()


# --- Flag file pruning ---

class TestFlagPruning:
    def _make_flags_dir(self, root: Path) -> tuple[Path, Path, Path]:
        harness = root / ".harness"
        hooks = root / ".cursor" / "hooks"
        harness.mkdir(parents=True, exist_ok=True)
        hooks.mkdir(parents=True, exist_ok=True)
        return harness, hooks, hooks

    def test_stale_routing_pending_removed(self, tmp_path):
        harness, hooks, _ = self._make_flags_dir(tmp_path)
        _make_state(tmp_path, [], tasks=[])
        _make_breadcrumbs(tmp_path, [])
        flag = harness / ".routing-pending"
        flag.touch()
        import os, time
        # Backdate mtime to > 30 minutes ago
        old_ts = time.time() - 31 * 60
        os.utime(flag, (old_ts, old_ts))

        result = run_prune("--apply", root=tmp_path)
        assert result.returncode == 0
        assert not flag.exists(), "Stale .routing-pending should be removed"

    def test_fresh_routing_pending_kept(self, tmp_path):
        harness, hooks, _ = self._make_flags_dir(tmp_path)
        _make_state(tmp_path, [], tasks=[])
        _make_breadcrumbs(tmp_path, [])
        flag = harness / ".routing-pending"
        flag.touch()  # mtime = now (< 30 min)

        run_prune("--apply", root=tmp_path)
        assert flag.exists(), "Fresh .routing-pending should be kept"

    def test_evaluator_active_removed_when_not_evaluating(self, tmp_path):
        harness, hooks, _ = self._make_flags_dir(tmp_path)
        _make_state(tmp_path, [], tasks=[])
        _make_breadcrumbs(tmp_path, [])
        # Contract with phase != evaluating
        contract = {"task_id": "feat-1", "phase": "building", "verified": False}
        (harness / "contract.json").write_text(json.dumps(contract))
        flag = hooks / ".evaluator-active"
        flag.touch()

        run_prune("--apply", root=tmp_path)
        assert not flag.exists(), ".evaluator-active should be removed when phase=building"

    def test_evaluator_active_kept_when_evaluating(self, tmp_path):
        harness, hooks, _ = self._make_flags_dir(tmp_path)
        _make_state(tmp_path, [], tasks=[])
        _make_breadcrumbs(tmp_path, [])
        contract = {"task_id": "feat-1", "phase": "evaluating", "verified": False}
        (harness / "contract.json").write_text(json.dumps(contract))
        flag = hooks / ".evaluator-active"
        flag.touch()

        run_prune("--apply", root=tmp_path)
        assert flag.exists(), ".evaluator-active should be kept when phase=evaluating"

    def test_commit_approved_removed_when_no_building_task(self, tmp_path):
        harness, hooks, _ = self._make_flags_dir(tmp_path)
        _make_state(tmp_path, [], tasks=[{"id": "feat-1", "status": "verified"}])
        _make_breadcrumbs(tmp_path, [])
        flag = hooks / ".commit-approved"
        flag.touch()

        run_prune("--apply", root=tmp_path)
        assert not flag.exists(), ".commit-approved removed when no building task"

    def test_commit_approved_kept_when_building_task(self, tmp_path):
        harness, hooks, _ = self._make_flags_dir(tmp_path)
        _make_state(tmp_path, [], tasks=[{"id": "feat-1", "status": "building"}])
        _make_breadcrumbs(tmp_path, [])
        flag = hooks / ".commit-approved"
        flag.touch()

        run_prune("--apply", root=tmp_path)
        assert flag.exists(), ".commit-approved kept when a task is building"

    def test_dry_run_does_not_remove_flags(self, tmp_path):
        harness, hooks, _ = self._make_flags_dir(tmp_path)
        _make_state(tmp_path, [], tasks=[])
        _make_breadcrumbs(tmp_path, [])
        import os, time
        flag = harness / ".routing-pending"
        flag.touch()
        old_ts = time.time() - 31 * 60
        os.utime(flag, (old_ts, old_ts))

        run_prune(root=tmp_path)  # dry-run (no --apply)
        assert flag.exists(), "Dry-run must not remove flag files"

    def test_absent_flag_no_error(self, tmp_path):
        self._make_flags_dir(tmp_path)
        _make_state(tmp_path, [], tasks=[])
        _make_breadcrumbs(tmp_path, [])
        # No flag files created — should exit 0 silently

        result = run_prune("--apply", root=tmp_path)
        assert result.returncode == 0


# --- State.json validity after apply ---

class TestStateValidAfterApply:
    def test_state_json_valid_after_prune(self, tmp_path):
        qs = ["RESOLVED: q1", "DEFERRED: q2", "Keep me"]
        _make_state(tmp_path, qs, tasks=[{"id": "feat-1", "status": "pending"}])
        _make_breadcrumbs(tmp_path, [])

        result = run_prune("--apply", root=tmp_path)
        assert result.returncode == 0

        state = json.loads((tmp_path / ".harness" / "state.json").read_text())
        assert "open_questions" in state
        assert "tasks" in state
        assert state["tasks"][0]["id"] == "feat-1"

    def test_empty_tasks_array_no_crash(self, tmp_path):
        _make_state(tmp_path, ["RESOLVED: q"], tasks=[])
        _make_breadcrumbs(tmp_path, [])

        result = run_prune("--apply", root=tmp_path)
        assert result.returncode == 0
