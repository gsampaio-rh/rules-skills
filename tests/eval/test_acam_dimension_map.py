"""Tests for feat-acam-scenario-mapping.

Covers:
  (a) All ci_suites.json scenarios are mapped in acam_dimension_map.json
  (b) Stale/extra map keys are detectable
  (c) All values are valid ACAM dimension strings
  (d) lint_acam_dimension_map returns ([], []) on valid map
  (e) lint returns non-empty errors when scenario missing from map
  (f) lint returns non-empty errors when invalid dimension value
  (g) lint returns non-empty warnings (empty errors) for stale-only entries
  (h) compute_summary acam_dimensions rollup populated from mock judgments
  (i) rollup emits null rate for dimension with no judgments
  (j) compute_summary([]) includes acam_dimensions all four dimensions {pass:0, total:0, rate:None}
  (k) lint errors when acam_dimension_map.json missing
  (l) lint errors on malformed JSON
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.eval.harness_lint import lint_acam_dimension_map
from tests.eval.session_report import compute_summary, ACAM_DIMENSIONS

FIXTURES_DIR = Path(__file__).parent.parent / "eval" / "fixtures"
EVAL_DIR = Path(__file__).parent.parent / "eval"


# ── Helpers ───────────────────────────────────────────────────────────────────


def _load_ci_suites() -> dict:
    return json.loads((FIXTURES_DIR / "ci_suites.json").read_text())


def _load_acam_map() -> dict:
    return json.loads((FIXTURES_DIR / "acam_dimension_map.json").read_text())


def _all_suite_ids() -> set[str]:
    suites = _load_ci_suites()
    return set(suites.get("pr", [])) | set(suites.get("nightly", []))


def _make_eval_dir(tmp_path: Path, dimension_map: dict, suites: dict | None = None) -> Path:
    """Build a minimal eval directory with fixtures for lint testing."""
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir(parents=True)
    (fixtures / "acam_dimension_map.json").write_text(json.dumps(dimension_map))
    if suites is None:
        suites = {
            "pr": ["scenario_a", "scenario_b"],
            "nightly": ["scenario_a", "scenario_c"],
        }
    (fixtures / "ci_suites.json").write_text(json.dumps(suites))
    return tmp_path


def _make_judgment(scenario_id: str, pass_count: int, total: int) -> dict:
    return {
        "scenario_id": scenario_id,
        "model": "test-model",
        "timestamp": "2026-06-12T00:00:00Z",
        "results": [],
        "summary": {
            "score": round(pass_count / max(total, 1), 2),
            "pass": pass_count,
            "total": total,
            "fail": total - pass_count,
            "unmatched": 0,
            "uncertain": 0,
        },
    }


# ── (a) All ci_suites scenarios are mapped ────────────────────────────────────


def test_all_ci_suites_scenarios_are_mapped():
    """Every scenario in ci_suites.json pr + nightly must appear in the map."""
    suite_ids = _all_suite_ids()
    dimension_map = _load_acam_map()
    missing = suite_ids - set(dimension_map)
    assert not missing, f"Scenarios missing from acam_dimension_map: {sorted(missing)}"


# ── (b) Stale/extra map keys are detectable ───────────────────────────────────


def test_no_stale_entries_in_real_map():
    """No stale scenario IDs in the committed map (all keys are in ci_suites)."""
    suite_ids = _all_suite_ids()
    dimension_map = _load_acam_map()
    stale = set(dimension_map) - suite_ids
    assert not stale, f"Stale entries in acam_dimension_map: {sorted(stale)}"


# ── (c) All values are valid ACAM dimension strings ──────────────────────────


def test_all_dimension_values_are_valid():
    """Every value in acam_dimension_map must be one of the four ACAM dimensions."""
    valid = set(ACAM_DIMENSIONS)
    dimension_map = _load_acam_map()
    invalid = {k: v for k, v in dimension_map.items() if v not in valid}
    assert not invalid, f"Invalid dimension values: {invalid}"


# ── (d) lint returns ([], []) on valid map ────────────────────────────────────


def test_lint_valid_map_returns_no_errors(tmp_path):
    valid_map = {"scenario_a": "workflows", "scenario_b": "configuration", "scenario_c": "multi_agent"}
    eval_dir = _make_eval_dir(tmp_path, valid_map)
    errors, warnings = lint_acam_dimension_map(eval_dir)
    assert errors == []
    assert warnings == []


# ── (e) lint errors when scenario missing from map ───────────────────────────


def test_lint_errors_on_missing_scenario(tmp_path):
    """Map missing scenario_c must produce an error naming scenario_c."""
    partial_map = {"scenario_a": "workflows", "scenario_b": "configuration"}
    eval_dir = _make_eval_dir(tmp_path, partial_map)
    errors, _warnings = lint_acam_dimension_map(eval_dir)
    assert errors, "Expected errors for missing scenario_c"
    assert any("scenario_c" in e for e in errors), f"Error must name missing scenario: {errors}"


# ── (f) lint errors on invalid dimension value ────────────────────────────────


def test_lint_errors_on_invalid_dimension_value(tmp_path):
    invalid_map = {"scenario_a": "workflows", "scenario_b": "INVALID_DIM", "scenario_c": "multi_agent"}
    eval_dir = _make_eval_dir(tmp_path, invalid_map)
    errors, _warnings = lint_acam_dimension_map(eval_dir)
    assert errors, "Expected errors for invalid dimension value"
    assert any("INVALID_DIM" in e or "scenario_b" in e for e in errors)


# ── (g) lint warns (not errors) for stale-only entries ───────────────────────


def test_lint_warns_not_errors_for_stale_entries(tmp_path):
    """Extra scenario in map that is not in ci_suites must warn, not error."""
    stale_map = {
        "scenario_a": "workflows",
        "scenario_b": "configuration",
        "scenario_c": "multi_agent",
        "stale_scenario": "interaction",
    }
    eval_dir = _make_eval_dir(tmp_path, stale_map)
    errors, warnings = lint_acam_dimension_map(eval_dir)
    assert errors == [], f"Stale entry must not produce errors, got: {errors}"
    assert warnings, "Stale entry must produce a warning"
    assert any("stale_scenario" in w for w in warnings)


# ── (h) compute_summary rollup from mock judgments ───────────────────────────


def test_compute_summary_acam_rollup_from_judgments(tmp_path, monkeypatch):
    """acam_dimensions rollup sums pass/total per ACAM dimension from judgments."""
    custom_map = {
        "scen_workflows": "workflows",
        "scen_config": "configuration",
    }
    map_path = tmp_path / "acam_dimension_map.json"
    map_path.write_text(json.dumps(custom_map))

    import tests.eval.session_report as sr
    monkeypatch.setattr(sr, "ACAM_DIMENSION_MAP_PATH", map_path)

    judgments = [
        _make_judgment("scen_workflows", pass_count=8, total=10),
        _make_judgment("scen_config", pass_count=5, total=5),
    ]
    summary = compute_summary(judgments)

    assert "acam_dimensions" in summary
    wf = summary["acam_dimensions"]["workflows"]
    assert wf["pass"] == 8 and wf["total"] == 10 and wf["rate"] == 0.80
    cfg = summary["acam_dimensions"]["configuration"]
    assert cfg["pass"] == 5 and cfg["total"] == 5 and cfg["rate"] == 1.0


# ── (i) rollup emits null rate for dimension with no judgments ────────────────


def test_compute_summary_acam_rollup_null_rate_for_empty_dimension(tmp_path, monkeypatch):
    """Dimensions with no matching judgments must emit rate=null."""
    custom_map = {"scen_a": "workflows"}
    map_path = tmp_path / "acam_dimension_map.json"
    map_path.write_text(json.dumps(custom_map))

    import tests.eval.session_report as sr
    monkeypatch.setattr(sr, "ACAM_DIMENSION_MAP_PATH", map_path)

    judgments = [_make_judgment("scen_a", pass_count=3, total=4)]
    summary = compute_summary(judgments)

    assert summary["acam_dimensions"]["configuration"]["rate"] is None
    assert summary["acam_dimensions"]["multi_agent"]["rate"] is None
    assert summary["acam_dimensions"]["interaction"]["rate"] is None
    assert summary["acam_dimensions"]["workflows"]["rate"] is not None


# ── (j) compute_summary([]) all dimensions at {pass:0, total:0, rate:None} ───


def test_compute_summary_empty_judgments_acam_dimensions():
    """compute_summary([]) must include acam_dimensions with all four dims at zero."""
    summary = compute_summary([])
    assert "acam_dimensions" in summary
    dims = summary["acam_dimensions"]
    assert set(dims.keys()) == set(ACAM_DIMENSIONS)
    for dim in ACAM_DIMENSIONS:
        assert dims[dim] == {"pass": 0, "total": 0, "rate": None}, (
            f"Expected {{pass:0, total:0, rate:None}} for {dim}, got {dims[dim]}"
        )


# ── (k) lint errors when map file missing ─────────────────────────────────────


def test_lint_errors_when_map_file_missing(tmp_path):
    """lint_acam_dimension_map must return errors when acam_dimension_map.json absent."""
    suites = {"pr": ["s1"], "nightly": ["s1"]}
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir()
    (fixtures / "ci_suites.json").write_text(json.dumps(suites))
    errors, _warnings = lint_acam_dimension_map(tmp_path)
    assert errors, "Expected error when acam_dimension_map.json is missing"


# ── (l) lint errors on malformed JSON ────────────────────────────────────────


def test_lint_errors_on_malformed_map_json(tmp_path):
    """lint_acam_dimension_map must return errors when map file has invalid JSON."""
    suites = {"pr": ["s1"], "nightly": ["s1"]}
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir()
    (fixtures / "ci_suites.json").write_text(json.dumps(suites))
    (fixtures / "acam_dimension_map.json").write_text("{ not valid json }")
    errors, _warnings = lint_acam_dimension_map(tmp_path)
    assert errors, "Expected error for malformed JSON"
