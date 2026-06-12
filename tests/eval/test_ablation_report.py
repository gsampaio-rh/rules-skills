"""Unit tests for ablation_report.py.

Tests verify all AC/EC for feat-16 using synthetic fixtures without live sessions.
"""

from __future__ import annotations

import json
import math
import tempfile
from pathlib import Path

import pytest

from tests.eval.ablation_report import _cohens_d, _wilcoxon_test, compute_report


# ─── Fixtures ─────────────────────────────────────────────────────────────────


def _make_judgment(scenario_id: str, score: float, results: list[dict] | None = None) -> dict:
    """Minimal judgment dict matching judge_session() output schema."""
    if results is None:
        results = [
            {"criterion": "criterion A", "result": "PASS", "tier": "computational"},
            {"criterion": "criterion B", "result": "FAIL", "tier": "structural"},
        ]
    return {
        "scenario_id": scenario_id,
        "model": "test-model",
        "summary": {
            "total": len(results),
            "pass": sum(1 for r in results if r["result"] == "PASS"),
            "fail": sum(1 for r in results if r["result"] == "FAIL"),
            "score": score,
        },
        "results": results,
    }


def _write_judgment_pair(
    run_dir: Path,
    rule_stem: str,
    scenario_id: str,
    control_score: float,
    ablated_score: float,
    control_results: list[dict] | None = None,
    ablated_results: list[dict] | None = None,
) -> None:
    for arm, score, extra_results in (
        ("control", control_score, control_results),
        ("ablated", ablated_score, ablated_results),
    ):
        j = _make_judgment(scenario_id, score, extra_results)
        out = run_dir / "ablation" / rule_stem / "judgments" / arm
        out.mkdir(parents=True, exist_ok=True)
        (out / f"{scenario_id}.json").write_text(json.dumps(j))


# ─── _cohens_d ────────────────────────────────────────────────────────────────


def test_cohens_d_typical():
    diffs = [0.1, 0.2, 0.3, 0.4, 0.5]
    d = _cohens_d(diffs)
    assert d is not None
    expected = sum(diffs) / len(diffs) / (
        math.sqrt(sum((x - sum(diffs) / len(diffs)) ** 2 for x in diffs) / (len(diffs) - 1))
    )
    assert abs(d - expected) < 1e-9


def test_cohens_d_n_less_than_2_returns_none():
    assert _cohens_d([]) is None
    assert _cohens_d([0.5]) is None


def test_cohens_d_all_zero_diffs_returns_zero(ec3: None = None):
    """EC3: all diffs zero → cohens_d = 0.0 (std == 0)."""
    assert _cohens_d([0.0, 0.0, 0.0]) == 0.0


def test_cohens_d_nonzero_equal_diffs_returns_zero(ec4: None = None):
    """EC4: n>=2, all diffs identical nonzero → std(ddof=1) == 0 → cohens_d = 0.0."""
    assert _cohens_d([0.3, 0.3, 0.3]) == 0.0


# ─── _wilcoxon_test ────────────────────────────────────────────────────────────


def test_wilcoxon_n_less_than_2_returns_nulls():
    """EC2: n=1 → all None + note."""
    stat, p, note = _wilcoxon_test([0.8], [0.5])
    assert stat is None
    assert p is None
    assert note is not None
    assert "insufficient" in note.lower()


def test_wilcoxon_n_greater_than_1_returns_floats():
    stat, p, note = _wilcoxon_test([0.8, 0.7, 0.9], [0.5, 0.4, 0.6])
    assert isinstance(stat, float)
    assert isinstance(p, float)
    assert note is None


def test_wilcoxon_all_zero_diffs_does_not_raise():
    """EC3: zero diffs with n>=2 must not raise."""
    stat, p, note = _wilcoxon_test([0.5, 0.5, 0.5], [0.5, 0.5, 0.5])
    # scipy raises ValueError for zero diffs in some versions;
    # our wrapper must catch it and return None gracefully.
    assert note is not None or isinstance(stat, float)


# ─── compute_report ─────────────────────────────────────────────────────────


def test_compute_report_aggregate_delta():
    """AC6: aggregate_delta = mean(control) - mean(ablated)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        run_dir = Path(tmpdir)
        _write_judgment_pair(run_dir, "test_rule", "s1", 0.8, 0.6)
        _write_judgment_pair(run_dir, "test_rule", "s2", 0.9, 0.5)
        _write_judgment_pair(run_dir, "test_rule", "s3", 0.7, 0.4)

        report = compute_report(run_dir, "test_rule")

        expected_delta = ((0.8 + 0.9 + 0.7) / 3) - ((0.6 + 0.5 + 0.4) / 3)
        assert abs(report["aggregate_delta"] - expected_delta) < 1e-9


def test_compute_report_cohens_d():
    """AC8: Cohen's d via paired mean/std formula."""
    with tempfile.TemporaryDirectory() as tmpdir:
        run_dir = Path(tmpdir)
        _write_judgment_pair(run_dir, "r", "s1", 0.8, 0.6)
        _write_judgment_pair(run_dir, "r", "s2", 0.9, 0.5)
        _write_judgment_pair(run_dir, "r", "s3", 0.7, 0.4)

        report = compute_report(run_dir, "r")
        assert report["cohens_d"] is not None
        assert report["cohens_d"] > 0


def test_compute_report_wilcoxon_fields():
    """AC7: wilcoxon_statistic and wilcoxon_p present for n>=2."""
    with tempfile.TemporaryDirectory() as tmpdir:
        run_dir = Path(tmpdir)
        _write_judgment_pair(run_dir, "r", "s1", 0.8, 0.6)
        _write_judgment_pair(run_dir, "r", "s2", 0.9, 0.5)

        report = compute_report(run_dir, "r")
        assert "wilcoxon_statistic" in report
        assert "wilcoxon_p" in report


def test_compute_report_n1_all_nulls():
    """EC2: n=1 → wilcoxon_statistic, wilcoxon_p, cohens_d all null; significant false."""
    with tempfile.TemporaryDirectory() as tmpdir:
        run_dir = Path(tmpdir)
        _write_judgment_pair(run_dir, "r", "s1", 0.8, 0.6)

        report = compute_report(run_dir, "r")
        assert report["wilcoxon_statistic"] is None
        assert report["wilcoxon_p"] is None
        assert report["cohens_d"] is None
        assert report["significant"] is False
        assert "note" in report
        assert "insufficient" in report["note"].lower()


def test_compute_report_all_zero_diffs_cohens_d_zero():
    """EC3: all diffs zero → cohens_d = 0.0, significant = False."""
    with tempfile.TemporaryDirectory() as tmpdir:
        run_dir = Path(tmpdir)
        _write_judgment_pair(run_dir, "r", "s1", 0.7, 0.7)
        _write_judgment_pair(run_dir, "r", "s2", 0.7, 0.7)
        _write_judgment_pair(run_dir, "r", "s3", 0.7, 0.7)

        report = compute_report(run_dir, "r")
        assert report["cohens_d"] == 0.0
        assert report["significant"] is False


def test_compute_report_nonzero_equal_diffs_cohens_d_zero():
    """EC4: n>=2, std(diffs)==0 but diffs nonzero → cohens_d = 0.0."""
    with tempfile.TemporaryDirectory() as tmpdir:
        run_dir = Path(tmpdir)
        _write_judgment_pair(run_dir, "r", "s1", 0.8, 0.5)
        _write_judgment_pair(run_dir, "r", "s2", 0.8, 0.5)
        _write_judgment_pair(run_dir, "r", "s3", 0.8, 0.5)

        report = compute_report(run_dir, "r")
        assert report["cohens_d"] == 0.0


def test_compute_report_key_schema():
    """AC9: report dict has all required top-level keys."""
    required_keys = {
        "rule", "scenarios_count", "per_scenario_deltas",
        "aggregate_delta", "wilcoxon_statistic", "wilcoxon_p",
        "cohens_d", "significant",
    }
    with tempfile.TemporaryDirectory() as tmpdir:
        run_dir = Path(tmpdir)
        _write_judgment_pair(run_dir, "myrule", "s1", 0.8, 0.6)
        _write_judgment_pair(run_dir, "myrule", "s2", 0.7, 0.5)

        report = compute_report(run_dir, "myrule")
        assert required_keys.issubset(report.keys())
        assert report["rule"] == "myrule"
        assert report["scenarios_count"] == 2


def test_compute_report_per_scenario_deltas_schema():
    """AC5: per_scenario_deltas entries have scenario_id, scores, delta, criteria list."""
    ctrl_results = [{"criterion": "X", "result": "PASS", "tier": "computational"}]
    abl_results = [{"criterion": "X", "result": "FAIL", "tier": "computational"}]

    with tempfile.TemporaryDirectory() as tmpdir:
        run_dir = Path(tmpdir)
        _write_judgment_pair(
            run_dir, "r", "s1", 0.8, 0.5,
            control_results=ctrl_results, ablated_results=abl_results,
        )
        _write_judgment_pair(run_dir, "r", "s2", 0.7, 0.4)

        report = compute_report(run_dir, "r")
        for entry in report["per_scenario_deltas"]:
            assert "scenario_id" in entry
            assert "control_score" in entry
            assert "ablated_score" in entry
            assert "delta" in entry
            assert "criteria" in entry
            assert abs(entry["delta"] - (entry["control_score"] - entry["ablated_score"])) < 1e-9

        s1 = next(e for e in report["per_scenario_deltas"] if e["scenario_id"] == "s1")
        assert len(s1["criteria"]) == 1
        crit = s1["criteria"][0]
        assert crit["criterion"] == "X"
        assert crit["control_result"] == "PASS"
        assert crit["ablated_result"] == "FAIL"
        assert crit["changed"] is True


def test_compute_report_significant_false_when_p_null():
    """AC9: significant is False (not TypeError) when wilcoxon_p is null."""
    with tempfile.TemporaryDirectory() as tmpdir:
        run_dir = Path(tmpdir)
        _write_judgment_pair(run_dir, "r", "s1", 0.8, 0.6)

        report = compute_report(run_dir, "r")
        assert report["significant"] is False


# ─── CaptureWorkspace excluded_rules ─────────────────────────────────────────


def test_capture_workspace_excluded_rules():
    """AC3: excluded_rules causes target rule to be absent; other rules present."""
    from tests.eval.sandbox import CaptureWorkspace

    with CaptureWorkspace(excluded_rules={"adversarial_harness.mdc"}) as ws:
        rules_dir = ws.path / ".cursor" / "rules"
        ablated_rule = rules_dir / "adversarial_harness.mdc"
        assert not ablated_rule.exists(), (
            "adversarial_harness.mdc should be absent in ablated workspace"
        )
        other_rules = [f for f in rules_dir.iterdir() if f.is_file() and f.suffix == ".mdc"]
        assert len(other_rules) >= 1, (
            "At least one other rule should still be present after exclusion"
        )
