#!/usr/bin/env python3
"""
Lean harness context package generator.

Outputs a compact JSON summary of current harness state, ready to inject
into agent prompts for handoffs (evaluator launch, session resume).

Output keys:
  task          — first active task (pending/building/evaluating) or null
  contract      — slice of contract.json or null
  breadcrumbs   — last ≤8 parsed breadcrumb entries
  open_questions — non-RESOLVED/non-DEFERRED open_questions from state.json
"""

import argparse
import json
import sys
from pathlib import Path

_DEFAULT_ROOT = Path.cwd()

_ACTIVE_STATUSES = {"pending", "building", "evaluating"}
_EXCLUDE_PREFIXES = ("RESOLVED", "DEFERRED")

BREADCRUMB_WINDOW = 8


def _resolve_paths(root: Path) -> dict:
    harness = root / ".harness"
    return {
        "state": harness / "state.json",
        "contract": harness / "contract.json",
        "breadcrumbs": harness / "breadcrumbs.jsonl",
    }


def _load_state(path: Path) -> dict:
    """Load state.json — raises SystemExit on missing or invalid."""
    if not path.exists():
        print(f"ERROR: {path} not found", file=sys.stderr)
        raise SystemExit(1)
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as e:
        print(f"ERROR: {path} invalid JSON: {e}", file=sys.stderr)
        raise SystemExit(1)


def _load_json_optional(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def _active_task(state: dict) -> dict | None:
    for task in state.get("tasks", []):
        if task.get("status") in _ACTIVE_STATUSES:
            return {"id": task.get("id"), "name": task.get("name"), "status": task.get("status")}
    return None


def _contract_slice(contract: dict | None) -> dict | None:
    if contract is None:
        return None
    return {
        "task_id": contract.get("task_id"),
        "acceptance_criteria": contract.get("acceptance_criteria", []),
        "phase": contract.get("phase"),
        "verified": contract.get("verified", False),
    }


def _load_breadcrumbs(path: Path) -> list[dict]:
    if not path.exists():
        return []
    lines = [ln for ln in path.read_text().splitlines() if ln.strip()]
    parsed = []
    for ln in lines:
        try:
            parsed.append(json.loads(ln))
        except json.JSONDecodeError:
            continue
    return parsed[-BREADCRUMB_WINDOW:]


def _active_questions(state: dict) -> list[str]:
    return [
        q for q in state.get("open_questions", [])
        if not q.startswith(_EXCLUDE_PREFIXES)
    ]


def build_package(paths: dict) -> dict:
    state = _load_state(paths["state"])
    contract_raw = _load_json_optional(paths["contract"])

    return {
        "task": _active_task(state),
        "contract": _contract_slice(contract_raw),
        "breadcrumbs": _load_breadcrumbs(paths["breadcrumbs"]),
        "open_questions": _active_questions(state),
    }


def _format_markdown(pkg: dict) -> str:
    lines = []

    lines.append("## Current Task")
    if pkg["task"]:
        t = pkg["task"]
        lines.append(f"**{t['id']}** — {t['name']} (`{t['status']}`)")
    else:
        lines.append("(none)")

    lines.append("")
    lines.append("## Acceptance Criteria")
    if pkg["contract"] and pkg["contract"]["acceptance_criteria"]:
        for ac in pkg["contract"]["acceptance_criteria"]:
            lines.append(f"- {ac}")
    else:
        lines.append("(none)")

    lines.append("")
    lines.append("## Recent Breadcrumbs")
    if pkg["breadcrumbs"]:
        for bc in pkg["breadcrumbs"]:
            ts = bc.get("ts", "?")
            role = bc.get("role", "?")
            msg = bc.get("msg", "?")
            result = bc.get("result", "")
            suffix = f" [{result}]" if result else ""
            lines.append(f"- `{ts}` **{role}**: {msg}{suffix}")
    else:
        lines.append("(none)")

    lines.append("")
    lines.append("## Open Questions")
    if pkg["open_questions"]:
        for q in pkg["open_questions"]:
            lines.append(f"- {q}")
    else:
        lines.append("(none)")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Output lean harness context package for agent handoffs."
    )
    parser.add_argument("--format", choices=["json", "markdown"], default="json",
                        help="Output format (default: json)")
    parser.add_argument("--write", type=Path, metavar="PATH",
                        help="Write JSON output to file (in addition to stdout)")
    parser.add_argument("--root", type=Path, default=_DEFAULT_ROOT,
                        help="Repository root (default: auto-detected from script location)")
    args = parser.parse_args()

    paths = _resolve_paths(args.root)

    try:
        pkg = build_package(paths)
    except SystemExit:
        return 1

    if args.format == "markdown":
        print(_format_markdown(pkg))
    else:
        output = json.dumps(pkg, indent=2)
        print(output)
        if args.write:
            args.write.write_text(output + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
