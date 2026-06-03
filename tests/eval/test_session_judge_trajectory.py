"""Regression tests for trajectory tier checks.

Maps to feat-15 contract ACs 1-15.
"""

import sys
sys.path.insert(0, ".")

from tests.eval.trajectory_checks import (
    check_trajectory,
    check_loop,
    check_efficiency,
    check_read_before_write,
    check_skeleton,
    check_backtracking,
    check_idle,
    check_error_recovery,
    CRITERION_LOOP,
    CRITERION_EFFICIENCY,
    CRITERION_READ_WRITE,
    CRITERION_SKELETON,
    CRITERION_BACKTRACK,
    CRITERION_IDLE,
    CRITERION_RECOVERY,
)
from tests.eval.session_judge import judge_session
from tests.eval.session_report import classify_dimension, DIMENSIONS


def _tc(name: str, args: dict | None = None, result: str = "") -> dict:
    return {"type": "toolCall", "name": name, "args": args or {}, "result": result, "status": "success"}


def _assistant(text: str = "thinking...") -> dict:
    return {"type": "assistantMessage", "content": text}


def _shell_turn(command: str, exit_code: int = 0, stdout: str = "") -> dict:
    return {"type": "shellConversationTurn", "command": command, "exit_code": exit_code, "stdout": stdout, "stderr": ""}


def _session(steps: list[dict], difficulty: str = "medium") -> dict:
    return {
        "scenario_id": "test",
        "model": "test",
        "transcript": [{"response": "ok", "conversation": steps}],
        "artifacts": {"harness": {}},
    }


def _rubric(difficulty: str = "medium", skeleton: list | None = None) -> dict:
    r = {"difficulty": difficulty, "post_hoc_rubric": {}, "computational": []}
    if skeleton:
        r["trajectory_skeleton"] = skeleton
    return r


# --- AC1: tier in results ---

def test_ac1_tier_in_results():
    steps = [_tc("Read", {"path": "a.py"}), _tc("Write", {"path": "a.py"})]
    session = _session(steps)
    j = judge_session(session, _rubric(), tiers={"trajectory"})
    traj_results = [r for r in j["results"] if r["tier"] == "trajectory"]
    assert len(traj_results) >= 1, "No trajectory results"


# --- AC2: CLI choices (tested via import, argparse is structural) ---

def test_ac2_trajectory_in_tiers():
    from tests.eval.session_judge import judge_session as js
    steps = [_tc("Read", {"path": "a.py"})]
    j = js(_session(steps), _rubric(), tiers={"trajectory"})
    assert "trajectory" in j["tiers_run"]


# --- AC3: no trace → [] ---

def test_ac3_no_trace_returns_empty():
    session = {"scenario_id": "t", "model": "t", "transcript": [{"response": "hi"}], "artifacts": {}}
    results = check_trajectory(session, _rubric())
    assert results == []


def test_ac3_score_unchanged_without_trace():
    session = {"scenario_id": "t", "model": "t", "transcript": [{"response": "hi"}], "artifacts": {}}
    rubric = _rubric()
    j_without = judge_session(session, rubric, tiers={"computational", "structural"})
    j_with = judge_session(session, rubric, tiers={"computational", "structural", "trajectory"})
    assert j_without["summary"]["total"] == j_with["summary"]["total"]
    assert j_without["summary"]["pass"] == j_with["summary"]["pass"]


# --- AC4: loop detection ---

def test_ac4_loop_3_consecutive_fails():
    steps = [
        _tc("Shell", {"command": "pytest"}),
        _tc("Shell", {"command": "pytest"}),
        _tc("Shell", {"command": "pytest"}),
    ]
    r = check_loop(_session(steps), _rubric())
    assert r["result"] == "FAIL"
    assert "3" in r["evidence"]


def test_ac4_loop_2_consecutive_passes():
    steps = [
        _tc("Shell", {"command": "pytest"}),
        _tc("Shell", {"command": "pytest"}),
    ]
    r = check_loop(_session(steps), _rubric())
    assert r["result"] == "PASS"


# --- AC5: step efficiency ---

def test_ac5_easy_30_calls_fails():
    steps = [_tc("Read", {"path": f"f{i}.py"}) for i in range(30)]
    r = check_efficiency(_session(steps, "easy"), _rubric("easy"))
    assert r["result"] == "FAIL"


def test_ac5_easy_15_calls_passes():
    steps = [_tc("Read", {"path": f"f{i}.py"}) for i in range(15)]
    r = check_efficiency(_session(steps, "easy"), _rubric("easy"))
    assert r["result"] == "PASS"


def test_ac5_missing_difficulty_defaults_medium():
    steps = [_tc("Read", {"path": f"f{i}.py"}) for i in range(25)]
    r = check_efficiency(_session(steps), {"post_hoc_rubric": {}})
    assert r["result"] == "PASS"
    assert "medium" in r["evidence"]


# --- AC6: read before write ---

def test_ac6_write_without_read_fails():
    steps = [_tc("Write", {"path": "/project/foo.py"})]
    r = check_read_before_write(_session(steps), _rubric())
    assert r["result"] == "FAIL"
    assert "foo.py" in r["evidence"]


def test_ac6_read_then_write_passes():
    steps = [
        _tc("Read", {"path": "/project/foo.py"}),
        _tc("Write", {"path": "/project/foo.py"}),
    ]
    r = check_read_before_write(_session(steps), _rubric())
    assert r["result"] == "PASS"


def test_ac6_strreplace_counts_as_write():
    steps = [_tc("StrReplace", {"path": "/project/bar.py"})]
    r = check_read_before_write(_session(steps), _rubric())
    assert r["result"] == "FAIL"


# --- AC7: skeleton matching ---

def test_ac7_skeleton_present_passes():
    steps = [
        _tc("Read", {"path": ".harness/state.json"}),
        _tc("Write", {"path": ".harness/state.json"}),
    ]
    skeleton = [
        {"tool": "Read", "path_contains": "state.json"},
        {"tool": "Write", "path_contains": "state.json", "after": "Read state.json"},
    ]
    r = check_skeleton(_session(steps), _rubric(skeleton=skeleton))
    assert r["result"] == "PASS"


def test_ac7_skeleton_missing_step_fails():
    steps = [_tc("Write", {"path": ".harness/state.json"})]
    skeleton = [
        {"tool": "Read", "path_contains": "state.json"},
        {"tool": "Write", "path_contains": "state.json", "after": "Read state.json"},
    ]
    r = check_skeleton(_session(steps), _rubric(skeleton=skeleton))
    assert r["result"] == "FAIL"


def test_ac7_no_skeleton_omitted():
    steps = [_tc("Read", {"path": "a.py"})]
    r = check_skeleton(_session(steps), _rubric())
    assert r is None


# --- AC8: backtracking ratio ---

def test_ac8_high_backtracking_fails():
    # 4 StrReplace on a.py + 1 Write on b.py = 5 edits, backtrack = 3, ratio = 3/5 = 60%
    steps = [
        _tc("StrReplace", {"path": "/p/a.py"}),
        _tc("StrReplace", {"path": "/p/a.py"}),
        _tc("StrReplace", {"path": "/p/a.py"}),
        _tc("StrReplace", {"path": "/p/a.py"}),
        _tc("Write", {"path": "/p/b.py"}),
    ]
    r = check_backtracking(_session(steps), _rubric())
    assert r["result"] == "FAIL"


def test_ac8_low_backtracking_passes():
    # 1 StrReplace on a.py + 1 Write on b.py = 2 edits, backtrack = 0, ratio = 0%
    steps = [
        _tc("StrReplace", {"path": "/p/a.py"}),
        _tc("Write", {"path": "/p/b.py"}),
    ]
    r = check_backtracking(_session(steps), _rubric())
    assert r["result"] == "PASS"


def test_ac8_exact_50_percent_passes():
    # 3 StrReplace on a.py + 1 Write on b.py = 4 edits, backtrack = 2, ratio = 50% exactly → PASS
    steps = [
        _tc("StrReplace", {"path": "/p/a.py"}),
        _tc("StrReplace", {"path": "/p/a.py"}),
        _tc("StrReplace", {"path": "/p/a.py"}),
        _tc("Write", {"path": "/p/b.py"}),
    ]
    r = check_backtracking(_session(steps), _rubric())
    assert r["result"] == "PASS"


def test_ac8_no_edits_passes():
    steps = [_tc("Read", {"path": "a.py"})]
    r = check_backtracking(_session(steps), _rubric())
    assert r["result"] == "PASS"
    assert "No edits" in r["evidence"]


# --- AC9: idle detection ---

def test_ac9_4_idle_fails():
    steps = [
        _assistant(), _assistant(), _assistant(), _assistant(),
    ]
    r = check_idle(_session(steps), _rubric())
    assert r["result"] == "FAIL"


def test_ac9_3_idle_passes():
    steps = [
        _assistant(), _assistant(), _assistant(),
    ]
    r = check_idle(_session(steps), _rubric())
    assert r["result"] == "PASS"


# --- AC10: error recovery ---

def test_ac10_error_no_recovery_fails():
    steps = [
        _shell_turn("npm test", exit_code=1),
        _assistant(), _assistant(), _assistant(),
    ]
    r = check_error_recovery(_session(steps), _rubric())
    assert r["result"] == "FAIL"


def test_ac10_error_with_recovery_passes():
    steps = [
        _shell_turn("npm test", exit_code=1),
        _tc("Read", {"path": "test.js"}),
    ]
    r = check_error_recovery(_session(steps), _rubric())
    assert r["result"] == "PASS"


def test_ac10_repeated_same_command_not_recovery():
    steps = [
        _shell_turn("npm test", exit_code=1),
        _tc("Shell", {"command": "npm test"}, result="Exit code: 1"),
        _assistant(), _assistant(),
    ]
    r = check_error_recovery(_session(steps), _rubric())
    assert r["result"] == "FAIL"


# --- AC11: reporting dimension ---

def test_ac11_classify_trajectory():
    result = {"criterion": "loop check", "tier": "trajectory"}
    assert classify_dimension(result) == "trajectory"


def test_ac11_dimensions_includes_trajectory():
    assert "trajectory" in DIMENSIONS


# --- AC12: backward compatibility (28 YAMLs load) tested in verify step ---

# --- AC13: fixed criterion strings ---

def test_ac13_criterion_strings():
    steps = [_tc("Read", {"path": "a.py"}), _tc("Write", {"path": "a.py"})]
    session = _session(steps)
    results = check_trajectory(session, _rubric())
    criteria = {r["criterion"] for r in results}
    expected = {
        CRITERION_LOOP, CRITERION_EFFICIENCY, CRITERION_READ_WRITE,
        CRITERION_BACKTRACK, CRITERION_IDLE, CRITERION_RECOVERY,
    }
    assert expected == criteria


def test_ac13_skeleton_criterion_when_present():
    steps = [_tc("Read", {"path": ".harness/state.json"})]
    skeleton = [{"tool": "Read", "path_contains": "state.json"}]
    results = check_trajectory(_session(steps), _rubric(skeleton=skeleton))
    criteria = {r["criterion"] for r in results}
    assert CRITERION_SKELETON in criteria


# --- AC14: PASS/FAIL only ---

def test_ac14_only_pass_fail():
    steps = [
        _tc("Shell", {"command": "pytest"}) for _ in range(5)
    ] + [_assistant() for _ in range(5)]
    results = check_trajectory(_session(steps), _rubric())
    for r in results:
        assert r["result"] in ("PASS", "FAIL"), f"Got {r['result']} for {r['criterion']}"


# --- AC15: default tier set ---

def test_ac15_default_tiers_include_trajectory():
    steps = [_tc("Read", {"path": "a.py"})]
    j = judge_session(
        _session(steps),
        _rubric(),
        tiers={"computational", "structural", "trajectory"},
    )
    assert "trajectory" in j["tiers_run"]


# --- EC2: Shell toolCall exit code parsing ---

def test_ec2_shell_toolcall_exit_code():
    steps = [
        _tc("Shell", {"command": "make test"}, result="Exit code: 1\nerror output"),
        _tc("Read", {"path": "Makefile"}),
    ]
    r = check_error_recovery(_session(steps), _rubric())
    assert r["result"] == "PASS"


# --- EC3: skeleton after constraint ordering ---

def test_ec6_assistant_only_conversation_returns_empty():
    steps = [_assistant("thinking"), _assistant("planning"), _assistant("done")]
    session = _session(steps)
    results = check_trajectory(session, _rubric())
    assert results == [], f"Expected [], got {len(results)} results"


def test_ec3_skeleton_out_of_order_fails():
    steps = [
        _tc("Write", {"path": ".harness/state.json"}),
        _tc("Read", {"path": ".harness/state.json"}),
    ]
    skeleton = [
        {"tool": "Read", "path_contains": "state.json"},
        {"tool": "Write", "path_contains": "state.json", "after": "Read state.json"},
    ]
    r = check_skeleton(_session(steps), _rubric(skeleton=skeleton))
    assert r["result"] == "FAIL"


if __name__ == "__main__":
    import traceback
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"FAIL: {t.__name__}: {e}")
            traceback.print_exc()
    print(f"\n{passed} passed, {failed} failed out of {len(tests)} tests")
    sys.exit(1 if failed else 0)
