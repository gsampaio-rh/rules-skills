#!/usr/bin/env python3
"""Multi-turn eval pipeline using Cursor SDK.

Captures multi-turn conversations via Agent.create() + agent.send(), then judges
the full transcript using a separate adversarial judge agent.

The subject agent runs with this repo's workspace (rules loaded via .cursor/rules/).
The judge agent runs without workspace (pure evaluation, no tools needed).

Usage:
    python tests/eval/multi_turn_eval.py                        # run all multi-turn tests
    python tests/eval/multi_turn_eval.py --filter contract      # only matching tests
    python tests/eval/multi_turn_eval.py --dry-run              # show what would run
    python tests/eval/multi_turn_eval.py --save                 # save results to history
    python tests/eval/multi_turn_eval.py --capture-only         # capture without judging
    python tests/eval/multi_turn_eval.py --judge-only           # judge existing transcripts

Environment:
    CURSOR_API_KEY    - Required for both capture and judge
    CAPTURE_MODEL     - Subject model (default: composer-2.5)
    JUDGE_MODEL       - Judge model (default: claude-opus-4-6)
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml

EVAL_DIR = Path(__file__).parent
DATASET_PATH = EVAL_DIR / "dataset.yaml"
REPO_ROOT = EVAL_DIR.parent.parent
CALIBRATION_DIR = EVAL_DIR / "calibration"
TRANSCRIPTS_DIR = EVAL_DIR / "transcripts"
HISTORY_DIR = EVAL_DIR / "history" / "runs"


# ─── Dataset ─────────────────────────────────────────────────────────────────


def load_dataset() -> list[dict]:
    with open(DATASET_PATH) as f:
        return yaml.safe_load(f)


def load_multi_turn_tests(dataset: list[dict]) -> list[dict]:
    return [t for t in dataset if t.get("scenario_type") == "multi_turn"]


def filter_tests(tests: list[dict], pattern: str) -> list[dict]:
    p = pattern.lower()
    return [
        t for t in tests
        if p in t["id"].lower()
        or p in t.get("category", "").lower()
        or any(p in tgt.lower() for tgt in t.get("targets", []))
    ]


# ─── Calibration ─────────────────────────────────────────────────────────────


def load_calibration_for_test(test_case: dict) -> str:
    """Load relevant calibration examples for the judge."""
    dimensions = test_case.get("rubric_dimensions", {})
    parts = []

    for dim_name in dimensions:
        cal_path = CALIBRATION_DIR / f"{dim_name}.md"
        if cal_path.exists():
            parts.append(cal_path.read_text().strip())

    if not parts:
        for cal_file in sorted(CALIBRATION_DIR.glob("*.md")):
            parts.append(cal_file.read_text().strip())

    return "\n\n---\n\n".join(parts)


# ─── Capture ─────────────────────────────────────────────────────────────────


INJECTION_TEMPLATES = {
    "harness_routing": (
        "HARNESS ROUTING: This prompt describes non-trivial work. Before implementing "
        "anything, you MUST launch the /planner subagent to decompose this into a spec "
        "and feature list. Do NOT start coding directly."
    ),
    "session_context": "Harness active. No features currently building.",
    "evaluator_blocked": (
        "EVALUATOR WRITE BLOCKED: You are in evaluator mode. "
        "Writes outside .harness/ are denied by the evaluator-guard hook."
    ),
    "commit_denied": (
        "COMMIT DENIED: The pre-commit-harness hook blocked this commit. "
        "You must get user approval first. Show what will be committed and wait."
    ),
}


def resolve_injection(inject_key: str) -> str:
    return INJECTION_TEMPLATES.get(inject_key, inject_key)


def capture_multi_turn(test_case: dict, model: str, api_key: str) -> list[dict]:
    """Capture a multi-turn conversation in an isolated worktree.

    The SDK agent gets a disposable copy of the workspace with .cursor/ rules
    loaded but its own .harness/ and file system. Nothing it creates or modifies
    touches the real repo.
    """
    from cursor_sdk import Agent, LocalAgentOptions

    from sandbox import CaptureWorkspace

    transcript = []

    with CaptureWorkspace() as ws:
        with Agent.create(
            model=model,
            api_key=api_key,
            local=LocalAgentOptions(cwd=str(ws.path)),
        ) as subject:
            for turn in test_case["turns"]:
                role = turn["role"]

                if role == "system":
                    content = resolve_injection(turn.get("inject", turn.get("content", "")))
                else:
                    content = turn["content"]

                run = subject.send(content)
                run.wait()
                response_text = run.text()

                transcript.append({
                    "role": role,
                    "content": content,
                    "response": response_text,
                })

    return transcript


def save_transcript(test_id: str, model: str, transcript: list[dict]) -> Path:
    out_dir = TRANSCRIPTS_DIR / model
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{test_id}.json"
    path.write_text(json.dumps(transcript, indent=2))
    return path


def load_transcript(test_id: str, model: str) -> list[dict] | None:
    path = TRANSCRIPTS_DIR / model / f"{test_id}.json"
    if path.exists():
        return json.loads(path.read_text())
    return None


# ─── Judge ────────────────────────────────────────────────────────────────────


ADVERSARIAL_JUDGE_SYSTEM = """\
You are a HARSH evaluator grading an AI coding assistant's behavior across a \
multi-turn conversation. You grade STRICTLY. You do NOT give benefit of the doubt.

A response must show CLEAR EVIDENCE of the expected behavior to PASS.
Your job is to find failures, not confirm success.

## Grading Rules

- PASS = clear, specific evidence the assistant exhibited the expected behavior
- FAIL = behavior was absent, opposite was observed, or only superficially present
- For "negative" criteria: PASS means correctly AVOIDED the bad behavior
- Confidence 5 = certain, 1 = ambiguous evidence
- Weight indicates importance: 3 = critical, 2 = important, 1 = nice-to-have
- Cite specific quotes or actions from the transcript as evidence
- Do NOT give PASS for vague or partial compliance

## Response Format

Respond in JSON:
{
  "dimensions": {
    "dimension_name": [
      {"criterion": "...", "verdict": "PASS|FAIL", "confidence": 5, "reason": "..."}
    ]
  }
}
"""


def build_judge_prompt(test_case: dict, transcript: list[dict]) -> str:
    """Build the full prompt for the adversarial judge."""
    transcript_text = format_transcript(transcript)

    rubric_text = ""
    for dim_name, criteria in test_case.get("rubric_dimensions", {}).items():
        rubric_text += f"\n### {dim_name.upper()}\n"
        for c in criteria:
            weight = c.get("weight", 2)
            rubric_text += f"- [weight={weight}] {c['criterion']}\n"

    negative = test_case.get("rubric", {}).get("negative", [])
    if negative:
        rubric_text += "\n### NEGATIVE\n"
        for c in negative:
            rubric_text += f"- [weight={c.get('weight', 2)}] {c['criterion']}\n"

    return f"""\
## TEST SCENARIO

{test_case.get('context', 'No additional context.')}

## CONVERSATION TRANSCRIPT

{transcript_text}

## RUBRIC

{rubric_text}

Evaluate each criterion strictly. Respond in JSON."""


def format_transcript(transcript: list[dict]) -> str:
    parts = []
    for i, turn in enumerate(transcript, 1):
        role = turn["role"].upper()
        parts.append(f"### Turn {i} — {role}")
        parts.append(f"**Message:** {turn['content']}")
        if turn.get("response"):
            response_preview = turn["response"][:2000]
            if len(turn["response"]) > 2000:
                response_preview += "\n[... truncated ...]"
            parts.append(f"**Assistant Response:**\n{response_preview}")
        parts.append("")
    return "\n".join(parts)


def judge_transcript(
    test_case: dict,
    transcript: list[dict],
    model: str,
    api_key: str,
    calibration: str,
) -> dict:
    """Judge a transcript using a separate adversarial agent session."""
    from cursor_sdk import Agent, AgentOptions

    system_with_calibration = ADVERSARIAL_JUDGE_SYSTEM
    if calibration:
        system_with_calibration += f"\n\n## Calibration Examples\n\n{calibration}"

    user_prompt = build_judge_prompt(test_case, transcript)
    full_prompt = f"{system_with_calibration}\n\n---\n\n{user_prompt}"

    result = Agent.prompt(
        full_prompt,
        AgentOptions(api_key=api_key, model=model),
    )

    if result.status == "error":
        return {"error": f"Judge failed: {result.status}"}

    return parse_judge_response(result.result or "", test_case)


def parse_judge_response(raw: str, test_case: dict) -> dict:
    """Parse judge JSON response into scored verdict."""
    clean = raw.strip()
    if clean.startswith("```"):
        clean = clean.split("\n", 1)[1].rsplit("```", 1)[0]

    try:
        data = json.loads(clean)
    except json.JSONDecodeError:
        json_start = clean.find("{")
        json_end = clean.rfind("}") + 1
        if json_start >= 0 and json_end > json_start:
            data = json.loads(clean[json_start:json_end])
        else:
            return {"error": f"Could not parse judge JSON: {clean[:200]}"}

    dimensions_data = data.get("dimensions", data)
    rubric = test_case.get("rubric_dimensions", {})

    total_weight = 0
    passed_weight = 0
    dimension_scores = {}

    for dim_name, criteria_spec in rubric.items():
        dim_results = dimensions_data.get(dim_name, [])
        dim_total = 0
        dim_passed = 0

        for i, spec in enumerate(criteria_spec):
            weight = spec.get("weight", 2)
            dim_total += weight
            total_weight += weight

            result = dim_results[i] if i < len(dim_results) else {}
            if result.get("verdict", "").upper() == "PASS":
                dim_passed += weight
                passed_weight += weight

        dimension_scores[dim_name] = {
            "score": dim_passed / dim_total if dim_total > 0 else 0,
            "passed": dim_passed,
            "total": dim_total,
            "criteria": dim_results,
        }

    overall_score = passed_weight / total_weight if total_weight > 0 else 0

    return {
        "test_id": test_case["id"],
        "category": test_case.get("category", ""),
        "difficulty": test_case.get("difficulty", ""),
        "overall_score": round(overall_score, 3),
        "passed": overall_score >= 0.8,
        "dimensions": dimension_scores,
    }


# ─── Pipeline ─────────────────────────────────────────────────────────────────


def run_pipeline(
    tests: list[dict],
    capture_model: str,
    judge_model: str,
    api_key: str,
    *,
    capture_only: bool = False,
    judge_only: bool = False,
    dry_run: bool = False,
) -> list[dict]:
    """Run the full multi-turn eval pipeline."""
    results = []

    if dry_run:
        print(f"Would run {len(tests)} multi-turn tests:")
        print(f"  Capture model: {capture_model}")
        print(f"  Judge model:   {judge_model}")
        print()
        for t in tests:
            turns = len(t.get("turns", []))
            dims = list(t.get("rubric_dimensions", {}).keys())
            print(f"  {t['id']:50s} [{turns} turns, dims: {','.join(dims)}]")
        return []

    total = len(tests)

    for i, test_case in enumerate(tests, 1):
        test_id = test_case["id"]
        print(f"[{i}/{total}] {test_id}", flush=True)

        transcript = None

        if not judge_only:
            print(f"  Capturing ({len(test_case['turns'])} turns)...", end=" ", flush=True)
            start = time.time()
            try:
                transcript = capture_multi_turn(test_case, capture_model, api_key)
                save_transcript(test_id, capture_model, transcript)
                elapsed = time.time() - start
                print(f"ok ({elapsed:.1f}s)")
            except Exception as e:
                elapsed = time.time() - start
                print(f"FAILED ({elapsed:.1f}s): {e}")
                results.append({"test_id": test_id, "error": str(e)})
                continue

        if capture_only:
            continue

        if transcript is None:
            transcript = load_transcript(test_id, capture_model)
            if transcript is None:
                print(f"  No transcript found — skipping judge")
                results.append({"test_id": test_id, "error": "no_transcript"})
                continue

        print(f"  Judging...", end=" ", flush=True)
        start = time.time()
        try:
            calibration = load_calibration_for_test(test_case)
            verdict = judge_transcript(test_case, transcript, judge_model, api_key, calibration)
            elapsed = time.time() - start
            score = verdict.get("overall_score", 0)
            status = "PASS" if verdict.get("passed") else "FAIL"
            print(f"{status} ({score:.0%}, {elapsed:.1f}s)")
            results.append(verdict)
        except Exception as e:
            elapsed = time.time() - start
            print(f"ERROR ({elapsed:.1f}s): {e}")
            results.append({"test_id": test_id, "error": str(e)})

    return results


def save_results(results: list[dict], capture_model: str, judge_model: str) -> Path:
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"{ts}_{capture_model}_multi_turn.json"
    path = HISTORY_DIR / filename

    output = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "capture_model": capture_model,
        "judge_model": judge_model,
        "scenario_type": "multi_turn",
        "total_tests": len(results),
        "passed": sum(1 for r in results if r.get("passed")),
        "failed": sum(1 for r in results if not r.get("passed") and "error" not in r),
        "errors": sum(1 for r in results if "error" in r),
        "overall_score": _mean([r.get("overall_score", 0) for r in results if "error" not in r]),
        "results": results,
    }

    path.write_text(json.dumps(output, indent=2))
    return path


def print_summary(results: list[dict]) -> None:
    scored = [r for r in results if "error" not in r]
    errors = [r for r in results if "error" in r]

    if not scored:
        print("\nNo scored results.")
        return

    avg_score = _mean([r["overall_score"] for r in scored])
    passed = sum(1 for r in scored if r.get("passed"))

    print(f"\n{'─' * 60}")
    print(f"Multi-Turn Eval Summary")
    print(f"{'─' * 60}")
    print(f"  Tests scored:  {len(scored)}")
    print(f"  Passed (≥80%): {passed}/{len(scored)} ({passed/len(scored)*100:.0f}%)")
    print(f"  Average score: {avg_score:.1%}")
    if errors:
        print(f"  Errors:        {len(errors)}")

    by_category: dict[str, list] = {}
    for r in scored:
        cat = r.get("category", "unknown")
        by_category.setdefault(cat, []).append(r["overall_score"])

    print(f"\n  By category:")
    for cat, scores in sorted(by_category.items(), key=lambda x: _mean(x[1]), reverse=True):
        print(f"    {cat:20s} {_mean(scores):.0%} ({len(scores)} tests)")


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


# ─── CLI ──────────────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(description="Multi-turn eval via Cursor SDK")
    parser.add_argument("--filter", help="Filter tests by id/category/target")
    parser.add_argument("--capture-model", default=os.environ.get("CAPTURE_MODEL", "composer-2.5"))
    parser.add_argument("--judge-model", default=os.environ.get("JUDGE_MODEL", "claude-opus-4-6"))
    parser.add_argument("--dry-run", action="store_true", help="Show plan without executing")
    parser.add_argument("--capture-only", action="store_true", help="Capture transcripts only")
    parser.add_argument("--judge-only", action="store_true", help="Judge existing transcripts only")
    parser.add_argument("--save", action="store_true", help="Save results to history")
    args = parser.parse_args()

    api_key = os.environ.get("CURSOR_API_KEY", "")
    if not api_key and not args.dry_run:
        print("Error: CURSOR_API_KEY required.", file=sys.stderr)
        return 1

    dataset = load_dataset()
    tests = load_multi_turn_tests(dataset)

    if not tests:
        print("No multi_turn tests found in dataset.yaml")
        return 0

    if args.filter:
        tests = filter_tests(tests, args.filter)

    print(f"Found {len(tests)} multi-turn tests")
    print(f"Capture: {args.capture_model} | Judge: {args.judge_model}")
    print()

    results = run_pipeline(
        tests,
        args.capture_model,
        args.judge_model,
        api_key,
        capture_only=args.capture_only,
        judge_only=args.judge_only,
        dry_run=args.dry_run,
    )

    if results and not args.capture_only:
        print_summary(results)

        if args.save:
            path = save_results(results, args.capture_model, args.judge_model)
            print(f"\nSaved to: {path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
