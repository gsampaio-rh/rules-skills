#!/usr/bin/env python3
"""Local evaluator using hybrid structural + LLM judge.

Uses hybrid_judge.py for criterion evaluation:
- Tier 1: Structural pattern matching (free, deterministic)
- Tier 2: LLM-as-judge fallback (when API key available)
- Tier 3: Low-confidence scoring for inconclusive checks

Usage:
    python tests/eval/local_judge.py --model composer-2.5 --save
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

from hybrid_judge import evaluate_criterion_hybrid, llm_available

EVAL_DIR = Path(__file__).parent
DATASET_PATH = EVAL_DIR / "dataset.yaml"
RESPONSES_DIR = EVAL_DIR / "responses"
HISTORY_DIR = EVAL_DIR / "history" / "runs"


def load_dataset() -> list[dict]:
    with open(DATASET_PATH) as f:
        return yaml.safe_load(f)


def load_response(test_id: str, model: str) -> str | None:
    path = RESPONSES_DIR / model / f"{test_id}.md"
    if path.exists():
        text = path.read_text().strip()
        if text and not text.startswith("<!-- Response for:"):
            return text
    return None


def evaluate_test(test_case: dict, response: str) -> dict:
    """Evaluate a test case response against its rubric using hybrid judge."""
    rubric = test_case.get("rubric", {})
    if not rubric:
        expected = test_case.get("expected", [])
        anti_expected = test_case.get("anti_expected", [])
        if expected:
            rubric["behavioral"] = [{"criterion": e, "weight": 2} for e in expected]
        if anti_expected:
            rubric["negative"] = [{"criterion": a, "weight": 2} for a in anti_expected]

    dimensions = {}
    total_weighted = 0
    passed_weighted = 0

    for dim_name, criteria in rubric.items():
        dim_results = []
        for spec in criteria:
            criterion = spec["criterion"]
            weight = spec.get("weight", 2)

            result = evaluate_criterion_hybrid(
                criterion=criterion,
                dimension=dim_name,
                weight=weight,
                response=response,
                test_case=test_case,
            )

            total_weighted += weight
            if result["verdict"] == "PASS":
                passed_weighted += weight

            dim_results.append(result)

        dim_score = sum(c["weight"] for c in dim_results if c["verdict"] == "PASS") / max(1, sum(c["weight"] for c in dim_results))
        dimensions[dim_name] = {"score": round(dim_score, 3), "criteria": dim_results}

    overall_score = passed_weighted / max(1, total_weighted)

    return {
        "test_id": test_case["id"],
        "targets": test_case.get("targets", []),
        "category": test_case.get("category", ""),
        "difficulty": test_case.get("difficulty", "medium"),
        "overall_score": round(overall_score, 3),
        "passed": overall_score >= 0.8,
        "avg_confidence": 3.5,
        "criteria_passed": f"{sum(1 for d in dimensions.values() for c in d['criteria'] if c['verdict'] == 'PASS')}/{sum(1 for d in dimensions.values() for _ in d['criteria'])}",
        "run_index": 0,
        "error": "",
        "dimensions": dimensions,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Hybrid eval (structural + optional LLM)")
    parser.add_argument("--model", default="composer-2.5")
    parser.add_argument("--filter", help="Filter tests by keyword")
    parser.add_argument("--category", help="Filter by category")
    parser.add_argument("--difficulty", help="Filter by difficulty")
    parser.add_argument("--save", action="store_true", help="Save results to history/")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show per-criterion results")
    args = parser.parse_args()

    dataset = load_dataset()
    if args.filter:
        f = args.filter.lower()
        dataset = [t for t in dataset if f in t["id"].lower() or f in t.get("category", "").lower()]
    if args.category:
        dataset = [t for t in dataset if t.get("category") == args.category]
    if args.difficulty:
        dataset = [t for t in dataset if t.get("difficulty") == args.difficulty]

    judge_mode = "hybrid (structural + LLM)" if llm_available() else "structural only"
    print(f"Judge mode: {judge_mode}\n")

    results = []
    tier_counts = {"structural": 0, "llm": 0, "inconclusive": 0}

    for i, test_case in enumerate(dataset, 1):
        response = load_response(test_case["id"], args.model)
        if response is None:
            results.append({
                "test_id": test_case["id"],
                "targets": test_case.get("targets", []),
                "category": test_case.get("category", ""),
                "difficulty": test_case.get("difficulty", "medium"),
                "overall_score": 0,
                "passed": False,
                "error": "no_response",
                "dimensions": {},
            })
            continue

        result = evaluate_test(test_case, response)
        results.append(result)

        for dim in result["dimensions"].values():
            for c in dim["criteria"]:
                tier = c.get("tier", "structural")
                tier_counts[tier] = tier_counts.get(tier, 0) + 1

        status = "PASS" if result["passed"] else "FAIL"
        print(f"[{i}/{len(dataset)}] {test_case['id']:50s} {status} ({result['overall_score']:.0%})")

        if args.verbose and not result["passed"]:
            for dim_name, dim in result["dimensions"].items():
                for c in dim["criteria"]:
                    if c["verdict"] == "FAIL":
                        tier_tag = f"[{c.get('tier', '?')}]"
                        print(f"           [{dim_name}] FAIL {tier_tag}: {c['criterion'][:55]}")
                        print(f"                    → {c['reason']}")

    # Summary
    evaluated = [r for r in results if r.get("error") != "no_response"]
    if not evaluated:
        print("No responses found.")
        return 1

    passed = sum(1 for r in evaluated if r["passed"])
    overall = sum(r["overall_score"] for r in evaluated) / len(evaluated)

    print(f"\n{'═' * 70}")
    print(f"  RESULTS: {passed}/{len(evaluated)} passed ({passed/len(evaluated)*100:.0f}%)")
    print(f"  OVERALL SCORE: {overall:.1%}")
    print(f"  JUDGE TIERS: structural={tier_counts['structural']}, llm={tier_counts['llm']}, inconclusive={tier_counts['inconclusive']}")
    print(f"{'═' * 70}")

    # By category
    from collections import defaultdict
    cats = defaultdict(list)
    for r in evaluated:
        cats[r["category"]].append(r)
    print(f"\n  {'Category':20s} {'Pass':>8s} {'Score':>7s}")
    for cat, cat_results in sorted(cats.items(), key=lambda x: sum(r["overall_score"] for r in x[1])/len(x[1])):
        cat_p = sum(1 for r in cat_results if r["passed"])
        cat_s = sum(r["overall_score"] for r in cat_results) / len(cat_results)
        print(f"  {cat:20s} {cat_p:>2d}/{len(cat_results):<3d}    {cat_s:.0%}")

    # By difficulty
    diffs = defaultdict(list)
    for r in evaluated:
        diffs[r["difficulty"]].append(r)
    print(f"\n  {'Difficulty':10s} {'Pass':>8s} {'Score':>7s}")
    for d in ["easy", "medium", "hard"]:
        if d in diffs:
            d_p = sum(1 for r in diffs[d] if r["passed"])
            d_s = sum(r["overall_score"] for r in diffs[d]) / len(diffs[d])
            print(f"  {d:10s} {d_p:>2d}/{len(diffs[d]):<3d}    {d_s:.0%}")

    if args.save:
        HISTORY_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
        path = HISTORY_DIR / f"{ts}_{args.model}_hybrid.json"
        data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "model": args.model,
            "judge": "hybrid",
            "judge_mode": judge_mode,
            "tier_counts": tier_counts,
            "total_cases": len(results),
            "evaluated": len(evaluated),
            "overall_score": overall,
            "results": results,
        }
        path.write_text(json.dumps(data, indent=2))
        print(f"\n  Saved to: {path}")

    return 0 if overall >= 0.8 else 1


if __name__ == "__main__":
    sys.exit(main())
