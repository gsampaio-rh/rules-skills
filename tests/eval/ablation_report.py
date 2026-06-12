#!/usr/bin/env python3
"""Ablation report: per-criterion delta, Wilcoxon signed-rank test, Cohen's d.

Compares paired control vs ablated session judgments produced by session_runner.py
--ablate-rule runs. All score values come from judgment['summary']['score'] (0.0-1.0).

Usage (called by session_runner.py after an ablation run):
    from tests.eval.ablation_report import compute_report
    report = compute_report(run_dir, rule_stem="adversarial_harness")
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any


def _load_judgment(path: Path) -> dict:
    return json.loads(path.read_text())


def _per_criterion_delta(
    control_judgment: dict,
    ablated_judgment: dict,
) -> list[dict]:
    """Build criterion-level comparison between control and ablated judgments.

    Matches criteria by text. Unmatched criteria in either judgment are skipped.
    `changed` is True when result differs between control and ablated.
    """
    control_map = {
        r["criterion"]: r["result"]
        for r in control_judgment.get("results", [])
    }
    ablated_map = {
        r["criterion"]: r["result"]
        for r in ablated_judgment.get("results", [])
    }
    shared = [c for c in control_map if c in ablated_map]
    return [
        {
            "criterion": c,
            "control_result": control_map[c],
            "ablated_result": ablated_map[c],
            "changed": control_map[c] != ablated_map[c],
        }
        for c in shared
    ]


def _cohens_d(diffs: list[float]) -> float | None:
    """Paired Cohen's d = mean(diffs) / std(diffs, ddof=1).

    Returns None when n < 2, 0.0 when std == 0.
    """
    n = len(diffs)
    if n < 2:
        return None
    mean = sum(diffs) / n
    variance = sum((x - mean) ** 2 for x in diffs) / (n - 1)
    std = math.sqrt(variance)
    if std == 0.0:
        return 0.0
    return mean / std


def _wilcoxon_test(
    control: list[float],
    ablated: list[float],
) -> tuple[float | None, float | None, str | None]:
    """Run Wilcoxon signed-rank test on paired scores.

    Returns (statistic, p_value, note). All None when n < 2.
    """
    n = len(control)
    if n < 2:
        return None, None, "insufficient pairs for Wilcoxon test (need >= 2)"
    try:
        from scipy.stats import wilcoxon
        result = wilcoxon(control, ablated, alternative="two-sided")
        return float(result.statistic), float(result.pvalue), None
    except Exception as exc:
        return None, None, f"Wilcoxon error: {exc}"


def compute_report(run_dir: Path, rule_stem: str) -> dict[str, Any]:
    """Compute ablation report from paired control/ablated judgments.

    Loads all judgment pairs from:
      run_dir/ablation/<rule_stem>/judgments/control/<scenario_id>.json
      run_dir/ablation/<rule_stem>/judgments/ablated/<scenario_id>.json

    Returns a report dict matching the AC9 schema. Writes nothing to disk;
    caller (session_runner.py) is responsible for serializing to report.json.
    """
    ablation_dir = run_dir / "ablation" / rule_stem
    control_dir = ablation_dir / "judgments" / "control"
    ablated_dir = ablation_dir / "judgments" / "ablated"

    control_paths = {p.stem: p for p in control_dir.glob("*.json")} if control_dir.exists() else {}
    ablated_paths = {p.stem: p for p in ablated_dir.glob("*.json")} if ablated_dir.exists() else {}

    paired_ids = sorted(set(control_paths) & set(ablated_paths))

    per_scenario_deltas: list[dict] = []
    control_scores: list[float] = []
    ablated_scores: list[float] = []

    for scenario_id in paired_ids:
        c_judgment = _load_judgment(control_paths[scenario_id])
        a_judgment = _load_judgment(ablated_paths[scenario_id])

        c_score = float(c_judgment.get("summary", {}).get("score", 0.0))
        a_score = float(a_judgment.get("summary", {}).get("score", 0.0))
        delta = c_score - a_score

        per_scenario_deltas.append({
            "scenario_id": scenario_id,
            "control_score": c_score,
            "ablated_score": a_score,
            "delta": delta,
            "criteria": _per_criterion_delta(c_judgment, a_judgment),
        })
        control_scores.append(c_score)
        ablated_scores.append(a_score)

    n = len(control_scores)
    aggregate_delta = (
        (sum(control_scores) - sum(ablated_scores)) / n if n > 0 else 0.0
    )

    diffs = [c - a for c, a in zip(control_scores, ablated_scores)]
    cohens_d = _cohens_d(diffs)
    w_stat, w_p, w_note = _wilcoxon_test(control_scores, ablated_scores)

    significant = False if w_p is None else (w_p < 0.05)

    report: dict[str, Any] = {
        "rule": rule_stem,
        "scenarios_count": n,
        "per_scenario_deltas": per_scenario_deltas,
        "aggregate_delta": aggregate_delta,
        "wilcoxon_statistic": w_stat,
        "wilcoxon_p": w_p,
        "cohens_d": cohens_d,
        "significant": significant,
    }
    if w_note:
        report["note"] = w_note

    return report


def print_summary(report: dict) -> None:
    """Print a human-readable summary of an ablation report."""
    rule = report["rule"]
    n = report["scenarios_count"]
    delta = report["aggregate_delta"]
    d = report["cohens_d"]
    p = report["wilcoxon_p"]
    sig = report["significant"]

    print(f"\nAblation report: {rule}")
    print(f"  Scenarios:       {n}")
    print(f"  Aggregate delta: {delta:+.3f}  (control - ablated; positive = rule helps)")
    print(f"  Cohen's d:       {d if d is not None else 'n/a'}")
    print(f"  Wilcoxon p:      {p if p is not None else 'n/a'}")
    print(f"  Significant:     {'YES (p < 0.05)' if sig else 'NO'}")

    if report.get("note"):
        print(f"  Note:            {report['note']}")

    changed_total = sum(
        sum(1 for c in s["criteria"] if c["changed"])
        for s in report.get("per_scenario_deltas", [])
    )
    print(f"\n  Per-scenario criterion changes: {changed_total} total")
    for entry in report.get("per_scenario_deltas", []):
        changed = sum(1 for c in entry["criteria"] if c["changed"])
        print(
            f"    {entry['scenario_id']:40s} "
            f"ctrl={entry['control_score']:.2f}  abl={entry['ablated_score']:.2f}  "
            f"Δ={entry['delta']:+.2f}  {changed} criteria changed"
        )
