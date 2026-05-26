#!/usr/bin/env python3
"""Local heuristic-based evaluator.

Evaluates captured responses against rubric criteria using keyword/pattern
matching. Fast, free, no API calls. Useful as a quick baseline and for
validating the pipeline before running expensive LLM-as-judge.

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


# ─── Criterion Evaluators ──────────────────────────────────────────────

def check_negative_criterion(criterion: str, response: str) -> tuple[bool, str]:
    """Check negative criteria (things that should NOT appear)."""
    resp_lower = response.lower()

    patterns = {
        "apolog": ["i'm sorry", "i apologize", "my apologies", "sorry about"],
        "summar": ["here's a summary", "to summarize", "in summary, i"],
        "shall i proceed": ["shall i proceed", "should i proceed", "would you like me to"],
        "coaching tip": ["> **tip:**", "> **tip:"],
        "launch.*planner": ["launching planner", "launch planner", "/planner"],
        "spec.md": ["spec.md", "state.json", "contract.json"],
        "audit": ["architecture-audit", "code-quality-audit", "design-audit", "organization-audit"],
        "vague.*criteria": ["works correctly", "good performance", "handles errors properly"],
        "commit.*without": ["git commit", "committed"],
        "push.*main": ["git push", "push to main", "pushed"],
        "hardcoded": ["import stripe", "from stripe"],
    }

    criterion_lower = criterion.lower()

    # "Does NOT apologize"
    if "apolog" in criterion_lower or "sorry" in criterion_lower:
        for p in patterns["apolog"]:
            if p in resp_lower:
                return False, f"Found '{p}' in response"
        return True, "No apologies found"

    # "Does NOT summarize"
    if "summar" in criterion_lower and "not" in criterion_lower.split("summar")[0]:
        for p in patterns["summar"]:
            if p in resp_lower:
                return False, f"Found summary pattern"
        return True, "No unsolicited summary"

    # "Does NOT ask shall I proceed"
    if "shall i" in criterion_lower or "should i" in criterion_lower or "ask" in criterion_lower:
        if any(p in resp_lower for p in patterns["shall i proceed"]):
            return False, "Found permission-seeking language"
        return True, "No permission-seeking language"

    # "Does NOT include coaching tip"
    if "coaching tip" in criterion_lower or "tip:" in criterion_lower:
        if any(p in resp_lower for p in patterns["coaching tip"]):
            return False, "Found coaching tip"
        return True, "No coaching tip found"

    # "Does NOT launch planner"
    if "planner" in criterion_lower and ("not" in criterion_lower or "does not" in criterion_lower):
        if any(p in resp_lower for p in patterns["launch.*planner"]):
            return False, "Found planner launch"
        return True, "No planner launch"

    # "Does NOT create spec/state/contract"
    if "spec.md" in criterion_lower or "state.json" in criterion_lower or "contract" in criterion_lower:
        if "not" in criterion_lower or "does not" in criterion_lower:
            found = [p for p in patterns["spec.md"] if p in resp_lower]
            if found:
                return False, f"Found harness artifacts: {found}"
            return True, "No harness artifacts"

    # "Does NOT auto-commit"
    if "commit" in criterion_lower and ("not" in criterion_lower or "never" in criterion_lower):
        if "git commit" in resp_lower and "confirm" not in resp_lower and "approval" not in resp_lower:
            return False, "Auto-committed without asking"
        return True, "Did not auto-commit"

    # Generic negative: if criterion says "Does NOT" check for key phrases
    if criterion_lower.startswith("does not") or "does not" in criterion_lower:
        return True, "Assumed PASS (no specific pattern to check)"

    return True, "Default PASS for negative criterion"


def check_positive_criterion(criterion: str, response: str) -> tuple[bool, str]:
    """Check positive criteria (things that SHOULD appear)."""
    resp_lower = response.lower()

    criterion_lower = criterion.lower()

    # Routing: launches planner
    if "launch" in criterion_lower and "planner" in criterion_lower:
        if any(p in resp_lower for p in ["planner", "/planner", "planning", "plan first", "spec.md"]):
            return True, "Found planner reference"
        return False, "No planner launch detected"

    # Routing: recognizes non-trivial
    if "non-trivial" in criterion_lower or "non trivial" in criterion_lower:
        if any(p in resp_lower for p in ["complex", "non-trivial", "multiple", "architectural", "plan", "several files"]):
            return True, "Recognized complexity"
        return False, "Did not acknowledge complexity"

    # Asks clarifying questions
    if "ask" in criterion_lower and ("clarif" in criterion_lower or "question" in criterion_lower):
        if "?" in response:
            return True, "Found questions in response"
        return False, "No questions found"

    # Creates TodoWrite/task plan
    if "todowrite" in criterion_lower or "task list" in criterion_lower or "task plan" in criterion_lower:
        if any(p in resp_lower for p in ["todowrite", "todo", "task list", "1.", "step 1"]):
            return True, "Found task planning"
        return False, "No task planning"

    # Breadcrumbs
    if "breadcrumb" in criterion_lower:
        if "breadcrumb" in resp_lower or "breadcrumbs.jsonl" in resp_lower:
            return True, "Found breadcrumbs reference"
        return False, "No breadcrumbs reference"

    # Type hints
    if "type hint" in criterion_lower:
        if any(p in response for p in ["-> ", ": str", ": int", ": float", ": list", ": dict", "-> None"]):
            return True, "Found type hints"
        return False, "No type hints found"

    # Pushes back / suggests alternative
    if "push" in criterion_lower and "back" in criterion_lower:
        if any(p in resp_lower for p in ["however", "instead", "suggest", "recommend", "better approach", "alternatively"]):
            return True, "Found pushback language"
        return False, "No pushback detected"

    # Warns about destructive
    if "warn" in criterion_lower and ("destruct" in criterion_lower or "irrevers" in criterion_lower):
        if any(p in resp_lower for p in ["warning", "destructive", "irreversible", "cannot be undone", "careful", "confirm"]):
            return True, "Found warning language"
        return False, "No warning about destructive action"

    # Asks before commit
    if "ask" in criterion_lower and "commit" in criterion_lower:
        if any(p in resp_lower for p in ["confirm", "shall i commit", "ready to commit", "approve", "want me to commit"]):
            return True, "Found commit confirmation request"
        return False, "No commit confirmation"

    # Identifies security issue (SQL injection, hardcoded secret)
    if "sql injection" in criterion_lower or "injection" in criterion_lower:
        if any(p in resp_lower for p in ["sql injection", "inject", "parameterized", "prepared statement"]):
            return True, "Found SQL injection identification"
        return False, "No SQL injection mention"

    if "hardcoded" in criterion_lower and ("key" in criterion_lower or "secret" in criterion_lower):
        if any(p in resp_lower for p in ["hardcoded", "hard-coded", "secret", "environment variable", "env var"]):
            return True, "Found hardcoded secret identification"
        return False, "No hardcoded secret flag"

    # Verification: runs tests/lint
    if "verif" in criterion_lower and ("run" in criterion_lower or "test" in criterion_lower or "lint" in criterion_lower):
        if any(p in resp_lower for p in ["pytest", "npm test", "lint", "ruff", "mypy", "build", "import"]):
            return True, "Found verification step"
        return False, "No verification detected"

    # Splits into functions
    if "split" in criterion_lower and "function" in criterion_lower:
        func_count = len(re.findall(r"def \w+", response))
        if func_count >= 3:
            return True, f"Found {func_count} function definitions"
        return False, f"Only {func_count} functions (expected 3+)"

    # Contract fields
    if "contract" in criterion_lower and "include" in criterion_lower:
        if any(p in resp_lower for p in ["acceptance_criteria", "edge_cases", "verification_method", "feature_id"]):
            return True, "Found contract fields"
        return False, "No contract fields"

    # Rubrics in contract
    if "rubric" in criterion_lower and ("include" in criterion_lower or "list" in criterion_lower):
        if "rubric" in resp_lower:
            return True, "Found rubrics reference"
        return False, "No rubrics reference"

    # Experiment design first
    if "experiment" in criterion_lower and "design" in criterion_lower:
        if any(p in resp_lower for p in ["hypothesis", "design", "methodology", "experiment.md", "conditions"]):
            return True, "Found experiment design"
        return False, "No experiment design"

    # Suggests fresh thread
    if "fresh" in criterion_lower and ("chat" in criterion_lower or "thread" in criterion_lower):
        if any(p in resp_lower for p in ["fresh", "new chat", "new thread", "new conversation", "start a new"]):
            return True, "Found fresh thread suggestion"
        return False, "No fresh thread suggestion"

    # Accessibility mentions
    if "accessib" in criterion_lower or "aria" in criterion_lower or "wcag" in criterion_lower:
        if any(p in resp_lower for p in ["aria", "accessibility", "wcag", "screen reader", "keyboard"]):
            return True, "Found accessibility reference"
        return False, "No accessibility mention"

    # Design tokens
    if "design token" in criterion_lower:
        if any(p in resp_lower for p in ["token", "css variable", "var(--", "design system"]):
            return True, "Found design token reference"
        return False, "No design tokens"

    # Baseline/controls mention
    if "baseline" in criterion_lower or "control" in criterion_lower:
        if any(p in resp_lower for p in ["baseline", "control", "comparison", "benchmark"]):
            return True, "Found baseline/control reference"
        return False, "No baseline/control mention"

    # DDD patterns
    if "ddd" in criterion_lower or "dependency direction" in criterion_lower or "aggregate" in criterion_lower:
        if any(p in resp_lower for p in ["domain", "infrastructure", "dependency", "aggregate", "port", "adapter", "interface"]):
            return True, "Found DDD/architecture pattern"
        return False, "No DDD patterns"

    # Generic: if contains key words from criterion
    key_words = [w for w in criterion_lower.split() if len(w) > 4 and w not in ("should", "their", "which", "where", "there", "about", "before", "after")]
    matches = sum(1 for w in key_words if w in resp_lower)
    if matches >= len(key_words) * 0.4:
        return True, f"Found {matches}/{len(key_words)} key terms"
    return False, f"Only {matches}/{len(key_words)} key terms found"


def evaluate_criterion(criterion: str, dimension: str, response: str) -> tuple[bool, int, str]:
    """Evaluate a single criterion. Returns (passed, confidence, reason)."""
    if dimension == "negative":
        passed, reason = check_negative_criterion(criterion, response)
        confidence = 4 if "specific pattern" not in reason.lower() else 3
    else:
        passed, reason = check_positive_criterion(criterion, response)
        confidence = 4 if passed else 3

    return passed, confidence, reason


def evaluate_test(test_case: dict, response: str) -> dict:
    """Evaluate a test case response against its rubric."""
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
            passed, confidence, reason = evaluate_criterion(criterion, dim_name, response)

            total_weighted += weight
            if passed:
                passed_weighted += weight

            dim_results.append({
                "criterion": criterion,
                "weight": weight,
                "verdict": "PASS" if passed else "FAIL",
                "confidence": confidence,
                "reason": reason,
            })

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
    parser = argparse.ArgumentParser(description="Local heuristic eval (no API calls)")
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

    results = []
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

        status = "PASS" if result["passed"] else "FAIL"
        print(f"[{i}/{len(dataset)}] {test_case['id']:50s} {status} ({result['overall_score']:.0%})")

        if args.verbose and not result["passed"]:
            for dim_name, dim in result["dimensions"].items():
                for c in dim["criteria"]:
                    if c["verdict"] == "FAIL":
                        print(f"           [{dim_name}] FAIL: {c['criterion'][:60]}")
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
        path = HISTORY_DIR / f"{ts}_{args.model}_local.json"
        data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "model": args.model,
            "judge": "local_heuristic",
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
