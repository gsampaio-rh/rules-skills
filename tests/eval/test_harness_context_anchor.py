"""
Behavioral tests for the breadcrumb anchor fix in harness-context.sh.

Extracts the inline Python MAINT block from harness-context.sh and runs it
via subprocess against synthetic fixtures, asserting on resulting file content.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent
HARNESS_CONTEXT = REPO_ROOT / "library" / "cursor" / "hooks" / "harness-context.sh"


def _extract_maint_source() -> str:
    text = HARNESS_CONTEXT.read_text()
    m = re.search(r"<<\s*'MAINT'[^\n]*\n(.*?)\nMAINT", text, re.DOTALL)
    assert m, "Could not find MAINT heredoc in harness-context.sh"
    return m.group(1)


MAINT_SOURCE = _extract_maint_source()


def _run_maint(tmp_path: Path, state: dict, crumb_lines: list[str], contract: dict | None = None):
    """Write fixtures, run MAINT block, return (retained_lines, archive_lines)."""
    state_path = tmp_path / "state.json"
    breadcrumbs_path = tmp_path / "breadcrumbs.jsonl"
    archive_path = tmp_path / ".archive" / "archive.jsonl"
    contract_path = tmp_path / "contract.json"

    archive_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state))
    breadcrumbs_path.write_text(
        "".join(l if l.endswith("\n") else l + "\n" for l in crumb_lines)
    )
    archive_path.write_text("")
    contract_path.write_text(json.dumps(contract or {}))

    result = subprocess.run(
        [
            sys.executable, "-",
            str(state_path), str(breadcrumbs_path), str(archive_path), str(contract_path),
        ],
        input=MAINT_SOURCE,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, f"MAINT block failed:\n{result.stderr}"

    retained = [l for l in breadcrumbs_path.read_text().splitlines() if l.strip()]
    archived = [l for l in archive_path.read_text().splitlines() if l.strip()]
    return retained, archived


def _signal(type_: str, feat: str) -> str:
    return json.dumps({"ts": "2026-01-01T00:00Z", "role": "builder", "type": type_, "feat": feat, "msg": f"x"})


def _noise() -> str:
    return json.dumps({"ts": "2026-01-01T00:00Z", "role": "system", "type": "session_start", "feat": None, "msg": "s"})


def _active_state(*task_ids: str, statuses: list[str] | None = None) -> dict:
    statuses = statuses or ["building"] * len(task_ids)
    return {
        "schema_version": 2,
        "tasks": [{"id": tid, "status": s} for tid, s in zip(task_ids, statuses)],
    }


# ---------------------------------------------------------------------------
# AC1 — anchor fires: signal at index 0 would be evicted by FIFO
# ---------------------------------------------------------------------------

def test_anchor_spliced_when_evicted(tmp_path):
    anchor = _signal("build", "task-1")
    lines = [anchor] + [_noise() for _ in range(34)]  # 35 lines; anchor evicted by FIFO

    retained, _ = _run_maint(tmp_path, _active_state("task-1"), lines)

    first = json.loads(retained[0])
    assert first["type"] == "build"
    assert first["feat"] == "task-1"
    assert len(retained) == 30  # AC4 covered here too


# ---------------------------------------------------------------------------
# AC2 — no-op: anchor already in retained window
# ---------------------------------------------------------------------------

def test_no_splice_when_anchor_in_window(tmp_path):
    # 35 lines; anchor at index 25 → within lines[-30:]
    anchor = _signal("build", "task-1")
    lines = [_noise() for _ in range(25)] + [anchor] + [_noise() for _ in range(9)]

    retained, archive = _run_maint(tmp_path, _active_state("task-1"), lines)

    assert len(retained) == 30
    assert any(json.loads(r).get("feat") == "task-1" for r in retained)
    # archive must contain only the 5 FIFO-evicted lines (no displaced)
    assert len(archive) == 5


# ---------------------------------------------------------------------------
# AC3 — no active task → plain FIFO, no splice
# ---------------------------------------------------------------------------

def test_plain_fifo_when_no_active_task(tmp_path):
    anchor = _signal("build", "task-1")
    lines = [anchor] + [_noise() for _ in range(34)]
    state = _active_state("task-1", statuses=["verified"])

    retained, _ = _run_maint(tmp_path, state, lines)

    assert len(retained) == 30
    assert not any(json.loads(r).get("feat") == "task-1" for r in retained)


# ---------------------------------------------------------------------------
# AC4 — retained window is exactly 30 after splice
# ---------------------------------------------------------------------------

def test_retained_window_exactly_30_after_splice(tmp_path):
    anchor = _signal("evaluate", "task-1")
    lines = [anchor] + [_noise() for _ in range(34)]

    retained, _ = _run_maint(tmp_path, _active_state("task-1", statuses=["evaluating"]), lines)

    assert len(retained) == 30


# ---------------------------------------------------------------------------
# AC5 — archive contains FIFO-evicted lines AND displaced retained line
# ---------------------------------------------------------------------------

def test_archive_contains_evicted_and_displaced(tmp_path):
    # 35 lines: anchor at 0, then 34 noise
    # FIFO evicts lines[0:5]; retained = lines[5:35]
    # Splice: anchor in archive (FIFO-evicted) + displaced = lines[5] also in archive
    anchor = _signal("negotiate", "task-1")
    lines = [anchor] + [_noise() for _ in range(34)]

    retained, archive = _run_maint(tmp_path, _active_state("task-1"), lines)

    assert len(archive) == 6  # 5 FIFO-evicted + 1 displaced
    archive_types = [json.loads(a).get("type") for a in archive]
    assert "negotiate" in archive_types  # anchor in archive (was FIFO-evicted)
    assert any(json.loads(r).get("type") == "negotiate" for r in retained)  # also in retained


# ---------------------------------------------------------------------------
# EC1 — active task but no signal entries → plain FIFO
# ---------------------------------------------------------------------------

def test_no_signal_entries_plain_fifo(tmp_path):
    lines = [_noise() for _ in range(35)]
    retained, archive = _run_maint(tmp_path, _active_state("task-1"), lines)

    assert len(retained) == 30
    assert len(archive) == 5  # only FIFO-evicted, no displaced


# ---------------------------------------------------------------------------
# EC2 — multiple active tasks: anchor uses first task only
# ---------------------------------------------------------------------------

def test_multi_task_anchors_first_task_only(tmp_path):
    # task-2 has a signal entry that would be evicted; task-1 has none
    anchor_task2 = _signal("evaluate", "task-2")
    lines = [anchor_task2] + [_noise() for _ in range(34)]
    state = _active_state("task-1", "task-2", statuses=["building", "evaluating"])

    retained, _ = _run_maint(tmp_path, state, lines)

    # task-1 has no signal → no splice fires, even though task-2 signal was evicted
    assert not any(json.loads(r).get("feat") == "task-2" for r in retained)
    assert len(retained) == 30


# ---------------------------------------------------------------------------
# EC3 — exactly 30 lines: no truncation, no anchor, file unchanged
# ---------------------------------------------------------------------------

def test_exactly_30_lines_no_op(tmp_path):
    lines = [_noise() for _ in range(30)]
    retained, archive = _run_maint(tmp_path, _active_state("task-1"), lines)

    assert len(retained) == 30
    assert len(archive) == 0  # nothing archived at all


# ---------------------------------------------------------------------------
# EC4 — anchor at exact boundary (lines[-30][0]): already in window, no splice
# ---------------------------------------------------------------------------

def test_anchor_at_boundary_no_splice(tmp_path):
    # 35 lines: 5 noise (evicted), anchor at index 5 = lines[-30][0] (IN window), 29 noise
    anchor = _signal("build", "task-1")
    lines = [_noise() for _ in range(5)] + [anchor] + [_noise() for _ in range(29)]

    retained, archive = _run_maint(tmp_path, _active_state("task-1"), lines)

    assert any(json.loads(r).get("feat") == "task-1" for r in retained)
    assert len(retained) == 30
    assert len(archive) == 5  # only FIFO-evicted, no displaced
