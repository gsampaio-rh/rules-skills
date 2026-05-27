"""Console reporting and run persistence for eval results."""

import json
from datetime import datetime, timezone
from pathlib import Path

from common import HISTORY_DIR
from judge import JudgeResult


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

    print(f"\n{'─' * 70}")
    print("BY TARGET (rules/skills)")
    print(f"{'─' * 70}")

    target_scores: dict[str, list[float]] = {}
    for r in evaluated:
        for t in r.targets:
            target_scores.setdefault(t, []).append(r.overall_score)

    for target, scores in sorted(target_scores.items(), key=lambda x: sum(x[1]) / len(x[1])):
        avg = sum(scores) / len(scores) * 100
        print(f"  {target:30s} {avg:5.1f}% ({len(scores)} tests)")

    if failed:
        print(f"\n{'─' * 70}")
        print("FAILURES")
        print(f"{'─' * 70}")
        _print_failures(failed)

    all_scores = [r.overall_score for r in evaluated if not r.error]
    overall = sum(all_scores) / len(all_scores) * 100 if all_scores else 0

    print(f"\n{'═' * 70}")
    print(f"  OVERALL: {overall:.1f}%")
    print(f"{'═' * 70}")


def _print_failures(failed: list[JudgeResult]) -> None:
    for r in failed:
        print(f"\n  ✗ {r.test_id} [{r.difficulty}] score={r.overall_score:.0%}")
        for dim_name, dim in r.dimensions.items():
            for c in dim.criteria:
                if not c.passed:
                    print(f"    [{dim_name}] FAIL: {c.criterion}")
                    print(f"             Reason: {c.reason}")


def save_run(results: list[JudgeResult], model: str | None = None) -> Path:
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
    model_label = model or "default"
    path = HISTORY_DIR / f"{ts}_{model_label}.json"

    scored = [r for r in results if not r.error]
    data = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model": model_label,
        "total_cases": len(results),
        "evaluated": len([r for r in results if r.error != "no_response"]),
        "overall_score": sum(r.overall_score for r in scored) / max(1, len(scored)),
        "results": [r.to_dict() for r in results],
    }

    path.write_text(json.dumps(data, indent=2))
    print(f"\nResults saved to: {path}")
    return path
