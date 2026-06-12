"""Unit tests for eval_regression_check.py.

Tests all pass/fail thresholds, strict boundaries, write-diff output, and edge cases.
All tests use synthetic fixture data — no live Cursor sessions required.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import pytest

# Allow importing from tests/eval without install
sys.path.insert(0, str(Path(__file__).parent))

from eval_regression_check import (
    ABSOLUTE_FLOOR,
    AGGREGATE_DELTA_THRESHOLD,
    SCENARIO_DELTA_THRESHOLD,
    _build_scenario_map,
    run_check,
)


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _make_summary(
    overall_pass_rate: float,
    scenarios: dict[str, float] | None = None,
    model: str = "composer-2.5",
) -> dict:
    """Build a minimal summary.json structure matching session_report.py output."""
    scenario_entries: dict[str, dict] = {}
    for scenario_id, score in (scenarios or {}).items():
        key = f"{model}/{scenario_id}"
        scenario_entries[key] = {
            "scenario_id": scenario_id,
            "model": model,
            "overall_score": score,
            "total_checks": 10,
            "pass_count": int(score * 10),
            "fail_count": 10 - int(score * 10),
            "unmatched_count": 0,
            "uncertain_count": 0,
            "dimensions": {},
        }
    return {
        "scenarios": scenario_entries,
        "aggregate": {
            "total_scenarios": len(scenario_entries),
            "overall_pass_rate": overall_pass_rate,
        },
    }


def _make_baseline(
    tier: str,
    aggregate_score: float | None,
    scenarios: dict[str, float] | None = None,
) -> dict:
    """Build a minimal eval_baseline.json structure."""
    return {
        tier: {
            "aggregate_score": aggregate_score,
            "scenarios": {sid: {"score": score} for sid, score in (scenarios or {}).items()},
        }
    }


def _write_fixture(tmp: Path, summary: dict, baseline: dict) -> tuple[Path, Path]:
    """Write summary.json and baseline.json to tmp; return (run_dir, baseline_path)."""
    run_dir = tmp / "run"
    run_dir.mkdir()
    (run_dir / "summary.json").write_text(json.dumps(summary))
    baseline_path = tmp / "baseline.json"
    baseline_path.write_text(json.dumps(baseline))
    return run_dir, baseline_path


# ─── AC9(a): equal to baseline → pass ─────────────────────────────────────────


def test_no_regression_passes():
    """AC9(a): current == baseline → exit 0 (no regression)."""
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        summary = _make_summary(0.80, {"protocol_fresh_repo": 0.85})
        baseline = _make_baseline("pr", aggregate_score=0.80, scenarios={"protocol_fresh_repo": 0.85})
        run_dir, bl = _write_fixture(tmp, summary, baseline)
        passed, diff = run_check(run_dir, bl, "pr")
    assert passed is True
    assert diff["regression"] is False
    assert diff["regressions"] == []


# ─── AC9(b): aggregate drops exactly 0.05 → exit 0 (strict >) ────────────────


def test_aggregate_drop_exactly_at_threshold_passes():
    """AC9(b): drop of exactly 0.05 is NOT a regression (strict >)."""
    # Use explicit float literals to avoid floating point arithmetic imprecision.
    # 0.85 - 0.05 in Python = 0.7999999999999999 due to IEEE 754, making the
    # "drop" slightly above 0.05. Using 0.90 - 0.85 = 0.05 exactly:
    baseline_val = 0.90
    current_val = 0.85  # drop = 0.05 exactly when both are representable floats
    drop = round(baseline_val - current_val, 10)
    assert drop == AGGREGATE_DELTA_THRESHOLD, f"Precondition: drop={drop} should equal threshold"
    with tempfile.TemporaryDirectory() as td:
        summary = _make_summary(current_val)
        baseline = _make_baseline("pr", aggregate_score=baseline_val)
        run_dir, bl = _write_fixture(Path(td), summary, baseline)
        passed, diff = run_check(run_dir, bl, "pr")
    assert passed is True, f"Drop of exactly {AGGREGATE_DELTA_THRESHOLD} should pass (strict >)"


# ─── AC9(c): aggregate drops 0.051 → exit 1 ──────────────────────────────────


def test_aggregate_drop_above_threshold_fails():
    """AC9(c): drop of 0.051 > threshold → regression."""
    baseline_val = 0.85
    current_val = round(baseline_val - AGGREGATE_DELTA_THRESHOLD - 0.001, 4)
    with tempfile.TemporaryDirectory() as td:
        summary = _make_summary(current_val)
        baseline = _make_baseline("pr", aggregate_score=baseline_val)
        run_dir, bl = _write_fixture(Path(td), summary, baseline)
        passed, diff = run_check(run_dir, bl, "pr")
    assert passed is False
    assert diff["regression"] is True
    assert any("aggregate regression" in r for r in diff["regressions"])


# ─── AC9(d): single scenario drops > 0.10 → exit 1 ──────────────────────────


def test_scenario_drop_above_threshold_fails():
    """AC9(d): scenario drops 0.15 > 0.10 threshold → regression."""
    with tempfile.TemporaryDirectory() as td:
        summary = _make_summary(0.80, {"protocol_fresh_repo": 0.70})
        baseline = _make_baseline("pr", aggregate_score=0.80, scenarios={"protocol_fresh_repo": 0.85})
        run_dir, bl = _write_fixture(Path(td), summary, baseline)
        passed, diff = run_check(run_dir, bl, "pr")
    assert passed is False
    assert any("protocol_fresh_repo" in r for r in diff["regressions"])


def test_scenario_drop_at_threshold_passes():
    """Scenario drop of exactly 0.10 should NOT fail (strict >)."""
    with tempfile.TemporaryDirectory() as td:
        summary = _make_summary(0.80, {"protocol_fresh_repo": 0.75})
        baseline = _make_baseline("pr", aggregate_score=0.80, scenarios={"protocol_fresh_repo": 0.85})
        run_dir, bl = _write_fixture(Path(td), summary, baseline)
        passed, diff = run_check(run_dir, bl, "pr")
    assert passed is True


# ─── AC9(e): aggregate < 0.70 floor → exit 1 ─────────────────────────────────


def test_aggregate_below_floor_fails():
    """AC9(e): aggregate 0.68 < floor 0.70 → regression."""
    with tempfile.TemporaryDirectory() as td:
        summary = _make_summary(0.68)
        baseline = _make_baseline("pr", aggregate_score=0.70)
        run_dir, bl = _write_fixture(Path(td), summary, baseline)
        passed, diff = run_check(run_dir, bl, "pr")
    assert passed is False
    assert any("below floor" in r for r in diff["regressions"])


def test_aggregate_at_floor_passes():
    """Aggregate exactly at floor 0.70 should pass (strict <)."""
    with tempfile.TemporaryDirectory() as td:
        summary = _make_summary(ABSOLUTE_FLOOR)
        baseline = _make_baseline("pr", aggregate_score=ABSOLUTE_FLOOR)
        run_dir, bl = _write_fixture(Path(td), summary, baseline)
        passed, diff = run_check(run_dir, bl, "pr")
    assert passed is True


# ─── AC9(f): --write-diff writes correct JSON keys ───────────────────────────


def test_write_diff_keys():
    """AC9(f): diff dict has required keys: tier, regression, per_scenario_deltas, aggregate_delta."""
    with tempfile.TemporaryDirectory() as td:
        summary = _make_summary(0.80, {"sc_a": 0.80})
        baseline = _make_baseline("pr", aggregate_score=0.80, scenarios={"sc_a": 0.80})
        run_dir, bl = _write_fixture(Path(td), summary, baseline)
        passed, diff = run_check(run_dir, bl, "pr")
    for key in ("tier", "regression", "per_scenario_deltas", "aggregate_delta"):
        assert key in diff, f"Missing key in diff: {key}"
    assert diff["tier"] == "pr"


# ─── AC9(g): scenario in baseline missing from current run → no fail ─────────


def test_missing_scenario_no_regression():
    """AC9(g): scenario in baseline not in current run → exit 0; current_score=null."""
    with tempfile.TemporaryDirectory() as td:
        summary = _make_summary(0.85, {})  # no scenarios in current run
        baseline = _make_baseline("pr", aggregate_score=0.85, scenarios={"missing_scenario": 0.80})
        run_dir, bl = _write_fixture(Path(td), summary, baseline)
        passed, diff = run_check(run_dir, bl, "pr")
    assert passed is True
    deltas = diff["per_scenario_deltas"]
    assert len(deltas) == 1
    assert deltas[0]["scenario_id"] == "missing_scenario"
    assert deltas[0]["current_score"] is None
    assert deltas[0]["delta"] is None


# ─── AC9(h) / EC3: null baseline aggregate_score → exit 0 with warning ────────


def test_null_baseline_aggregate_skips_gate():
    """AC9(h) / EC3: aggregate_score null → exit 0 + 'baseline not seeded' warning."""
    with tempfile.TemporaryDirectory() as td:
        summary = _make_summary(0.60)  # would fail floor check if seeded
        baseline = _make_baseline("pr", aggregate_score=None)
        run_dir, bl = _write_fixture(Path(td), summary, baseline)
        passed, diff = run_check(run_dir, bl, "pr")
    assert passed is True
    assert diff["regression"] is False
    assert any("baseline not seeded" in w for w in diff.get("warnings", []))


# ─── _build_scenario_map handles composite keys ───────────────────────────────


def test_build_scenario_map_strips_model_prefix():
    """_build_scenario_map: composite key '{model}/{scenario_id}' → bare scenario_id."""
    summary = {
        "scenarios": {
            "composer-2.5/protocol_foo": {"scenario_id": "protocol_foo", "overall_score": 0.80},
            "gpt-4o/protocol_foo": {"scenario_id": "protocol_foo", "overall_score": 0.85},
            "composer-2.5/protocol_bar": {"scenario_id": "protocol_bar", "overall_score": 0.70},
        }
    }
    result = _build_scenario_map(summary)
    assert result["protocol_foo"] == 0.85  # max of 0.80 and 0.85
    assert result["protocol_bar"] == 0.70


# ─── Multiple regressions in single run ───────────────────────────────────────


def test_multiple_regressions_all_reported():
    """Both aggregate and per-scenario regressions reported in same run."""
    with tempfile.TemporaryDirectory() as td:
        summary = _make_summary(0.60, {"sc_a": 0.60, "sc_b": 0.60})
        baseline = _make_baseline("pr", aggregate_score=0.80,
                                  scenarios={"sc_a": 0.80, "sc_b": 0.80})
        run_dir, bl = _write_fixture(Path(td), summary, baseline)
        passed, diff = run_check(run_dir, bl, "pr")
    assert passed is False
    assert len(diff["regressions"]) >= 3  # agg, floor, sc_a, sc_b
