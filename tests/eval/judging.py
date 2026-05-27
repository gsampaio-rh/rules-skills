"""Evaluation orchestration: run rubric judging over captured responses."""

from judge import JudgeResult, evaluate_multi_run, evaluate_single
from capture import load_response


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
            best = max(multi, key=lambda r: r.overall_score) if multi else multi[0]
            results.append(best)

        r = results[-1]
        if r.error:
            print(f"ERROR: {r.error}")
        else:
            status = "PASS" if r.passed else "FAIL"
            print(f"{status} ({r.overall_score:.0%}, conf={r.avg_confidence:.1f})")

    return results
