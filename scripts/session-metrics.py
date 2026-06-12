"""
session-metrics.py — Measure interaction patterns from breadcrumbs.jsonl.

Satisfies ACAM Advanced Interaction Criterion 2: "Are interaction patterns
measured across sessions (prompt clarity, turns to completion)?"

Reads .harness/breadcrumbs.jsonl and outputs per-session and aggregate metrics:
  - tasks completed per session
  - session boundary advisory rate
  - mean tasks per session
  - role activity breakdown
  - breadcrumb type distribution

Usage:
    python scripts/session-metrics.py [--breadcrumbs PATH] [--json] [--since DATE]

Examples:
    python scripts/session-metrics.py
    python scripts/session-metrics.py --json
    python scripts/session-metrics.py --since 2026-06-01
    python scripts/session-metrics.py --breadcrumbs .harness/breadcrumbs.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


DEFAULT_BREADCRUMBS = Path(".harness/breadcrumbs.jsonl")
BOUNDARY_THRESHOLD = 3  # sessions_tasks_completed threshold for advisory


# ── Parsing ──────────────────────────────────────────────────────────────────


def load_breadcrumbs(path: Path) -> list[dict]:
    """Parse JSONL breadcrumbs, skip malformed lines."""
    if not path.exists():
        return []
    entries = []
    for lineno, raw in enumerate(path.read_text().splitlines(), 1):
        raw = raw.strip()
        if not raw:
            continue
        try:
            entries.append(json.loads(raw))
        except json.JSONDecodeError:
            pass  # skip corrupt lines silently
    return entries


def split_into_sessions(entries: list[dict]) -> list[list[dict]]:
    """Split breadcrumbs at each session_start marker.

    Returns a list of session windows. Window 0 is entries before the first
    session_start (usually empty or from initial setup).
    """
    sessions: list[list[dict]] = [[]]
    for entry in entries:
        if entry.get("type") == "session_start":
            sessions.append([entry])
        else:
            sessions[-1].append(entry)
    # Drop empty prefix window
    return [s for s in sessions if s]


# ── Per-Session Metrics ───────────────────────────────────────────────────────


def session_metrics(window: list[dict]) -> dict[str, Any]:
    """Compute metrics for a single session window."""
    start_entry = next((e for e in window if e.get("type") == "session_start"), None)
    session_ts = start_entry.get("ts", "") if start_entry else ""

    # Tasks completed: unique non-null feat IDs with role=builder, type=build, result=pass
    completed_feat_ids: set[str] = set()
    for e in window:
        feat = e.get("feat")
        if (
            feat
            and e.get("role") == "builder"
            and e.get("type") == "build"
            and str(e.get("result", "")).lower() == "pass"
        ):
            completed_feat_ids.add(feat)

    tasks_completed = len(completed_feat_ids)
    boundary_advisory_fired = tasks_completed >= BOUNDARY_THRESHOLD

    type_counts: Counter[str] = Counter(
        e.get("type", "unknown") for e in window if e.get("type") != "session_start"
    )
    role_counts: Counter[str] = Counter(
        e.get("role", "unknown") for e in window if e.get("type") != "session_start"
    )

    # Detect checkpoint/handoff entries (boundary was acted on)
    handoff_entries = [
        e for e in window
        if e.get("type") in {"checkpoint"}
        or "handoff" in str(e.get("msg", "")).lower()
        or "fresh" in str(e.get("msg", "")).lower()
    ]

    return {
        "session_ts": session_ts,
        "tasks_completed": tasks_completed,
        "boundary_advisory_threshold_met": boundary_advisory_fired,
        "handoff_written": bool(handoff_entries),
        "type_counts": dict(type_counts),
        "role_counts": dict(role_counts),
        "entry_count": len(window),
    }


# ── Aggregate Metrics ─────────────────────────────────────────────────────────


def aggregate_metrics(sessions: list[dict[str, Any]]) -> dict[str, Any]:
    """Roll up per-session metrics into aggregate statistics."""
    if not sessions:
        return {}

    task_counts = [s["tasks_completed"] for s in sessions]
    advisory_count = sum(1 for s in sessions if s["boundary_advisory_threshold_met"])
    handoff_count = sum(1 for s in sessions if s["handoff_written"])

    # Boundary compliance: sessions where advisory fired AND handoff was written
    advisory_sessions = [s for s in sessions if s["boundary_advisory_threshold_met"]]
    compliant = sum(1 for s in advisory_sessions if s["handoff_written"])
    compliance_rate = compliant / len(advisory_sessions) if advisory_sessions else None

    # Type and role totals across all sessions
    type_total: Counter[str] = Counter()
    role_total: Counter[str] = Counter()
    for s in sessions:
        type_total.update(s["type_counts"])
        role_total.update(s["role_counts"])

    return {
        "total_sessions": len(sessions),
        "total_tasks_completed": sum(task_counts),
        "mean_tasks_per_session": round(sum(task_counts) / len(sessions), 2),
        "max_tasks_in_session": max(task_counts),
        "sessions_with_advisory": advisory_count,
        "advisory_rate_pct": round(100 * advisory_count / len(sessions), 1),
        "handoff_compliance_rate_pct": (
            round(100 * compliance_rate, 1) if compliance_rate is not None else None
        ),
        "type_distribution": dict(type_total.most_common()),
        "role_distribution": dict(role_total.most_common()),
    }


# ── Formatting ────────────────────────────────────────────────────────────────


def fmt_table(rows: list[tuple[str, str]], indent: int = 2) -> str:
    if not rows:
        return ""
    w = max(len(r[0]) for r in rows)
    pad = " " * indent
    return "\n".join(f"{pad}{label:<{w}}  {value}" for label, value in rows)


def print_report(
    per_session: list[dict[str, Any]],
    agg: dict[str, Any],
) -> None:
    print("\n=== Session Interaction Metrics ===\n")

    if not per_session:
        print("  No sessions found in breadcrumbs.")
        return

    # Per-session table
    print("Per-session summary:")
    print(f"  {'#':<4} {'Start':<24} {'Tasks':>6} {'Advisory':>9} {'Handoff':>8} {'Entries':>8}")
    print(f"  {'-'*4} {'-'*24} {'-'*6} {'-'*9} {'-'*8} {'-'*8}")
    for i, s in enumerate(per_session, 1):
        ts = s["session_ts"][:19] if s["session_ts"] else "—"
        adv = "YES" if s["boundary_advisory_threshold_met"] else "—"
        hof = "YES" if s["handoff_written"] else "—"
        print(f"  {i:<4} {ts:<24} {s['tasks_completed']:>6} {adv:>9} {hof:>8} {s['entry_count']:>8}")

    # Aggregate
    print(f"\nAggregate ({agg['total_sessions']} sessions):")
    rows = [
        ("Total tasks completed:", str(agg["total_tasks_completed"])),
        ("Mean tasks / session:", str(agg["mean_tasks_per_session"])),
        ("Max tasks in one session:", str(agg["max_tasks_in_session"])),
        (f"Sessions with advisory (≥{BOUNDARY_THRESHOLD} tasks):",
         f"{agg['sessions_with_advisory']} ({agg['advisory_rate_pct']}%)"),
    ]
    if agg["handoff_compliance_rate_pct"] is not None:
        rows.append((
            "Boundary compliance (advisory→handoff):",
            f"{agg['handoff_compliance_rate_pct']}%",
        ))
    print(fmt_table(rows))

    # Type distribution
    print("\nBreadcrumb type distribution:")
    for typ, count in sorted(agg["type_distribution"].items(), key=lambda x: -x[1]):
        bar = "█" * min(count, 40)
        print(f"  {typ:<20} {count:>5}  {bar}")

    # Role distribution
    print("\nBreadcrumb role distribution:")
    for role, count in sorted(agg["role_distribution"].items(), key=lambda x: -x[1]):
        bar = "█" * min(count, 40)
        print(f"  {role:<20} {count:>5}  {bar}")

    print()


# ── CLI ───────────────────────────────────────────────────────────────────────


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Measure interaction patterns from breadcrumbs.jsonl",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--breadcrumbs",
        type=Path,
        default=DEFAULT_BREADCRUMBS,
        help="Path to breadcrumbs.jsonl (default: .harness/breadcrumbs.jsonl)",
    )
    p.add_argument(
        "--json",
        dest="output_json",
        action="store_true",
        help="Output raw JSON instead of human-readable report",
    )
    p.add_argument(
        "--since",
        metavar="DATE",
        help="Filter sessions starting after this ISO date (e.g. 2026-06-01)",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    entries = load_breadcrumbs(args.breadcrumbs)

    if not entries:
        print(f"No breadcrumbs found at {args.breadcrumbs}", file=sys.stderr)
        sys.exit(0)

    sessions_raw = split_into_sessions(entries)

    # Apply --since filter
    if args.since:
        sessions_raw = [
            s for s in sessions_raw
            if any(e.get("ts", "") >= args.since for e in s)
        ]

    per_session = [session_metrics(s) for s in sessions_raw]
    agg = aggregate_metrics(per_session)

    if args.output_json:
        print(json.dumps({"sessions": per_session, "aggregate": agg}, indent=2))
    else:
        print_report(per_session, agg)


if __name__ == "__main__":
    main()
