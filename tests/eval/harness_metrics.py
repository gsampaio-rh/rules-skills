#!/usr/bin/env python3
"""Harness effectiveness metrics.

Reads .harness/ state files (breadcrumbs, state, contracts, eval reports)
and produces a unified metrics report covering both harness workflow
effectiveness and rule compliance trends.

Usage:
    python tests/eval/harness_metrics.py              # print + save metrics
    python tests/eval/harness_metrics.py --json       # JSON output only
    python tests/eval/harness_metrics.py --no-save    # print without saving
"""

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

HARNESS_DIR = Path(".harness")
STATE_PATH = HARNESS_DIR / "state.json"
CONTRACT_PATH = HARNESS_DIR / "contract.json"
BREADCRUMBS_PATH = HARNESS_DIR / "breadcrumbs.jsonl"
EVALS_DIR = HARNESS_DIR / "evals"
METRICS_PATH = HARNESS_DIR / "metrics.json"


def load_breadcrumbs() -> list[dict]:
    if not BREADCRUMBS_PATH.exists():
        return []
    entries = []
    for line in BREADCRUMBS_PATH.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return entries


def load_state() -> dict:
    if not STATE_PATH.exists():
        return {}
    try:
        return json.loads(STATE_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def load_contract() -> dict:
    if not CONTRACT_PATH.exists():
        return {}
    try:
        return json.loads(CONTRACT_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def load_eval_reports() -> list[dict]:
    if not EVALS_DIR.exists():
        return []
    reports = []
    for path in sorted(EVALS_DIR.glob("eval-*.json")):
        try:
            reports.append(json.loads(path.read_text()))
        except (json.JSONDecodeError, OSError):
            continue
    return reports


def compute_feature_metrics(state: dict) -> dict:
    features = state.get("features", [])
    status_counts = Counter(f.get("status", "unknown") for f in features)
    completed = status_counts.get("verified", 0) + status_counts.get("committed", 0)
    pending = len(features) - completed
    return {
        "total": len(features),
        "by_status": dict(status_counts),
        "features_completed": completed,
        "features_pending": pending,
        "completion_rate": completed / max(len(features), 1),
    }


def compute_breadcrumb_metrics(breadcrumbs: list[dict]) -> dict:
    if not breadcrumbs:
        return {
            "total_entries": 0,
            "by_role": {},
            "by_type": {},
            "negotiation_rounds": 0,
            "build_evaluate_cycles": 0,
            "scrap_count": 0,
            "scrap_rate": 0.0,
            "features_touched": 0,
        }

    role_counts = Counter(b.get("role", "unknown") for b in breadcrumbs)
    type_counts = Counter(b.get("type", "unknown") for b in breadcrumbs)
    features_seen = {b.get("feat") for b in breadcrumbs if b.get("feat")}

    negotiate_entries = [
        b for b in breadcrumbs if b.get("type") in ("negotiate", "negotiation")
    ]
    eval_entries = [
        b for b in breadcrumbs if b.get("type") in ("eval", "verify")
    ]
    scrap_entries = [b for b in breadcrumbs if b.get("type") == "scrap"]
    total_cycles = max(len(eval_entries), 1)

    return {
        "total_entries": len(breadcrumbs),
        "by_role": dict(role_counts),
        "by_type": dict(type_counts),
        "negotiation_rounds": len(negotiate_entries),
        "build_evaluate_cycles": len(eval_entries),
        "scrap_count": len(scrap_entries),
        "scrap_rate": len(scrap_entries) / total_cycles,
        "features_touched": len(features_seen),
    }


def compute_contract_metrics(contract: dict) -> dict:
    if not contract:
        return {"active": False}

    criteria = contract.get("acceptance_criteria", [])
    edge_cases = contract.get("edge_cases", [])

    return {
        "active": True,
        "feature_id": contract.get("feature_id", "unknown"),
        "phase": contract.get("phase", "unknown"),
        "verified": contract.get("verified", False),
        "criteria_count": len(criteria),
        "edge_case_count": len(edge_cases),
        "negotiation_rounds": contract.get("negotiation_rounds", 0),
        "has_rubrics": bool(contract.get("rubrics")),
    }


def compute_eval_metrics(reports: list[dict]) -> dict:
    if not reports:
        return {"total_reports": 0}

    pass_count = sum(
        1 for r in reports if r.get("verified") or r.get("result") == "pass"
    )

    return {
        "total_reports": len(reports),
        "pass_count": pass_count,
        "fail_count": len(reports) - pass_count,
        "pass_rate": pass_count / max(len(reports), 1),
    }


def build_metrics() -> dict:
    state = load_state()
    contract = load_contract()
    breadcrumbs = load_breadcrumbs()
    eval_reports = load_eval_reports()

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "project": state.get("project", "unknown"),
        "features": compute_feature_metrics(state),
        "breadcrumbs": compute_breadcrumb_metrics(breadcrumbs),
        "contract": compute_contract_metrics(contract),
        "evaluations": compute_eval_metrics(eval_reports),
    }


def print_dashboard(metrics: dict) -> None:
    print("=" * 60)
    print("HARNESS METRICS DASHBOARD")
    print("=" * 60)

    feat = metrics["features"]
    print(f"\n  Project: {metrics['project']}")
    print(f"  Features: {feat['total']} total, {feat['completion_rate']:.0%} complete")
    for status, count in sorted(feat.get("by_status", {}).items()):
        print(f"    {status}: {count}")

    bc = metrics["breadcrumbs"]
    print(f"\n  Breadcrumbs: {bc['total_entries']} entries")
    print(f"    Negotiation rounds: {bc['negotiation_rounds']}")
    print(f"    Build-evaluate cycles: {bc['build_evaluate_cycles']}")
    print(f"    Scrap-and-restart: {bc['scrap_count']}")
    print(f"    Features touched: {bc['features_touched']}")

    ct = metrics["contract"]
    if ct.get("active"):
        print(f"\n  Active Contract: {ct['feature_id']} (phase={ct['phase']})")
        print(f"    Criteria: {ct['criteria_count']}, Edge cases: {ct['edge_case_count']}")
        print(f"    Verified: {ct['verified']}")
    else:
        print("\n  No active contract")

    ev = metrics["evaluations"]
    print(f"\n  Eval Reports: {ev['total_reports']}")
    if ev["total_reports"] > 0:
        print(f"    Pass rate: {ev.get('pass_rate', 0):.0%}")

    print("\n" + "=" * 60)


def main() -> int:
    parser = argparse.ArgumentParser(description="Harness effectiveness metrics")
    parser.add_argument("--json", action="store_true", help="JSON output only")
    parser.add_argument("--no-save", action="store_true", help="Don't save to file")
    args = parser.parse_args()

    metrics = build_metrics()

    if args.json:
        print(json.dumps(metrics, indent=2))
    else:
        print_dashboard(metrics)

    if not args.no_save:
        METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
        METRICS_PATH.write_text(json.dumps(metrics, indent=2) + "\n")
        if not args.json:
            print(f"  Saved to {METRICS_PATH}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
