"""Regression tests for _evaluate_behavioral and UNMATCHED verdict handling.

Covers AC9 (synthetic + known criterion) and EC3 (scoring formula).
"""

import pytest
from tests.eval.session_judge import (
    _evaluate_behavioral,
    check_behavioral,
    judge_session,
)


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
