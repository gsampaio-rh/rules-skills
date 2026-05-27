#!/usr/bin/env python3
"""Point a Cursor agent at failing eval traces to identify improvement opportunities.

The agent reads transcripts where the subject scored poorly, identifies
judgment divergence patterns, and suggests specific rule/prompt changes.

This implements the Anthropic pattern: "read traces, find where judgment
diverged from ours, then tune prompts."

Usage:
    python tests/eval/trace_review.py                           # review latest failing traces
    python tests/eval/trace_review.py --focus routing,contract  # focus on specific categories
    python tests/eval/trace_review.py --top 5                   # review top 5 worst scores
    python tests/eval/trace_review.py --model claude-opus-4-6   # use specific reviewer model

Environment:
    CURSOR_API_KEY - Required
"""

import argparse
import json
import os
import sys
from pathlib import Path

import yaml

EVAL_DIR = Path(__file__).parent
DATASET_PATH = EVAL_DIR / "dataset.yaml"
REPO_ROOT = EVAL_DIR.parent.parent
TRANSCRIPTS_DIR = EVAL_DIR / "transcripts"
RESPONSES_DIR = EVAL_DIR / "responses"
HISTORY_DIR = EVAL_DIR / "history" / "runs"
RULES_DIR = REPO_ROOT / "library" / "cursor" / "rules"


def load_dataset() -> dict[str, dict]:
    with open(DATASET_PATH) as f:
        tests = yaml.safe_load(f)
    return {t["id"]: t for t in tests}


def find_latest_run() -> Path | None:
    if not HISTORY_DIR.exists():
        return None
    runs = sorted(HISTORY_DIR.glob("*.json"), reverse=True)
    return runs[0] if runs else None


def load_failing_results(run_path: Path, focus: list[str] | None, top_n: int) -> list[dict]:
    """Load the worst-scoring results from a run."""
    run_data = json.loads(run_path.read_text())
    results = run_data.get("results", [])

    scored = [r for r in results if "error" not in r and not r.get("passed")]

    if focus:
        scored = [r for r in scored if r.get("category", "") in focus]

    scored.sort(key=lambda x: x.get("overall_score", 0))
    return scored[:top_n]


def load_trace_for_test(test_id: str, model: str) -> str | None:
    """Load transcript or response for a test case."""
    transcript_path = TRANSCRIPTS_DIR / model / f"{test_id}.json"
    if transcript_path.exists():
        transcript = json.loads(transcript_path.read_text())
        return format_transcript_text(transcript)

    response_path = RESPONSES_DIR / model / f"{test_id}.md"
    if response_path.exists():
        return response_path.read_text()

    return None


def format_transcript_text(transcript: list[dict]) -> str:
    parts = []
    for i, turn in enumerate(transcript, 1):
        parts.append(f"--- Turn {i} ({turn['role']}) ---")
        parts.append(f"Input: {turn['content']}")
        if turn.get("response"):
            parts.append(f"Response: {turn['response'][:3000]}")
        parts.append("")
    return "\n".join(parts)


def load_relevant_rules(targets: list[str]) -> str:
    """Load the rule files relevant to failing tests."""
    rules_text = []
    loaded = set()

    for target in targets:
        rule_path = RULES_DIR / f"{target}.mdc"
        if rule_path.exists() and target not in loaded:
            content = rule_path.read_text()
            if len(content) > 2000:
                content = content[:2000] + "\n[... truncated ...]"
            rules_text.append(f"### {target}.mdc\n{content}")
            loaded.add(target)

    return "\n\n".join(rules_text) if rules_text else "No matching rule files found."


REVIEW_PROMPT = """\
You are analyzing agent behavior traces where the agent scored poorly on behavioral evals.

Your job is to identify SPECIFIC divergence patterns and suggest CONCRETE fixes.

For each failing trace, identify:
1. WHERE exactly the agent's behavior diverged from expected (cite the specific turn/response)
2. WHAT the agent should have done instead
3. WHICH rule or prompt could be tuned to prevent this — cite the specific rule file and section

## Failing Traces

{traces}

## Rules Currently In Effect

{rules}

## Eval Results (scores and failing criteria)

{results}

## Instructions

Produce a structured analysis:

1. **Pattern Summary**: What common themes do you see across the failures?
2. **Per-Test Analysis**: For each test, what specific divergence occurred?
3. **Suggested Fixes**: Concrete changes to rules/prompts (quote the current wording, propose new wording)
4. **Priority Ranking**: Which fix would improve the most tests?

Be specific. Don't say "the rule should be clearer" — say exactly how to reword it.
"""


def run_trace_review(
    failing: list[dict],
    dataset: dict[str, dict],
    model: str,
    capture_model: str,
    api_key: str,
) -> str:
    """Send failing traces to a reviewer agent for analysis."""
    from cursor_sdk import Agent, AgentOptions

    traces_text = []
    all_targets = set()
    results_text = []

    for result in failing:
        test_id = result["test_id"]
        test_case = dataset.get(test_id, {})
        trace = load_trace_for_test(test_id, capture_model)

        if trace:
            traces_text.append(f"### {test_id} (score: {result.get('overall_score', 0):.0%})\n{trace[:2000]}")

        for target in test_case.get("targets", []):
            all_targets.add(target)

        results_text.append(
            f"- {test_id}: {result.get('overall_score', 0):.0%} "
            f"[{result.get('category', '')}]"
        )
        for dim_name, dim_data in result.get("dimensions", {}).items():
            if isinstance(dim_data, dict):
                for c in dim_data.get("criteria", []):
                    if isinstance(c, dict) and c.get("verdict") == "FAIL":
                        results_text.append(f"  FAIL [{dim_name}]: {c.get('reason', '')[:100]}")

    rules = load_relevant_rules(list(all_targets))

    prompt = REVIEW_PROMPT.format(
        traces="\n\n".join(traces_text) if traces_text else "No traces available.",
        rules=rules,
        results="\n".join(results_text),
    )

    print(f"  Sending {len(traces_text)} traces to reviewer ({model})...", flush=True)

    result = Agent.prompt(
        prompt,
        AgentOptions(api_key=api_key, model=model),
    )

    if result.status == "error":
        return f"Reviewer agent failed: {result.status}"

    return result.result or "No response from reviewer."


def main() -> int:
    parser = argparse.ArgumentParser(description="AI-powered trace review for eval failures")
    parser.add_argument("--focus", help="Comma-separated categories to focus on")
    parser.add_argument("--top", type=int, default=10, help="Number of worst tests to review")
    parser.add_argument("--model", default=os.environ.get("JUDGE_MODEL", "claude-opus-4-6"))
    parser.add_argument("--capture-model", default=os.environ.get("CAPTURE_MODEL", "composer-2.5"))
    parser.add_argument("--run", help="Specific run file to analyze")
    args = parser.parse_args()

    api_key = os.environ.get("CURSOR_API_KEY", "")
    if not api_key:
        print("Error: CURSOR_API_KEY required.", file=sys.stderr)
        return 1

    if args.run:
        run_path = HISTORY_DIR / args.run if not Path(args.run).exists() else Path(args.run)
    else:
        run_path = find_latest_run()

    if not run_path or not run_path.exists():
        print("No eval run found. Run eval first.", file=sys.stderr)
        return 1

    focus = args.focus.split(",") if args.focus else None
    failing = load_failing_results(run_path, focus, args.top)

    if not failing:
        print("No failing tests found — nothing to review.")
        return 0

    dataset = load_dataset()
    print(f"Reviewing {len(failing)} failing tests from {run_path.name}")
    if focus:
        print(f"Focus: {', '.join(focus)}")

    review = run_trace_review(failing, dataset, args.model, args.capture_model, api_key)

    print("\n" + "─" * 60)
    print("TRACE REVIEW RESULTS")
    print("─" * 60)
    print(review)

    output_dir = EVAL_DIR / "history" / "reviews"
    output_dir.mkdir(parents=True, exist_ok=True)
    from datetime import datetime, timezone
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"{ts}_review.md"
    output_path.write_text(review)
    print(f"\nSaved to: {output_path}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
