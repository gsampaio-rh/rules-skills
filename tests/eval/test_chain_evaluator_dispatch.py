"""Unit tests for feat-13b programmatic state-transition orchestration.

Tests chain-evaluator.sh by invoking it in a temp directory (chdir fixture).
Asserts stdout JSON, file side effects, and breadcrumb content.
"""

from __future__ import annotations

import json
import os
import stat
import subprocess
import tempfile
from pathlib import Path

import pytest

# Path to the hook under test
HOOK_PATH = (
    Path(__file__).parent.parent.parent
    / "library" / "cursor" / "hooks" / "chain-evaluator.sh"
).resolve()

HOOKS_LIB = (
    Path(__file__).parent.parent.parent
    / "library" / "cursor" / "hooks" / "hooks-lib.sh"
).resolve()


def _run_hook(tmpdir: Path, stdin: str = "{}") -> tuple[int, dict]:
    """Run chain-evaluator.sh from tmpdir and return (exit_code, parsed_stdout_json)."""
    env = os.environ.copy()
    env["HOOK_LOG"] = str(tmpdir / "hooks.log")
    result = subprocess.run(
        ["bash", str(HOOK_PATH)],
        cwd=str(tmpdir),
        input=stdin,
        capture_output=True,
        text=True,
        env=env,
    )
    stdout = result.stdout.strip()
    try:
        parsed = json.loads(stdout) if stdout else {}
    except json.JSONDecodeError:
        parsed = {"_raw": stdout}
    return result.returncode, parsed


def _write_contract(tmpdir: Path, phase: str, verified: bool = False, task_id: str = "test-feat") -> None:
    harness_dir = tmpdir / ".harness"
    harness_dir.mkdir(exist_ok=True)
    contract = {
        "task_id": task_id,
        "feature": "test feature",
        "phase": phase,
        "verified": verified,
    }
    (harness_dir / "contract.json").write_text(json.dumps(contract, indent=2))


def _read_contract_phase(tmpdir: Path) -> str:
    contract_path = tmpdir / ".harness" / "contract.json"
    return json.loads(contract_path.read_text()).get("phase", "unknown")


def _read_breadcrumbs(tmpdir: Path) -> list[dict]:
    bc_path = tmpdir / ".harness" / "breadcrumbs.jsonl"
    if not bc_path.exists():
        return []
    return [json.loads(line) for line in bc_path.read_text().splitlines() if line.strip()]


# ─── AC7(a): phase=building → full state transition ──────────────────────────


def test_building_advances_phase_to_evaluating(tmp_path):
    """AC7(a): phase=building → contract.json phase becomes evaluating."""
    _write_contract(tmp_path, "building")
    (tmp_path / ".harness").mkdir(exist_ok=True)
    exit_code, result = _run_hook(tmp_path)

    assert exit_code == 0
    assert _read_contract_phase(tmp_path) == "evaluating"


def test_building_creates_evaluator_active_flag(tmp_path):
    """AC7(a): phase=building → .cursor/hooks/.evaluator-active created."""
    _write_contract(tmp_path, "building")
    exit_code, _ = _run_hook(tmp_path)

    assert exit_code == 0
    flag_path = tmp_path / ".cursor" / "hooks" / ".evaluator-active"
    assert flag_path.exists(), "evaluator-active flag should be created"


def test_building_appends_dispatch_breadcrumb(tmp_path):
    """AC7(a): phase=building → dispatch breadcrumb appended to breadcrumbs.jsonl."""
    _write_contract(tmp_path, "building", task_id="feat-xyz")
    exit_code, _ = _run_hook(tmp_path)

    assert exit_code == 0
    crumbs = _read_breadcrumbs(tmp_path)
    dispatch_crumbs = [c for c in crumbs if c.get("type") == "dispatch"]
    assert len(dispatch_crumbs) >= 1
    crumb = dispatch_crumbs[0]
    assert crumb["role"] == "system"
    assert crumb["result"] == "pass"
    assert "evaluating" in crumb.get("msg", "").lower()


def test_building_stdout_contains_required_phrases(tmp_path):
    """AC7(a): stdout followup_message contains 'Launch /evaluator now' and 'Phase auto-advanced to evaluating'."""
    _write_contract(tmp_path, "building")
    exit_code, result = _run_hook(tmp_path)

    assert exit_code == 0
    msg = result.get("followup_message", "")
    assert "Launch /evaluator now" in msg, f"Missing phrase in: {msg}"
    assert "Phase auto-advanced to evaluating" in msg, f"Missing phrase in: {msg}"


def test_building_breadcrumb_uses_task_id(tmp_path):
    """AC2: breadcrumb feat matches contract task_id."""
    _write_contract(tmp_path, "building", task_id="gap-99")
    _run_hook(tmp_path)

    crumbs = _read_breadcrumbs(tmp_path)
    dispatch_crumbs = [c for c in crumbs if c.get("type") == "dispatch"]
    assert any(c.get("feat") == "gap-99" for c in dispatch_crumbs)


# ─── AC7(b): write error → MANUAL fallback ────────────────────────────────────


def test_building_write_error_returns_manual_fallback(tmp_path):
    """AC7(b): contract.json read-only → MANUAL fallback message, exit 0."""
    _write_contract(tmp_path, "building")
    contract_path = tmp_path / ".harness" / "contract.json"
    # Make contract.json read-only
    contract_path.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)

    try:
        exit_code, result = _run_hook(tmp_path)
        assert exit_code == 0
        msg = result.get("followup_message", "")
        assert "MANUAL" in msg or "manually" in msg.lower(), f"Missing MANUAL fallback in: {msg}"
    finally:
        contract_path.chmod(stat.S_IRUSR | stat.S_IWUSR)  # restore for cleanup


# ─── AC7(c): evaluating+unverified → EVAL FAIL ────────────────────────────────


def test_evaluating_unverified_returns_eval_fail(tmp_path):
    """AC7(c): phase=evaluating, verified=false → EVAL FAIL message with max-retry reminder."""
    _write_contract(tmp_path, "evaluating", verified=False)
    exit_code, result = _run_hook(tmp_path)

    assert exit_code == 0
    msg = result.get("followup_message", "")
    assert "EVAL FAIL" in msg, f"Missing EVAL FAIL in: {msg}"
    # Static max-retry reminder
    assert "2" in msg or "max" in msg.lower(), f"Missing max-retry hint in: {msg}"


# ─── AC7(d): evaluating+verified → {} ────────────────────────────────────────


def test_evaluating_verified_returns_empty_dict(tmp_path):
    """AC7(d): phase=evaluating, verified=true → {} (pass through)."""
    _write_contract(tmp_path, "evaluating", verified=True)
    exit_code, result = _run_hook(tmp_path)

    assert exit_code == 0
    assert result == {}, f"Expected empty dict, got: {result}"


# ─── AC4: negotiating/negotiated → imperative message ────────────────────────


@pytest.mark.parametrize("phase", ["negotiating", "negotiated"])
def test_negotiating_returns_imperative_message(tmp_path, phase):
    """AC4: phase=negotiating/negotiated → imperative 'Set phase to building...' message."""
    _write_contract(tmp_path, phase)
    exit_code, result = _run_hook(tmp_path)

    assert exit_code == 0
    msg = result.get("followup_message", "")
    assert "building" in msg.lower(), f"Missing 'building' in: {msg}"
    assert "implementation" in msg.lower() or "start" in msg.lower(), f"Missing action in: {msg}"


# ─── EC1: no task_id field → feat='' in breadcrumb, no crash ─────────────────


def test_no_task_id_uses_empty_feat(tmp_path):
    """EC1: contract has no task_id → breadcrumb feat is empty string, no crash."""
    harness_dir = tmp_path / ".harness"
    harness_dir.mkdir(exist_ok=True)
    contract = {"feature": "no-id feature", "phase": "building", "verified": False}
    (harness_dir / "contract.json").write_text(json.dumps(contract))

    exit_code, result = _run_hook(tmp_path)

    assert exit_code == 0
    crumbs = _read_breadcrumbs(tmp_path)
    dispatch_crumbs = [c for c in crumbs if c.get("type") == "dispatch"]
    if dispatch_crumbs:
        assert dispatch_crumbs[0].get("feat", "MISSING") in ("", None)


# ─── EC2: .cursor dir blocked → MANUAL fallback ──────────────────────────────


def test_building_flag_dir_failure_returns_manual_fallback(tmp_path):
    """EC2/AC5: .cursor exists as a file (blocks mkdir) → MANUAL fallback message."""
    _write_contract(tmp_path, "building")
    # Create .cursor as a file to block os.makedirs(.cursor/hooks/)
    cursor_as_file = tmp_path / ".cursor"
    cursor_as_file.write_text("I am a file, not a dir")

    exit_code, result = _run_hook(tmp_path)

    assert exit_code == 0
    msg = result.get("followup_message", "")
    assert "MANUAL" in msg or "manually" in msg.lower(), f"Missing MANUAL fallback in: {msg}"


# ─── EC4: double-fire idempotency ────────────────────────────────────────────


def test_building_double_fire_idempotent(tmp_path):
    """EC4: phase=building fires twice → second run is idempotent (phase re-patched, flag recreated)."""
    _write_contract(tmp_path, "building")
    _run_hook(tmp_path)

    # Reset phase manually to building to simulate double-fire
    _write_contract(tmp_path, "building")
    exit_code, result = _run_hook(tmp_path)

    assert exit_code == 0
    assert _read_contract_phase(tmp_path) == "evaluating"
    flag_path = tmp_path / ".cursor" / "hooks" / ".evaluator-active"
    assert flag_path.exists()


# ─── bug-chain-evaluator-advance: subagent_type allowlist ─────────────────────


def test_explore_building_skips_advance(tmp_path):
    """AC1: explore + building → no phase advance, no flag, no dispatch crumb."""
    _write_contract(tmp_path, "building", task_id="feat-x")
    (tmp_path / ".harness" / "breadcrumbs.jsonl").write_text("")
    exit_code, result = _run_hook(tmp_path, json.dumps({"subagent_type": "explore"}))
    assert exit_code == 0
    assert result == {}
    assert _read_contract_phase(tmp_path) == "building"
    assert not (tmp_path / ".cursor" / "hooks" / ".evaluator-active").exists()
    crumbs = _read_breadcrumbs(tmp_path)
    assert not any(c.get("type") == "dispatch" for c in crumbs)


def test_legacy_empty_stdin_building_still_advances(tmp_path):
    """AC2: empty stdin keeps feat-13b auto-advance."""
    _write_contract(tmp_path, "building")
    exit_code, result = _run_hook(tmp_path, "")
    assert exit_code == 0
    assert _read_contract_phase(tmp_path) == "evaluating"
    assert (tmp_path / ".cursor" / "hooks" / ".evaluator-active").exists()
    msg = result.get("followup_message", "")
    assert "Launch /evaluator now" in msg
    assert "Phase auto-advanced to evaluating" in msg


def test_evaluator_type_building_advances(tmp_path):
    """AC3: evaluator + building still advances."""
    _write_contract(tmp_path, "building")
    exit_code, result = _run_hook(tmp_path, json.dumps({"subagent_type": "evaluator"}))
    assert exit_code == 0
    assert _read_contract_phase(tmp_path) == "evaluating"
    assert (tmp_path / ".cursor" / "hooks" / ".evaluator-active").exists()
    assert "Launch /evaluator now" in result.get("followup_message", "")


def test_plan_gate_planner_and_legacy(tmp_path):
    """AC4a: fresh state, no contract → PLAN GATE for {} and planner."""
    harness = tmp_path / ".harness"
    harness.mkdir()
    (harness / "state.json").write_text(
        json.dumps(
            {
                "project": "t",
                "schema_version": 2,
                "vision": "v",
                "tasks": [{"id": "t1", "name": "n", "type": "feature", "status": "pending"}],
            }
        )
    )
    for stdin in ("{}", json.dumps({"subagent_type": "planner"})):
        exit_code, result = _run_hook(tmp_path, stdin)
        assert exit_code == 0, stdin
        assert "PLAN GATE" in result.get("followup_message", ""), result


def test_plan_gate_explore_skipped(tmp_path):
    """AC4b: explore must not PLAN GATE."""
    harness = tmp_path / ".harness"
    harness.mkdir()
    (harness / "state.json").write_text(
        json.dumps(
            {
                "project": "t",
                "schema_version": 2,
                "vision": "v",
                "tasks": [{"id": "t1", "name": "n", "type": "feature", "status": "pending"}],
            }
        )
    )
    exit_code, result = _run_hook(tmp_path, json.dumps({"subagent_type": "explore"}))
    assert exit_code == 0
    assert result == {}
    assert "PLAN GATE" not in json.dumps(result)


def test_shell_evaluating_skips_eval_fail(tmp_path):
    """AC5: shell + evaluating unverified → {} (no EVAL FAIL)."""
    _write_contract(tmp_path, "evaluating", verified=False)
    exit_code, result = _run_hook(tmp_path, json.dumps({"subagent_type": "shell"}))
    assert exit_code == 0
    assert result == {}
    assert "EVAL FAIL" not in json.dumps(result)


def test_explore_clears_evaluator_active_without_advance(tmp_path):
    """AC6: explore clears pre-existing flag; phase stays building."""
    _write_contract(tmp_path, "building")
    flag = tmp_path / ".cursor" / "hooks" / ".evaluator-active"
    flag.parent.mkdir(parents=True)
    flag.write_text("")
    exit_code, result = _run_hook(tmp_path, json.dumps({"subagent_type": "explore"}))
    assert exit_code == 0
    assert result == {}
    assert not flag.exists()
    assert _read_contract_phase(tmp_path) == "building"


def test_general_purpose_skips_like_explore(tmp_path):
    """EC: unknown types behave like explore."""
    _write_contract(tmp_path, "building")
    exit_code, result = _run_hook(
        tmp_path, json.dumps({"subagent_type": "generalPurpose"})
    )
    assert exit_code == 0
    assert result == {}
    assert _read_contract_phase(tmp_path) == "building"
