#!/usr/bin/env python3
"""
Harness state prune script.

Dry-run by default; use --apply to mutate files.

Actions:
  1. Archive old breadcrumbs from breadcrumbs.jsonl → .harness/.archive/archive.jsonl
     (same forensic sink as sessionStart / harness-context).
     Retention: keep whichever of (last 30 lines) or (lines within 7 days) retains more.
  2. Remove stale flag files with per-flag staleness rules.

Deprecated sinks (do not write): .archive/breadcrumbs.jsonl, .archive/questions.jsonl
"""

import argparse
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

BREADCRUMB_KEEP_COUNT = 30
BREADCRUMB_KEEP_DAYS = 7

_DEFAULT_ROOT = Path.cwd()


def _resolve_paths(root: Path) -> dict:
    harness = root / ".harness"
    archive = harness / ".archive"
    hooks = root / ".cursor" / "hooks"
    return {
        "state": harness / "state.json",
        "breadcrumbs": harness / "breadcrumbs.jsonl",
        "contract": harness / "contract.json",
        "archive_dir": archive,
        "archive_jsonl": archive / "archive.jsonl",
        "flag_routing": harness / ".routing-pending",
        "flag_evaluator": hooks / ".evaluator-active",
        "flag_commit": hooks / ".commit-approved",
    }


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def _load_jsonl(path: Path) -> list[str]:
    if not path.exists():
        return []
    return [ln for ln in path.read_text().splitlines() if ln.strip()]


# --- Breadcrumb pruning ---

def _parse_ts(line: str) -> datetime | None:
    try:
        obj = json.loads(line)
        ts_str = obj.get("ts", "")
        if not ts_str:
            return None
        dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (json.JSONDecodeError, ValueError):
        return None


def _retention_indices(lines: list[str]) -> set[int]:
    """Return indices of lines to KEEP using whichever policy retains more."""
    cutoff = _now() - timedelta(days=BREADCRUMB_KEEP_DAYS)

    last_n = set(range(max(0, len(lines) - BREADCRUMB_KEEP_COUNT), len(lines)))

    age_set = set()
    for i, ln in enumerate(lines):
        ts = _parse_ts(ln)
        if ts is None or ts >= cutoff:
            age_set.add(i)

    return last_n if len(last_n) >= len(age_set) else age_set


def _plan_breadcrumbs(lines: list[str]) -> int:
    return len(lines) - len(_retention_indices(lines))


def _apply_breadcrumbs(lines: list[str], paths: dict) -> int:
    keep_indices = _retention_indices(lines)
    to_archive = [ln for i, ln in enumerate(lines) if i not in keep_indices]
    to_keep = [ln for i, ln in enumerate(lines) if i in keep_indices]

    if not to_archive:
        return 0

    # Raw breadcrumb JSONL lines — same schema as harness-context overflow.
    paths["archive_jsonl"].parent.mkdir(parents=True, exist_ok=True)
    with paths["archive_jsonl"].open("a") as f:
        f.write("\n".join(to_archive) + "\n")
    with paths["breadcrumbs"].open("w") as f:
        f.write("\n".join(to_keep) + ("\n" if to_keep else ""))

    return len(to_archive)


# --- Flag file pruning ---

def _flag_stale_by_mtime(path: Path, max_age_seconds: int) -> bool:
    if not path.exists():
        return False
    return time.time() - path.stat().st_mtime > max_age_seconds


def _plan_flags(state: dict, paths: dict) -> list[tuple[Path, str]]:
    removable = []

    if _flag_stale_by_mtime(paths["flag_routing"], 30 * 60):
        removable.append((paths["flag_routing"], "mtime > 30min"))

    if paths["flag_evaluator"].exists():
        contract = _load_json(paths["contract"])
        phase = (contract or {}).get("phase", "none")
        if phase != "evaluating":
            removable.append((paths["flag_evaluator"], f"contract.phase={phase!r}, not 'evaluating'"))

    if paths["flag_commit"].exists():
        tasks = (state or {}).get("tasks", [])
        if not any(t.get("status") == "building" for t in tasks):
            removable.append((paths["flag_commit"], "no task in status=building"))

    return removable


def _apply_flags(removable: list[tuple[Path, str]]) -> int:
    for path, _ in removable:
        try:
            path.unlink(missing_ok=True)
        except OSError as e:
            print(f"  WARNING: could not remove {path}: {e}", file=sys.stderr)
    return len(removable)


# --- Main ---

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prune stale .harness/ state. Dry-run by default; use --apply to mutate."
    )
    parser.add_argument("--apply", action="store_true", help="Apply mutations (default: dry-run)")
    parser.add_argument("--root", type=Path, default=_DEFAULT_ROOT,
                        help="Repository root (default: auto-detected from script location)")
    args = parser.parse_args()

    paths = _resolve_paths(args.root)
    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"prune-harness ({mode})")
    print()

    state = _load_json(paths["state"])
    if state is None:
        print("ERROR: .harness/state.json not found or invalid JSON", file=sys.stderr)
        return 1

    any_action = False

    # 1. Breadcrumbs → archive.jsonl
    if not paths["breadcrumbs"].exists():
        print("  breadcrumbs.jsonl: not found — skipping", file=sys.stderr)
    else:
        lines = _load_jsonl(paths["breadcrumbs"])
        to_archive_b = _plan_breadcrumbs(lines)
        if to_archive_b:
            print(f"  breadcrumbs: {to_archive_b}/{len(lines)} lines → archive.jsonl")
            if args.apply:
                _apply_breadcrumbs(lines, paths)
            any_action = True
        else:
            print(f"  breadcrumbs: all {len(lines)} lines within retention window — nothing to archive")

    # 2. Flag files
    removable_flags = _plan_flags(state, paths)
    if removable_flags:
        print(f"  flags: {len(removable_flags)} stale flag(s) to remove")
        for path, reason in removable_flags:
            print(f"    - {path} ({reason})")
        if args.apply:
            _apply_flags(removable_flags)
        any_action = True
    else:
        print("  flags: no stale flag files")

    print()
    if not any_action:
        print("Nothing to prune.")
    elif not args.apply:
        print("Dry-run complete. Run with --apply to apply changes.")
    else:
        print("Prune applied.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
