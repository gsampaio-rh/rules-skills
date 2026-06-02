#!/usr/bin/env python3
"""Tier 3: Post-hoc session judge.

Analyzes completed session results against scenario rubrics using three
signal layers: computational checks, structural checks, and LLM judge.

Usage:
    python tests/eval/session_judge.py                                    # judge all sessions
    python tests/eval/session_judge.py --session sessions/composer-2.5/build-cli-tool.json
    python tests/eval/session_judge.py --tier computational               # fast checks only
    python tests/eval/session_judge.py --tier structural                  # pattern checks only
    python tests/eval/session_judge.py --tier llm                         # LLM judge only
    python tests/eval/session_judge.py --json                             # JSON output

Environment:
    CURSOR_API_KEY    - Required for LLM tier
    JUDGE_MODEL       - Judge model (default: claude-opus-4-6)
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

EVAL_DIR = Path(__file__).parent
SCENARIOS_DIR = EVAL_DIR / "scenarios"
LONG_SCENARIOS_DIR = SCENARIOS_DIR / "long"
EVAL_RESULTS_DIR = EVAL_DIR.parent / "eval_results"


def _resolve_run_dir(run_dir: str | None = None) -> Path:
    """Find the run directory: explicit path, or latest by name."""
    if run_dir:
        return Path(run_dir)
    if not EVAL_RESULTS_DIR.exists():
        return EVAL_RESULTS_DIR / "none"
    runs = sorted(d for d in EVAL_RESULTS_DIR.iterdir() if d.is_dir())
    if not runs:
        return EVAL_RESULTS_DIR / "none"
    return runs[-1]


def load_scenario(scenario_id: str) -> dict | None:
    """Load scenario YAML, trying both underscore and hyphen variants in both dirs."""
    for directory in (SCENARIOS_DIR, LONG_SCENARIOS_DIR):
        for name in (scenario_id, scenario_id.replace("_", "-"), scenario_id.replace("-", "_")):
            path = directory / f"{name}.yaml"
            if path.exists():
                return yaml.safe_load(path.read_text())
    return None


def find_sessions(run_dir: Path, filter_str: str | None = None) -> list[Path]:
    sessions_dir = run_dir / "sessions"
    sessions = []
    if not sessions_dir.exists():
        return sessions
    for path in sorted(sessions_dir.rglob("*.json")):
        if filter_str and filter_str not in path.stem:
            continue
        sessions.append(path)
    return sessions


# ─── Computational Checks ─────────────────────────────────────────────────────

def _task_list(state: dict) -> list:
    return state.get("tasks", [])


VALID_BREADCRUMB_ROLES = {"planner", "builder", "evaluator", "system"}
VALID_BREADCRUMB_TYPES = {
    "plan", "negotiate", "build", "verify", "eval", "checkpoint",
    "decision", "scrap", "init", "session_start", "evaluation",
    "evaluate", "clarify", "progress", "complete", "review",
    "test", "implement", "spike", "gap",
}
ISO_TS_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}")


def _extract_tool_calls(session: dict) -> list[dict]:
    """Extract all tool calls from the conversation trace across all turns.

    Returns a list of dicts with at least {name, args, result, status}.
    Falls back to empty list if no conversation trace was captured.
    """
    calls: list[dict] = []
    for turn in session.get("transcript", []):
        for step in turn.get("conversation", []):
            if step.get("type") == "toolCall":
                calls.append(step)
    return calls


def _extract_shell_commands(session: dict) -> list[dict]:
    """Extract all shell commands from the conversation trace.

    Includes both toolCall(Shell) and shellConversationTurn entries.
    Returns dicts with {command, stdout, stderr, exit_code}.
    """
    commands: list[dict] = []
    for turn in session.get("transcript", []):
        for step in turn.get("conversation", []):
            if step.get("type") == "shellConversationTurn":
                commands.append(step)
            elif step.get("type") == "toolCall" and step.get("name") == "Shell":
                args = step.get("args", {}) or {}
                result = step.get("result") or ""
                commands.append({
                    "command": args.get("command", ""),
                    "stdout": result if isinstance(result, str) else str(result),
                    "stderr": "",
                    "exit_code": 0,
                })
    return commands


def _has_tool_call(session: dict, name: str) -> bool:
    """Check if any tool call with the given name exists in the trace."""
    return any(tc.get("name") == name for tc in _extract_tool_calls(session))


def _has_trace(session: dict) -> bool:
    """Check if conversation trace data was captured for this session."""
    return any(
        turn.get("conversation")
        for turn in session.get("transcript", [])
    )


def _is_negative_harness_scenario(rubric: dict) -> bool:
    """Detect scenarios where harness should NOT activate."""
    compliance = rubric.get("post_hoc_rubric", {}).get("harness_compliance", [])
    negative_signals = ("no .harness", "not activate", "no contract", "no /planner", "no /evaluator")
    return any(
        any(sig in c.lower() for sig in negative_signals)
        for c in compliance
    )


def _get_harness_level(rubric: dict) -> str:
    """Read harness_level from scenario: 'full' (default), 'light', or 'none'.

    'light' skips contract/evaluator/builder checks — use for scenarios
    that test behavioral traits (pushback, autonomy) rather than protocol.
    """
    return rubric.get("harness_level", "full")


def check_harness_compliance(session: dict, rubric: dict) -> list[dict]:
    """Fast, deterministic checks on harness state."""
    results = []
    artifacts = session.get("artifacts", {})
    harness = artifacts.get("harness", {})

    if _is_negative_harness_scenario(rubric):
        return _check_harness_absent(harness)

    level = _get_harness_level(rubric)

    state = harness.get("state.json", {})
    state_tasks = _task_list(state)
    has_state = bool(state and state_tasks)
    results.append({
        "criterion": "Agent created .harness/state.json with tasks",
        "result": "PASS" if has_state else "FAIL",
        "evidence": f"{len(state_tasks)} tasks" if has_state else "No tasks in state",
        "tier": "computational",
    })

    breadcrumbs = harness.get("breadcrumbs.jsonl", [])

    if level == "full":
        contract = harness.get("contract.json", {})
        contract_phase = contract.get("phase", "none")
        contract_verified = contract.get("verified", False)

        has_negotiate = any(
            b.get("type") in ("negotiate", "negotiation")
            for b in breadcrumbs if isinstance(b, dict)
        )
        contract_implies_negotiation = bool(
            contract and contract_phase in ("negotiated", "building", "evaluating", "evaluated", "verified")
        )
        negotiate_pass = has_negotiate or contract_implies_negotiation
        if has_negotiate:
            neg_evidence = "Found negotiate breadcrumb"
        elif contract_implies_negotiation:
            neg_evidence = f"Contract exists at phase={contract_phase} (implies negotiation completed)"
        else:
            neg_evidence = "No negotiate entries in breadcrumbs and no contract"
        results.append({
            "criterion": "Contract negotiation occurred",
            "result": "PASS" if negotiate_pass else "FAIL",
            "evidence": neg_evidence,
            "tier": "computational",
        })

        has_eval = any(
            b.get("type") in ("eval", "verify", "evaluation", "evaluate", "checkpoint")
            or b.get("role") == "evaluator"
            for b in breadcrumbs if isinstance(b, dict)
        )
        contract_implies_eval = contract_phase in ("evaluated", "verified") or contract_verified
        eval_pass = has_eval or contract_implies_eval
        if has_eval:
            eval_evidence = "Found evaluator activity in breadcrumbs"
        elif contract_implies_eval:
            eval_evidence = f"Contract phase={contract_phase}, verified={contract_verified} (implies evaluator ran)"
        else:
            eval_evidence = "No evaluator role or eval-type entries"
        results.append({
            "criterion": "Evaluator was launched",
            "result": "PASS" if eval_pass else "FAIL",
            "evidence": eval_evidence,
            "tier": "computational",
        })

        results.append({
            "criterion": "Contract was verified before completion",
            "result": "PASS" if contract_verified else "FAIL",
            "evidence": f"verified={contract_verified}, phase={contract_phase}",
            "tier": "computational",
        })

    results.extend(_check_breadcrumbs_schema(breadcrumbs))

    if level == "full":
        contract = harness.get("contract.json", {})
        results.extend(_check_phase_progression(contract, breadcrumbs))

    hooks_log = harness.get("hooks.log", "")
    if hooks_log and "contract-gate: DENIED" in hooks_log:
        results.append({
            "criterion": "Hook enforcement active (contract-gate blocked writes)",
            "result": "PASS",
            "evidence": "hooks.log contains DENIED entries — deterministic enforcement worked",
            "tier": "computational",
        })

    return results


def _check_harness_absent(harness: dict) -> list[dict]:
    """For negative scenarios: harness artifacts should NOT exist."""
    results = []
    has_state = bool(harness.get("state.json"))
    results.append({
        "criterion": "No .harness/state.json created (expected for simple task)",
        "result": "PASS" if not has_state else "FAIL",
        "evidence": "state.json absent" if not has_state else "state.json exists unexpectedly",
        "tier": "computational",
    })

    has_contract = bool(harness.get("contract.json"))
    results.append({
        "criterion": "No .harness/contract.json created (expected for simple task)",
        "result": "PASS" if not has_contract else "FAIL",
        "evidence": "contract.json absent" if not has_contract else "contract.json exists unexpectedly",
        "tier": "computational",
    })

    breadcrumbs = harness.get("breadcrumbs.jsonl", [])
    harness_types = {"negotiate", "eval", "plan"}
    harness_activity = [
        b for b in breadcrumbs
        if isinstance(b, dict) and b.get("type") in harness_types
    ]
    results.append({
        "criterion": "No harness workflow activity in breadcrumbs",
        "result": "PASS" if not harness_activity else "FAIL",
        "evidence": "No harness types found" if not harness_activity else f"Found: {[b['type'] for b in harness_activity]}",
        "tier": "computational",
    })

    return results


def _check_breadcrumbs_schema(breadcrumbs: list[dict]) -> list[dict]:
    """Validate breadcrumbs follow the required JSONL schema."""
    results = []
    if not breadcrumbs:
        results.append({
            "criterion": "Breadcrumbs exist (at least 1 entry)",
            "result": "FAIL",
            "evidence": "No breadcrumbs found",
            "tier": "computational",
        })
        return results

    required_fields = {"ts", "role", "type", "msg"}
    schema_errors = []
    for i, b in enumerate(breadcrumbs):
        if not isinstance(b, dict):
            schema_errors.append(f"Line {i}: not a dict")
            continue
        missing = required_fields - set(b.keys())
        if missing:
            schema_errors.append(f"Line {i}: missing {missing}")
        if b.get("role") and b["role"] not in VALID_BREADCRUMB_ROLES:
            schema_errors.append(f"Line {i}: invalid role '{b['role']}'")
        if b.get("type") and b["type"] not in VALID_BREADCRUMB_TYPES:
            schema_errors.append(f"Line {i}: invalid type '{b['type']}'")
        if b.get("ts") and not ISO_TS_PATTERN.match(str(b["ts"])):
            schema_errors.append(f"Line {i}: bad timestamp '{b['ts']}'")

    results.append({
        "criterion": "Breadcrumbs follow JSONL schema (ts, role, type, msg)",
        "result": "PASS" if not schema_errors else "FAIL",
        "evidence": "All entries valid" if not schema_errors else "; ".join(schema_errors[:5]),
        "tier": "computational",
    })

    roles_present = {b.get("role") for b in breadcrumbs if isinstance(b, dict)}
    has_builder = "builder" in roles_present or "planner" in roles_present
    if not has_builder:
        build_types = {b.get("type") for b in breadcrumbs if isinstance(b, dict)}
        has_build_activity = bool(build_types & {"build", "negotiate", "eval", "verify", "checkpoint"})
        if has_build_activity:
            has_builder = True
    results.append({
        "criterion": "Builder or planner role present in breadcrumbs",
        "result": "PASS" if has_builder else "FAIL",
        "evidence": f"Roles found: {sorted(roles_present)}",
        "tier": "computational",
    })

    return results


def _check_phase_progression(contract: dict, breadcrumbs: list[dict]) -> list[dict]:
    """Check that contract phase progressed beyond initial state."""
    results = []
    if not contract:
        return results

    phase = contract.get("phase", "")
    late_phases = {"building", "evaluating", "evaluated", "verified", "negotiated", "committed"}
    progressed = phase in late_phases
    results.append({
        "criterion": "Contract phase progressed beyond 'negotiating'",
        "result": "PASS" if progressed else "FAIL",
        "evidence": f"Current phase: {phase}",
        "tier": "computational",
    })

    types_in_order = [b.get("type") for b in breadcrumbs if isinstance(b, dict)]
    build_types = {"negotiate", "negotiation", "build", "evaluation", "eval", "checkpoint"}
    found_progression = [t for t in types_in_order if t in build_types]
    has_build_activity = any(t in ("build", "evaluation", "eval", "checkpoint") for t in found_progression)
    results.append({
        "criterion": "Breadcrumb types follow logical order (negotiate → build)",
        "result": "PASS" if (has_build_activity and len(found_progression) >= 2) else "FAIL",
        "evidence": f"Type sequence: {found_progression}",
        "tier": "computational",
    })

    return results


def check_contract_quality(session: dict) -> list[dict]:
    """Check contract criteria quality using the contract_lint logic."""
    results = []
    harness = session.get("artifacts", {}).get("harness", {})
    contract = harness.get("contract.json", {})

    if not contract:
        results.append({
            "criterion": "Contract exists",
            "result": "FAIL",
            "evidence": "No contract.json found",
            "tier": "computational",
        })
        return results

    criteria = contract.get("acceptance_criteria", [])
    results.append({
        "criterion": "Acceptance criteria are present",
        "result": "PASS" if len(criteria) >= 3 else "FAIL",
        "evidence": f"{len(criteria)} criteria defined",
        "tier": "computational",
    })

    edge_cases = contract.get("edge_cases", [])
    results.append({
        "criterion": "At least 2 edge cases defined",
        "result": "PASS" if len(edge_cases) >= 2 else "FAIL",
        "evidence": f"{len(edge_cases)} edge cases",
        "tier": "computational",
    })

    vague_patterns = [
        re.compile(r"\b(clean|good|nice|proper|appropriate)\b", re.I),
        re.compile(r"\b(should work|looks? correct)\b", re.I),
    ]
    vague_count = sum(
        1 for c in criteria
        if any(p.search(c) for p in vague_patterns)
    )
    results.append({
        "criterion": "Criteria are binary-testable (not vague)",
        "result": "PASS" if vague_count == 0 else "FAIL",
        "evidence": f"{vague_count} vague criteria detected" if vague_count else "All criteria appear specific",
        "tier": "computational",
    })

    verification = contract.get("verification_method", "")
    has_runnable = bool(verification and len(verification) > 20)
    results.append({
        "criterion": "Verification method is substantive",
        "result": "PASS" if has_runnable else "FAIL",
        "evidence": f"Method: {verification[:80]}..." if has_runnable else "Missing or too short",
        "tier": "computational",
    })

    return results


# ─── Structural Checks ─────────────────────────────────────────────────────────


def check_artifacts(session: dict, rubric: dict) -> list[dict]:
    """Pattern-match checks on produced files, contents, and validations."""
    results = []
    artifacts = session.get("artifacts", {})
    files = artifacts.get("files", [])
    contents = artifacts.get("file_contents", {})
    validations = artifacts.get("validations", [])

    artifact_checks = rubric.get("post_hoc_rubric", {}).get("artifact_quality", [])
    for check_text in artifact_checks:
        passed, evidence = _evaluate_structural_check(
            check_text, files, contents, validations, session,
        )
        results.append({
            "criterion": check_text,
            "result": "PASS" if passed else "FAIL",
            "evidence": evidence,
            "tier": "structural",
        })

    return results


def _evaluate_structural_check(
    check: str,
    files: list[str],
    contents: dict[str, str],
    validations: list[dict],
    session: dict,
) -> tuple[bool, str]:
    """Heuristic evaluation of structural checks against files, contents, and validations."""
    check_lower = check.lower()
    all_content = "\n".join(contents.values())

    # Harness-artifact-aware path: when criterion references .harness/state.json,
    # inspect the parsed harness object directly instead of keyword-matching
    # file contents (avoids false positives from domain term overlap).
    if ".harness/state.json" in check_lower or "harness task" in check_lower:
        harness = session.get("artifacts", {}).get("harness", {})
        passed, evidence = _check_harness_state(check_lower, harness)
        return passed, evidence

    files_changed = session.get("artifacts", {}).get("files_changed", [])
    non_harness_changes = [f for f in files_changed if not f.startswith(".harness") and not f.startswith(".cursor")]
    if check_lower.startswith("if changes were made") or check_lower.startswith("changes address"):
        if not non_harness_changes:
            return True, "No non-harness file changes — conditional check passes vacuously"

    if "typescript" in check_lower and ".js" in check_lower:
        src_files = [f for f in files if f.startswith("src/")]
        js_files = [f for f in src_files if f.endswith(".js")]
        passed = len(js_files) == 0 and len(src_files) > 0
        return passed, f"{len(src_files)} src files, {len(js_files)} .js files"

    if "no .js files" in check_lower:
        src_files = [f for f in files if f.startswith("src/")]
        js = [f for f in src_files if f.endswith(".js")]
        return len(js) == 0, f"Found {len(js)} .js files in src/"

    if _is_validation_check(check_lower):
        passed, evidence = _check_validations(check_lower, validations)
        if passed:
            return True, evidence

    if any(kw in check_lower for kw in ("compiles cleanly", "still parses", "valid python", "syntax")):
        if validations:
            all_pass = all(v.get("status", "PASS") == "PASS" and v.get("exit_code", 0) == 0 for v in validations)
            if all_pass:
                return True, f"All {len(validations)} verify commands passed"
        if contents:
            py_files = [f for f in files if f.endswith(".py")]
            if py_files:
                return True, f"Python files present: {py_files[:3]}"

    if "no other changes" in check_lower:
        non_harness = [f for f in files if not f.startswith(".harness")]
        if len(non_harness) <= 2:
            return True, f"Only {len(non_harness)} non-harness file(s) modified"
        return False, f"{len(non_harness)} files modified (expected minimal changes)"

    file_extensions = re.findall(r"\.\w+", check)
    if file_extensions:
        found = [
            ext for ext in file_extensions
            if any(f.endswith(ext) for f in files)
        ]
        if found:
            return True, f"Extensions found: {found}"

    passed, evidence = _check_content(check_lower, all_content, contents)
    if passed:
        return True, evidence

    transcript = session.get("transcript", [])
    transcript_text = "\n".join(
        t.get("response", "") for t in transcript if t.get("response")
    )
    if transcript_text:
        passed, evidence = _check_content(
            check_lower, transcript_text, {"transcript": transcript_text},
        )
        if passed:
            return True, evidence

    if _has_trace(session):
        tool_calls = _extract_tool_calls(session)
        tool_text = " ".join(
            f"{tc.get('name', '')} {json.dumps(tc.get('args', {}), default=str)[:200]} {str(tc.get('result', ''))[:200]}"
            for tc in tool_calls
        )
        passed, evidence = _check_content(
            check_lower, tool_text, {"tool_calls": tool_text},
        )
        if passed:
            return True, f"Trace: {evidence}"

    return False, "No matching heuristic"


def _is_validation_check(check: str) -> bool:
    return any(kw in check for kw in ("test", "pytest", "npm test", "passes", "exit code", "parse", "compile", "valid"))


def _check_validations(check: str, validations: list[dict]) -> tuple[bool, str]:
    if not validations:
        return False, "No validation commands were run"

    def _v_passed(v: dict) -> bool:
        status = v.get("status", "").upper()
        if status in ("PASS", "FAIL"):
            return status == "PASS"
        return v.get("exit_code") == 0

    all_pass = all(_v_passed(v) for v in validations)
    if "pass" in check or "exit code 0" in check:
        summary = "; ".join(
            f"{v['command'][:60]}→{v.get('status', v.get('exit_code'))}" for v in validations
        )
        return all_pass, f"Validations: {summary}"

    for v in validations:
        cmd = v.get("command", "")
        if any(kw in cmd for kw in ("pytest", "test", "npm test")):
            return _v_passed(v), f"{cmd} → {v.get('status', v.get('exit_code'))}"

    return False, "No matching validation found"



def _check_content(check: str, all_content: str, contents: dict[str, str]) -> tuple[bool, str]:
    backtick_kws = re.findall(r"`([^`]+)`", check)
    quoted_kws = re.findall(r"['\"]([^'\"]+)['\"]", check)
    flag_kws = re.findall(r"(--[\w-]+)", check)

    keywords = backtick_kws or quoted_kws or flag_kws
    if not keywords:
        stop_words = {"the", "and", "with", "that", "from", "main", "file", "exists", "present", "handling", "script", "handles"}
        tokens = [w for w in check.split() if len(w) > 3 and w.lower() not in stop_words]
        keywords = tokens[:3]

    if not keywords:
        return False, "Could not extract keywords from check"

    all_lower = all_content.lower()
    found_in: list[str] = []
    for kw in keywords:
        kw_lower = kw.lower()
        for path, text in contents.items():
            if kw_lower in text.lower():
                found_in.append(f"'{kw}' in {path}")
                break

    if found_in:
        return True, "; ".join(found_in)
    return False, f"Keywords {keywords} not found in file contents"


def _check_harness_state(check: str, harness: dict) -> tuple[bool, str]:
    """Check criteria that reference .harness/state.json using the parsed harness object."""
    state = harness.get("state.json", {})
    if isinstance(state, dict) and "_error" in state:
        return False, f"state.json parse error: {state['_error']}"

    if not state:
        return False, ".harness/state.json not found or empty"

    tasks = state.get("tasks", [])

    if "tasks" in check and ("array" in check or "contains" in check or "task objects" in check):
        if not tasks:
            return False, "state.json has no tasks"
        has_fields = all("id" in t and "name" in t for t in tasks)
        return has_fields, f"state.json has {len(tasks)} task(s), fields present: {has_fields}"

    if "vision" in check or "project" in check:
        has_vision = "vision" in state or "project" in state
        return has_vision, f"vision={'vision' in state}, project={'project' in state}"

    if "schema_version" in check:
        sv = state.get("schema_version")
        return sv == 2, f"schema_version={sv}"

    if "valid json" in check or "remains valid" in check:
        return True, "state.json parsed successfully as valid JSON"

    if "preserved" in check or "lost" in check:
        backtick_fields = re.findall(r"`([^`]+)`", check)
        if backtick_fields:
            missing = [f for f in backtick_fields if f not in state]
            return len(missing) == 0, f"present: {[f for f in backtick_fields if f in state]}, missing: {missing}"
        return bool(state), f"state.json has {len(state)} top-level keys"

    if "duplicate" in check:
        ids = [t.get("id") for t in tasks]
        dupes = len(ids) != len(set(ids))
        return not dupes, f"task ids: {ids}, unique: {not dupes}"

    if "status" in check and ("enum" in check or "valid" in check):
        valid_status = {"pending", "building", "evaluating", "verified", "committed", "cancelled"}
        valid_type = {"feature", "fix", "bug", "gap", "spike", "chore"}
        bad = [t for t in tasks if t.get("status") not in valid_status or t.get("type") not in valid_type]
        return len(bad) == 0, f"{len(tasks)} tasks, {len(bad)} with invalid enum values"

    backtick_ids = re.findall(r"`(feat-\d+|gap-\d+|spike-\d+|chore-\d+)`", check)
    if backtick_ids:
        task_ids = {t.get("id") for t in tasks}
        found = [tid for tid in backtick_ids if tid in task_ids]
        missing = [tid for tid in backtick_ids if tid not in task_ids]
        if "progressed" in check or "advanced" in check or "beyond" in check:
            for tid in backtick_ids:
                t = next((t for t in tasks if t.get("id") == tid), None)
                if t and t.get("status") == "pending":
                    return False, f"{tid} still pending"
            return True, f"{backtick_ids} all advanced past pending"
        return len(missing) == 0, f"found: {found}, missing: {missing}"

    if "breadcrumbs" in check:
        bc = harness.get("breadcrumbs.jsonl", [])
        return bool(bc), f"breadcrumbs.jsonl has {len(bc)} entries"

    return bool(state and tasks), f"state.json exists with {len(tasks)} task(s)"


# ─── Behavioral Checks ────────────────────────────────────────────────────────


def check_behavioral(session: dict, rubric: dict) -> list[dict]:
    """Check transcript behavioral patterns."""
    results = []
    transcript = session.get("transcript", [])
    full_text = " ".join(
        t.get("response", "") for t in transcript if t.get("response")
    )

    has_trace = _has_trace(session)
    behavioral_checks = rubric.get("post_hoc_rubric", {}).get("behavioral", [])
    for check_text in behavioral_checks:
        passed = _evaluate_behavioral(check_text, full_text, session)
        evidence = "Trace-verified" if has_trace and passed else (
            "Pattern-based heuristic (no trace)" if not has_trace else "Pattern-based heuristic"
        )
        results.append({
            "criterion": check_text,
            "result": "PASS" if passed else "UNCERTAIN",
            "evidence": evidence,
            "tier": "structural",
        })

    return results


def _evaluate_behavioral(check: str, transcript_text: str, session: dict) -> bool:
    check_lower = check.lower()

    if "no apolog" in check_lower:
        apology_patterns = re.compile(r"\b(i'm sorry|i apologize|sorry about)\b", re.I)
        return not apology_patterns.search(transcript_text)

    if "autonomously" in check_lower or "autonomous" in check_lower:
        if _has_trace(session):
            shell_cmds = _extract_shell_commands(session)
            action_tools = {"Shell", "ReadLints"}
            has_action_tool = any(
                tc.get("name") in action_tools for tc in _extract_tool_calls(session)
            )
            return has_action_tool or len(shell_cmds) >= 1
        action_indicators = ["Running", "Executing", "Installing", "npm", "pip", "make", "pytest", "python"]
        return any(ind in transcript_text for ind in action_indicators)

    if "breadcrumbs" in check_lower and "complete" in check_lower:
        harness = session.get("artifacts", {}).get("harness", {})
        breadcrumbs = harness.get("breadcrumbs.jsonl", [])
        return len(breadcrumbs) >= 3

    if "shall i proceed" in check_lower or "should i" in check_lower:
        proceed_patterns = re.compile(r"\b(shall I proceed|should I|want me to|would you like me to)\b", re.I)
        return not proceed_patterns.search(transcript_text)

    if "directly" in check_lower and ("without" in check_lower or "no" in check_lower):
        proceed_patterns = re.compile(r"\b(shall I proceed|should I|want me to)\b", re.I)
        return not proceed_patterns.search(transcript_text)

    if "no todowrite" in check_lower:
        return "TodoWrite" not in transcript_text

    if "todowrite" in check_lower or "progress track" in check_lower:
        if _has_trace(session):
            has_todowrite = _has_tool_call(session, "TodoWrite")
            if has_todowrite:
                return True
        harness = session.get("artifacts", {}).get("harness", {})
        breadcrumbs = harness.get("breadcrumbs.jsonl", [])
        has_build_entries = sum(
            1 for b in breadcrumbs
            if isinstance(b, dict) and b.get("type") == "build"
        )
        return has_build_entries >= 2 or "TodoWrite" in transcript_text

    if "push back" in check_lower or "pushback" in check_lower:
        clarify_patterns = re.compile(
            r"\b(clarif|what do you mean|could you specify|more specific|narrow|"
            r"before (I|we) (start|begin|implement|make)|let me (understand|scope|define)|"
            r"what (specifically|exactly|areas|aspects)|I.d (suggest|recommend)|"
            r"here.s (what|my plan)|focus on|propose|could you (elaborate|tell me more)|"
            r"what (kind of|type of) improvement)\b", re.I,
        )
        pushed_back = bool(clarify_patterns.search(transcript_text))
        if "scoped contract" in check_lower or "then proposed" in check_lower:
            contract = session.get("artifacts", {}).get("harness", {}).get("contract.json")
            return pushed_back and contract is not None
        return pushed_back

    if "scoped contract" in check_lower or "deliberate scoping" in check_lower:
        contract = session.get("artifacts", {}).get("harness", {}).get("contract.json")
        if not contract:
            return False
        criteria = contract.get("acceptance_criteria", [])
        return len(criteria) >= 2 and len(criteria) <= 8

    if "off-plan" in check_lower or "out of scope" in check_lower or "defer" in check_lower:
        defer_patterns = re.compile(
            r"\b(defer|later|out of scope|off.?plan|not in the current|backlog|"
            r"park (that|this|it)|note (that|this|it) for|after (we|I) (finish|complete)|"
            r"separate task|new task|future|deviat|outside.*scope|"
            r"scope creep|tangential|unrelated to|not part of|"
            r"add (it|them|this|that) (to|as).*task|"
            r"(focus|stay|continue|stick) (on|with) (the |feat|current)|"
            r"let.s (finish|complete|focus))\b", re.I,
        )
        return bool(defer_patterns.search(transcript_text))

    if "abandon" in check_lower or "derail" in check_lower or "not derail" in check_lower:
        harness = session.get("artifacts", {}).get("harness", {})
        contract = harness.get("contract.json", {})
        state = harness.get("state.json", {})
        tasks = state.get("tasks", [])
        building = [t for t in tasks if t.get("status") == "building"]
        if contract and building:
            return contract.get("task_id") == building[0].get("id")
        return bool(building)

    if "follow" in check_lower and ("priority" in check_lower or "order" in check_lower):
        harness = session.get("artifacts", {}).get("harness", {})
        breadcrumbs = harness.get("breadcrumbs.jsonl", [])
        build_feats = [
            b.get("feat") for b in breadcrumbs
            if isinstance(b, dict) and b.get("type") == "build" and b.get("feat")
        ]
        if len(build_feats) < 2:
            return "TodoWrite" in transcript_text or len(build_feats) == 1
        for i in range(len(build_feats) - 1):
            a, b = build_feats[i], build_feats[i + 1]
            if a and b and a > b:
                return False
        return True

    if "proactively updated" in check_lower and "plan" in check_lower:
        harness = session.get("artifacts", {}).get("harness", {})
        state = harness.get("state.json", {})
        trade_offs = state.get("trade_offs", [])
        direction = state.get("direction", "")
        has_update = len(trade_offs) > 1 or "dedup" in direction.lower() or "index" in direction.lower()
        breadcrumbs = harness.get("breadcrumbs.jsonl", [])
        discovery_crumb = any(
            isinstance(b, dict) and any(
                w in b.get("msg", "").lower()
                for w in ("discover", "trade", "update", "revis", "storage", "constraint")
            )
            for b in breadcrumbs
        )
        return has_update or discovery_crumb

    if "did not modify" in check_lower or "not refactor" in check_lower:
        if _has_trace(session):
            write_calls = [
                tc for tc in _extract_tool_calls(session)
                if tc.get("name") in ("Write", "StrReplace")
            ]
            return len(write_calls) == 0
        artifacts = session.get("artifacts", {})
        files = artifacts.get("files", [])
        return len(files) <= 1

    if "verif" in check_lower and ("syntax" in check_lower or "import" in check_lower or "test" in check_lower):
        if _has_trace(session):
            shell_cmds = _extract_shell_commands(session)
            verify_cmd_patterns = ("pytest", "python -c", "python -m", "npm test", "tsc", "py_compile", "ruff", "eslint", "make test")
            for cmd in shell_cmds:
                cmd_text = cmd.get("command", "")
                if any(p in cmd_text for p in verify_cmd_patterns):
                    return True
            if _has_tool_call(session, "ReadLints"):
                return True
        verify_patterns = ["py_compile", "import ", "pytest", "python -c", "npm test", "tsc"]
        return any(p in transcript_text for p in verify_patterns)

    if "fresh thread" in check_lower or "session boundary" in check_lower or ("checkpoint" in check_lower and "task" in check_lower):
        boundary_patterns = re.compile(
            r"\b(fresh thread|new session|new chat|checkpoint|let.?s commit|"
            r"(I.ll|let me|should (we |I )?)commit|commit (the|these|this|current|before)|"
            r"before (we )?(continue|move on|proceed|adding)|wrap.*(up|this)|"
            r"suggest(ing)? (we )?(start|switch|open)|hand.?off|"
            r"save.*(progress|work)|separate.*(session|thread))\b", re.I,
        )
        return bool(boundary_patterns.search(transcript_text))

    if "silently accept all" in check_lower or "without pausing" in check_lower:
        boundary_patterns = re.compile(
            r"\b(fresh thread|new session|checkpoint|commit first|let.?s commit|"
            r"(I.ll|let me) commit|hand.?off|too many|accumulating|scope creep|"
            r"pause|break|before.*(continu|proceed|mov)|wrap.*up|"
            r"getting (large|big)|a lot of changes|separate)\b", re.I,
        )
        return bool(boundary_patterns.search(transcript_text))

    if "evaluator" in check_lower and ("not modify source" in check_lower or "did not modify source" in check_lower):
        artifacts = session.get("artifacts", {})
        files = artifacts.get("files", [])
        non_harness_files = [f for f in files if not f.startswith(".harness/") and not f.startswith(".harness\\")]
        return len(non_harness_files) == 0

    if "focused summary" in check_lower or ("not produce" in check_lower and "exploration" in check_lower):
        transcript = session.get("transcript", [])
        if transcript:
            first_response = next(
                (t.get("response", "") for t in transcript if t.get("response")),
                "",
            )
            return len(first_response.split()) < 800

    if ("read breadcrumbs" in check_lower or "read state" in check_lower) and "first" in check_lower:
        if _has_trace(session):
            first_turn = session.get("transcript", [{}])[0]
            early_calls = first_turn.get("conversation", [])[:10]
            read_calls = [
                c for c in early_calls
                if c.get("type") == "toolCall" and c.get("name") == "Read"
            ]
            target_files = ("breadcrumbs", "state.json")
            for rc in read_calls:
                args = rc.get("args", {}) or {}
                path = args.get("path", "") if isinstance(args, dict) else str(args)
                if any(t in path for t in target_files):
                    return True
        transcript = session.get("transcript", [])
        early_text = " ".join(
            t.get("response", "") for t in transcript[:3] if t.get("response")
        )
        return "breadcrumb" in early_text.lower() or "state.json" in early_text.lower() or "pending" in early_text.lower()

    if "full project exploration" in check_lower or "readme-style" in check_lower:
        transcript = session.get("transcript", [])
        if transcript:
            first_response = next(
                (t.get("response", "") for t in transcript if t.get("response")),
                "",
            )
            return len(first_response.split()) < 800

    if "asked what to work on" in check_lower or "suggesting starting" in check_lower:
        work_patterns = re.compile(
            r"\b(what (would you|do you want|should).*(work|start|focus|tackle)|"
            r"want to (start|work|continue|pick up)|"
            r"suggest.*(start|work|feat|next)|"
            r"shall (we|I).*(start|begin|work|continue))\b", re.I,
        )
        return bool(work_patterns.search(transcript_text))

    if "proposed" in check_lower and "plan" in check_lower:
        plan_patterns = re.compile(
            r"\b(here.s (what|my)|plan:|approach:|strategy:|phase \d|step \d|"
            r"I.ll (start|begin|first)|first.*(then|next)|1\.|(\d)\))\b", re.I,
        )
        return bool(plan_patterns.search(transcript_text))

    if "presented" in check_lower and "option" in check_lower:
        option_patterns = re.compile(
            r"\b(option [A-C1-3]|approach \d|alternative|layout \d|"
            r"design [A-C1-3]|could (go with|choose|pick)|"
            r"here are (some|a few|two|three)|which (do you|would you))\b", re.I,
        )
        return bool(option_patterns.search(transcript_text))

    if "contract" in check_lower and ("negotiat" in check_lower or "before implementation" in check_lower):
        contract_patterns = re.compile(
            r"\b(contract\.json|\.harness/contract|acceptance.criteria|"
            r"negotiat|propose.*(contract|criteria)|"
            r"write.*(contract|criteria).*before|evaluator.*(negotiat|review))\b", re.I,
        )
        harness = session.get("artifacts", {}).get("harness", {})
        has_contract = bool(harness.get("contract.json"))
        return has_contract or bool(contract_patterns.search(transcript_text))

    if "identified" in check_lower and "complexity" in check_lower:
        complexity_patterns = re.compile(
            r"\b(touch(es|ing)?\s+\d+\s+file|multiple file|several file|"
            r"non.?trivial|complex(ity)?|architectural|"
            r"across\s+(all|multiple|several)|harness|state\.json)\b", re.I,
        )
        return bool(complexity_patterns.search(transcript_text))

    return True


# ─── Skill Activation Checks ─────────────────────────────────────────────────


def check_skill_activation(session: dict, rubric: dict) -> list[dict]:
    """Check if the correct skill was activated based on rubric's skill_activation category."""
    results = []
    skill_checks = rubric.get("post_hoc_rubric", {}).get("skill_activation", [])
    if not skill_checks:
        return results

    transcript = session.get("transcript", [])
    full_text = " ".join(
        t.get("response", "") for t in transcript if t.get("response")
    )
    artifacts = session.get("artifacts", {})
    harness = artifacts.get("harness", {})

    for check_text in skill_checks:
        check_lower = check_text.lower()
        passed = True
        evidence = "Pattern-based heuristic"

        if "code-review" in check_lower or "code review" in check_lower:
            review_indicators = ["severity", "finding", "vulnerability", "issue", "bug", "security"]
            found = [ind for ind in review_indicators if ind in full_text.lower()]
            passed = len(found) >= 2
            evidence = f"Review indicators found: {found}" if found else "No review structure detected"

        elif "no harness" in check_lower:
            has_contract = bool(harness.get("contract.json"))
            passed = not has_contract
            evidence = "No harness ceremony" if not has_contract else "Harness activated unexpectedly"

        elif "security" in check_lower and "priorit" in check_lower:
            security_terms = ["sql injection", "xss", "hash", "md5", "secret", "hardcoded", "parameterized"]
            found = [t for t in security_terms if t in full_text.lower()]
            passed = len(found) >= 2
            evidence = f"Security terms: {found}" if found else "Security issues not highlighted"

        results.append({
            "criterion": check_text,
            "result": "PASS" if passed else "FAIL",
            "evidence": evidence,
            "tier": "structural",
        })

    return results


# ─── Design Compliance Checks ─────────────────────────────────────────────────


def check_design_compliance(session: dict, rubric: dict) -> list[dict]:
    """Check frontend design patterns in produced artifacts and file contents."""
    results = []
    design_checks = rubric.get("post_hoc_rubric", {}).get("design_compliance", [])
    if not design_checks:
        return results

    artifacts = session.get("artifacts", {})
    contents = artifacts.get("file_contents", {})
    all_content = "\n".join(contents.values()).lower()

    for check_text in design_checks:
        check_lower = check_text.lower()
        passed = False
        evidence = "No matching pattern"

        if "custom propert" in check_lower or "var(--" in check_lower or "--color" in check_lower:
            token_hits = re.findall(r"var\(--[\w-]+\)", all_content)
            raw_defs = re.findall(r"--[\w-]+\s*:", all_content)
            total = len(token_hits) + len(raw_defs)
            passed = total >= 3
            evidence = f"{len(raw_defs)} definitions, {len(token_hits)} usages" if passed else f"Only {total} token references found"

        elif "spacing" in check_lower and ("8px" in check_lower or "grid" in check_lower or "multiple" in check_lower):
            spacing_vals = re.findall(r":\s*(\d+)px", all_content)
            multiples_of_4 = [v for v in spacing_vals if int(v) % 4 == 0 and int(v) > 0]
            ratio = len(multiples_of_4) / max(len(spacing_vals), 1)
            passed = ratio >= 0.5 and len(multiples_of_4) >= 3
            evidence = f"{len(multiples_of_4)}/{len(spacing_vals)} spacing values are 4px-grid multiples"

        elif "typography" in check_lower and ("scale" in check_lower or "token" in check_lower or "font" in check_lower):
            valid_sizes = {"12px", "14px", "16px", "20px", "24px", "32px"}
            font_sizes = re.findall(r"font-size\s*:\s*(\d+px)", all_content)
            token_defs = re.findall(r"--font-size[\w-]*:\s*(\d+px)", all_content)
            token_refs = re.findall(r"var\(--font-size", all_content)
            all_sizes = font_sizes + token_defs
            on_scale = [s for s in all_sizes if s in valid_sizes]
            passed = len(on_scale) >= 2 or len(token_refs) >= 2
            evidence = f"Font sizes on scale: {on_scale}, token refs: {len(token_refs)}"

        elif "color" in check_lower and "palette" in check_lower:
            palette = ["#2563eb", "#3b82f6", "#1d4ed8", "#7c3aed",
                       "#f8fafc", "#f1f5f9", "#e2e8f0", "#cbd5e1",
                       "#64748b", "#334155", "#0f172a",
                       "#16a34a", "#d97706", "#dc2626", "#0891b2"]
            used_colors = re.findall(r"#[0-9a-f]{6}", all_content)
            on_palette = [c for c in used_colors if c in palette]
            off_palette = [c for c in used_colors if c not in palette and c != "#000000" and c != "#ffffff"]
            passed = len(on_palette) >= 3 and len(off_palette) <= len(on_palette)
            evidence = f"{len(on_palette)} on-palette, {len(off_palette)} off-palette colors"

        elif "touch" in check_lower or "44px" in check_lower or ("interactive" in check_lower and "siz" in check_lower):
            min_heights = re.findall(r"min-height\s*:\s*(\d+)px", all_content)
            large_enough = [s for s in min_heights if 44 <= int(s) <= 200]
            explicit_heights = re.findall(r"(?:width|height)\s*:\s*(\d+)px", all_content)
            large_explicit = [s for s in explicit_heights if 44 <= int(s) <= 200]
            token_defs = dict(re.findall(r"--(spacing-[\w-]+)\s*:\s*(\d+)px", all_content))
            token_heights = re.findall(r"(?:width|height)\s*:\s*var\(--(spacing-[\w-]+)\)", all_content)
            large_tokens = [t for t in token_heights if int(token_defs.get(t, "0")) >= 44]
            padding_hits = re.findall(r"padding\s*:\s*(\d+)px", all_content)
            generous_padding = [p for p in padding_hits if int(p) >= 12]
            total_large = len(large_enough) + len(large_explicit) + len(large_tokens)
            passed = total_large >= 1 or len(generous_padding) >= 2
            evidence = f"min-height>=44: {large_enough}, explicit>=44: {large_explicit}, token-resolved>=44: {large_tokens}, padding>=12: {len(generous_padding)}"

        elif "breakpoint" in check_lower or "responsive" in check_lower:
            media_queries = re.findall(r"min-width:\s*(\d+)px", all_content)
            target_bps = {"768", "1024"}
            found_bps = target_bps.intersection(set(media_queries))
            passed = len(found_bps) >= 1
            evidence = f"Breakpoints found: {sorted(set(media_queries))}" if media_queries else "No @media breakpoints"

        elif "<nav>" in check_lower or ("nav" in check_lower and "collaps" in check_lower):
            html_content = "\n".join(v for k, v in contents.items() if k.endswith(".html")).lower()
            has_nav = "<nav" in html_content
            has_collapse = any(kw in all_content for kw in ("is-open", "is-active", "collapse", "toggle", "translatex", "display: none"))
            passed = has_nav and has_collapse
            evidence = f"<nav>: {has_nav}, collapse mechanism: {has_collapse}"

        elif "no" in check_lower and "style=" in check_lower and "inline" in check_lower:
            html_content = "\n".join(v for k, v in contents.items() if k.endswith(".html"))
            inline_styles = re.findall(r'\bstyle\s*=\s*["\']', html_content)
            passed = len(inline_styles) == 0
            evidence = f"0 inline style= attributes" if passed else f"{len(inline_styles)} inline style= found"

        results.append({
            "criterion": check_text,
            "result": "PASS" if passed else "FAIL",
            "evidence": evidence,
            "tier": "structural",
        })

    return results


# ─── Long Scenario Checks ─────────────────────────────────────────────────────


def check_long_scenario(session: dict, rubric: dict) -> list[dict]:
    """Additional checks for long-running scenarios: coherence, breadcrumb density, multi-contract, recovery."""
    long_rubric = rubric.get("post_hoc_rubric", {}).get("long_scenario", {})
    if not long_rubric:
        return []

    results = []
    artifacts = session.get("artifacts", {})
    harness = artifacts.get("harness", {})
    breadcrumbs = harness.get("breadcrumbs.jsonl", [])
    transcript = session.get("transcript", [])
    full_text = " ".join(
        t.get("response", "") for t in transcript if t.get("response")
    )

    results.extend(_check_breadcrumb_density(breadcrumbs, long_rubric))
    results.extend(_check_multi_contract(breadcrumbs, harness, long_rubric))
    results.extend(_check_coherence(full_text, artifacts, long_rubric))
    results.extend(_check_recovery(full_text, breadcrumbs, harness, long_rubric))

    return results


def _check_breadcrumb_density(breadcrumbs: list[dict], long_rubric: dict) -> list[dict]:
    """Verify enough breadcrumbs were written across the session."""
    results = []
    density_config = long_rubric.get("breadcrumb_density", {})
    if not density_config:
        return results

    min_entries = density_config.get("min_entries", 4)
    count = len([b for b in breadcrumbs if isinstance(b, dict)])
    results.append({
        "criterion": f"Breadcrumb density: at least {min_entries} entries across session",
        "result": "PASS" if count >= min_entries else "FAIL",
        "evidence": f"{count} breadcrumbs found (min: {min_entries})",
        "tier": "computational",
    })

    roles = {b.get("role") for b in breadcrumbs if isinstance(b, dict)}
    types = {b.get("type") for b in breadcrumbs if isinstance(b, dict)}
    has_variety = len(types) >= 2
    results.append({
        "criterion": "Breadcrumbs show variety (multiple types/phases)",
        "result": "PASS" if has_variety else "FAIL",
        "evidence": f"Roles: {sorted(roles)}, Types: {sorted(types)}",
        "tier": "computational",
    })

    return results


def _check_multi_contract(breadcrumbs: list[dict], harness: dict, long_rubric: dict) -> list[dict]:
    """Verify each feature had its own contract cycle."""
    results = []
    contract_checks = long_rubric.get("multi_contract", [])
    if not contract_checks:
        return results

    negotiate_entries = [
        b for b in breadcrumbs
        if isinstance(b, dict) and b.get("type") in ("negotiate", "negotiation")
    ]

    state = harness.get("state.json", {})
    tasks = _task_list(state)
    task_count = len(tasks) if isinstance(tasks, list) else 0

    for check_text in contract_checks:
        check_lower = check_text.lower()

        if ("each feature" in check_lower or "each task" in check_lower) and "contract" in check_lower:
            passed = len(negotiate_entries) >= max(task_count - 1, 1)
            results.append({
                "criterion": check_text,
                "result": "PASS" if passed else "FAIL",
                "evidence": f"{len(negotiate_entries)} negotiate entries for {task_count} tasks",
                "tier": "computational",
            })
        elif "progression" in check_lower or "pending" in check_lower:
            statuses = [t.get("status", "") for t in tasks if isinstance(t, dict)]
            has_progression = any(s in ("verified", "committed", "building") for s in statuses)
            results.append({
                "criterion": check_text,
                "result": "PASS" if has_progression else "FAIL",
                "evidence": f"Feature statuses: {statuses}",
                "tier": "computational",
            })
        else:
            results.append({
                "criterion": check_text,
                "result": "UNCERTAIN",
                "evidence": "Requires LLM evaluation",
                "tier": "structural",
            })

    return results


def _check_coherence(full_text: str, artifacts: dict, long_rubric: dict) -> list[dict]:
    """Check that later features don't break earlier ones."""
    results = []
    coherence_checks = long_rubric.get("coherence", [])
    if not coherence_checks:
        return results

    contents = artifacts.get("file_contents", {})
    all_content = "\n".join(contents.values())
    validations = artifacts.get("validations", [])

    for check_text in coherence_checks:
        check_lower = check_text.lower()

        if "regress" in check_lower or "break" in check_lower or "did not break" in check_lower:
            all_validations_pass = all(v.get("exit_code") == 0 for v in validations) if validations else False
            no_error_in_transcript = "error" not in full_text.lower()[-500:]
            passed = all_validations_pass or no_error_in_transcript
            results.append({
                "criterion": check_text,
                "result": "PASS" if passed else "UNCERTAIN",
                "evidence": "Validations pass or no errors in final output" if passed else "Could not confirm non-regression",
                "tier": "structural",
            })
        elif "integrat" in check_lower or "uses" in check_lower or "same" in check_lower:
            keywords = re.findall(r"\b\w{4,}\b", check_lower)
            domain_kws = [k for k in keywords if k not in ("from", "with", "that", "feature", "plugin", "system", "endpoint")]
            found = sum(1 for kw in domain_kws[:4] if kw in all_content.lower())
            passed = found >= len(domain_kws[:4]) // 2
            results.append({
                "criterion": check_text,
                "result": "PASS" if passed else "UNCERTAIN",
                "evidence": f"Found {found}/{len(domain_kws[:4])} domain keywords in code" if found else "Requires LLM evaluation",
                "tier": "structural",
            })
        else:
            results.append({
                "criterion": check_text,
                "result": "UNCERTAIN",
                "evidence": "Requires LLM evaluation for coherence check",
                "tier": "structural",
            })

    return results


def _check_recovery(full_text: str, breadcrumbs: list[dict], harness: dict, long_rubric: dict) -> list[dict]:
    """Check resilience/recovery patterns for scenarios with seeded bugs."""
    results = []
    recovery_checks = long_rubric.get("recovery", [])
    if not recovery_checks:
        return results

    for check_text in recovery_checks:
        check_lower = check_text.lower()

        if "detected" in check_lower and ("error" in check_lower or "import" in check_lower or "bug" in check_lower):
            fix_indicators = ["fix", "error", "import", "traceback", "ModuleNotFoundError", "KeyError"]
            found = [ind for ind in fix_indicators if ind.lower() in full_text.lower()]
            passed = len(found) >= 2
            results.append({
                "criterion": check_text,
                "result": "PASS" if passed else "UNCERTAIN",
                "evidence": f"Fix indicators: {found}" if found else "No error detection signals found",
                "tier": "structural",
            })
        elif "before harness" in check_lower or "before" in check_lower and "feature" in check_lower:
            build_types = [b for b in breadcrumbs if isinstance(b, dict) and b.get("type") == "build"]
            negotiate_types = [b for b in breadcrumbs if isinstance(b, dict) and b.get("type") in ("negotiate", "negotiation")]
            if build_types and negotiate_types:
                passed = True
                evidence = "Build entries exist after negotiation"
            else:
                passed = len(breadcrumbs) >= 2
                evidence = "Breadcrumbs indicate sequential work"
            results.append({
                "criterion": check_text,
                "result": "PASS" if passed else "UNCERTAIN",
                "evidence": evidence,
                "tier": "structural",
            })
        elif "no harness" in check_lower and ("bugfix" in check_lower or "simple" in check_lower):
            early_breadcrumbs = breadcrumbs[:3] if len(breadcrumbs) >= 3 else breadcrumbs
            early_negotiate = any(
                b.get("type") in ("negotiate", "negotiation")
                for b in early_breadcrumbs if isinstance(b, dict)
            )
            passed = not early_negotiate
            results.append({
                "criterion": check_text,
                "result": "PASS" if passed else "FAIL",
                "evidence": "No early negotiation (bugfix was simple)" if passed else "Harness activated too early for bugfix",
                "tier": "computational",
            })
        else:
            results.append({
                "criterion": check_text,
                "result": "UNCERTAIN",
                "evidence": "Requires LLM evaluation",
                "tier": "structural",
            })

    return results


# ─── LLM Judge ──────────────────────────────────────────────────────────────────


LLM_JUDGE_SYSTEM = """\
You are an adversarial judge evaluating an AI coding assistant's session.
You grade STRICTLY based on evidence in the transcript and artifacts.

For each criterion, return:
- "result": "PASS" or "FAIL"
- "evidence": specific quote or observation from the transcript
- "confidence": 1-5 (5 = certain)

Return a JSON array of results matching the criteria order.
"""


def judge_with_llm(
    session: dict,
    rubric: dict,
    criteria: list[str],
    api_key: str,
    model: str,
) -> list[dict]:
    """Use LLM to judge subjective criteria."""
    try:
        from cursor_sdk import Agent, LocalAgentOptions
    except ImportError:
        return [
            {"criterion": c, "result": "SKIP", "evidence": "cursor_sdk not available", "tier": "llm"}
            for c in criteria
        ]

    transcript_text = json.dumps(session.get("transcript", []), indent=2)
    artifacts_summary = json.dumps(
        {k: v for k, v in session.get("artifacts", {}).items() if k != "files"},
        indent=2,
    )

    prompt = f"""Judge this session against these criteria:

{json.dumps(criteria, indent=2)}

## Transcript
{transcript_text[:8000]}

## Artifacts
{artifacts_summary[:4000]}

Return ONLY a JSON array with one object per criterion:
[{{"criterion": "...", "result": "PASS|FAIL", "evidence": "...", "confidence": 1-5}}]
"""

    try:
        with Agent.create(model=model, api_key=api_key) as judge:
            run = judge.send(prompt)
            run.wait()
            response = run.text()

        match = re.search(r"\[.*\]", response, re.DOTALL)
        if match:
            parsed = json.loads(match.group())
            for item in parsed:
                item["tier"] = "llm"
            return parsed
    except Exception as e:
        return [
            {"criterion": c, "result": "ERROR", "evidence": str(e), "tier": "llm"}
            for c in criteria
        ]

    return [
        {"criterion": c, "result": "ERROR", "evidence": "Failed to parse LLM response", "tier": "llm"}
        for c in criteria
    ]


# ─── Orchestrator ──────────────────────────────────────────────────────────────


def judge_session(
    session: dict,
    rubric: dict,
    tiers: set[str],
    api_key: str = "",
    judge_model: str = "claude-opus-4-6",
) -> dict:
    """Run all applicable judge tiers on a session."""
    all_results: list[dict] = []

    level = _get_harness_level(rubric)

    is_negative = _is_negative_harness_scenario(rubric)

    has_negotiation_rubric = bool(rubric.get("post_hoc_rubric", {}).get("negotiation_quality"))

    if "computational" in tiers:
        all_results.extend(check_harness_compliance(session, rubric))
        if (level == "full" or has_negotiation_rubric) and not is_negative:
            all_results.extend(check_contract_quality(session))

    if "structural" in tiers:
        all_results.extend(check_artifacts(session, rubric))
        all_results.extend(check_behavioral(session, rubric))
        all_results.extend(check_skill_activation(session, rubric))
        all_results.extend(check_design_compliance(session, rubric))
        all_results.extend(check_long_scenario(session, rubric))

    if "llm" in tiers and api_key:
        llm_criteria = rubric.get("post_hoc_rubric", {}).get("negotiation_quality", [])
        if llm_criteria:
            all_results.extend(
                judge_with_llm(session, rubric, llm_criteria, api_key, judge_model)
            )

    pass_count = sum(1 for r in all_results if r["result"] == "PASS")
    fail_count = sum(1 for r in all_results if r["result"] == "FAIL")
    total = len(all_results)

    return {
        "scenario_id": session.get("scenario_id"),
        "model": session.get("model"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tiers_run": sorted(tiers),
        "results": all_results,
        "summary": {
            "total": total,
            "pass": pass_count,
            "fail": fail_count,
            "skip_or_uncertain": total - pass_count - fail_count,
            "score": round(pass_count / max(total, 1), 2),
        },
    }


def save_judgment(judgment: dict, run_dir: Path) -> Path:
    model = judgment.get("model", "unknown")
    scenario_id = judgment.get("scenario_id", "unknown")
    out_dir = run_dir / "judgments" / model
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{scenario_id}.json"
    path.write_text(json.dumps(judgment, indent=2) + "\n")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="Judge session scenarios post-hoc")
    parser.add_argument("--session", help="Path to specific session JSON")
    parser.add_argument("--run-dir", help="Path to eval run dir (default: latest)")
    parser.add_argument("--filter", help="Filter sessions by scenario id")
    parser.add_argument("--tier", choices=["computational", "structural", "llm"],
                        help="Run only this tier")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--judge-model", default=os.environ.get("JUDGE_MODEL", "claude-opus-4-6"))
    args = parser.parse_args()

    api_key = os.environ.get("CURSOR_API_KEY", "")
    run_dir = _resolve_run_dir(args.run_dir)

    if args.tier:
        tiers = {args.tier}
    else:
        tiers = {"computational", "structural"}
        if api_key:
            tiers.add("llm")

    if args.session:
        session_paths = [Path(args.session)]
    else:
        session_paths = find_sessions(run_dir, args.filter)

    if not session_paths:
        print(f"No sessions found in {run_dir}/sessions/. Run session_runner.py first.")
        return 1

    all_judgments = []

    for sp in session_paths:
        if not sp.exists():
            print(f"Session not found: {sp}")
            continue

        session = json.loads(sp.read_text())
        scenario_id = session.get("scenario_id", sp.stem)
        rubric_data = load_scenario(scenario_id) or {}

        judgment = judge_session(session, rubric_data, tiers, api_key, args.judge_model)
        path = save_judgment(judgment, run_dir)
        all_judgments.append(judgment)

        if not args.json:
            summary = judgment["summary"]
            print(f"\n{scenario_id}: {summary['pass']}/{summary['total']} PASS "
                  f"(score: {summary['score']:.0%})")
            for r in judgment["results"]:
                status = "PASS" if r["result"] == "PASS" else "FAIL" if r["result"] == "FAIL" else "????"
                print(f"  [{r.get('tier', '?'):13s}] {status} {r['criterion'][:70]}")
            print(f"  Saved: {path}")

    if args.json:
        print(json.dumps(all_judgments, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
