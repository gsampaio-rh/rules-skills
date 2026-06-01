#!/usr/bin/env python3
"""Migrate state.json, contract.json, and metrics.json from v1 to v2 schema.

Changes:
  - state.json: rename 'features' → 'tasks', set schema_version=2,
    infer/fix type from id prefix, map legacy types (gap/fix → bug),
    clear resolved open_questions, update direction text.
  - contract.json: rename 'feature_id' → 'task_id' (keep feature_id as alias).
  - metrics.json: rename 'features' section → 'tasks'.

Idempotent — safe to run multiple times.

Usage:
    python scripts/migrate-state-schema.py [--dry-run] [--harness-dir .harness]
"""

import argparse
import json
import sys
from pathlib import Path

TYPE_FROM_PREFIX = {
    "feat-": "feature",
    "gap-": "bug",
    "spike-": "spike",
    "chore-": "chore",
}

LEGACY_TYPE_MAP = {
    "gap": "bug",
    "fix": "bug",
}

VALID_TYPES = {"feature", "bug", "spike", "chore"}


def infer_type(task: dict) -> str:
    """Determine canonical type from existing type or id prefix."""
    existing = task.get("type", "")
    if existing in VALID_TYPES:
        return existing
    if existing in LEGACY_TYPE_MAP:
        return LEGACY_TYPE_MAP[existing]
    task_id = task.get("id", "")
    for prefix, task_type in TYPE_FROM_PREFIX.items():
        if task_id.startswith(prefix):
            return task_type
    return "feature"


def migrate_state(state: dict) -> dict:
    """Migrate state.json from v1 to v2."""
    if state.get("schema_version", 1) >= 2 and "tasks" in state:
        for task in state.get("tasks", []):
            task["type"] = infer_type(task)
        return state

    tasks = state.pop("features", state.get("tasks", []))
    for task in tasks:
        task["type"] = infer_type(task)

    state["tasks"] = tasks
    state["schema_version"] = 2

    state["open_questions"] = []

    if "direction" in state:
        direction = state["direction"]
        direction = direction.replace(
            "contract.json keeps feature_id (task id)",
            "contract.json uses task_id (feature_id accepted as alias)",
        )
        state["direction"] = direction

    return state


def migrate_contract(contract: dict) -> dict:
    """Rename feature_id → task_id (keep both during transition)."""
    if "task_id" in contract:
        return contract
    fid = contract.pop("feature_id", "")
    if fid:
        contract["task_id"] = fid
        contract["feature_id"] = fid
    return contract


def migrate_metrics(metrics: dict) -> dict:
    """Rename 'features' section → 'tasks'."""
    if "tasks" in metrics and "features" not in metrics:
        return metrics
    features_data = metrics.pop("features", None)
    if features_data:
        if "features_completed" in features_data:
            features_data["tasks_completed"] = features_data.pop("features_completed")
        if "features_pending" in features_data:
            features_data["tasks_pending"] = features_data.pop("features_pending")
        metrics["tasks"] = features_data
    return metrics


def migrate_file(path: Path, migrator, label: str, dry_run: bool) -> bool:
    """Apply a migration function to a JSON file."""
    if not path.exists():
        print(f"  {label}: not found, skipping")
        return False

    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        print(f"  {label}: invalid JSON — {e}")
        return False

    migrated = migrator(data)
    output = json.dumps(migrated, indent=2, ensure_ascii=False) + "\n"

    if dry_run:
        print(f"  {label}: would write {len(output)} bytes")
        return True

    path.write_text(output)
    print(f"  {label}: migrated ({len(output)} bytes)")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate harness files to v2 schema")
    parser.add_argument("--harness-dir", default=".harness", help="Path to harness directory")
    parser.add_argument("--dry-run", action="store_true", help="Show changes without writing")
    args = parser.parse_args()

    harness = Path(args.harness_dir)
    if not harness.exists():
        print(f"No harness directory at {harness}")
        return 1

    print(f"Migrating harness files in {harness}/ to v2 schema...")
    if args.dry_run:
        print("  (dry run — no files will be modified)\n")

    results = []
    results.append(migrate_file(harness / "state.json", migrate_state, "state.json", args.dry_run))
    results.append(migrate_file(harness / "contract.json", migrate_contract, "contract.json", args.dry_run))
    results.append(migrate_file(harness / "metrics.json", migrate_metrics, "metrics.json", args.dry_run))

    migrated = sum(1 for r in results if r)
    print(f"\nDone: {migrated} file(s) migrated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
