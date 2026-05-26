#!/usr/bin/env python3
"""Statistical analysis and regression detection for eval results.

Compares current run against baseline, detects regressions, computes
confidence intervals, and tracks trends over time.

Usage:
    python tests/eval/stats.py --baseline          # set current results as baseline
    python tests/eval/stats.py --regress           # check for regressions vs baseline
    python tests/eval/stats.py --trends            # show score trends over time
    python tests/eval/stats.py --summary           # summary of latest run
"""

import argparse
import json
import math
import sys
from pathlib import Path

EVAL_DIR = Path(__file__).parent
HISTORY_DIR = EVAL_DIR / "history"
RUNS_DIR = HISTORY_DIR / "runs"
BASELINE_PATH = HISTORY_DIR / "baseline.json"
TRENDS_PATH = HISTORY_DIR / "trends.json"

REGRESSION_THRESHOLD = 0.10  # 10% drop triggers regression alert


def load_latest_run() -> dict | None:
    if not RUNS_DIR.exists():
        return None
    runs = sorted(RUNS_DIR.glob("*.json"), reverse=True)
    if not runs:
        return None
    return json.loads(runs[0].read_text())


def load_baseline() -> dict | None:
    if not BASELINE_PATH.exists():
        return None
    return json.loads(BASELINE_PATH.read_text())


def load_all_runs() -> list[dict]:
    if not RUNS_DIR.exists():
        return []
    runs = sorted(RUNS_DIR.glob("*.json"))
    return [json.loads(r.read_text()) for r in runs]


def confidence_interval_95(scores: list[float]) -> tuple[float, float]:
    """Compute 95% confidence interval assuming normal distribution."""
    n = len(scores)
    if n < 2:
        return (scores[0] if scores else 0.0, scores[0] if scores else 0.0)

    mean = sum(scores) / n
    variance = sum((x - mean) ** 2 for x in scores) / (n - 1)
    std = math.sqrt(variance)
    margin = 1.96 * std / math.sqrt(n)
    return (mean - margin, mean + margin)


def set_baseline() -> None:
    latest = load_latest_run()
    if not latest:
        print("No run results found. Run eval first: python tests/eval/run_eval.py --save")
        sys.exit(1)

    baseline_data = {
        "timestamp": latest["timestamp"],
        "model": latest["model"],
        "overall_score": latest["overall_score"],
        "scores_by_test": {
            r["test_id"]: r["overall_score"]
            for r in latest["results"]
            if not r.get("error")
        },
        "scores_by_category": {},
        "scores_by_difficulty": {},
    }

    categories: dict[str, list[float]] = {}
    difficulties: dict[str, list[float]] = {}

    for r in latest["results"]:
        if r.get("error"):
            continue
        categories.setdefault(r["category"], []).append(r["overall_score"])
        difficulties.setdefault(r["difficulty"], []).append(r["overall_score"])

    baseline_data["scores_by_category"] = {
        cat: sum(scores) / len(scores) for cat, scores in categories.items()
    }
    baseline_data["scores_by_difficulty"] = {
        diff: sum(scores) / len(scores) for diff, scores in difficulties.items()
    }

    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    BASELINE_PATH.write_text(json.dumps(baseline_data, indent=2))
    print(f"Baseline set from run at {latest['timestamp']}")
    print(f"  Overall: {latest['overall_score']:.1%}")
    print(f"  Tests: {len(baseline_data['scores_by_test'])}")


def check_regressions() -> int:
    baseline = load_baseline()
    latest = load_latest_run()

    if not baseline:
        print("No baseline set. Run: python tests/eval/stats.py --baseline")
        return 1
    if not latest:
        print("No run results found. Run eval first with --save.")
        return 1

    print(f"Comparing against baseline ({baseline['timestamp'][:10]})")
    print(f"{'─' * 60}")

    regressions = []
    improvements = []

    current_scores = {
        r["test_id"]: r["overall_score"]
        for r in latest["results"]
        if not r.get("error")
    }

    for test_id, baseline_score in baseline["scores_by_test"].items():
        current_score = current_scores.get(test_id)
        if current_score is None:
            continue

        delta = current_score - baseline_score
        if delta < -REGRESSION_THRESHOLD:
            regressions.append((test_id, baseline_score, current_score, delta))
        elif delta > REGRESSION_THRESHOLD:
            improvements.append((test_id, baseline_score, current_score, delta))

    overall_delta = latest["overall_score"] - baseline["overall_score"]

    if regressions:
        print(f"\n⚠  REGRESSIONS DETECTED ({len(regressions)}):")
        for test_id, base, curr, delta in sorted(regressions, key=lambda x: x[3]):
            print(f"  ✗ {test_id:45s} {base:.0%} → {curr:.0%} ({delta:+.0%})")

    if improvements:
        print(f"\n✓  IMPROVEMENTS ({len(improvements)}):")
        for test_id, base, curr, delta in sorted(improvements, key=lambda x: -x[3]):
            print(f"  ✓ {test_id:45s} {base:.0%} → {curr:.0%} ({delta:+.0%})")

    print(f"\n{'─' * 60}")
    print(f"  Overall: {baseline['overall_score']:.1%} → {latest['overall_score']:.1%} ({overall_delta:+.1%})")

    if regressions:
        print(f"\n  STATUS: REGRESSION ({len(regressions)} tests dropped >{REGRESSION_THRESHOLD:.0%})")
        return 1
    else:
        print(f"\n  STATUS: OK (no regressions)")
        return 0


def show_trends() -> None:
    runs = load_all_runs()
    if not runs:
        print("No run history found. Run eval with --save to build history.")
        return

    print(f"{'─' * 60}")
    print("SCORE TRENDS")
    print(f"{'─' * 60}")
    print(f"  {'Date':12s} {'Model':15s} {'Score':8s} {'Evaluated':10s}")
    print(f"  {'─'*12} {'─'*15} {'─'*8} {'─'*10}")

    for run in runs:
        date = run["timestamp"][:10]
        model = run["model"][:15]
        score = run["overall_score"]
        evaluated = run["evaluated"]
        print(f"  {date:12s} {model:15s} {score:7.1%} {evaluated:10d}")

    if len(runs) >= 2:
        scores = [r["overall_score"] for r in runs]
        low, high = confidence_interval_95(scores)
        mean = sum(scores) / len(scores)
        print(f"\n  Mean: {mean:.1%}  95% CI: [{low:.1%}, {high:.1%}]  N={len(runs)} runs")

    # Category trends
    print(f"\n{'─' * 60}")
    print("CATEGORY TRENDS (latest 3 runs)")
    print(f"{'─' * 60}")

    recent = runs[-3:]
    all_cats: set[str] = set()
    for run in recent:
        for r in run["results"]:
            if not r.get("error"):
                all_cats.add(r["category"])

    for cat in sorted(all_cats):
        scores_per_run = []
        for run in recent:
            cat_scores = [
                r["overall_score"] for r in run["results"]
                if r["category"] == cat and not r.get("error")
            ]
            if cat_scores:
                scores_per_run.append(sum(cat_scores) / len(cat_scores))

        if scores_per_run:
            trend = " → ".join(f"{s:.0%}" for s in scores_per_run)
            print(f"  {cat:20s}  {trend}")


def show_summary() -> None:
    latest = load_latest_run()
    if not latest:
        print("No run results found.")
        return

    print(f"{'═' * 60}")
    print(f"LATEST RUN SUMMARY")
    print(f"{'═' * 60}")
    print(f"  Timestamp: {latest['timestamp']}")
    print(f"  Model: {latest['model']}")
    print(f"  Overall: {latest['overall_score']:.1%}")
    print(f"  Evaluated: {latest['evaluated']}/{latest['total_cases']}")

    categories: dict[str, list[float]] = {}
    difficulties: dict[str, list[float]] = {}
    dimensions_all: dict[str, list[float]] = {}

    for r in latest["results"]:
        if r.get("error"):
            continue
        categories.setdefault(r["category"], []).append(r["overall_score"])
        difficulties.setdefault(r["difficulty"], []).append(r["overall_score"])

        for dim_name, dim_data in r.get("dimensions", {}).items():
            dimensions_all.setdefault(dim_name, []).append(dim_data.get("score", 0))

    print(f"\n  By Category:")
    for cat, scores in sorted(categories.items(), key=lambda x: sum(x[1])/len(x[1])):
        avg = sum(scores) / len(scores)
        print(f"    {cat:20s} {avg:.0%} ({len(scores)} tests)")

    print(f"\n  By Difficulty:")
    for diff in ["easy", "medium", "hard"]:
        if diff in difficulties:
            scores = difficulties[diff]
            avg = sum(scores) / len(scores)
            print(f"    {diff:10s} {avg:.0%} ({len(scores)} tests)")

    if dimensions_all:
        print(f"\n  By Dimension:")
        for dim, scores in sorted(dimensions_all.items(), key=lambda x: sum(x[1])/len(x[1])):
            avg = sum(scores) / len(scores)
            print(f"    {dim:20s} {avg:.0%} ({len(scores)} tests)")


def main() -> int:
    parser = argparse.ArgumentParser(description="Statistical analysis for eval results")
    parser.add_argument("--baseline", action="store_true", help="Set current results as baseline")
    parser.add_argument("--regress", action="store_true", help="Check for regressions vs baseline")
    parser.add_argument("--trends", action="store_true", help="Show score trends over time")
    parser.add_argument("--summary", action="store_true", help="Summary of latest run")
    args = parser.parse_args()

    if args.baseline:
        set_baseline()
        return 0
    elif args.regress:
        return check_regressions()
    elif args.trends:
        show_trends()
        return 0
    elif args.summary:
        show_summary()
        return 0
    else:
        show_summary()
        return 0


if __name__ == "__main__":
    sys.exit(main())
