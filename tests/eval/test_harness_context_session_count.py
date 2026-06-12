"""Unit tests for the session task counting logic in harness-context.sh.

Tests the Python counting algorithm by calling it directly (extracted as a helper).
All 4 AC7 cases + edge cases.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest


def _count_session_tasks(breadcrumbs_lines: list[str]) -> tuple[int, bool]:
    """Replicate the counting logic from harness-context.sh for testing.

    Returns (session_task_count, advisory_injected).
    advisory_injected is True when count >= 3.
    """
    parsed = []
    for line in breadcrumbs_lines:
        line = line.strip()
        if not line:
            continue
        try:
            parsed.append(json.loads(line))
        except Exception:
            parsed.append(None)

    marker_indices = [
        i for i, e in enumerate(parsed)
        if e is not None and e.get("type") == "session_start"
    ]

    session_task_count = 0
    if len(marker_indices) >= 2:
        lo = marker_indices[-2] + 1
        hi = marker_indices[-1]
        window = [e for e in parsed[lo:hi] if e is not None]
        feat_ids: set[str] = set()
        for e in window:
            feat = e.get("feat")
            if (feat
                    and e.get("role") == "builder"
                    and e.get("type") == "build"
                    and str(e.get("result", "")).lower() == "pass"):
                feat_ids.add(feat)
        session_task_count = len(feat_ids)

    return session_task_count, session_task_count >= 3


def _session_start(ts: str = "2026-01-01T00:00:00Z") -> str:
    return json.dumps({"ts": ts, "role": "system", "type": "session_start", "feat": None, "msg": "New chat session started", "result": "pass"})


def _build_pass(feat: str, ts: str = "2026-01-01T01:00:00Z") -> str:
    return json.dumps({"ts": ts, "role": "builder", "type": "build", "feat": feat, "msg": f"built {feat}", "result": "pass"})


def _build_fail(feat: str) -> str:
    return json.dumps({"ts": "2026-01-01T01:00:00Z", "role": "builder", "type": "build", "feat": feat, "msg": f"failed {feat}", "result": "fail"})


# ─── AC7(a): 2 session_starts + 3 feats between → N=3 → advisory ─────────────


def test_three_feats_between_markers_triggers_advisory():
    """AC7(a): 3 unique build-pass feats between last two session_starts → N=3, advisory=True."""
    lines = [
        _session_start("2026-01-01T00:00:00Z"),
        _build_pass("feat-1", "2026-01-01T01:00:00Z"),
        _build_pass("feat-2", "2026-01-01T02:00:00Z"),
        _build_pass("feat-3", "2026-01-01T03:00:00Z"),
        _session_start("2026-01-01T10:00:00Z"),  # new session start (just appended)
    ]
    count, advisory = _count_session_tasks(lines)
    assert count == 3
    assert advisory is True


# ─── AC7(b): builds before first marker + 1 after → N=1 → no advisory ────────


def test_builds_outside_window_not_counted():
    """AC7(b): builds before first session_start don't count; 1 build in window → N=1."""
    lines = [
        _build_pass("feat-a", "2026-01-01T00:30:00Z"),  # before any session_start
        _build_pass("feat-b", "2026-01-01T00:31:00Z"),  # before any session_start
        _session_start("2026-01-01T01:00:00Z"),          # first marker
        _build_pass("feat-c", "2026-01-01T02:00:00Z"),   # in window
        _session_start("2026-01-01T10:00:00Z"),          # second marker (just appended)
    ]
    count, advisory = _count_session_tasks(lines)
    assert count == 1
    assert advisory is False


# ─── AC7(c): 2 feats between markers → N=2 → no advisory (off-by-one guard) ─


def test_two_feats_no_advisory():
    """AC7(c): exactly 2 unique feats → N=2 → no advisory (strict >= 3)."""
    lines = [
        _session_start("2026-01-01T00:00:00Z"),
        _build_pass("feat-x", "2026-01-01T01:00:00Z"),
        _build_pass("feat-y", "2026-01-01T02:00:00Z"),
        _session_start("2026-01-01T10:00:00Z"),
    ]
    count, advisory = _count_session_tasks(lines)
    assert count == 2
    assert advisory is False


# ─── AC7(d) / EC4: session_start is last line → N=0 ─────────────────────────


def test_session_start_as_last_line_zero_count():
    """AC7(d)/EC4: only one session_start (just appended, nothing between markers) → N=0."""
    lines = [
        _session_start("2026-01-01T10:00:00Z"),  # only marker in file
    ]
    count, advisory = _count_session_tasks(lines)
    assert count == 0
    assert advisory is False


# ─── EC1: all builds before any session_start ─────────────────────────────────


def test_all_builds_before_any_session_start():
    """EC1: builds exist but no session_start yet → N=0."""
    lines = [
        _build_pass("feat-1"),
        _build_pass("feat-2"),
        _build_pass("feat-3"),
    ]
    count, advisory = _count_session_tasks(lines)
    assert count == 0
    assert advisory is False


# ─── EC2: duplicate feat ids in window counted once ───────────────────────────


def test_duplicate_feat_ids_counted_once():
    """EC2: same feat id appears 3 times in window → N=1, no inflation."""
    lines = [
        _session_start("2026-01-01T00:00:00Z"),
        _build_pass("feat-1", "2026-01-01T01:00:00Z"),
        _build_pass("feat-1", "2026-01-01T02:00:00Z"),
        _build_pass("feat-1", "2026-01-01T03:00:00Z"),
        _session_start("2026-01-01T10:00:00Z"),
    ]
    count, advisory = _count_session_tasks(lines)
    assert count == 1
    assert advisory is False


# ─── EC3: malformed JSON lines skipped ────────────────────────────────────────


def test_malformed_json_lines_skipped():
    """EC3: malformed lines don't crash; only valid entries counted."""
    lines = [
        _session_start("2026-01-01T00:00:00Z"),
        "NOT VALID JSON {{{",
        _build_pass("feat-1", "2026-01-01T01:00:00Z"),
        "{bad",
        _build_pass("feat-2", "2026-01-01T02:00:00Z"),
        _build_pass("feat-3", "2026-01-01T03:00:00Z"),
        _session_start("2026-01-01T10:00:00Z"),
    ]
    count, advisory = _count_session_tasks(lines)
    assert count == 3
    assert advisory is True


# ─── Null/missing feat excluded ───────────────────────────────────────────────


def test_null_feat_not_counted():
    """Builds with feat=null or missing feat are not counted (evaluator note)."""
    lines = [
        _session_start("2026-01-01T00:00:00Z"),
        json.dumps({"ts": "2026-01-01T01:00:00Z", "role": "builder", "type": "build", "feat": None, "result": "pass"}),
        json.dumps({"ts": "2026-01-01T02:00:00Z", "role": "builder", "type": "build", "result": "pass"}),
        _session_start("2026-01-01T10:00:00Z"),
    ]
    count, advisory = _count_session_tasks(lines)
    assert count == 0
    assert advisory is False


# ─── 5 feats: above threshold, multiple builds ────────────────────────────────


def test_five_feats_advisory():
    """5 unique feats → N=5 → advisory."""
    lines = [
        _session_start("t0"),
        *[_build_pass(f"feat-{i}") for i in range(1, 6)],
        _session_start("t1"),
    ]
    count, advisory = _count_session_tasks(lines)
    assert count == 5
    assert advisory is True


# ─── Failed builds not counted ────────────────────────────────────────────────


def test_failed_builds_not_counted():
    """build+fail entries don't count toward session_task_count."""
    lines = [
        _session_start("t0"),
        _build_fail("feat-1"),
        _build_fail("feat-2"),
        _build_pass("feat-3"),
        _session_start("t1"),
    ]
    count, advisory = _count_session_tasks(lines)
    assert count == 1
    assert advisory is False
