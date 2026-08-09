#!/usr/bin/env python3
"""Tier 1 fast lint: contract quality checks.

Validates .harness/contract.json for structural completeness and
criteria quality. No API calls — runs in seconds.

Usage:
    python tests/eval/contract_lint.py                    # lint current contract
    python tests/eval/contract_lint.py path/to/contract   # lint specific file
    python tests/eval/contract_lint.py --json             # JSON output
"""

import argparse
import json
import re
import sys
from pathlib import Path

VAGUE_PATTERNS = [
    re.compile(r"\b(clean|good|nice|proper|appropriate|well.structured)\b", re.I),
    re.compile(r"\b(should work|looks? correct|seems? right)\b", re.I),
    re.compile(r"\b(check the code|review the implementation|inspect)\b", re.I),
    re.compile(r"\b(is reasonable|makes? sense)\b", re.I),
]

REQUIRED_FIELDS = [
    "feature",
    "acceptance_criteria",
    "edge_cases",
    "verification_method",
    "phase",
    "verified",
]

VALID_PHASES = [
    "negotiating",
    "negotiated",
    "building",
    "evaluating",
]


def lint_contract(contract: dict) -> tuple[list[str], list[str]]:
    """Returns (errors, warnings) for a contract."""
    errors: list[str] = []
    warnings: list[str] = []

    for field in REQUIRED_FIELDS:
        if field not in contract:
            errors.append(f"Missing required field: {field}")

    if "task_id" not in contract:
        errors.append("Missing required field: task_id")

    criteria = contract.get("acceptance_criteria", [])
    if not isinstance(criteria, list):
        errors.append("acceptance_criteria must be a list")
        criteria = []

    if len(criteria) == 0:
        errors.append("No acceptance criteria defined")
    elif len(criteria) < 3:
        warnings.append(f"Only {len(criteria)} criteria — consider adding more for coverage")

    for i, criterion in enumerate(criteria):
        if not isinstance(criterion, str):
            errors.append(f"Criterion {i} is not a string")
            continue
        for pattern in VAGUE_PATTERNS:
            if pattern.search(criterion):
                warnings.append(
                    f"Criterion {i} may be vague (matched '{pattern.pattern}'): "
                    f"'{criterion[:80]}...'" if len(criterion) > 80 else
                    f"Criterion {i} may be vague (matched '{pattern.pattern}'): '{criterion}'"
                )
                break

    edge_cases = contract.get("edge_cases", [])
    if not isinstance(edge_cases, list):
        errors.append("edge_cases must be a list")
    elif len(edge_cases) < 2:
        errors.append(f"Need at least 2 edge cases, found {len(edge_cases)}")

    verification = contract.get("verification_method", "")
    if isinstance(verification, str):
        if len(verification) < 10:
            errors.append("verification_method is too short to be useful")
        for pattern in VAGUE_PATTERNS:
            if pattern.search(verification):
                warnings.append(
                    f"verification_method may be vague (matched '{pattern.pattern}')"
                )
                break

    phase = contract.get("phase", "")
    if phase and phase not in VALID_PHASES:
        errors.append(f"Invalid phase: '{phase}' (valid: {', '.join(VALID_PHASES)})")

    # verified is a boolean; phase stays evaluating (or earlier). Do not require phase=verified.

    rounds = contract.get("negotiation_rounds", 0)
    if isinstance(rounds, int) and rounds > 3:
        warnings.append(f"Negotiation rounds ({rounds}) exceeds recommended max of 3")

    if not contract.get("rubrics"):
        warnings.append("No rubrics specified — consider adding domain rubrics")

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="Lint contract.json for quality")
    parser.add_argument("path", nargs="?", default=".harness/contract.json")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    contract_path = Path(args.path)
    if not contract_path.exists():
        if args.json:
            print(json.dumps({"status": "skip", "reason": "no contract found"}))
        else:
            print(f"No contract at {contract_path} — skipping")
        return 0

    try:
        contract = json.loads(contract_path.read_text())
    except json.JSONDecodeError as e:
        if args.json:
            print(json.dumps({"status": "fail", "errors": [f"Invalid JSON: {e}"]}))
        else:
            print(f"FAIL: Invalid JSON in {contract_path}: {e}")
        return 1

    errors, warnings = lint_contract(contract)

    if args.json:
        print(json.dumps({
            "status": "fail" if errors else "pass",
            "errors": errors,
            "warnings": warnings,
            "task_id": contract.get("task_id", "unknown"),
        }, indent=2))
    else:
        task = contract.get("task_id", "unknown")
        print(f"Contract lint: {task} ({contract_path})")
        if errors:
            for e in errors:
                print(f"  ERROR: {e}")
        if warnings:
            for w in warnings:
                print(f"  WARN:  {w}")
        if not errors and not warnings:
            print("  All checks passed")
        print(f"\nResult: {len(errors)} errors, {len(warnings)} warnings")

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
