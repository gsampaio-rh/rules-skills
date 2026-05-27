#!/usr/bin/env python3
"""Divergence analysis: identify where model behavior diverges from expectations.

Reads eval results (both single-turn and multi-turn) and produces:
1. Category-level patterns (which rules are consistently weak?)
2. Dimension-level patterns (Judgment fails more than Compliance?)
3. Specific divergence examples with root-cause hypotheses
4. Suggested rule/prompt tuning based on patterns

Usage:
    python tests/eval/divergence.py                        # analyze latest run
    python tests/eval/divergence.py --run FILENAME         # analyze specific run
    python tests/eval/divergence.py --compare baseline     # compare vs baseline
    python tests/eval/divergence.py --verbose              # include per-test details
"""

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

EVAL_DIR = Path(__file__).parent
HISTORY_DIR = EVAL_DIR / "history" / "runs"
DIVERGENCE_DIR = EVAL_DIR / "history" / "divergence"


def find_latest_run(suffix: str = "") -> Path | None:
    if not HISTORY_DIR.exists():
        return None
    runs = sorted(HISTORY_DIR.glob(f"*{suffix}.json"), reverse=True)
    return runs[0] if runs else None


def load_run(path: Path) -> dict:
    return json.loads(path.read_text())


def analyze_category_patterns(results: list[dict]) -> dict[str, dict]:
    """Group results by category and compute pass rates."""
    by_category: dict[str, list[float]] = defaultdict(list)

    for r in results:
        if "error" in r:
            continue
        cat = r.get("category", "unknown")
        by_category[cat].append(r.get("overall_score", 0))

    patterns = {}
    for cat, scores in sorted(by_category.items(), key=lambda x: _mean(x[1])):
        patterns[cat] = {
            "avg_score": round(_mean(scores), 3),
            "tests": len(scores),
            "passed": sum(1 for s in scores if s >= 0.8),
            "weakest_scores": sorted(scores)[:3],
        }
    return patterns


def analyze_dimension_patterns(results: list[dict]) -> dict[str, dict]:
    """Aggregate scores by rubric dimension across all tests."""
    by_dimension: dict[str, list[float]] = defaultdict(list)

    for r in results:
        dims = r.get("dimensions", {})
        for dim_name, dim_data in dims.items():
            if isinstance(dim_data, dict):
                score = dim_data.get("score", 0)
                by_dimension[dim_name].append(score)

    patterns = {}
    for dim, scores in sorted(by_dimension.items(), key=lambda x: _mean(x[1])):
        patterns[dim] = {
            "avg_score": round(_mean(scores), 3),
            "tests": len(scores),
            "passed": sum(1 for s in scores if s >= 0.8),
        }
    return patterns


def find_systematic_failures(results: list[dict]) -> list[dict]:
    """Find criteria that fail systematically across multiple tests."""
    criterion_results: dict[str, list[dict]] = defaultdict(list)

    for r in results:
        dims = r.get("dimensions", {})
        for dim_name, dim_data in dims.items():
            if not isinstance(dim_data, dict):
                continue
            for criterion_info in dim_data.get("criteria", []):
                if isinstance(criterion_info, dict):
                    key = criterion_info.get("criterion", "")[:80]
                    criterion_results[key].append({
                        "test_id": r.get("test_id", ""),
                        "verdict": criterion_info.get("verdict", ""),
                        "reason": criterion_info.get("reason", ""),
                    })

    failures = []
    for criterion_key, occurrences in criterion_results.items():
        fail_count = sum(1 for o in occurrences if o["verdict"] == "FAIL")
        total = len(occurrences)
        if total >= 2 and fail_count / total >= 0.6:
            failures.append({
                "criterion": criterion_key,
                "fail_rate": round(fail_count / total, 2),
                "occurrences": total,
                "sample_reasons": [o["reason"] for o in occurrences if o["verdict"] == "FAIL"][:3],
            })

    return sorted(failures, key=lambda x: x["fail_rate"], reverse=True)


def generate_hypotheses(category_patterns: dict, dimension_patterns: dict, failures: list) -> list[str]:
    """Generate root-cause hypotheses based on divergence patterns."""
    hypotheses = []

    weak_categories = [
        (cat, data) for cat, data in category_patterns.items()
        if data["avg_score"] < 0.5
    ]
    for cat, data in weak_categories:
        if cat in ("routing", "contract", "adversarial"):
            hypotheses.append(
                f"Category '{cat}' ({data['avg_score']:.0%}) likely bottlenecked by "
                f"single-turn mode suppressing multi-step workflows. "
                f"Multi-turn eval should improve this."
            )
        else:
            hypotheses.append(
                f"Category '{cat}' ({data['avg_score']:.0%}) has {data['tests']} tests, "
                f"only {data['passed']} passing. Review rule wording and calibration."
            )

    if "judgment" in dimension_patterns:
        j_score = dimension_patterns["judgment"]["avg_score"]
        if j_score < 0.5:
            hypotheses.append(
                f"Judgment dimension is weakest ({j_score:.0%}). "
                f"Model likely over-applies ceremony to simple tasks or under-applies to complex ones. "
                f"Check classify_complexity() thresholds in auto_capture.py."
            )

    if "autonomy" in dimension_patterns:
        a_score = dimension_patterns["autonomy"]["avg_score"]
        if a_score > 0.8:
            hypotheses.append(
                f"Autonomy dimension is strong ({a_score:.0%}). "
                f"No action needed — model acts decisively."
            )

    for failure in failures[:3]:
        hypotheses.append(
            f"Systematic failure: '{failure['criterion'][:60]}...' "
            f"fails {failure['fail_rate']:.0%} of the time across {failure['occurrences']} tests. "
            f"Reasons: {failure['sample_reasons'][0] if failure['sample_reasons'] else 'unknown'}"
        )

    return hypotheses


def generate_report(
    run_data: dict,
    category_patterns: dict,
    dimension_patterns: dict,
    failures: list[dict],
    hypotheses: list[str],
    verbose: bool = False,
) -> str:
    """Generate markdown divergence report."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    results = run_data.get("results", [])
    scored = [r for r in results if "error" not in r]

    lines = [
        f"# Divergence Report — {ts}",
        "",
        f"**Run**: {run_data.get('timestamp', 'unknown')}",
        f"**Model**: {run_data.get('capture_model', run_data.get('model', 'unknown'))}",
        f"**Tests**: {len(scored)} scored, {len(results) - len(scored)} errors",
        f"**Overall**: {run_data.get('overall_score', 0):.1%}",
        "",
        "## Category Patterns",
        "",
        "| Category | Avg Score | Pass Rate | Tests |",
        "|---|---|---|---|",
    ]

    for cat, data in category_patterns.items():
        lines.append(
            f"| {cat} | {data['avg_score']:.0%} | "
            f"{data['passed']}/{data['tests']} | {data['tests']} |"
        )

    if dimension_patterns:
        lines.extend([
            "",
            "## Dimension Patterns",
            "",
            "| Dimension | Avg Score | Tests |",
            "|---|---|---|",
        ])
        for dim, data in dimension_patterns.items():
            lines.append(f"| {dim} | {data['avg_score']:.0%} | {data['tests']} |")

    if failures:
        lines.extend([
            "",
            "## Systematic Failures",
            "",
        ])
        for f in failures[:10]:
            lines.append(
                f"- **{f['criterion'][:80]}** — fails {f['fail_rate']:.0%} "
                f"({f['occurrences']} occurrences)"
            )
            if f["sample_reasons"]:
                lines.append(f"  - Reason: {f['sample_reasons'][0][:120]}")

    if hypotheses:
        lines.extend([
            "",
            "## Root-Cause Hypotheses",
            "",
        ])
        for i, h in enumerate(hypotheses, 1):
            lines.append(f"{i}. {h}")

    if verbose:
        lines.extend([
            "",
            "## Per-Test Details (Failing)",
            "",
        ])
        failing = [r for r in scored if not r.get("passed")]
        for r in sorted(failing, key=lambda x: x.get("overall_score", 0)):
            lines.append(f"### {r['test_id']} ({r['overall_score']:.0%})")
            for dim_name, dim_data in r.get("dimensions", {}).items():
                if isinstance(dim_data, dict) and dim_data.get("criteria"):
                    for c in dim_data["criteria"]:
                        if isinstance(c, dict) and c.get("verdict") == "FAIL":
                            lines.append(f"  - FAIL [{dim_name}]: {c.get('reason', 'no reason')[:100]}")
            lines.append("")

    return "\n".join(lines)


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def main() -> int:
    parser = argparse.ArgumentParser(description="Divergence analysis for eval results")
    parser.add_argument("--run", help="Specific run file to analyze (in history/runs/)")
    parser.add_argument("--compare", help="Compare against this run (e.g., 'baseline')")
    parser.add_argument("--verbose", action="store_true", help="Include per-test failure details")
    parser.add_argument("--output", help="Write report to this file (default: stdout + history)")
    args = parser.parse_args()

    if args.run:
        run_path = HISTORY_DIR / args.run if not Path(args.run).exists() else Path(args.run)
    else:
        run_path = find_latest_run()

    if not run_path or not run_path.exists():
        print("No eval run found. Run 'make eval-full' or 'make eval-multi-save' first.", file=sys.stderr)
        return 1

    run_data = load_run(run_path)
    results = run_data.get("results", [])

    if not results:
        print(f"Run {run_path.name} has no results.", file=sys.stderr)
        return 1

    category_patterns = analyze_category_patterns(results)
    dimension_patterns = analyze_dimension_patterns(results)
    failures = find_systematic_failures(results)
    hypotheses = generate_hypotheses(category_patterns, dimension_patterns, failures)

    report = generate_report(
        run_data, category_patterns, dimension_patterns,
        failures, hypotheses, verbose=args.verbose,
    )

    print(report)

    DIVERGENCE_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    report_path = DIVERGENCE_DIR / f"{ts}_divergence.md"
    report_path.write_text(report)
    print(f"\nSaved to: {report_path}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
