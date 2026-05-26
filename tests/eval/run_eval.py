#!/usr/bin/env python3
"""LLM-as-judge evaluator for Cursor rules and skills.

Reads test cases from dataset.yaml, matches them with captured agent responses,
and scores each response using rubric-based multi-dimensional evaluation.

Modes:
    eval-quick:  N=1 judge run per test (fast, cheap, less reliable)
    eval-full:   N=3 judge runs per test (slower, statistical confidence)

Usage:
    python tests/eval/run_eval.py                           # quick eval (N=1)
    python tests/eval/run_eval.py --full                    # full eval (N=3)
    python tests/eval/run_eval.py --model composer-2.5      # specific model
    python tests/eval/run_eval.py --filter security         # only matching tests
    python tests/eval/run_eval.py --category routing        # only a category
    python tests/eval/run_eval.py --difficulty hard         # only hard tests
    python tests/eval/run_eval.py --compare                 # compare models
    python tests/eval/run_eval.py --dry-run                 # show plan
    python tests/eval/run_eval.py --save                    # save results to history/

Environment variables:
    EVAL_PROVIDER   - 'openai' or 'anthropic' (default: openai)
    EVAL_MODEL      - model name (default: gpt-4o for openai, claude-sonnet-4-20250514 for anthropic)
    EVAL_API_KEY    - API key (or OPENAI_API_KEY / ANTHROPIC_API_KEY)
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

from judge import JudgeResult, evaluate_single, evaluate_multi_run

EVAL_DIR = Path(__file__).parent
DATASET_PATH = EVAL_DIR / "dataset.yaml"
RESPONSES_DIR = EVAL_DIR / "responses"
HISTORY_DIR = EVAL_DIR / "history" / "runs"


def load_dataset() -> list[dict]:
    with open(DATASET_PATH) as f:
        return yaml.safe_load(f)


def discover_models() -> list[str]:
    if not RESPONSES_DIR.exists():
        return []
    return sorted(
        d.name for d in RESPONSES_DIR.iterdir()
        if d.is_dir() and any(d.glob("*.md"))
    )


def load_response(test_id: str, model: str | None = None) -> str | None:
    if model:
        path = RESPONSES_DIR / model / f"{test_id}.md"
        if path.exists():
            text = path.read_text().strip()
            if text and not text.startswith("<!-- Response for:"):
                return text

    path = RESPONSES_DIR / f"{test_id}.md"
    if path.exists():
        text = path.read_text().strip()
        if text and not text.startswith("<!-- Response for:"):
            return text
    return None


def filter_dataset(
    dataset: list[dict],
    pattern: str | None = None,
    category: str | None = None,
    difficulty: str | None = None,
) -> list[dict]:
    result = dataset

    if pattern:
        f = pattern.lower()
        result = [
            t for t in result
            if f in t["id"].lower()
            or f in t.get("category", "").lower()
            or any(f in tgt.lower() for tgt in t.get("targets", []))
        ]

    if category:
        result = [t for t in result if t.get("category") == category]

    if difficulty:
        result = [t for t in result if t.get("difficulty") == difficulty]

    return result


def run_evaluation(
    dataset: list[dict],
    model: str | None = None,
    n_runs: int = 1,
) -> list[JudgeResult]:
    results = []
    total = len(dataset)
    label = f" (model: {model})" if model else ""

    for i, test_case in enumerate(dataset, 1):
        response = load_response(test_case["id"], model)
        if response is None:
            results.append(JudgeResult(
                test_id=test_case["id"],
                targets=test_case.get("targets", []),
                category=test_case.get("category", ""),
                difficulty=test_case.get("difficulty", "medium"),
                error="no_response",
            ))
            continue

        print(f"[{i}/{total}]{label} {test_case['id']}...", end=" ", flush=True)

        if n_runs == 1:
            result = evaluate_single(test_case, response)
            results.append(result)
        else:
            multi = evaluate_multi_run(test_case, response, n_runs)
            scores = [r.overall_score for r in multi if not r.error]
            avg_score = sum(scores) / len(scores) if scores else 0.0
            best = max(multi, key=lambda r: r.overall_score) if multi else multi[0]
            results.append(best)

        r = results[-1]
        if r.error:
            print(f"ERROR: {r.error}")
        else:
            status = "PASS" if r.passed else "FAIL"
            print(f"{status} ({r.overall_score:.0%}, conf={r.avg_confidence:.1f})")

    return results


def print_report(results: list[JudgeResult]) -> None:
    evaluated = [r for r in results if r.error != "no_response"]
    skipped = [r for r in results if r.error == "no_response"]

    if not evaluated:
        print("No responses found. Run `python tests/eval/auto_capture.py` first.")
        return

    print("\n" + "=" * 70)
    print("EVAL REPORT")
    print("=" * 70)

    passed = [r for r in evaluated if r.passed]
    failed = [r for r in evaluated if not r.passed and not r.error]
    errors = [r for r in evaluated if r.error and r.error != "no_response"]

    print(f"\n  Total: {len(evaluated)} evaluated, {len(skipped)} skipped")
    print(f"  Passed: {len(passed)} ({len(passed)/len(evaluated)*100:.0f}%)")
    print(f"  Failed: {len(failed)}")
    if errors:
        print(f"  Errors: {len(errors)}")

    # By category
    print(f"\n{'─' * 70}")
    print("BY CATEGORY")
    print(f"{'─' * 70}")

    categories: dict[str, list[JudgeResult]] = {}
    for r in evaluated:
        categories.setdefault(r.category, []).append(r)

    for cat, cat_results in sorted(categories.items()):
        cat_passed = sum(1 for r in cat_results if r.passed)
        avg_score = sum(r.overall_score for r in cat_results) / len(cat_results)
        print(f"  {cat:20s}  {cat_passed}/{len(cat_results)} pass  avg={avg_score:.0%}")

    # By difficulty
    print(f"\n{'─' * 70}")
    print("BY DIFFICULTY")
    print(f"{'─' * 70}")

    difficulties: dict[str, list[JudgeResult]] = {}
    for r in evaluated:
        difficulties.setdefault(r.difficulty, []).append(r)

    for diff in ["easy", "medium", "hard"]:
        if diff in difficulties:
            diff_results = difficulties[diff]
            diff_passed = sum(1 for r in diff_results if r.passed)
            avg_score = sum(r.overall_score for r in diff_results) / len(diff_results)
            print(f"  {diff:10s}  {diff_passed}/{len(diff_results)} pass  avg={avg_score:.0%}")

    # By target
    print(f"\n{'─' * 70}")
    print("BY TARGET (rules/skills)")
    print(f"{'─' * 70}")

    target_scores: dict[str, list[float]] = {}
    for r in evaluated:
        for t in r.targets:
            target_scores.setdefault(t, []).append(r.overall_score)

    for target, scores in sorted(target_scores.items(), key=lambda x: sum(x[1])/len(x[1])):
        avg = sum(scores) / len(scores) * 100
        print(f"  {target:30s} {avg:5.1f}% ({len(scores)} tests)")

    # Failures detail
    if failed:
        print(f"\n{'─' * 70}")
        print("FAILURES")
        print(f"{'─' * 70}")

        for r in failed:
            print(f"\n  ✗ {r.test_id} [{r.difficulty}] score={r.overall_score:.0%}")
            for dim_name, dim in r.dimensions.items():
                for c in dim.criteria:
                    if not c.passed:
                        print(f"    [{dim_name}] FAIL: {c.criterion}")
                        print(f"             Reason: {c.reason}")

    # Overall
    all_scores = [r.overall_score for r in evaluated if not r.error]
    overall = sum(all_scores) / len(all_scores) * 100 if all_scores else 0

    print(f"\n{'═' * 70}")
    print(f"  OVERALL: {overall:.1f}%")
    print(f"{'═' * 70}")


def save_run(results: list[JudgeResult], model: str | None = None) -> Path:
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
    model_label = model or "default"
    filename = f"{ts}_{model_label}.json"
    path = HISTORY_DIR / filename

    data = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model": model_label,
        "total_cases": len(results),
        "evaluated": len([r for r in results if r.error != "no_response"]),
        "overall_score": sum(r.overall_score for r in results if not r.error) / max(1, len([r for r in results if not r.error])),
        "results": [r.to_dict() for r in results],
    }

    path.write_text(json.dumps(data, indent=2))
    print(f"\nResults saved to: {path}")
    return path


def print_compare(dataset: list[dict], models: list[str]) -> None:
    print("\n" + "=" * 70)
    print("MODEL COMPARISON")
    print("=" * 70)

    for m in models:
        count = sum(1 for t in dataset if load_response(t["id"], m))
        print(f"  {m}: {count}/{len(dataset)} responses captured")


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate agent responses against rules/skills")
    parser.add_argument("--filter", help="Only tests matching this string (id, target, or category)")
    parser.add_argument("--category", help="Only tests in this category")
    parser.add_argument("--difficulty", help="Only tests at this difficulty (easy/medium/hard)")
    parser.add_argument("--model", help="Evaluate responses from a specific model subdirectory")
    parser.add_argument("--full", action="store_true", help="Full eval with N=3 runs per test")
    parser.add_argument("--runs", type=int, default=None, help="Custom number of judge runs (default: 1, --full: 3)")
    parser.add_argument("--compare", action="store_true", help="Compare response availability across models")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be evaluated")
    parser.add_argument("--save", action="store_true", help="Save results to history/runs/")
    args = parser.parse_args()

    dataset = load_dataset()
    dataset = filter_dataset(dataset, args.filter, args.category, args.difficulty)

    if args.compare:
        models = discover_models()
        if not models:
            print("No model subdirectories found in responses/.")
            return 1
        print_compare(dataset, models)
        return 0

    if args.dry_run:
        print(f"Would evaluate {len(dataset)} test cases:\n")
        for t in dataset:
            response = load_response(t["id"], args.model)
            status = "has response" if response else "needs capture"
            dims = list(t.get("rubric", {}).keys()) or ["behavioral", "negative"]
            print(f"  {t['id']:50s} [{t.get('difficulty','?'):6s}] {status} dims={dims}")
        return 0

    n_runs = args.runs or (3 if args.full else 1)
    print(f"Running evaluation (N={n_runs} runs per test)...\n")

    results = run_evaluation(dataset, args.model, n_runs)
    print_report(results)

    if args.save:
        save_run(results, args.model)

    evaluated = [r for r in results if r.error != "no_response"]
    if evaluated:
        overall = sum(r.overall_score for r in evaluated) / len(evaluated)
        return 0 if overall >= 0.8 else 1
    return 1


if __name__ == "__main__":
    sys.exit(main())
