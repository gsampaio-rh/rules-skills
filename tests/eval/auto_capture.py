#!/usr/bin/env python3
"""Automated response capture via Cursor SDK.

Sends each test case's prompt to a local Cursor agent and saves the response.
The agent runs against this repo's workspace so .cursor/rules/ are active.

Usage:
    python tests/eval/auto_capture.py                          # capture all missing responses
    python tests/eval/auto_capture.py --filter security        # only tests matching 'security'
    python tests/eval/auto_capture.py --model auto             # use a specific model
    python tests/eval/auto_capture.py --force                  # re-capture even if response exists
    python tests/eval/auto_capture.py --dry-run                # show what would be captured

Environment variables:
    CURSOR_API_KEY  - Cursor API key (required)
    CAPTURE_MODEL   - model override (default: composer-2.5)
"""

import argparse
import os
import sys
import time
from pathlib import Path

import yaml

EVAL_DIR = Path(__file__).parent
DATASET_PATH = EVAL_DIR / "dataset.yaml"
REPO_ROOT = EVAL_DIR.parent.parent


def load_dataset() -> list[dict]:
    with open(DATASET_PATH) as f:
        return yaml.safe_load(f)


def responses_dir(model: str) -> Path:
    return EVAL_DIR / "responses" / model


def has_response(test_id: str, model: str) -> bool:
    path = responses_dir(model) / f"{test_id}.md"
    if not path.exists():
        return False
    text = path.read_text().strip()
    return bool(text) and not text.startswith("<!-- Response for:")


def save_response(test_id: str, model: str, response: str) -> Path:
    out_dir = responses_dir(model)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{test_id}.md"
    path.write_text(response)
    return path


def capture_one(prompt: str, model: str, api_key: str) -> str:
    from cursor_sdk import Agent, AgentOptions, LocalAgentOptions

    result = Agent.prompt(
        prompt,
        AgentOptions(
            api_key=api_key,
            model=model,
            local=LocalAgentOptions(cwd=str(REPO_ROOT)),
        ),
    )

    if result.status == "error":
        raise RuntimeError(f"Agent run failed (id={result.id}): status={result.status}")

    return result.result or ""


def filter_dataset(dataset: list[dict], pattern: str) -> list[dict]:
    f = pattern.lower()
    return [
        t for t in dataset
        if f in t["id"].lower()
        or f in t.get("category", "").lower()
        or any(f in tgt.lower() for tgt in t.get("targets", []))
    ]


def show_status(dataset: list[dict], model: str) -> None:
    captured = sum(1 for t in dataset if has_response(t["id"], model))
    total = len(dataset)
    pct = (captured / total * 100) if total > 0 else 0
    print(f"Captured: {captured}/{total} ({pct:.0f}%) for model '{model}'")


def main() -> int:
    parser = argparse.ArgumentParser(description="Automated response capture via Cursor SDK")
    parser.add_argument("--filter", help="Only capture tests matching this string")
    parser.add_argument("--model", default=os.environ.get("CAPTURE_MODEL", "composer-2.5"),
                        help="Cursor model to use (default: composer-2.5)")
    parser.add_argument("--force", action="store_true",
                        help="Re-capture even if response already exists")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be captured without running")
    parser.add_argument("--status", action="store_true",
                        help="Show capture progress and exit")
    args = parser.parse_args()

    api_key = os.environ.get("CURSOR_API_KEY", "")
    if not api_key and not args.dry_run and not args.status:
        print("Error: CURSOR_API_KEY environment variable is required.", file=sys.stderr)
        print("Get your key at: https://cursor.com/dashboard/integrations", file=sys.stderr)
        return 1

    dataset = load_dataset()
    if args.filter:
        dataset = filter_dataset(dataset, args.filter)

    if args.status:
        show_status(dataset, args.model)
        return 0

    to_capture = [
        t for t in dataset
        if args.force or not has_response(t["id"], args.model)
    ]

    if not to_capture:
        print("All test cases already have responses.")
        show_status(dataset, args.model)
        return 0

    if args.dry_run:
        print(f"Would capture {len(to_capture)} responses with model '{args.model}':\n")
        for t in to_capture:
            status = "exists (--force)" if has_response(t["id"], args.model) else "missing"
            print(f"  {t['id']:50s} [{status}]")
        return 0

    total = len(to_capture)
    passed = 0
    failed = 0

    print(f"Capturing {total} responses with model '{args.model}'...")
    print(f"Workspace: {REPO_ROOT}\n")

    for i, test_case in enumerate(to_capture, 1):
        test_id = test_case["id"]
        print(f"[{i}/{total}] {test_id}...", end=" ", flush=True)

        start = time.time()
        try:
            response = capture_one(test_case["prompt"], args.model, api_key)
            path = save_response(test_id, args.model, response)
            elapsed = time.time() - start
            print(f"ok ({elapsed:.1f}s, {len(response)} chars) -> {path.name}")
            passed += 1
        except Exception as e:
            elapsed = time.time() - start
            print(f"FAILED ({elapsed:.1f}s): {e}")
            failed += 1

    print(f"\nDone: {passed} captured, {failed} failed, {total - passed - failed} skipped")
    show_status(dataset, args.model)
    return 1 if failed > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
