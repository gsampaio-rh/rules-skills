#!/usr/bin/env python3
"""Manual capture helper for eval test cases.

For automated capture, use auto_capture.py instead (requires Cursor SDK).
This script is for manual paste-based capture as a fallback.

Usage:
    python tests/eval/manual_capture.py              # show all uncaptured tests
    python tests/eval/manual_capture.py --next       # show the next uncaptured test and open file
    python tests/eval/manual_capture.py --status     # show capture progress
    python tests/eval/manual_capture.py --filter sec # show uncaptured tests matching 'sec'
"""

import argparse
import os
import subprocess
import sys

from capture import create_response_file, has_response
from common import filter_dataset, load_dataset


def show_status(dataset: list[dict]) -> None:
    captured = [t for t in dataset if has_response(t["id"])]
    uncaptured = [t for t in dataset if not has_response(t["id"])]

    total = len(dataset)
    done = len(captured)
    pct = (done / total * 100) if total > 0 else 0

    print(f"Capture progress: {done}/{total} ({pct:.0f}%)\n")

    by_category: dict[str, dict[str, int]] = {}
    for t in dataset:
        cat = t.get("category", "unknown")
        by_category.setdefault(cat, {"total": 0, "captured": 0})
        by_category[cat]["total"] += 1
        if has_response(t["id"]):
            by_category[cat]["captured"] += 1

    for cat, counts in sorted(by_category.items()):
        bar_total = 20
        filled = int(counts["captured"] / counts["total"] * bar_total)
        bar = "\u2588" * filled + "\u2591" * (bar_total - filled)
        print(f"  {cat:20s} {bar} {counts['captured']}/{counts['total']}")

    if uncaptured:
        print(f"\nNext uncaptured: {uncaptured[0]['id']}")
        print(f"Run: python tests/eval/manual_capture.py --next")


def show_test(test_case: dict) -> None:
    print("=" * 60)
    print(f"Test: {test_case['id']}")
    print(f"Targets: {', '.join(test_case.get('targets', []))}")
    print(f"Category: {test_case.get('category', '')}")
    print("=" * 60)
    print(f"\nCONTEXT:\n{test_case.get('context', 'No additional context.')}")
    print(f"\nPROMPT (paste this into a new Cursor chat):")
    print("-" * 40)
    print(test_case["prompt"])
    print("-" * 40)
    print(f"\nEXPECTED BEHAVIORS:")
    for e in test_case.get("expected", []):
        print(f"  + {e}")
    print(f"\nANTI-EXPECTED (should NOT happen):")
    for a in test_case.get("anti_expected", []):
        print(f"  - {a}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture agent responses for eval")
    parser.add_argument("--next", action="store_true", help="Show next uncaptured test and open response file")
    parser.add_argument("--status", action="store_true", help="Show capture progress")
    parser.add_argument("--filter", help="Filter tests by id, target, or category")
    parser.add_argument("--open", action="store_true", help="Open response file in default editor (with --next)")
    args = parser.parse_args()

    dataset = load_dataset()
    dataset = filter_dataset(dataset, pattern=args.filter)

    if args.status:
        show_status(dataset)
        return 0

    uncaptured = [t for t in dataset if not has_response(t["id"])]

    if not uncaptured:
        print("All test cases have responses captured.")
        show_status(dataset)
        return 0

    if args.next:
        test = uncaptured[0]
        show_test(test)
        path = create_response_file(test["id"])
        print(f"\nResponse file: {path}")
        print("Paste the agent's response into this file, then run this command again.")

        remaining = len(uncaptured) - 1
        if remaining > 0:
            print(f"\n{remaining} more tests remaining after this one.")

        if args.open:
            editor = os.environ.get("EDITOR", "code")
            subprocess.run([editor, str(path)])

        return 0

    print(f"{len(uncaptured)} tests need responses:\n")
    for t in uncaptured:
        targets = ", ".join(t.get("targets", []))
        print(f"  {t['id']:45s} [{targets}]")

    print(f"\nRun: python tests/eval/manual_capture.py --next")
    return 0


if __name__ == "__main__":
    sys.exit(main())
