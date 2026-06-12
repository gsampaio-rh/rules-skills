#!/usr/bin/env python3
"""Archive verified/cancelled tasks from state.json to .harness/.archive/tasks.jsonl.

Keeps tasks[] as active backlog only. Archived tasks preserve all fields
plus an archived_at timestamp.

Usage:
    python scripts/archive-tasks.py [--dry-run] [--skip-checks]

Verification checks (bypass with --skip-checks):
  - verified tasks must have a breadcrumb with role=evaluator, result=pass
    OR an eval report file at .harness/evals/eval-{id}.json
  - cancelled tasks must have a non-empty details or reason field
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

STATE_PATH = Path(".harness/state.json")
ARCHIVE_PATH = Path(".harness/.archive/tasks.jsonl")
BREADCRUMBS_PATH = Path(".harness/breadcrumbs.jsonl")
EVALS_DIR = Path(".harness/evals")
ARCHIVABLE_STATUSES = {"verified", "committed", "cancelled"}


def _load_verified_ids() -> set[str]:
    """Return set of task ids that have evidence of completion in breadcrumbs.

    Accepts either:
    - evaluator PASS breadcrumb (role=evaluator, result=pass)
    - builder build breadcrumb (role=builder, type=build, result=pass)
      — covers simple 1-2 file tasks that legitimately bypass the full harness
    """
    if not BREADCRUMBS_PATH.exists():
        return set()
    ids: set[str] = set()
    for line in BREADCRUMBS_PATH.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            b = json.loads(line)
            feat = b.get("feat", "")
            result = str(b.get("result", "")).lower()
            if not feat or result != "pass":
                continue
            role = b.get("role", "")
            btype = b.get("type", "")
            if role == "evaluator" or (role == "builder" and btype == "build"):
                ids.add(feat)
        except Exception:
            continue
    return ids


def _has_eval_report(task_id: str) -> bool:
    """Check if an eval report JSON exists for the task."""
    return (EVALS_DIR / f"eval-{task_id}.json").exists()


def _check_task(task: dict, verified_ids: set[str], skip_checks: bool) -> list[str]:
    """Return a list of warning strings for a task; empty if all checks pass."""
    if skip_checks:
        return []
    warnings: list[str] = []
    status = task.get("status", "")
    tid = task.get("id", "?")

    if status in ("verified", "committed"):
        has_breadcrumb = tid in verified_ids
        has_report = _has_eval_report(tid)
        if not has_breadcrumb and not has_report:
            warnings.append(
                f"  [{tid}] WARN: status={status} but no evaluator PASS breadcrumb "
                f"and no .harness/evals/eval-{tid}.json"
            )

    elif status == "cancelled":
        details = task.get("details", "").strip()
        reason = task.get("reason", "").strip()
        if not details and not reason:
            warnings.append(
                f"  [{tid}] WARN: status=cancelled but no details/reason field "
                f"explaining the cancellation"
            )

    return warnings


def main() -> int:
    dry_run = "--dry-run" in sys.argv
    skip_checks = "--skip-checks" in sys.argv

    if not STATE_PATH.exists():
        print("No .harness/state.json found.")
        return 1

    state = json.loads(STATE_PATH.read_text())
    tasks = state.get("tasks", state.get("features", []))

    to_archive = [t for t in tasks if t.get("status") in ARCHIVABLE_STATUSES]
    to_keep = [t for t in tasks if t.get("status") not in ARCHIVABLE_STATUSES]

    if not to_archive:
        print("No tasks to archive.")
        return 0

    verified_ids = _load_verified_ids()

    all_warnings: list[str] = []
    for task in to_archive:
        all_warnings.extend(_check_task(task, verified_ids, skip_checks))

    if all_warnings:
        print("Archive verification warnings:")
        for w in all_warnings:
            print(w)
        if not skip_checks:
            print(
                "\nRe-run with --skip-checks to archive anyway, "
                "or fix the missing evidence first."
            )
            return 1

    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")

    print(f"Archiving {len(to_archive)} tasks, keeping {len(to_keep)} active.")
    if dry_run:
        print("[DRY RUN] Would archive:")
        for t in to_archive:
            print(f"  {t['id']} ({t.get('status')}) — {t.get('name', '')[:60]}")
        return 0

    ARCHIVE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with ARCHIVE_PATH.open("a") as f:
        for t in to_archive:
            t["archived_at"] = ts
            f.write(json.dumps(t, ensure_ascii=False) + "\n")

    state["tasks"] = to_keep
    STATE_PATH.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n")

    print(f"Done. Archived {len(to_archive)} tasks to {ARCHIVE_PATH}")
    print(f"state.json: {len(to_keep)} active tasks remain.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
