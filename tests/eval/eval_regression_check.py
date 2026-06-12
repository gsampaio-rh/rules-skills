#!/usr/bin/env python3
"""Eval regression gate for CI.

Compares current run summary.json against committed baseline scores.
Exits 1 on regression; exits 0 when scores hold or baseline is unseeded.

Usage:
    python tests/eval/eval_regression_check.py \\
        --run-dir tests/eval_results/<run> \\
        --baseline tests/eval/fixtures/eval_baseline.json \\
        --tier pr \\
        --write-diff regression.json

    python tests/eval/eval_regression_check.py \\
        --update-baseline --run-dir <green_run> --tier pr
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

EVAL_DIR = Path(__file__).parent
DEFAULT_BASELINE = EVAL_DIR / "fixtures" / "eval_baseline.json"

# Regression thresholds
AGGREGATE_DELTA_THRESHOLD = 0.05   # fail if aggregate drops > this
SCENARIO_DELTA_THRESHOLD = 0.10    # fail if any scenario drops > this
ABSOLUTE_FLOOR = 0.70              # fail if aggregate falls below this


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def _find_summary(run_dir: Path) -> Path:
    """Locate summary.json in a run directory.

    session_report.py writes to run_dir/summary.json.
    """
    candidate = run_dir / "summary.json"
    if candidate.exists():
        return candidate
    raise FileNotFoundError(f"summary.json not found in {run_dir}")


def _build_scenario_map(summary: dict) -> dict[str, float]:
    """Map scenario_id -> overall_score from summary.scenarios composite-key dict.

    summary.scenarios keys are '{model}/{scenario_id}'; we match on the
    scenario_id field inside each entry, taking the max score if duplicated.
    """
    result: dict[str, float] = {}
    for entry in summary.get("scenarios", {}).values():
        sid = entry.get("scenario_id", "")
        score = float(entry.get("overall_score", 0.0))
        if sid:
            result[sid] = max(result.get(sid, score), score)
    return result


def run_check(
    run_dir: Path,
    baseline_path: Path,
    tier: str,
) -> tuple[bool, dict]:
    """Run the regression check; return (passed, diff_dict).

    passed=True means no regression detected (or baseline is unseeded).
    diff_dict is always populated for artifact writes.
    """
    summary_path = _find_summary(run_dir)
    summary = _load_json(summary_path)
    baseline = _load_json(baseline_path)

    tier_baseline = baseline.get(tier, {})
    baseline_agg = tier_baseline.get("aggregate_score")

    per_scenario_deltas: list[dict] = []
    regressions: list[str] = []
    warnings: list[str] = []

    # ─── Unseeded baseline → skip regression gate ─────────────────────────────
    if baseline_agg is None:
        warnings.append(f"baseline not seeded for tier '{tier}'; skipping regression gate")
        diff = {
            "tier": tier,
            "regression": False,
            "warnings": warnings,
            "per_scenario_deltas": [],
            "aggregate_delta": None,
        }
        return True, diff

    # ─── Aggregate regression check ───────────────────────────────────────────
    current_agg = float(summary.get("aggregate", {}).get("overall_pass_rate", 0.0))
    aggregate_delta = current_agg - baseline_agg

    agg_drop = round(baseline_agg - current_agg, 6)
    if agg_drop > AGGREGATE_DELTA_THRESHOLD:
        regressions.append(
            f"aggregate regression: baseline={baseline_agg:.3f} current={current_agg:.3f} "
            f"drop={agg_drop:.3f} > threshold {AGGREGATE_DELTA_THRESHOLD}"
        )
    if current_agg < ABSOLUTE_FLOOR:
        regressions.append(
            f"aggregate below floor: current={current_agg:.3f} < floor {ABSOLUTE_FLOOR}"
        )

    # ─── Per-scenario regression check ────────────────────────────────────────
    current_map = _build_scenario_map(summary)
    baseline_scenarios = tier_baseline.get("scenarios", {})

    for scenario_id, b_entry in baseline_scenarios.items():
        b_score = float(b_entry.get("score", 0.0)) if isinstance(b_entry, dict) else float(b_entry)
        c_score = current_map.get(scenario_id)

        delta_entry: dict = {
            "scenario_id": scenario_id,
            "baseline_score": b_score,
            "current_score": c_score,
            "delta": None if c_score is None else round(c_score - b_score, 4),
        }
        per_scenario_deltas.append(delta_entry)

        if c_score is None:
            warnings.append(f"scenario '{scenario_id}' in baseline but not in current run (no data)")
            continue

        drop = round(b_score - c_score, 6)
        if drop > SCENARIO_DELTA_THRESHOLD:
            regressions.append(
                f"scenario '{scenario_id}': baseline={b_score:.3f} current={c_score:.3f} "
                f"drop={drop:.3f} > threshold {SCENARIO_DELTA_THRESHOLD}"
            )

    passed = len(regressions) == 0
    diff = {
        "tier": tier,
        "regression": not passed,
        "regressions": regressions,
        "warnings": warnings,
        "per_scenario_deltas": per_scenario_deltas,
        "aggregate_delta": round(aggregate_delta, 4),
        "current_aggregate": current_agg,
        "baseline_aggregate": baseline_agg,
    }
    return passed, diff


def update_baseline(run_dir: Path, baseline_path: Path, tier: str) -> None:
    """Refresh baseline from a green run (maintainer tool, not invoked in CI)."""
    summary_path = _find_summary(run_dir)
    summary = _load_json(summary_path)

    baseline = _load_json(baseline_path) if baseline_path.exists() else {"pr": {}, "nightly": {}}
    current_agg = float(summary.get("aggregate", {}).get("overall_pass_rate", 0.0))
    current_map = _build_scenario_map(summary)

    baseline[tier] = {
        "aggregate_score": current_agg,
        "scenarios": {sid: {"score": score} for sid, score in sorted(current_map.items())},
    }
    baseline_path.write_text(json.dumps(baseline, indent=2) + "\n")
    print(f"Baseline updated for tier '{tier}': aggregate={current_agg:.3f}, {len(current_map)} scenarios")


def main() -> int:
    parser = argparse.ArgumentParser(description="CI eval regression gate")
    parser.add_argument("--run-dir", required=True, help="Path to eval run directory")
    parser.add_argument("--baseline", default=str(DEFAULT_BASELINE), help="Path to eval_baseline.json")
    parser.add_argument("--tier", required=True, choices=["pr", "nightly"], help="CI tier to check")
    parser.add_argument("--write-diff", metavar="PATH", help="Write regression diff JSON to this path")
    parser.add_argument("--update-baseline", action="store_true",
                        help="Update baseline from run (maintainer use only, not for CI)")
    args = parser.parse_args()

    run_dir = Path(args.run_dir)
    baseline_path = Path(args.baseline)

    if args.update_baseline:
        update_baseline(run_dir, baseline_path, args.tier)
        return 0

    try:
        passed, diff = run_check(run_dir, baseline_path, args.tier)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    if args.write_diff:
        diff_path = Path(args.write_diff)
        diff_path.parent.mkdir(parents=True, exist_ok=True)
        diff_path.write_text(json.dumps(diff, indent=2) + "\n")

    for w in diff.get("warnings", []):
        print(f"WARNING: {w}")
    for r in diff.get("regressions", []):
        print(f"REGRESSION: {r}", file=sys.stderr)

    if passed:
        agg = diff.get("current_aggregate")
        if agg is not None:
            print(f"Regression check PASSED (aggregate={agg:.3f})")
        else:
            print("Regression check PASSED (baseline not seeded)")
    else:
        print("Regression check FAILED", file=sys.stderr)

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
