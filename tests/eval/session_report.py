"""Aggregated reporting for session evaluation judgments.

Reads all judgment files, produces:
  1. A console table with per-scenario, per-dimension pass rates
  2. A summary.json with structured results for CI/tooling
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

EVAL_DIR = Path(__file__).parent
RESULTS_DIR = EVAL_DIR.parent / "results"
JUDGMENTS_DIR = RESULTS_DIR / "judgments"
SUMMARIES_DIR = RESULTS_DIR / "summaries"

DIMENSIONS = ["harness", "contract", "artifact", "behavioral", "negotiation"]


def load_judgments(filter_model: str = "") -> list[dict]:
    judgments = []
    if not JUDGMENTS_DIR.exists():
        return judgments

    for model_dir in sorted(JUDGMENTS_DIR.iterdir()):
        if not model_dir.is_dir():
            continue
        if filter_model and model_dir.name != filter_model:
            continue
        for jp in sorted(model_dir.glob("*.json")):
            try:
                judgments.append(json.loads(jp.read_text()))
            except (json.JSONDecodeError, OSError):
                continue
    return judgments


def classify_dimension(result: dict) -> str:
    """Map a judgment result to a reporting dimension."""
    criterion = result.get("criterion", "").lower()
    tier = result.get("tier", "")

    if tier == "llm" or "negotiation" in criterion:
        return "negotiation"
    if any(kw in criterion for kw in ("harness", "breadcrumb", "state.json", "evaluator")):
        return "harness"
    if any(kw in criterion for kw in ("contract", "acceptance criteria", "edge case", "verification method")):
        return "contract"
    if any(kw in criterion for kw in ("apolog", "autonomously", "breadcrumbs trace")):
        return "behavioral"
    return "artifact"


def compute_summary(judgments: list[dict]) -> dict:
    """Build a structured summary from all judgments."""
    scenarios: dict[str, dict] = {}

    for j in judgments:
        sid = j.get("scenario_id", "unknown")
        model = j.get("model", "unknown")
        key = f"{model}/{sid}"

        dims: dict[str, dict] = defaultdict(lambda: {"pass": 0, "fail": 0, "total": 0})

        for r in j.get("results", []):
            dim = classify_dimension(r)
            dims[dim]["total"] += 1
            if r.get("result") == "PASS":
                dims[dim]["pass"] += 1
            elif r.get("result") == "FAIL":
                dims[dim]["fail"] += 1

        dim_scores = {}
        for dim_name in DIMENSIONS:
            d = dims[dim_name]
            if d["total"] > 0:
                dim_scores[dim_name] = {
                    "pass": d["pass"],
                    "total": d["total"],
                    "rate": round(d["pass"] / d["total"], 2),
                }

        overall = j.get("summary", {})

        scenarios[key] = {
            "scenario_id": sid,
            "model": model,
            "timestamp": j.get("timestamp", ""),
            "dimensions": dim_scores,
            "overall_score": overall.get("score", 0),
            "total_checks": overall.get("total", 0),
            "pass_count": overall.get("pass", 0),
            "fail_count": overall.get("fail", 0),
        }

    total_pass = sum(s["pass_count"] for s in scenarios.values())
    total_checks = sum(s["total_checks"] for s in scenarios.values())

    from datetime import datetime, timezone

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "scenarios": scenarios,
        "aggregate": {
            "total_scenarios": len(scenarios),
            "total_checks": total_checks,
            "total_pass": total_pass,
            "overall_pass_rate": round(total_pass / max(total_checks, 1), 2),
        },
    }


def print_table(summary: dict):
    """Print a console table of results."""
    scenarios = summary["scenarios"]
    agg = summary["aggregate"]

    if not scenarios:
        print("No judgments found.")
        return

    header = f"{'Scenario':<30} {'Model':<20} " + " ".join(f"{d:<12}" for d in DIMENSIONS) + f" {'Overall':<10}"
    print("\n" + "=" * len(header))
    print("SESSION EVAL REPORT")
    print("=" * len(header))
    print(header)
    print("-" * len(header))

    for key, s in sorted(scenarios.items()):
        row = f"{s['scenario_id']:<30} {s['model']:<20} "
        for dim in DIMENSIONS:
            d = s["dimensions"].get(dim)
            if d:
                rate_str = f"{d['pass']}/{d['total']} ({d['rate']:.0%})"
            else:
                rate_str = "-"
            row += f"{rate_str:<12} "
        row += f"{s['overall_score']:.0%}"
        print(row)

    print("-" * len(header))
    print(f"{'AGGREGATE':<30} {'':<20} " + " " * (13 * len(DIMENSIONS)) + f"{agg['overall_pass_rate']:.0%}")
    print(f"\nTotal scenarios: {agg['total_scenarios']} | "
          f"Total checks: {agg['total_checks']} | "
          f"Pass: {agg['total_pass']} | "
          f"Pass rate: {agg['overall_pass_rate']:.0%}")
    print()


def save_summary(summary: dict) -> Path:
    from datetime import datetime, timezone

    SUMMARIES_DIR.mkdir(exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")
    path = SUMMARIES_DIR / f"summary-{ts}.json"
    path.write_text(json.dumps(summary, indent=2) + "\n")
    return path


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Aggregate session eval judgments into a report")
    parser.add_argument("--model", default="", help="Filter by model name")
    parser.add_argument("--json", action="store_true", help="Output JSON only")
    parser.add_argument("--save", action="store_true", help="Save summary.json")
    args = parser.parse_args()

    judgments = load_judgments(args.model)

    if not judgments:
        print("No judgment files found in tests/eval/judgments/")
        print("Run: make eval-session-judge")
        return 1

    summary = compute_summary(judgments)

    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print_table(summary)

    if args.save or not args.json:
        path = save_summary(summary)
        if not args.json:
            print(f"Summary saved to {path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
