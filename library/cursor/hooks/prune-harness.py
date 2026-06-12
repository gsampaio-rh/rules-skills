#!/usr/bin/env python3
"""
Harness state prune script.

Dry-run by default; use --apply to mutate files.

Actions:
  1. Archive RESOLVED/DEFERRED open_questions from state.json → .harness/.archive/questions.jsonl
  2. Archive old breadcrumbs from breadcrumbs.jsonl → .harness/.archive/breadcrumbs.jsonl
     Retention: keep whichever of (last 50 lines) or (lines within 7 days) retains more.
  3. Remove stale flag files with per-flag staleness rules.
"""

import argparse
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

BREADCRUMB_KEEP_COUNT = 50
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
        "questions_archive": archive / "questions.jsonl",
        "breadcrumbs_archive": archive / "breadcrumbs.jsonl",
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


# --- Questions pruning ---

def _is_archivable_question(q: str) -> bool:
    return q.startswith("RESOLVED") or q.startswith("DEFERRED")


def _plan_questions(state: dict) -> list[str]:
    return [q for q in state.get("open_questions", []) if _is_archivable_question(q)]


def _apply_questions(state: dict, paths: dict) -> tuple[int, dict]:
    to_archive = _plan_questions(state)
    to_keep = [q for q in state.get("open_questions", []) if not _is_archivable_question(q)]

    if not to_archive:
        return 0, state

    ts = _now().isoformat()
    archive_path = paths["questions_archive"]
    existing_lines = _load_jsonl(archive_path)
    existing_set = set(existing_lines)

    new_lines = []
    for q in to_archive:
        line = json.dumps({"question": q, "archived_at": ts})
        if line not in existing_set:
            new_lines.append(line)
            existing_set.add(line)

    if new_lines:
        archive_path.parent.mkdir(parents=True, exist_ok=True)
        with archive_path.open("a") as f:
            f.write("\n".join(new_lines) + "\n")

    updated = {**state, "open_questions": to_keep}
    return len(to_archive), updated


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

    paths["breadcrumbs_archive"].parent.mkdir(parents=True, exist_ok=True)
    with paths["breadcrumbs_archive"].open("a") as f:
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

    changed_state = state
    any_action = False

    # 1. Questions
    to_archive_q = _plan_questions(state)
    if to_archive_q:
        print(f"  open_questions: {len(to_archive_q)} RESOLVED/DEFERRED → questions_archive.jsonl")
        for q in to_archive_q:
            print(f"    - {q[:80]}{'…' if len(q) > 80 else ''}")
        if args.apply:
            count, changed_state = _apply_questions(changed_state, paths)
        any_action = True
    else:
        print("  open_questions: nothing to archive")

    # 2. Breadcrumbs
    if not paths["breadcrumbs"].exists():
        print("  breadcrumbs.jsonl: not found — skipping", file=sys.stderr)
    else:
        lines = _load_jsonl(paths["breadcrumbs"])
        to_archive_b = _plan_breadcrumbs(lines)
        if to_archive_b:
            print(f"  breadcrumbs: {to_archive_b}/{len(lines)} lines → breadcrumbs_archive.jsonl")
            if args.apply:
                _apply_breadcrumbs(lines, paths)
            any_action = True
        else:
            print(f"  breadcrumbs: all {len(lines)} lines within retention window — nothing to archive")

    # 3. Flag files
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

    # Write updated state.json
    if args.apply and to_archive_q:
        paths["state"].write_text(json.dumps(changed_state, indent=2) + "\n")
        print()
        print(f"  state.json updated: {len(to_archive_q)} question(s) archived")

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
