#!/usr/bin/env python3
"""LLM-as-judge evaluator for Cursor rules and skills.

Reads test cases from dataset.yaml, matches them with captured agent responses
in responses/, and scores each response against behavioral criteria using an LLM judge.

Supports multi-model response directories:
    responses/composer-2.5/test_id.md   (model-specific, preferred)
    responses/test_id.md                (legacy flat layout, fallback)

Usage:
    python tests/eval/run_eval.py                           # evaluate all captured responses
    python tests/eval/run_eval.py --model composer-2.5      # evaluate a specific model's responses
    python tests/eval/run_eval.py --filter security         # only tests matching 'security'
    python tests/eval/run_eval.py --compare                 # compare scores across all models
    python tests/eval/run_eval.py --dry-run                 # show what would be evaluated

Environment variables:
    EVAL_PROVIDER   - 'openai' or 'anthropic' (default: openai)
    EVAL_MODEL      - model name (default: gpt-4o for openai, claude-sonnet-4-20250514 for anthropic)
    EVAL_API_KEY    - API key for the chosen provider (or OPENAI_API_KEY / ANTHROPIC_API_KEY)
"""

import argparse
import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml


EVAL_DIR = Path(__file__).parent
DATASET_PATH = EVAL_DIR / "dataset.yaml"
RESPONSES_DIR = EVAL_DIR / "responses"

JUDGE_SYSTEM_PROMPT = """\
You are an expert evaluator assessing whether an AI coding assistant followed \
specific behavioral guidelines. You will receive:

1. The PROMPT that was given to the assistant
2. The CONTEXT describing the test scenario
3. The assistant's RESPONSE
4. EXPECTED behaviors (the assistant SHOULD exhibit these)
5. ANTI-EXPECTED behaviors (the assistant should NOT exhibit these)

For each criterion, respond with PASS or FAIL and a brief reason (one sentence).

Respond in JSON format:
{
  "expected": [
    {"criterion": "...", "verdict": "PASS|FAIL", "reason": "..."}
  ],
  "anti_expected": [
    {"criterion": "...", "verdict": "PASS|FAIL", "reason": "..."}
  ]
}

For EXPECTED criteria: PASS means the assistant exhibited the behavior, FAIL means it didn't.
For ANTI-EXPECTED criteria: PASS means the assistant correctly AVOIDED the behavior, \
FAIL means it exhibited the unwanted behavior.

Be strict but fair. Only mark PASS when there is clear evidence in the response."""


@dataclass
class Criterion:
    text: str
    verdict: str = ""
    reason: str = ""

    @property
    def passed(self) -> bool:
        return self.verdict == "PASS"


@dataclass
class TestResult:
    test_id: str
    targets: list[str]
    category: str
    expected: list[Criterion] = field(default_factory=list)
    anti_expected: list[Criterion] = field(default_factory=list)
    error: str = ""

    @property
    def total_criteria(self) -> int:
        return len(self.expected) + len(self.anti_expected)

    @property
    def passed_criteria(self) -> int:
        return sum(1 for c in self.expected if c.passed) + sum(
            1 for c in self.anti_expected if c.passed
        )

    @property
    def passed(self) -> bool:
        return self.error == "" and self.passed_criteria == self.total_criteria

    @property
    def score(self) -> float:
        if self.total_criteria == 0:
            return 0.0
        return self.passed_criteria / self.total_criteria


def load_dataset() -> list[dict]:
    with open(DATASET_PATH) as f:
        return yaml.safe_load(f)


def discover_models() -> list[str]:
    """Find all model subdirectories under responses/."""
    if not RESPONSES_DIR.exists():
        return []
    return sorted(
        d.name for d in RESPONSES_DIR.iterdir()
        if d.is_dir() and any(d.glob("*.md"))
    )


def load_response(test_id: str, model: str | None = None) -> str | None:
    """Load a response, checking model subdir first, then legacy flat layout."""
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


def build_judge_prompt(test_case: dict, response: str) -> str:
    expected_list = "\n".join(f"- {e}" for e in test_case.get("expected", []))
    anti_list = "\n".join(f"- {a}" for a in test_case.get("anti_expected", []))

    return f"""\
## PROMPT
{test_case['prompt']}

## CONTEXT
{test_case.get('context', 'No additional context.')}

## RESPONSE
{response}

## EXPECTED BEHAVIORS (assistant SHOULD do these)
{expected_list}

## ANTI-EXPECTED BEHAVIORS (assistant should NOT do these)
{anti_list}

Evaluate each criterion and respond in JSON."""


def call_openai(system: str, user: str, model: str, api_key: str) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        response_format={"type": "json_object"},
        temperature=0.0,
    )
    return resp.choices[0].message.content or ""


def call_anthropic(system: str, user: str, model: str, api_key: str) -> str:
    from anthropic import Anthropic

    client = Anthropic(api_key=api_key)
    resp = client.messages.create(
        model=model,
        max_tokens=2048,
        system=system,
        messages=[{"role": "user", "content": user}],
        temperature=0.0,
    )
    return resp.content[0].text


def call_judge(system: str, user: str) -> dict:
    provider = os.environ.get("EVAL_PROVIDER", "openai").lower()

    if provider == "openai":
        model = os.environ.get("EVAL_MODEL", "gpt-4o")
        api_key = os.environ.get("EVAL_API_KEY") or os.environ.get("OPENAI_API_KEY", "")
        raw = call_openai(system, user, model, api_key)
    elif provider == "anthropic":
        model = os.environ.get("EVAL_MODEL", "claude-sonnet-4-20250514")
        api_key = os.environ.get("EVAL_API_KEY") or os.environ.get("ANTHROPIC_API_KEY", "")
        raw = call_anthropic(system, user, model, api_key)
    else:
        raise ValueError(f"Unknown provider: {provider}. Use 'openai' or 'anthropic'.")

    clean = raw.strip()
    if clean.startswith("```"):
        clean = clean.split("\n", 1)[1].rsplit("```", 1)[0]

    return json.loads(clean)


def evaluate_test(test_case: dict, model: str | None = None) -> TestResult:
    test_id = test_case["id"]
    result = TestResult(
        test_id=test_id,
        targets=test_case.get("targets", []),
        category=test_case.get("category", ""),
    )

    response = load_response(test_id, model)
    if response is None:
        result.error = "no_response"
        return result

    user_prompt = build_judge_prompt(test_case, response)

    try:
        verdict = call_judge(JUDGE_SYSTEM_PROMPT, user_prompt)
    except Exception as e:
        result.error = f"judge_error: {e}"
        return result

    for item in verdict.get("expected", []):
        result.expected.append(
            Criterion(
                text=item.get("criterion", ""),
                verdict=item.get("verdict", "FAIL"),
                reason=item.get("reason", ""),
            )
        )

    for item in verdict.get("anti_expected", []):
        result.anti_expected.append(
            Criterion(
                text=item.get("criterion", ""),
                verdict=item.get("verdict", "FAIL"),
                reason=item.get("reason", ""),
            )
        )

    return result


def print_report(results: list[TestResult]) -> None:
    evaluated = [r for r in results if r.error != "no_response"]
    skipped = [r for r in results if r.error == "no_response"]

    if not evaluated:
        print("No responses found. Run `python tests/eval/capture.py` to capture responses.")
        return

    print("\n" + "=" * 60)
    print("EVAL REPORT")
    print("=" * 60)

    for r in evaluated:
        status = "PASS" if r.passed else "FAIL"
        icon = "\u2705" if r.passed else "\u274c"
        print(f"\n{icon} {r.test_id} [{status}] ({r.passed_criteria}/{r.total_criteria})")
        print(f"   Targets: {', '.join(r.targets)} | Category: {r.category}")

        if r.error and r.error != "no_response":
            print(f"   Error: {r.error}")
            continue

        for c in r.expected:
            icon = "\u2705" if c.passed else "\u274c"
            print(f"   {icon} [expected] {c.text}")
            if not c.passed:
                print(f"      Reason: {c.reason}")

        for c in r.anti_expected:
            icon = "\u2705" if c.passed else "\u274c"
            print(f"   {icon} [anti-expected] {c.text}")
            if not c.passed:
                print(f"      Reason: {c.reason}")

    # Aggregate by target
    target_scores: dict[str, list[float]] = {}
    for r in evaluated:
        for t in r.targets:
            target_scores.setdefault(t, []).append(r.score)

    print("\n" + "-" * 60)
    print("SCORES BY RULE/SKILL")
    print("-" * 60)

    for target, scores in sorted(target_scores.items()):
        avg = sum(scores) / len(scores) * 100
        print(f"  {target:30s} {avg:5.1f}% ({len(scores)} tests)")

    # Overall
    all_scores = [r.score for r in evaluated]
    overall = sum(all_scores) / len(all_scores) * 100 if all_scores else 0

    print(f"\n{'─' * 60}")
    print(f"Overall: {overall:.1f}% | Evaluated: {len(evaluated)} | Skipped: {len(skipped)}")

    if skipped:
        print(f"Skipped (no response): {', '.join(r.test_id for r in skipped)}")


def run_eval_for_model(dataset: list[dict], model: str | None = None) -> list[TestResult]:
    results = []
    total = len(dataset)
    label = f" (model: {model})" if model else ""

    for i, test_case in enumerate(dataset, 1):
        response = load_response(test_case["id"], model)
        if response is None:
            results.append(
                TestResult(
                    test_id=test_case["id"],
                    targets=test_case.get("targets", []),
                    category=test_case.get("category", ""),
                    error="no_response",
                )
            )
            continue

        print(f"Evaluating [{i}/{total}]{label}: {test_case['id']}...", flush=True)
        results.append(evaluate_test(test_case, model))

    return results


def print_compare(dataset: list[dict], models: list[str]) -> None:
    print("\n" + "=" * 70)
    print("MODEL COMPARISON")
    print("=" * 70)

    header = f"  {'test_id':45s}"
    for m in models:
        header += f" {m:>10s}"
    print(header)
    print("  " + "-" * (45 + 11 * len(models)))

    for t in dataset:
        row = f"  {t['id']:45s}"
        for m in models:
            resp = load_response(t["id"], m)
            row += f" {'   yes':>10s}" if resp else f" {'    -':>10s}"
        print(row)

    print(f"\n  Responses per model:")
    for m in models:
        count = sum(1 for t in dataset if load_response(t["id"], m))
        print(f"    {m}: {count}/{len(dataset)}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate agent responses against rules/skills")
    parser.add_argument("--filter", help="Only run tests matching this string (id, target, or category)")
    parser.add_argument("--model", help="Evaluate responses from a specific model subdirectory")
    parser.add_argument("--compare", action="store_true", help="Compare response availability across models")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be evaluated")
    args = parser.parse_args()

    dataset = load_dataset()

    if args.filter:
        f = args.filter.lower()
        dataset = [
            t for t in dataset
            if f in t["id"].lower()
            or f in t.get("category", "").lower()
            or any(f in tgt.lower() for tgt in t.get("targets", []))
        ]

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
            print(f"  {t['id']:45s} [{status}]")
        return 0

    results = run_eval_for_model(dataset, args.model)
    print_report(results)

    evaluated = [r for r in results if r.error != "no_response"]
    if evaluated and all(r.passed for r in evaluated):
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
