"""Trajectory tier: deterministic tool-call checks for session evaluation.

Runs between structural and LLM tiers. All checks are deterministic (no API calls).
Sessions without conversation trace return [] (no score impact).

Checks:
  1. Loop detection — repeated identical tool calls
  2. Step efficiency — tool call count vs difficulty range
  3. Read-before-write — Read before Write/StrReplace on same file
  4. Skeleton matching — required tool-call subsequence from scenario YAML
  5. Backtracking ratio — excessive same-file edits
  6. Idle detection — consecutive responses without tool calls
  7. Error recovery — shell errors followed by corrective action
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import PurePosixPath

from tests.eval.session_judge import (
    _extract_shell_commands,
    _extract_tool_calls,
    _has_trace,
)

DIFFICULTY_RANGES: dict[str, tuple[int, int]] = {
    "easy": (5, 25),
    "medium": (10, 50),
    "hard": (20, 100),
}

CRITERION_LOOP = "No repeated identical tool calls"
CRITERION_EFFICIENCY = "Tool call count within difficulty range"
CRITERION_READ_WRITE = "Read before write on same file"
CRITERION_SKELETON = "Trajectory skeleton satisfied"
CRITERION_BACKTRACK = "Edit backtracking ratio acceptable"
CRITERION_IDLE = "No excessive idle turns without tools"
CRITERION_RECOVERY = "Shell errors followed by recovery within 3 steps"

WRITE_TOOLS = {"Write", "StrReplace", "EditNotebook"}
READ_TOOLS = {"Read"}


def _result(criterion: str, passed: bool, evidence: str) -> dict:
    return {
        "criterion": criterion,
        "result": "PASS" if passed else "FAIL",
        "evidence": evidence,
        "tier": "trajectory",
    }


def _args_hash(args: dict | None) -> str:
    """Canonical hash for tool call args (sorted keys JSON)."""
    if not args:
        return ""
    return hashlib.md5(
        json.dumps(args, sort_keys=True, default=str).encode()
    ).hexdigest()[:12]


def _file_path(tc: dict) -> str | None:
    """Extract and normalize file path from a tool call's args."""
    args = tc.get("args") or {}
    path = args.get("path") or args.get("target_notebook") or ""
    if not path:
        return None
    try:
        return str(PurePosixPath(path).name) if "/" in path else path
    except Exception:
        return path


def _iter_timeline(session: dict) -> list[dict]:
    """Ordered timeline of all conversation steps across turns."""
    steps = []
    for turn in session.get("transcript", []):
        for step in turn.get("conversation", []):
            steps.append(step)
    return steps


# --- Check implementations ---


def check_loop(session: dict, rubric: dict) -> dict:
    """Detect consecutive identical tool calls (same name + args hash)."""
    tool_calls = _extract_tool_calls(session)
    if not tool_calls:
        return _result(CRITERION_LOOP, True, "No tool calls in trace")

    max_streak = 1
    current_streak = 1
    streak_tool = ""
    prev_key = None
    for tc in tool_calls:
        key = (tc.get("name", ""), _args_hash(tc.get("args")))
        if key == prev_key:
            current_streak += 1
            if current_streak > max_streak:
                max_streak = current_streak
                streak_tool = tc.get("name", "")
        else:
            current_streak = 1
        prev_key = key

    if max_streak > 2:
        return _result(
            CRITERION_LOOP, False,
            f"{max_streak} consecutive identical {streak_tool}() calls"
        )
    return _result(CRITERION_LOOP, True, f"Max streak: {max_streak}")


def check_efficiency(session: dict, rubric: dict) -> dict:
    """Check total tool calls against difficulty-adjusted range."""
    tool_calls = _extract_tool_calls(session)
    count = len(tool_calls)
    difficulty = rubric.get("difficulty", "medium")
    lo, hi = DIFFICULTY_RANGES.get(difficulty, DIFFICULTY_RANGES["medium"])

    if lo <= count <= hi:
        return _result(
            CRITERION_EFFICIENCY, True,
            f"{count} tool calls within {difficulty} range [{lo}-{hi}]"
        )
    return _result(
        CRITERION_EFFICIENCY, False,
        f"{count} tool calls outside {difficulty} range [{lo}-{hi}]"
    )


def check_read_before_write(session: dict, rubric: dict) -> dict:
    """Verify Read precedes Write/StrReplace for each file."""
    timeline = _iter_timeline(session)
    read_files: set[str] = set()
    violations: list[str] = []

    for step in timeline:
        if step.get("type") != "toolCall":
            continue
        name = step.get("name", "")
        path = _file_path(step)
        if not path:
            continue

        if name in READ_TOOLS:
            read_files.add(path)
        elif name in WRITE_TOOLS and path not in read_files:
            violations.append(f"{name}({path})")

    if violations:
        return _result(
            CRITERION_READ_WRITE, False,
            f"Write without prior Read: {', '.join(violations[:5])}"
        )
    return _result(CRITERION_READ_WRITE, True, "All writes preceded by reads")


def check_skeleton(session: dict, rubric: dict) -> dict | None:
    """Check required tool-call subsequence from scenario YAML."""
    skeleton = rubric.get("trajectory_skeleton")
    if not skeleton:
        return None

    timeline = _iter_timeline(session)
    tool_steps = [s for s in timeline if s.get("type") == "toolCall"]

    skeleton_idx = 0
    matched_labels: list[str] = []

    for step in tool_steps:
        if skeleton_idx >= len(skeleton):
            break

        req = skeleton[skeleton_idx]
        if not _skeleton_step_matches(step, req):
            continue

        after = req.get("after")
        if after and after not in matched_labels:
            continue

        label = _skeleton_label(req)
        matched_labels.append(label)
        skeleton_idx += 1

    if skeleton_idx >= len(skeleton):
        return _result(CRITERION_SKELETON, True, f"All {len(skeleton)} skeleton steps matched")

    missing = skeleton[skeleton_idx]
    return _result(
        CRITERION_SKELETON, False,
        f"Missing skeleton step: {_skeleton_label(missing)} (matched {skeleton_idx}/{len(skeleton)})"
    )


def _skeleton_step_matches(step: dict, req: dict) -> bool:
    """Check if a trace step matches a skeleton requirement."""
    if step.get("name") != req.get("tool"):
        return False
    args = step.get("args") or {}
    path = args.get("path", "") or args.get("target_notebook", "") or ""
    command = args.get("command", "") or ""

    if req.get("path_contains") and req["path_contains"] not in path:
        return False
    if req.get("command_contains") and req["command_contains"] not in command:
        return False
    return True


def _skeleton_label(req: dict) -> str:
    """Human-readable label for a skeleton step."""
    parts = [req.get("tool", "?")]
    if req.get("path_contains"):
        parts.append(req["path_contains"])
    if req.get("command_contains"):
        parts.append(req["command_contains"])
    return " ".join(parts)


def check_backtracking(session: dict, rubric: dict) -> dict:
    """Check ratio of same-file re-edits to total edits."""
    timeline = _iter_timeline(session)
    edit_counts: dict[str, int] = {}
    total_edits = 0

    for step in timeline:
        if step.get("type") != "toolCall":
            continue
        name = step.get("name", "")
        if name not in WRITE_TOOLS:
            continue
        path = _file_path(step)
        if not path:
            continue
        total_edits += 1
        edit_counts[path] = edit_counts.get(path, 0) + 1

    if total_edits == 0:
        return _result(CRITERION_BACKTRACK, True, "No edits in trace")

    backtrack_edits = sum(max(0, c - 1) for c in edit_counts.values())
    ratio = backtrack_edits / total_edits

    if ratio > 0.5:
        worst_file = max(edit_counts, key=edit_counts.get)  # type: ignore[arg-type]
        return _result(
            CRITERION_BACKTRACK, False,
            f"Backtracking ratio {ratio:.0%} ({backtrack_edits}/{total_edits}); "
            f"worst: {worst_file} ({edit_counts[worst_file]} edits)"
        )
    return _result(
        CRITERION_BACKTRACK, True,
        f"Backtracking ratio {ratio:.0%} ({backtrack_edits}/{total_edits})"
    )


def check_idle(session: dict, rubric: dict) -> dict:
    """Detect consecutive response steps without any tool call."""
    max_idle = 0
    current_idle = 0

    for turn in session.get("transcript", []):
        for step in turn.get("conversation", []):
            if step.get("type") == "toolCall":
                current_idle = 0
            elif step.get("type") in ("assistantMessage", "assistantTurn"):
                current_idle += 1
                max_idle = max(max_idle, current_idle)

    if max_idle > 3:
        return _result(
            CRITERION_IDLE, False,
            f"{max_idle} consecutive assistant steps without tool calls"
        )
    return _result(CRITERION_IDLE, True, f"Max idle streak: {max_idle}")


def check_error_recovery(session: dict, rubric: dict) -> dict:
    """Check that shell errors are followed by corrective action within 3 steps."""
    timeline = _iter_timeline(session)
    shell_commands = _extract_shell_commands(session)

    error_indices: list[int] = []
    for i, step in enumerate(timeline):
        if step.get("type") == "shellConversationTurn" and step.get("exit_code", 0) != 0:
            error_indices.append(i)
        elif (step.get("type") == "toolCall" and step.get("name") == "Shell"):
            result = step.get("result") or ""
            result_str = result if isinstance(result, str) else str(result)
            if re.search(r"[Ee]xit[ _]code[:\s]+([1-9]\d*)", result_str):
                error_indices.append(i)

    if not error_indices:
        return _result(CRITERION_RECOVERY, True, "No shell errors in trace")

    unrecovered: list[int] = []
    for err_idx in error_indices:
        window = timeline[err_idx + 1: err_idx + 4]
        recovered = False
        err_step = timeline[err_idx]
        err_cmd = ""
        if err_step.get("type") == "shellConversationTurn":
            err_cmd = err_step.get("command", "")
        elif err_step.get("type") == "toolCall":
            err_cmd = (err_step.get("args") or {}).get("command", "")

        for w in window:
            if w.get("type") != "toolCall":
                continue
            wname = w.get("name", "")
            if wname in READ_TOOLS | WRITE_TOOLS | {"Grep", "Glob", "SemanticSearch", "ReadLints"}:
                recovered = True
                break
            if wname == "Shell":
                w_cmd = (w.get("args") or {}).get("command", "")
                if w_cmd != err_cmd:
                    recovered = True
                    break

        if not recovered:
            unrecovered.append(err_idx)

    if unrecovered:
        return _result(
            CRITERION_RECOVERY, False,
            f"{len(unrecovered)} shell error(s) without recovery within 3 steps"
        )
    return _result(
        CRITERION_RECOVERY, True,
        f"All {len(error_indices)} shell error(s) recovered within 3 steps"
    )


# --- Orchestrator ---


def check_trajectory(session: dict, rubric: dict) -> list[dict]:
    """Run all trajectory checks. Returns [] if no trace or no tool calls."""
    if not _has_trace(session):
        return []
    if not _extract_tool_calls(session):
        return []

    results: list[dict] = []
    for fn in [
        check_loop,
        check_efficiency,
        check_read_before_write,
        check_backtracking,
        check_idle,
        check_error_recovery,
    ]:
        results.append(fn(session, rubric))

    skeleton_result = check_skeleton(session, rubric)
    if skeleton_result is not None:
        results.append(skeleton_result)

    return results
