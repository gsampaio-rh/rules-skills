#!/usr/bin/env python3
"""Rich report generator for eval results.

Produces detailed markdown reports with:
- Per-dimension scores
- Score distribution analysis
- Regression warnings
- Failure clustering
- Prioritized recommendations

Usage:
    python tests/eval/report.py                     # generate from latest run
    python tests/eval/report.py --output report.md  # save to file
    python tests/eval/report.py --run <filename>    # specific run file
"""

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

EVAL_DIR = Path(__file__).parent
HISTORY_DIR = EVAL_DIR / "history"
RUNS_DIR = HISTORY_DIR / "runs"
BASELINE_PATH = HISTORY_DIR / "baseline.json"
REPORT_DEFAULT = EVAL_DIR / "EVAL_REPORT.md"


def load_run(filename: str | None = None) -> dict | None:
    if filename:
        path = RUNS_DIR / filename
        if path.exists():
            return json.loads(path.read_text())
        return None

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


def cluster_failures(results: list[dict]) -> dict[str, list[dict]]:
    """Cluster failures by common patterns in failed criteria."""
    failures = [r for r in results if not r.get("passed") and not r.get("error")]
    clusters: dict[str, list[dict]] = defaultdict(list)

    for r in failures:
        for dim_name, dim_data in r.get("dimensions", {}).items():
            for c in dim_data.get("criteria", []):
                if c.get("verdict") == "FAIL":
                    pattern = f"[{dim_name}] {c['criterion'][:60]}"
                    clusters[pattern].append(r)

    return dict(sorted(clusters.items(), key=lambda x: -len(x[1])))


def generate_recommendations(results: list[dict], clusters: dict) -> list[str]:
    """Generate prioritized recommendations from failure patterns."""
    recs = []

    # Rec 1: most common failure cluster
    if clusters:
        top_pattern, cases = next(iter(clusters.items()))
        recs.append(
            f"**Fix most common failure** ({len(cases)} tests): {top_pattern}"
        )

    # Rec 2: worst category
    category_scores: dict[str, list[float]] = defaultdict(list)
    for r in results:
        if not r.get("error"):
            category_scores[r["category"]].append(r["overall_score"])

    if category_scores:
        worst_cat = min(category_scores.items(), key=lambda x: sum(x[1])/len(x[1]))
        avg = sum(worst_cat[1]) / len(worst_cat[1])
        recs.append(
            f"**Improve '{worst_cat[0]}' category** (avg {avg:.0%}, lowest of all categories)"
        )

    # Rec 3: hard test improvement opportunity
    hard_fails = [
        r for r in results
        if r.get("difficulty") == "hard" and not r.get("passed") and not r.get("error")
    ]
    if hard_fails:
        recs.append(
            f"**Address hard-difficulty failures** ({len(hard_fails)} hard tests failing)"
        )

    # Rec 4: low confidence scores
    low_conf = [
        r for r in results
        if r.get("avg_confidence", 5) < 3.0 and not r.get("error")
    ]
    if low_conf:
        recs.append(
            f"**Investigate low-confidence verdicts** ({len(low_conf)} tests with confidence <3)"
        )

    # Rec 5: routing issues
    routing_fails = [
        r for r in results
        if r.get("category") == "routing" and not r.get("passed") and not r.get("error")
    ]
    if routing_fails:
        recs.append(
            f"**Fix routing issues** ({len(routing_fails)} routing tests failing — wrong skill/agent activated)"
        )

    return recs[:5]


def score_histogram(scores: list[float]) -> str:
    """Generate a simple text histogram of score distribution."""
    buckets = {"0-20%": 0, "20-40%": 0, "40-60%": 0, "60-80%": 0, "80-100%": 0}
    for s in scores:
        pct = s * 100
        if pct < 20:
            buckets["0-20%"] += 1
        elif pct < 40:
            buckets["20-40%"] += 1
        elif pct < 60:
            buckets["40-60%"] += 1
        elif pct < 80:
            buckets["60-80%"] += 1
        else:
            buckets["80-100%"] += 1

    lines = []
    max_count = max(buckets.values()) if buckets.values() else 1
    for bucket, count in buckets.items():
        bar_len = int(count / max_count * 30) if max_count > 0 else 0
        bar = "█" * bar_len
        lines.append(f"  {bucket:8s} {bar} {count}")
    return "\n".join(lines)


def generate_report(run: dict, baseline: dict | None = None) -> str:
    """Generate full markdown report."""
    results = run["results"]
    evaluated = [r for r in results if r.get("error") != "no_response"]
    scored = [r for r in evaluated if not r.get("error")]

    lines = []
    lines.append("# Eval Report")
    lines.append("")
    lines.append(f"**Generated**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append(f"**Run**: {run['timestamp']}")
    lines.append(f"**Model**: {run['model']}")
    lines.append("")

    # Overall summary
    overall = run["overall_score"]
    passed = sum(1 for r in scored if r.get("passed"))
    lines.append("## Summary")
    lines.append("")
    lines.append(f"| Metric | Value |")
    lines.append(f"|---|---|")
    lines.append(f"| Overall Score | **{overall:.1%}** |")
    lines.append(f"| Tests Evaluated | {len(evaluated)} |")
    lines.append(f"| Tests Passed (≥80%) | {passed}/{len(scored)} ({passed/len(scored)*100:.0f}%) |")
    lines.append(f"| Tests Skipped (no response) | {len(results) - len(evaluated)} |")

    if baseline:
        delta = overall - baseline["overall_score"]
        arrow = "↑" if delta > 0 else "↓" if delta < 0 else "→"
        lines.append(f"| vs Baseline | {arrow} {delta:+.1%} (from {baseline['overall_score']:.1%}) |")

    lines.append("")

    # Score distribution
    all_scores = [r["overall_score"] for r in scored]
    lines.append("## Score Distribution")
    lines.append("")
    lines.append("```")
    lines.append(score_histogram(all_scores))
    lines.append("```")
    lines.append("")

    # By category
    lines.append("## Results by Category")
    lines.append("")
    lines.append("| Category | Pass Rate | Avg Score | Count |")
    lines.append("|---|---|---|---|")

    category_data: dict[str, list[dict]] = defaultdict(list)
    for r in scored:
        category_data[r["category"]].append(r)

    for cat, cat_results in sorted(category_data.items(), key=lambda x: sum(r["overall_score"] for r in x[1])/len(x[1])):
        cat_passed = sum(1 for r in cat_results if r.get("passed"))
        cat_avg = sum(r["overall_score"] for r in cat_results) / len(cat_results)
        lines.append(f"| {cat} | {cat_passed}/{len(cat_results)} | {cat_avg:.0%} | {len(cat_results)} |")

    lines.append("")

    # By difficulty
    lines.append("## Results by Difficulty")
    lines.append("")
    lines.append("| Difficulty | Pass Rate | Avg Score | Count |")
    lines.append("|---|---|---|---|")

    diff_data: dict[str, list[dict]] = defaultdict(list)
    for r in scored:
        diff_data[r["difficulty"]].append(r)

    for diff in ["easy", "medium", "hard"]:
        if diff in diff_data:
            diff_results = diff_data[diff]
            diff_passed = sum(1 for r in diff_results if r.get("passed"))
            diff_avg = sum(r["overall_score"] for r in diff_results) / len(diff_results)
            lines.append(f"| {diff} | {diff_passed}/{len(diff_results)} | {diff_avg:.0%} | {len(diff_results)} |")

    lines.append("")

    # By dimension
    lines.append("## Results by Scoring Dimension")
    lines.append("")
    lines.append("| Dimension | Avg Score | Appearances |")
    lines.append("|---|---|---|")

    dim_scores: dict[str, list[float]] = defaultdict(list)
    for r in scored:
        for dim_name, dim_data in r.get("dimensions", {}).items():
            dim_scores[dim_name].append(dim_data.get("score", 0))

    for dim, scores in sorted(dim_scores.items(), key=lambda x: sum(x[1])/len(x[1])):
        avg = sum(scores) / len(scores)
        lines.append(f"| {dim} | {avg:.0%} | {len(scores)} |")

    lines.append("")

    # Regression warnings
    if baseline:
        regressions = []
        for r in scored:
            baseline_score = baseline.get("scores_by_test", {}).get(r["test_id"])
            if baseline_score is not None:
                delta = r["overall_score"] - baseline_score
                if delta < -0.10:
                    regressions.append((r["test_id"], baseline_score, r["overall_score"], delta))

        if regressions:
            lines.append("## ⚠ Regressions vs Baseline")
            lines.append("")
            lines.append("| Test | Baseline | Current | Delta |")
            lines.append("|---|---|---|---|")
            for test_id, base, curr, delta in sorted(regressions, key=lambda x: x[3]):
                lines.append(f"| {test_id} | {base:.0%} | {curr:.0%} | {delta:+.0%} |")
            lines.append("")

    # Failure clustering
    clusters = cluster_failures(scored)
    if clusters:
        lines.append("## Failure Clusters")
        lines.append("")
        lines.append("Failures grouped by common criterion pattern:")
        lines.append("")

        for pattern, cases in list(clusters.items())[:10]:
            test_ids = [c["test_id"] for c in cases[:5]]
            lines.append(f"- **{pattern}** ({len(cases)} tests)")
            lines.append(f"  - Tests: {', '.join(test_ids)}")

        lines.append("")

    # Recommendations
    recs = generate_recommendations(scored, clusters)
    if recs:
        lines.append("## Recommendations")
        lines.append("")
        for i, rec in enumerate(recs, 1):
            lines.append(f"{i}. {rec}")
        lines.append("")

    # Detailed failures
    failures = [r for r in scored if not r.get("passed")]
    if failures:
        lines.append("## Detailed Failures")
        lines.append("")
        for r in sorted(failures, key=lambda x: x["overall_score"]):
            lines.append(f"### ✗ {r['test_id']}")
            lines.append(f"")
            lines.append(f"- **Score**: {r['overall_score']:.0%}")
            lines.append(f"- **Category**: {r['category']}")
            lines.append(f"- **Difficulty**: {r['difficulty']}")
            lines.append(f"- **Confidence**: {r.get('avg_confidence', 0):.1f}/5")
            lines.append(f"")
            lines.append("| Dimension | Criterion | Verdict | Reason |")
            lines.append("|---|---|---|---|")

            for dim_name, dim_data in r.get("dimensions", {}).items():
                for c in dim_data.get("criteria", []):
                    if c.get("verdict") == "FAIL":
                        reason = c.get("reason", "").replace("|", "\\|")
                        lines.append(f"| {dim_name} | {c['criterion'][:50]} | FAIL | {reason[:80]} |")

            lines.append("")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate rich eval report")
    parser.add_argument("--output", "-o", default=str(REPORT_DEFAULT), help="Output path for the report")
    parser.add_argument("--run", help="Specific run file to report on (filename in history/runs/)")
    parser.add_argument("--stdout", action="store_true", help="Print to stdout instead of file")
    args = parser.parse_args()

    run = load_run(args.run)
    if not run:
        print("No run results found. Run eval with --save first.")
        return 1

    baseline = load_baseline()
    report = generate_report(run, baseline)

    if args.stdout:
        print(report)
    else:
        output_path = Path(args.output)
        output_path.write_text(report)
        print(f"Report written to: {output_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
