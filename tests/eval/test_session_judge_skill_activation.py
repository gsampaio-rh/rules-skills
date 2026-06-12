"""Unit tests for check_skill_activation() in session_judge.py.

Tests all branches: code-review, code-quality-audit, llm-skeptic, no-harness,
plus EC1 (unmatched) and EC2 (empty transcript) per chore-skill-scenarios contract.
"""

from __future__ import annotations

import pytest

from tests.eval.session_judge import check_skill_activation


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _make_session(transcript_text: str = "", has_contract: bool = False) -> dict:
    """Build a minimal session dict for skill_activation tests."""
    transcript = []
    if transcript_text:
        transcript = [{"role": "user", "content": "prompt", "response": transcript_text}]
    return {
        "transcript": transcript,
        "artifacts": {
            "harness": {"contract.json": {"phase": "building"} if has_contract else {}},
        },
    }


def _make_rubric(skill_activation: list[str]) -> dict:
    return {"post_hoc_rubric": {"skill_activation": skill_activation}}


# ─── code-review branch ───────────────────────────────────────────────────────


def test_code_review_positive():
    session = _make_session("CRITICAL: sql injection vulnerability found. HIGH: security issue.")
    rubric = _make_rubric(["code-review skill: output includes severity table"])
    results = check_skill_activation(session, rubric)
    assert len(results) == 1
    assert results[0]["result"] == "PASS"


def test_code_review_negative():
    session = _make_session("The code looks fine, I made some changes.")
    rubric = _make_rubric(["code-review skill: output includes severity table"])
    results = check_skill_activation(session, rubric)
    assert results[0]["result"] == "FAIL"


def test_code_review_empty_transcript():
    """EC2: empty transcript -> FAIL for transcript-dependent branch."""
    session = _make_session("")
    rubric = _make_rubric(["code-review skill: output includes severity table"])
    results = check_skill_activation(session, rubric)
    assert results[0]["result"] == "FAIL"


# ─── code-quality-audit branch ───────────────────────────────────────────────


def test_code_quality_audit_positive():
    """AC4 + AC9(a): SOLID violation + complexity detected → PASS."""
    transcript = (
        "The ReportManager class violates SRP (Single Responsibility Principle). "
        "It handles too many concerns — high coupling between email, storage, and reporting. "
        "Function size exceeds 50 lines in generate_report. DRY violations throughout."
    )
    session = _make_session(transcript)
    rubric = _make_rubric(["code-quality-audit skill: identifies SOLID violations"])
    results = check_skill_activation(session, rubric)
    assert results[0]["result"] == "PASS"


def test_code_quality_audit_negative():
    """AC9(e): generic text without quality indicators → FAIL."""
    session = _make_session("The code works well. I reviewed the module and it looks correct.")
    rubric = _make_rubric(["code-quality-audit skill: identifies SOLID violations"])
    results = check_skill_activation(session, rubric)
    assert results[0]["result"] == "FAIL"


def test_code_quality_audit_empty_transcript():
    """EC2: empty transcript → FAIL."""
    session = _make_session("")
    rubric = _make_rubric(["code-quality-audit skill: identifies SOLID violations"])
    results = check_skill_activation(session, rubric)
    assert results[0]["result"] == "FAIL"


def test_code_quality_audit_criterion_variant():
    """AC4: 'code quality audit' (space) also triggers the branch."""
    transcript = "SOLID violation: single responsibility broken. Complexity is high, coupling too tight."
    session = _make_session(transcript)
    rubric = _make_rubric(["code quality audit skill: SOLID and complexity"])
    results = check_skill_activation(session, rubric)
    assert results[0]["result"] == "PASS"


# ─── llm-skeptic branch ───────────────────────────────────────────────────────


def test_llm_skeptic_positive():
    """AC5 + AC9(b): skeptic signals → PASS."""
    transcript = (
        "Before adding an LLM, I'd challenge whether this is necessary. "
        "A simpler rule-based approach with regex and keyword matching would handle 90% of cases "
        "at near-zero cost, without the complexity of an external API. "
        "LLM integration here feels like overkill."
    )
    session = _make_session(transcript)
    rubric = _make_rubric(["llm-skeptic skill: agent questions whether LLM is needed"])
    results = check_skill_activation(session, rubric)
    assert results[0]["result"] == "PASS"


def test_llm_skeptic_negative():
    """AC9(e): directly implements LLM without questioning → FAIL."""
    session = _make_session(
        "I will integrate OpenAI GPT for sentiment analysis. Here is the implementation..."
    )
    rubric = _make_rubric(["llm-skeptic skill: agent questions whether LLM is needed"])
    results = check_skill_activation(session, rubric)
    assert results[0]["result"] == "FAIL"


def test_llm_skeptic_empty_transcript():
    """EC2: empty transcript → FAIL."""
    session = _make_session("")
    rubric = _make_rubric(["llm-skeptic skill: agent questions whether LLM is needed"])
    results = check_skill_activation(session, rubric)
    assert results[0]["result"] == "FAIL"


def test_llm_skeptic_criterion_variant():
    """AC5: 'llm skeptic' (space) also triggers the branch."""
    transcript = "A heuristic-based alternative would be simpler and less costly."
    session = _make_session(transcript)
    rubric = _make_rubric(["llm skeptic skill: proposes simpler alternative"])
    results = check_skill_activation(session, rubric)
    assert results[0]["result"] == "PASS"


# ─── no-harness branch ────────────────────────────────────────────────────────


def test_no_harness_passes_when_no_contract():
    session = _make_session("Done.", has_contract=False)
    rubric = _make_rubric(["no harness expected for this simple task"])
    results = check_skill_activation(session, rubric)
    assert results[0]["result"] == "PASS"


def test_no_harness_fails_when_contract_exists():
    session = _make_session("Done.", has_contract=True)
    rubric = _make_rubric(["no harness expected for this simple task"])
    results = check_skill_activation(session, rubric)
    assert results[0]["result"] == "FAIL"


# ─── EC1: unmatched criterion ─────────────────────────────────────────────────


def test_unmatched_criterion_passes_with_heuristic_no_exception():
    """EC1: unknown criterion text → PASS + Pattern-based heuristic, no exception."""
    session = _make_session("Some output about things.")
    rubric = _make_rubric(["completely-unknown-skill: does something exotic"])
    results = check_skill_activation(session, rubric)
    assert results[0]["result"] == "PASS"
    assert "heuristic" in results[0]["evidence"].lower()


# ─── Empty rubric ─────────────────────────────────────────────────────────────


def test_empty_skill_activation_rubric_returns_empty():
    """No skill_activation in rubric → empty list, no crash."""
    session = _make_session("Some output.")
    rubric = {"post_hoc_rubric": {}}
    results = check_skill_activation(session, rubric)
    assert results == []


# ─── Multiple criteria in one session ─────────────────────────────────────────


def test_multiple_criteria_all_evaluated():
    """Multiple skill_activation criteria in same scenario all get evaluated."""
    transcript = (
        "CRITICAL severity: sql injection. Finding: vulnerability in auth module. "
        "SOLID violation: high coupling. Complexity: function too long."
    )
    session = _make_session(transcript)
    rubric = _make_rubric([
        "code-review skill: severity table present",
        "code-quality-audit skill: SOLID violations identified",
    ])
    results = check_skill_activation(session, rubric)
    assert len(results) == 2
    assert all(r["result"] == "PASS" for r in results)
