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
    """Load scenario YAML, trying both underscore and hyphen variants."""
    for name in (scenario_id, scenario_id.replace("_", "-"), scenario_id.replace("-", "_")):
        path = SCENARIOS_DIR / f"{name}.yaml"
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

VALID_BREADCRUMB_ROLES = {"planner", "builder", "evaluator", "system"}
VALID_BREADCRUMB_TYPES = {
    "plan", "negotiate", "build", "verify", "eval", "checkpoint",
    "decision", "scrap", "init", "session_start", "evaluation",
}
ISO_TS_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}")


def _is_negative_harness_scenario(rubric: dict) -> bool:
    """Detect scenarios where harness should NOT activate."""
    compliance = rubric.get("post_hoc_rubric", {}).get("harness_compliance", [])
    negative_signals = ("no .harness", "not activate", "no contract", "no /planner", "no /evaluator")
    return any(
        any(sig in c.lower() for sig in negative_signals)
        for c in compliance
    )


def check_harness_compliance(session: dict, rubric: dict) -> list[dict]:
    """Fast, deterministic checks on harness state."""
    results = []
    artifacts = session.get("artifacts", {})
    harness = artifacts.get("harness", {})

    if _is_negative_harness_scenario(rubric):
        return _check_harness_absent(harness)

    state = harness.get("state.json", {})
    has_state = bool(state and (state.get("features") or state.get("feature_list")))
    results.append({
        "criterion": "Agent created .harness/state.json with features",
        "result": "PASS" if has_state else "FAIL",
        "evidence": f"{len(state.get('features', state.get('feature_list', [])))} features" if has_state else "No features in state",
        "tier": "computational",
    })

    breadcrumbs = harness.get("breadcrumbs.jsonl", [])
    has_negotiate = any(
        b.get("type") in ("negotiate", "negotiation")
        for b in breadcrumbs if isinstance(b, dict)
    )
    results.append({
        "criterion": "Contract negotiation occurred",
        "result": "PASS" if has_negotiate else "FAIL",
        "evidence": "Found negotiate breadcrumb" if has_negotiate else "No negotiate entries in breadcrumbs",
        "tier": "computational",
    })

    has_eval = any(
        b.get("type") in ("eval", "verify", "evaluation")
        or b.get("role") == "evaluator"
        for b in breadcrumbs if isinstance(b, dict)
    )
    results.append({
        "criterion": "Evaluator was launched",
        "result": "PASS" if has_eval else "FAIL",
        "evidence": "Found evaluator activity in breadcrumbs" if has_eval else "No evaluator role or eval-type entries",
        "tier": "computational",
    })

    contract = harness.get("contract.json", {})
    verified = contract.get("verified", False)
    phase = contract.get("phase", "none")
    results.append({
        "criterion": "Contract was verified before completion",
        "result": "PASS" if verified else "FAIL",
        "evidence": f"verified={verified}, phase={phase}",
        "tier": "computational",
    })

    results.extend(_check_breadcrumbs_schema(breadcrumbs))
    results.extend(_check_phase_progression(contract, breadcrumbs))

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
    has_builder = "builder" in roles_present
    results.append({
        "criterion": "Builder role present in breadcrumbs",
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
    late_phases = {"building", "evaluating", "verified", "negotiated"}
    progressed = phase in late_phases
    results.append({
        "criterion": "Contract phase progressed beyond 'negotiating'",
        "result": "PASS" if progressed else "FAIL",
        "evidence": f"Current phase: {phase}",
        "tier": "computational",
    })

    types_in_order = [b.get("type") for b in breadcrumbs if isinstance(b, dict)]
    expected_progression = ["negotiate", "build"]
    found_progression = [t for t in types_in_order if t in expected_progression]
    ordered = found_progression == sorted(found_progression, key=expected_progression.index)
    results.append({
        "criterion": "Breadcrumb types follow logical order (negotiate → build)",
        "result": "PASS" if (ordered and len(found_progression) >= 2) else "FAIL",
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
        return _check_validations(check_lower, validations)

    if _is_content_check(check_lower):
        return _check_content(check_lower, all_content, contents)

    file_extensions = re.findall(r"\.\w+", check)
    if file_extensions:
        found = [
            ext for ext in file_extensions
            if any(f.endswith(ext) for f in files)
        ]
        passed = len(found) > 0
        return passed, f"Extensions found: {found}" if found else f"None of {file_extensions} found"

    return False, "No matching heuristic"


def _is_validation_check(check: str) -> bool:
    return any(kw in check for kw in ("test", "pytest", "npm test", "passes", "exit code"))


def _check_validations(check: str, validations: list[dict]) -> tuple[bool, str]:
    if not validations:
        return False, "No validation commands were run"

    all_pass = all(v.get("exit_code") == 0 for v in validations)
    if "pass" in check or "exit code 0" in check:
        summary = "; ".join(
            f"{v['command']}→{v['exit_code']}" for v in validations
        )
        return all_pass, f"Validations: {summary}"

    for v in validations:
        cmd = v.get("command", "")
        if any(kw in cmd for kw in ("pytest", "test", "npm test")):
            passed = v.get("exit_code") == 0
            return passed, f"{cmd} exit_code={v.get('exit_code')}"

    return False, "No matching validation found"


def _is_content_check(check: str) -> bool:
    return any(kw in check for kw in (
        "argparse", "click", "uses", "contains", "import", "class ",
        "function", "def ", "flag", "--", "type hint", "docstring",
        "error handling", "error", "exception", "present", "exists",
        "handling", "permission",
    ))


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


# ─── Behavioral Checks ────────────────────────────────────────────────────────


def check_behavioral(session: dict, rubric: dict) -> list[dict]:
    """Check transcript behavioral patterns."""
    results = []
    transcript = session.get("transcript", [])
    full_text = " ".join(
        t.get("response", "") for t in transcript if t.get("response")
    )

    behavioral_checks = rubric.get("post_hoc_rubric", {}).get("behavioral", [])
    for check_text in behavioral_checks:
        passed = _evaluate_behavioral(check_text, full_text, session)
        results.append({
            "criterion": check_text,
            "result": "PASS" if passed else "UNCERTAIN",
            "evidence": "Pattern-based heuristic",
            "tier": "structural",
        })

    return results


def _evaluate_behavioral(check: str, transcript_text: str, session: dict) -> bool:
    check_lower = check.lower()

    if "no apolog" in check_lower:
        apology_patterns = re.compile(r"\b(i'm sorry|i apologize|sorry about)\b", re.I)
        return not apology_patterns.search(transcript_text)

    if "autonomously" in check_lower or "autonomous" in check_lower:
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

    if "todowrite" in check_lower or "progress track" in check_lower:
        harness = session.get("artifacts", {}).get("harness", {})
        breadcrumbs = harness.get("breadcrumbs.jsonl", [])
        has_build_entries = sum(
            1 for b in breadcrumbs
            if isinstance(b, dict) and b.get("type") == "build"
        )
        return has_build_entries >= 2 or "TodoWrite" in transcript_text

    if "push back" in check_lower or "pushback" in check_lower:
        clarify_patterns = re.compile(r"\b(clarif|what do you mean|could you specify|more specific|narrow)\b", re.I)
        return bool(clarify_patterns.search(transcript_text))

    if "did not modify" in check_lower or "not refactor" in check_lower:
        artifacts = session.get("artifacts", {})
        files = artifacts.get("files", [])
        return len(files) <= 1

    if "verif" in check_lower and ("syntax" in check_lower or "import" in check_lower or "test" in check_lower):
        verify_patterns = ["py_compile", "import ", "pytest", "python -c", "npm test", "tsc"]
        return any(p in transcript_text for p in verify_patterns)

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
            run.wait(timeout=120)
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

    if "computational" in tiers:
        all_results.extend(check_harness_compliance(session, rubric))
        all_results.extend(check_contract_quality(session))

    if "structural" in tiers:
        all_results.extend(check_artifacts(session, rubric))
        all_results.extend(check_behavioral(session, rubric))
        all_results.extend(check_skill_activation(session, rubric))

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
