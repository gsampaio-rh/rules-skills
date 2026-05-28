#!/usr/bin/env python3
"""Tier 1 fast lint: harness state consistency checks.

Validates breadcrumbs integrity, state.json consistency, and cross-file
coherence. No API calls — runs in seconds.

Usage:
    python tests/eval/harness_lint.py                # lint .harness/
    python tests/eval/harness_lint.py path/to/dir    # lint specific directory
    python tests/eval/harness_lint.py --json         # JSON output
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def _parse_ts(ts: str) -> datetime:
    """Parse ISO-8601 timestamp, normalizing to UTC-aware."""
    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def lint_breadcrumbs(path: Path) -> tuple[list[str], list[str]]:
    """Validate breadcrumbs.jsonl structure and integrity."""
    errors: list[str] = []
    warnings: list[str] = []

    if not path.exists():
        warnings.append("breadcrumbs.jsonl not found")
        return errors, warnings

    lines = path.read_text().splitlines()
    if not lines:
        warnings.append("breadcrumbs.jsonl is empty")
        return errors, warnings

    required_fields = {"ts", "role", "msg"}
    valid_roles = {"planner", "builder", "evaluator", "system"}
    valid_types = {
        "plan", "negotiate", "negotiation", "build", "verify", "eval",
        "checkpoint", "decision", "scrap", "session_start", "cleanup",
    }

    prev_ts = None
    bad_json_count = 0
    entries = []

    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            bad_json_count += 1
            if bad_json_count <= 3:
                errors.append(f"Line {i + 1}: invalid JSON")
            continue

        entries.append(entry)

        missing = required_fields - set(entry.keys())
        if missing:
            errors.append(f"Line {i + 1}: missing fields: {', '.join(sorted(missing))}")

        role = entry.get("role", "")
        if role and role not in valid_roles:
            warnings.append(f"Line {i + 1}: unknown role '{role}'")

        entry_type = entry.get("type", "")
        if entry_type and entry_type not in valid_types:
            warnings.append(f"Line {i + 1}: unknown type '{entry_type}'")

        ts = entry.get("ts", "")
        if ts and prev_ts:
            try:
                current = _parse_ts(ts)
                previous = _parse_ts(prev_ts)
                if current < previous:
                    warnings.append(f"Line {i + 1}: timestamp out of order ({ts} < {prev_ts})")
            except (ValueError, TypeError):
                pass
        if ts:
            prev_ts = ts

    if bad_json_count > 3:
        errors.append(f"... and {bad_json_count - 3} more invalid JSON lines")

    return errors, warnings


def lint_state(path: Path) -> tuple[list[str], list[str]]:
    """Validate state.json structure."""
    errors: list[str] = []
    warnings: list[str] = []

    if not path.exists():
        warnings.append("state.json not found")
        return errors, warnings

    try:
        state = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        errors.append(f"Invalid JSON: {e}")
        return errors, warnings

    if "project" not in state:
        warnings.append("Missing 'project' field")

    features = state.get("features", [])
    if not isinstance(features, list):
        errors.append("'features' must be a list")
        return errors, warnings

    valid_statuses = {"pending", "building", "evaluating", "verified", "committed"}
    seen_ids: set[str] = set()

    for i, feat in enumerate(features):
        fid = feat.get("id", "")
        if not fid:
            errors.append(f"Feature {i}: missing 'id'")
        elif fid in seen_ids:
            errors.append(f"Feature {i}: duplicate id '{fid}'")
        else:
            seen_ids.add(fid)

        if not feat.get("name"):
            warnings.append(f"Feature {i} ({fid}): missing 'name'")

        status = feat.get("status", "")
        if status and status not in valid_statuses:
            errors.append(f"Feature {fid}: invalid status '{status}'")

    return errors, warnings


def lint_cross_consistency(
    harness_dir: Path,
) -> tuple[list[str], list[str]]:
    """Check cross-file consistency between state, contract, and breadcrumbs."""
    errors: list[str] = []
    warnings: list[str] = []

    state_path = harness_dir / "state.json"
    contract_path = harness_dir / "contract.json"

    if not state_path.exists():
        return errors, warnings

    try:
        state = json.loads(state_path.read_text())
    except (json.JSONDecodeError, OSError):
        return errors, warnings

    features = state.get("features", [])
    feature_ids = {f.get("id") for f in features if f.get("id")}

    if contract_path.exists():
        try:
            contract = json.loads(contract_path.read_text())
            contract_fid = contract.get("feature_id", "")
            if contract_fid and contract_fid not in feature_ids:
                errors.append(
                    f"Contract references '{contract_fid}' but state.json has no such feature"
                )

            if contract.get("verified") and contract.get("phase") != "verified":
                warnings.append("Contract verified=true but phase != 'verified'")

        except (json.JSONDecodeError, OSError):
            pass

    stuck = [
        f for f in features
        if f.get("status") == "evaluating"
    ]
    if stuck:
        ids = [f.get("id", "?") for f in stuck]
        warnings.append(f"Potentially stuck features (status=evaluating): {', '.join(ids)}")

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="Lint harness state files")
    parser.add_argument("path", nargs="?", default=".harness")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    harness_dir = Path(args.path)
    if not harness_dir.exists():
        if args.json:
            print(json.dumps({"status": "skip", "reason": "no .harness/ directory"}))
        else:
            print(f"No harness directory at {harness_dir} — skipping")
        return 0

    all_errors: list[str] = []
    all_warnings: list[str] = []
    sections: dict[str, dict] = {}

    for name, lint_fn, file_path in [
        ("breadcrumbs", lint_breadcrumbs, harness_dir / "breadcrumbs.jsonl"),
        ("state", lint_state, harness_dir / "state.json"),
    ]:
        errs, warns = lint_fn(file_path)
        all_errors.extend(errs)
        all_warnings.extend(warns)
        sections[name] = {"errors": errs, "warnings": warns}

    cross_errs, cross_warns = lint_cross_consistency(harness_dir)
    all_errors.extend(cross_errs)
    all_warnings.extend(cross_warns)
    sections["cross_consistency"] = {"errors": cross_errs, "warnings": cross_warns}

    if args.json:
        print(json.dumps({
            "status": "fail" if all_errors else "pass",
            "errors": all_errors,
            "warnings": all_warnings,
            "sections": sections,
        }, indent=2))
    else:
        print(f"Harness lint: {harness_dir}")
        for section, data in sections.items():
            errs = data["errors"]
            warns = data["warnings"]
            if errs or warns:
                print(f"\n  [{section}]")
                for e in errs:
                    print(f"    ERROR: {e}")
                for w in warns:
                    print(f"    WARN:  {w}")
        if not all_errors and not all_warnings:
            print("  All checks passed")
        print(f"\nResult: {len(all_errors)} errors, {len(all_warnings)} warnings")

    return 1 if all_errors else 0


if __name__ == "__main__":
    sys.exit(main())
