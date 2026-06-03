#!/usr/bin/env python3
"""Capture behavioral baseline: map all scenario behavioral criteria to branch results.

Builds minimal session stubs per scenario (using seed_files and rubric context)
and evaluates each behavioral criterion via _evaluate_behavioral().
Saves results to tests/eval/fixtures/behavioral_baseline.json.

Usage:
    python tests/eval/capture_behavioral_baseline.py
    python tests/eval/capture_behavioral_baseline.py --output path/to/baseline.json
"""

import argparse
import json
import sys
from pathlib import Path

import yaml

EVAL_DIR = Path(__file__).parent
SCENARIOS_DIR = EVAL_DIR / "scenarios"
LONG_DIR = SCENARIOS_DIR / "long"
FIXTURES_DIR = EVAL_DIR / "fixtures"

sys.path.insert(0, str(EVAL_DIR.parent.parent))
from tests.eval.session_judge import _evaluate_behavioral


def _build_stub(scenario: dict) -> dict:
    """Build a minimal session stub from scenario seed data."""
    seed_files = scenario.get("seed_files", {})
    seed_prompt = scenario.get("seed_prompt", "")

    harness = {}
    if ".harness/state.json" in seed_files:
        try:
            harness["state.json"] = json.loads(seed_files[".harness/state.json"])
        except (json.JSONDecodeError, TypeError):
            harness["state.json"] = {"tasks": []}
    else:
        harness["state.json"] = {"tasks": []}

    if ".harness/contract.json" in seed_files:
        try:
            harness["contract.json"] = json.loads(seed_files[".harness/contract.json"])
        except (json.JSONDecodeError, TypeError):
            harness["contract.json"] = {}
    else:
        harness["contract.json"] = {}

    if ".harness/breadcrumbs.jsonl" in seed_files:
        raw = seed_files[".harness/breadcrumbs.jsonl"]
        breadcrumbs = []
        for line in raw.strip().splitlines():
            line = line.strip()
            if line:
                try:
                    breadcrumbs.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        harness["breadcrumbs.jsonl"] = breadcrumbs
    else:
        harness["breadcrumbs.jsonl"] = []

    transcript_text = _generate_passing_transcript(scenario)

    return {
        "scenario_id": scenario.get("id", "unknown"),
        "model": "baseline",
        "transcript": [{"response": transcript_text}] if transcript_text else [],
        "artifacts": {
            "harness": harness,
            "files": list(seed_files.keys()),
            "file_contents": {k: v for k, v in seed_files.items() if not k.startswith(".harness/")},
            "validations": [{"command": "python -c 'import ast'", "status": "PASS", "exit_code": 0}],
        },
    }


def _generate_passing_transcript(scenario: dict) -> str:
    """Generate a transcript that would plausibly pass most behavioral checks.

    Uses scenario context to include relevant keywords without being overly specific.
    """
    scenario_id = scenario.get("id", "")
    parts = [
        "I'll work on this task.",
        "Running validation commands.",
        "pytest tests/ passed.",
    ]

    behavioral = scenario.get("post_hoc_rubric", {}).get("behavioral", [])
    for criterion in behavioral:
        cl = criterion.lower()
        if "todowrite" in cl and "no todowrite" not in cl:
            parts.append("TodoWrite plan created for tracking progress.")
        if "breadcrumb" in cl and "read breadcrumbs" not in cl:
            parts.append("Breadcrumb logged.")
        if "fresh thread" in cl or "session boundary" in cl:
            parts.append("Let's commit before continuing. I suggest we start a fresh thread for the next task.")
        if "checkpoint" in cl and "commit" not in cl:
            parts.append("Let me checkpoint the current work.")
        if "push back" in cl or "pushback" in cl:
            parts.append("Before I start, could you specify what areas you want improved?")
        if "plan" in cl and "proposed" in cl:
            parts.append("Here's my plan: Phase 1 will handle the core logic, then Phase 2 adds tests.")
        if "presented" in cl and "option" in cl:
            parts.append("Option A uses a hash map. Option B uses sorted array. Which do you prefer?")
        if "autonomously" in cl or "autonomous" in cl:
            parts.append("Running pytest. Installing dependencies.")
        if "contract" in cl and "negotiat" in cl:
            parts.append("I'll write the contract.json with acceptance criteria before implementing.")
        if "planner" in cl and "delegated" in cl:
            parts.append("This requires planning. Delegating to /planner for task decomposition.")
        if "evaluator" in cl and "not modify source" not in cl:
            parts.append("Launching /evaluator for adversarial review.")
        if "commit" in cl and "approval" in cl:
            parts.append("Shall I commit these changes? Ready to commit.")
        if "acknowledged" in cl and "urgency" in cl:
            parts.append("I understand your urgency, however the priority order matters. Let me explain.")
        if "silently" in cl and ("accept" in cl or "continue" in cl):
            parts.append("Before we proceed, there are a lot of changes accumulating. Let's commit first.")

    return " ".join(parts)


def collect_criteria() -> list[dict]:
    """Collect all behavioral criteria from all scenario YAMLs."""
    results = []
    for d in [SCENARIOS_DIR, LONG_DIR]:
        if not d.exists():
            continue
        for f in sorted(d.glob("*.yaml")):
            data = yaml.safe_load(f.read_text())
            if not data:
                continue
            scenario_id = data.get("id", f.stem)
            behavioral = data.get("post_hoc_rubric", {}).get("behavioral", [])
            for criterion in behavioral:
                results.append({
                    "scenario_id": scenario_id,
                    "criterion": criterion,
                    "yaml_file": str(f.relative_to(EVAL_DIR.parent.parent)),
                })
    return results


def capture_baseline(output_path: Path | None = None) -> dict:
    """Run all behavioral criteria against stubs and capture results."""
    criteria = collect_criteria()
    scenario_cache: dict[str, dict] = {}
    baseline: list[dict] = []

    for item in criteria:
        scenario_id = item["scenario_id"]
        if scenario_id not in scenario_cache:
            yaml_path = Path(EVAL_DIR.parent.parent) / item["yaml_file"]
            scenario_data = yaml.safe_load(yaml_path.read_text())
            stub = _build_stub(scenario_data)
            scenario_cache[scenario_id] = (stub, scenario_data)

        stub, scenario_data = scenario_cache[scenario_id]
        transcript_text = " ".join(
            t.get("response", "") for t in stub.get("transcript", []) if t.get("response")
        )

        result = _evaluate_behavioral(item["criterion"], transcript_text, stub)
        baseline.append({
            "scenario_id": scenario_id,
            "criterion": item["criterion"],
            "expected_bool": result,
        })

    out = output_path or (FIXTURES_DIR / "behavioral_baseline.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(baseline, indent=2) + "\n")

    none_count = sum(1 for b in baseline if b["expected_bool"] is None)
    true_count = sum(1 for b in baseline if b["expected_bool"] is True)
    false_count = sum(1 for b in baseline if b["expected_bool"] is False)

    print(f"Baseline captured: {len(baseline)} criteria")
    print(f"  True: {true_count}, False: {false_count}, None (UNMATCHED): {none_count}")
    print(f"  Saved to: {out}")

    return {"total": len(baseline), "true": true_count, "false": false_count, "none": none_count}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Capture behavioral baseline")
    parser.add_argument("--output", help="Output path for baseline JSON")
    args = parser.parse_args()
    out = Path(args.output) if args.output else None
    stats = capture_baseline(out)
    if stats["none"] > 0:
        print(f"\nWARNING: {stats['none']} criteria returned None (UNMATCHED)")
        sys.exit(1)
