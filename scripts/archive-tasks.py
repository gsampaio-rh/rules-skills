#!/usr/bin/env python3
"""Archive verified/cancelled tasks from state.json to .harness/archive.jsonl.

Keeps tasks[] as active backlog only. Archived tasks preserve all fields
plus an archived_at timestamp.

Usage:
    python scripts/archive-tasks.py [--dry-run]
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

STATE_PATH = Path(".harness/state.json")
ARCHIVE_PATH = Path(".harness/archive.jsonl")
ARCHIVABLE_STATUSES = {"verified", "committed", "cancelled"}


def main():
    dry_run = "--dry-run" in sys.argv

    if not STATE_PATH.exists():
        print("No .harness/state.json found.")
        return

    state = json.loads(STATE_PATH.read_text())
    tasks = state.get("tasks", state.get("features", []))

    to_archive = [t for t in tasks if t.get("status") in ARCHIVABLE_STATUSES]
    to_keep = [t for t in tasks if t.get("status") not in ARCHIVABLE_STATUSES]

    if not to_archive:
        print("No tasks to archive.")
        return

    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")

    print(f"Archiving {len(to_archive)} tasks, keeping {len(to_keep)} active.")
    if dry_run:
        print("[DRY RUN] Would archive:")
        for t in to_archive:
            print(f"  {t['id']} ({t.get('status')}) — {t.get('name', '')[:60]}")
        return

    with ARCHIVE_PATH.open("a") as f:
        for t in to_archive:
            t["archived_at"] = ts
            f.write(json.dumps(t, ensure_ascii=False) + "\n")

    state["tasks"] = to_keep
    STATE_PATH.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n")

    print(f"Done. Archived {len(to_archive)} tasks to {ARCHIVE_PATH}")
    print(f"state.json: {len(to_keep)} active tasks remain.")


if __name__ == "__main__":
    main()
