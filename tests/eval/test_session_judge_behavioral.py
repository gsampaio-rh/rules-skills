"""Regression tests for _evaluate_behavioral and UNMATCHED verdict handling.

Covers:
- Existing: UNMATCHED sentinel (AC9), scoring formula (EC3)
- gap-26: proceed merge (4/5), concise-response merge (19/21), defer tightening (10),
  plan-update artifact detection (13), session boundary consolidation (16/17),
  empty-transcript handling, branch count, baseline regression
"""

import ast
import json
from pathlib import Path

import pytest
from tests.eval.session_judge import (
    _check_session_boundary,
    _evaluate_behavioral,
    check_behavioral,
    judge_session,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _make_session(transcript_text: str = "", **harness_overrides) -> dict:
    harness = {
        "state.json": {"tasks": []},
        "contract.json": {},
        "breadcrumbs.jsonl": [],
    }
    harness.update(harness_overrides)
    return {
        "scenario_id": "test",
        "model": "test",
        "transcript": [{"response": transcript_text}] if transcript_text else [],
        "artifacts": {"harness": harness},
    }


class TestUnmatchedSentinel:
    """AC9: synthetic unmatched → UNMATCHED, known criterion → PASS."""

    def test_synthetic_returns_none(self):
        session = _make_session("normal text")
        result = _evaluate_behavioral("__synthetic_unmatched__", "normal text", session)
        assert result is None

    def test_known_no_apologies_returns_true(self):
        session = _make_session("This response has no apologies.")
        result = _evaluate_behavioral("No apologies in transcript", "This response has no apologies.", session)
        assert result is True

    def test_known_no_apologies_with_apology_returns_false(self):
        text = "I'm sorry about the confusion."
        session = _make_session(text)
        result = _evaluate_behavioral("No apologies in transcript", text, session)
        assert result is False


class TestCheckBehavioralUnmatched:
    """UNMATCHED propagates through check_behavioral correctly."""

    def test_unmatched_criterion_produces_unmatched_result(self):
        session = _make_session("normal text")
        rubric = {"post_hoc_rubric": {"behavioral": ["__synthetic_unmatched__"]}}
        results = check_behavioral(session, rubric)
        assert len(results) == 1
        assert results[0]["result"] == "UNMATCHED"
        assert "warning" in results[0]

    def test_matched_criterion_produces_pass_or_uncertain(self):
        session = _make_session("normal text without apologies")
        rubric = {"post_hoc_rubric": {"behavioral": ["No apologies in transcript"]}}
        results = check_behavioral(session, rubric)
        assert len(results) == 1
        assert results[0]["result"] in ("PASS", "UNCERTAIN")

    def test_mixed_criteria(self):
        session = _make_session("normal text without apologies")
        rubric = {"post_hoc_rubric": {"behavioral": [
            "No apologies in transcript",
            "__synthetic_unmatched__",
        ]}}
        results = check_behavioral(session, rubric)
        assert len(results) == 2
        verdicts = {r["criterion"]: r["result"] for r in results}
        assert verdicts["No apologies in transcript"] in ("PASS", "UNCERTAIN")
        assert verdicts["__synthetic_unmatched__"] == "UNMATCHED"


class TestScoringFormulaEC3:
    """EC3: UNMATCHED is not counted as PASS in the scoring formula."""

    def test_unmatched_not_counted_as_pass(self):
        session = _make_session("normal text")
        rubric = {
            "post_hoc_rubric": {
                "behavioral": ["__synthetic_unmatched__"],
            },
            "computational": [],
        }
        judgment = judge_session(session, rubric, tiers={"structural"})
        summary = judgment["summary"]
        assert summary["unmatched"] >= 1
        assert summary["pass"] == 0
        assert summary["score"] == 0.0

    def test_pass_plus_unmatched_score(self):
        session = _make_session("clean text no apologies")
        rubric = {
            "post_hoc_rubric": {
                "behavioral": [
                    "No apologies in transcript",
                    "__synthetic_unmatched__",
                ],
            },
            "computational": [],
        }
        judgment = judge_session(session, rubric, tiers={"structural"})
        summary = judgment["summary"]
        assert summary["pass"] >= 1
        assert summary["unmatched"] >= 1
        expected_score = round(summary["pass"] / summary["total"], 2)
        assert summary["score"] == expected_score


# ─── gap-26: Merged proceed/ask-permission branch (4/5) ──────────────────────


class TestProceedMerge:
    """Branches 4/5 merged: proceed/ask-permission patterns."""

    @pytest.mark.parametrize("criterion,transcript,expected", [
        ("No 'shall I proceed?' before making changes", "Just doing the work.", True),
        ("No 'shall I proceed?' before making changes", "Shall I proceed with this?", False),
        ("Change made directly without asking 'should I proceed?'", "Implemented it.", True),
        ("Implemented directly without ceremony", "Done without ceremony.", True),
    ])
    def test_proceed_branch_results(self, criterion, transcript, expected):
        session = _make_session(transcript)
        result = _evaluate_behavioral(criterion, transcript, session)
        assert result == expected

    def test_ec2_should_implement_does_not_trigger_proceed(self):
        """EC2: 'should implement' must NOT enter proceed branch."""
        session = _make_session("Working on it.")
        result = _evaluate_behavioral("Agent should implement the feature", "Working on it.", session)
        assert result is None  # UNMATCHED — does not match proceed

    def test_ec3_commit_not_proceed(self):
        """EC3: 'Shall I commit?' is commit-approval, not proceed."""
        session = _make_session("Shall I commit these changes?")
        result = _evaluate_behavioral(
            "Agent asked the user for commit approval before creating the flag file",
            "Shall I commit these changes?",
            session,
        )
        assert result is True  # routes to commit-approval branch


# ─── gap-26: Merged concise-response branch (19/21) ──────────────────────────


class TestConciseResponseMerge:
    """Branches 19/21 merged: concise-response (<800 words)."""

    @pytest.mark.parametrize("criterion", [
        "Agent presented focused summary (pending feature, last activity)",
        "Agent did NOT produce a long project exploration or full README-style summary",
        "Agent resumed work without re-exploring the entire codebase",
        "Agent focused on existing contract and pending work, not full project exploration",
    ])
    def test_short_response_passes(self, criterion):
        session = _make_session("Short focused response about the task.")
        result = _evaluate_behavioral(criterion, "Short focused response about the task.", session)
        assert result is True

    def test_long_response_fails(self):
        long_text = " ".join(["word"] * 900)
        session = _make_session(long_text)
        result = _evaluate_behavioral("Agent presented focused summary", long_text, session)
        assert result is False

    def test_ac3_empty_transcript_returns_false(self):
        """AC3: Empty transcript → False (UNCERTAIN), not None (UNMATCHED)."""
        session = _make_session("")
        result = _evaluate_behavioral("Agent presented focused summary", "", session)
        assert result is False

    def test_no_transcript_returns_false(self):
        """AC3: Session with no transcript entries → False."""
        session = {"transcript": [], "artifacts": {"harness": {}}}
        result = _evaluate_behavioral(
            "Agent did NOT produce a long project exploration",
            "",
            session,
        )
        assert result is False


# ─── gap-26: Tightened defer branch (10) ──────────────────────────────────────


class TestDeferBranchTightened:
    """Branch 10: defer regex reduced to core signals."""

    @pytest.mark.parametrize("phrase", [
        "We should defer this.",
        "That is out of scope for this task.",
        "This is off-plan work.",
        "Create a separate task for it.",
        "This is scope creep.",
    ])
    def test_positive_defer_phrases_match(self, phrase):
        session = _make_session(phrase)
        result = _evaluate_behavioral("Agent deferred off-plan requests", phrase, session)
        assert result is True

    @pytest.mark.parametrize("phrase", [
        "feat-3 is in the backlog",
        "Let us focus on feat-1",
        "I will continue with the current task",
        "Added later: support for JSON",
    ])
    def test_ec4_negative_phrases_do_not_match(self, phrase):
        """EC4: high-FP terms removed from defer regex."""
        session = _make_session(phrase)
        result = _evaluate_behavioral("Agent deferred off-plan requests", phrase, session)
        assert result is False


# ─── gap-26: Strengthened plan-update branch (13) ────────────────────────────


class TestPlanUpdateArtifact:
    """Branch 13: artifact-based detection instead of indirect heuristic."""

    def test_ac5_breadcrumb_with_plan_update_returns_true(self):
        session = _make_session(
            "Updated direction.",
            **{"breadcrumbs.jsonl": [
                {"type": "build", "msg": "Updated state.json direction field", "role": "builder"},
            ]},
        )
        result = _evaluate_behavioral(
            "Agent updated plan fields in state.json, not just code",
            "Updated direction.",
            session,
        )
        assert result is True

    def test_ec5_no_plan_signals_returns_false(self):
        """EC5: No plan-update breadcrumbs + state unchanged → False."""
        session = _make_session(
            "Working on the feature.",
            **{"breadcrumbs.jsonl": [
                {"type": "build", "msg": "Implemented the handler", "role": "builder"},
            ]},
        )
        result = _evaluate_behavioral(
            "Agent updated plan fields in state.json, not just code",
            "Working on the feature.",
            session,
        )
        assert result is False

    def test_trade_off_breadcrumb_matches(self):
        session = _make_session(
            "Discovered trade-off.",
            **{"breadcrumbs.jsonl": [
                {"type": "decision", "msg": "Added trade_off: chose JSON over YAML", "role": "builder"},
            ]},
        )
        result = _evaluate_behavioral(
            "Agent proactively updated plan after discovering constraints",
            "Discovered trade-off.",
            session,
        )
        assert result is True

    def test_protocol_replan_mid_build_positive(self):
        """AC5 positive fixture from protocol-replan-mid-build scenario seed."""
        session = _make_session(
            "Updated state.json with new direction after discovering YAML requirement.",
            **{"breadcrumbs.jsonl": [
                {"type": "plan", "msg": "Created state: 2 features. Direction: JSON-only.", "role": "planner"},
                {"type": "negotiate", "msg": "Contract for JSON config loader", "role": "builder"},
                {"type": "build", "msg": "Updated state.json direction to include YAML", "role": "builder"},
            ]},
        )
        result = _evaluate_behavioral(
            "Agent updated plan fields in state.json, not just code",
            "Updated state.json with new direction after discovering YAML requirement.",
            session,
        )
        assert result is True

    def test_trace_state_json_write_detection(self):
        """AC5 path (b): trace-based detection of state.json writes."""
        session = {
            "scenario_id": "test",
            "model": "test",
            "transcript": [{
                "response": "Updating direction.",
                "conversation": [
                    {"type": "toolCall", "name": "Read", "args": {"path": ".harness/state.json"}, "result": "{}"},
                    {"type": "toolCall", "name": "StrReplace", "args": {"path": ".harness/state.json", "old_string": "old", "new_string": "new"}, "result": "ok"},
                ],
            }],
            "artifacts": {"harness": {
                "state.json": {"tasks": []},
                "breadcrumbs.jsonl": [
                    {"type": "build", "msg": "Implemented handler", "role": "builder"},
                ],
            }},
        }
        result = _evaluate_behavioral(
            "Agent updated plan fields in state.json, not just code",
            "Updating direction.",
            session,
        )
        assert result is True


# ─── gap-26: Consolidated session boundary (16/17) ───────────────────────────


class TestSessionBoundaryConsolidated:
    """Branches 16/17: shared helper with distinct trigger sets."""

    def test_branch16_positive_boundary_signal(self):
        result = _check_session_boundary(
            "agent suggested fresh thread or checkpoint",
            "Let's commit before continuing. Fresh thread recommended.",
        )
        assert result is True

    def test_branch16_no_signal(self):
        result = _check_session_boundary(
            "agent suggested fresh thread or checkpoint",
            "Working on the task.",
        )
        assert result is False

    def test_branch17_anti_silence_with_boundary(self):
        result = _check_session_boundary(
            "agent did not silently accept all tasks without pausing",
            "Let's commit first.",
        )
        assert result is True

    def test_branch17_anti_silence_only(self):
        result = _check_session_boundary(
            "agent did not silently continue complex work without acknowledging degraded context",
            "There are too many changes accumulating.",
        )
        assert result is True

    def test_branch17_no_signals_returns_false(self):
        result = _check_session_boundary(
            "agent did not silently accept all tasks without pausing",
            "Working on the task.",
        )
        assert result is False


# ─── gap-26: Branch count verification (AC11) ────────────────────────────────


class TestBranchCount:
    """AC11: top-level if count in _evaluate_behavioral ≤ 33."""

    def test_branch_count_reduced(self):
        source = Path(__file__).parent / "session_judge.py"
        tree = ast.parse(source.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_evaluate_behavioral":
                top_level_ifs = [n for n in node.body if isinstance(n, ast.If)]
                assert len(top_level_ifs) <= 33, (
                    f"Expected ≤33 top-level if statements, got {len(top_level_ifs)}"
                )
                return
        pytest.fail("_evaluate_behavioral function not found")


# ─── gap-26: Baseline regression check (AC7/AC10) ────────────────────────────


class TestBaselineRegression:
    """AC7/AC10: all 87 criteria match baseline."""

    def test_corpus_matches_baseline(self):
        baseline_path = FIXTURES_DIR / "behavioral_baseline.json"
        if not baseline_path.exists():
            pytest.skip("Baseline fixture not found")

        from tests.eval.capture_behavioral_baseline import capture_baseline

        current_path = Path("/tmp/test_behavioral_current.json")
        capture_baseline(current_path)

        baseline = json.loads(baseline_path.read_text())
        current = json.loads(current_path.read_text())

        assert len(baseline) == len(current), (
            f"Criterion count mismatch: baseline={len(baseline)}, current={len(current)}"
        )

        mismatches = []
        for b, c in zip(baseline, current):
            if b["expected_bool"] != c["expected_bool"]:
                mismatches.append(
                    f"[{b['scenario_id']}] {b['criterion'][:60]}: "
                    f"was={b['expected_bool']} now={c['expected_bool']}"
                )

        assert not mismatches, f"Regressions found:\n" + "\n".join(mismatches)

    def test_no_unmatched_in_corpus(self):
        baseline_path = FIXTURES_DIR / "behavioral_baseline.json"
        if not baseline_path.exists():
            pytest.skip("Baseline fixture not found")

        baseline = json.loads(baseline_path.read_text())
        unmatched = [b for b in baseline if b["expected_bool"] is None]
        assert not unmatched, f"UNMATCHED criteria: {[b['criterion'][:60] for b in unmatched]}"


# ─── gap-26: sys import cleanup (AC12) ───────────────────────────────────────


class TestSysImportCleanup:
    """AC12: no import inside _evaluate_behavioral."""

    def test_no_import_in_evaluate_behavioral(self):
        source = Path(__file__).parent / "session_judge.py"
        tree = ast.parse(source.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "_evaluate_behavioral":
                imports = [
                    n for n in ast.walk(node)
                    if isinstance(n, (ast.Import, ast.ImportFrom))
                ]
                assert not imports, (
                    f"Found import statements inside _evaluate_behavioral: "
                    f"{[ast.dump(i) for i in imports]}"
                )
                return
        pytest.fail("_evaluate_behavioral function not found")


class TestCheckHarnessAbsentSeeded:
    """Regression: _check_harness_absent must skip state.json check when seeded."""

    def _make_harness(self, has_state=True, has_contract=False, breadcrumbs=None):
        h = {}
        if has_state:
            h["state.json"] = {"tasks": [{"id": "spike-1"}]}
        if has_contract:
            h["contract.json"] = {"task_id": "spike-1"}
        h["breadcrumbs.jsonl"] = breadcrumbs or []
        return h

    def test_seeded_state_not_flagged(self):
        """state.json exists but is seeded → no state.json criterion in results."""
        from tests.eval.session_judge import _check_harness_absent
        harness = self._make_harness(has_state=True)
        rubric = {"seed_files": {".harness/state.json": "{}"}}
        results = _check_harness_absent(harness, rubric)
        criteria = [r["criterion"] for r in results]
        assert not any("state.json" in c for c in criteria), (
            "state.json criterion should be skipped when seeded"
        )

    def test_unseeded_state_still_flagged(self):
        """state.json exists and NOT seeded → FAIL criterion present."""
        from tests.eval.session_judge import _check_harness_absent
        harness = self._make_harness(has_state=True)
        results = _check_harness_absent(harness, {})
        state_results = [r for r in results if "state.json" in r["criterion"]]
        assert len(state_results) == 1
        assert state_results[0]["result"] == "FAIL"

    def test_absent_state_passes(self):
        """state.json absent and not seeded → PASS."""
        from tests.eval.session_judge import _check_harness_absent
        harness = self._make_harness(has_state=False)
        results = _check_harness_absent(harness, {})
        state_results = [r for r in results if "state.json" in r["criterion"]]
        assert len(state_results) == 1
        assert state_results[0]["result"] == "PASS"

    def test_seeded_breadcrumbs_excluded_from_activity_check(self):
        """Pre-seeded breadcrumbs with 'plan' type not counted as agent harness activity."""
        from tests.eval.session_judge import _check_harness_absent
        seeded_crumbs = [{"ts": "T", "role": "planner", "type": "plan", "msg": "seeded"}]
        harness = self._make_harness(has_state=True, breadcrumbs=seeded_crumbs)
        rubric = {
            "seed_files": {
                ".harness/state.json": "{}",
                ".harness/breadcrumbs.jsonl": '{"ts":"T","role":"planner","type":"plan","msg":"seeded"}\n',
            }
        }
        results = _check_harness_absent(harness, rubric)
        activity = next(r for r in results if "workflow activity" in r["criterion"])
        assert activity["result"] == "PASS", (
            "Seeded 'plan' breadcrumb should not count as agent harness activity"
        )
