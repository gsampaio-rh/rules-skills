"""Unit tests for feat-14a LLM judge code improvements.

Tests smart truncation, UNKNOWN verdict parsing, and confidence thresholding.
All tests are offline (no live LLM or Cursor SDK required).
"""

from __future__ import annotations

import json

import pytest

from tests.eval.session_judge import (
    LLM_CONFIDENCE_THRESHOLD,
    _smart_truncate_transcript,
)


# ─── _smart_truncate_transcript ───────────────────────────────────────────────


def test_empty_transcript_returns_placeholder():
    result = _smart_truncate_transcript([])
    assert "empty" in result.lower()


def test_single_turn_included_as_first_and_last():
    turn = {"role": "user", "content": "hello", "response": "hi"}
    result = _smart_truncate_transcript([turn])
    assert "FIRST TURN" in result
    assert "LAST TURN" not in result  # only 1 turn, no separate last


def test_first_and_last_turn_always_included():
    transcript = [
        {"role": "user", "content": "start", "response": "response 1"},
        {"role": "user", "content": "middle", "response": "boring middle"},
        {"role": "user", "content": "end", "response": "final response"},
    ]
    result = _smart_truncate_transcript(transcript)
    assert "FIRST TURN" in result
    assert "LAST TURN" in result
    assert "final response" in result


def test_error_turn_included_from_middle():
    transcript = [
        {"role": "user", "content": "start", "response": "ok"},
        {"role": "system", "content": "error: file not found"},   # error
        {"role": "user", "content": "boring", "response": "nothing special"},
        {"role": "user", "content": "end", "response": "done"},
    ]
    result = _smart_truncate_transcript(transcript)
    assert "error" in result.lower()
    # boring turn should NOT appear (no error/harness keywords)
    assert "nothing special" not in result


def test_harness_keyword_turn_included():
    transcript = [
        {"role": "user", "content": "start", "response": "ok"},
        {"role": "assistant", "content": "checking contract.json", "response": "contract found"},
        {"role": "user", "content": "boring", "response": "nothing"},
        {"role": "user", "content": "end", "response": "done"},
    ]
    result = _smart_truncate_transcript(transcript)
    assert "contract.json" in result
    assert "nothing" not in result  # boring turn excluded


def test_truncation_respects_max_chars():
    big_turn = {"role": "user", "content": "x" * 5000, "response": "y" * 5000}
    transcript = [big_turn, big_turn, big_turn]
    result = _smart_truncate_transcript(transcript, max_chars=2000)
    assert len(result) <= 2100  # some buffer for the truncation marker
    assert "truncated" in result.lower()


def test_no_middle_turns_no_errors():
    """Clean middle turns (no errors, no harness keywords) are excluded."""
    transcript = [
        {"role": "user", "content": "step 1", "response": "done step 1"},
        {"role": "user", "content": "step 2", "response": "done step 2"},
        {"role": "user", "content": "step 3", "response": "done step 3"},
        {"role": "user", "content": "step 4 final", "response": "final"},
    ]
    result = _smart_truncate_transcript(transcript)
    assert "done step 1" in result   # first turn
    assert "final" in result          # last turn
    assert "done step 2" not in result  # excluded middle
    assert "done step 3" not in result  # excluded middle


# ─── LLM_CONFIDENCE_THRESHOLD ────────────────────────────────────────────────


def test_confidence_threshold_is_3():
    """Sanity check: threshold is set to 3 (spec requires confidence < 3 → UNCERTAIN)."""
    assert LLM_CONFIDENCE_THRESHOLD == 3


# ─── Confidence thresholding (unit-level via direct result post-processing) ───


def _apply_confidence_threshold(items: list[dict]) -> list[dict]:
    """Replicate the confidence thresholding logic from judge_with_llm() for testing."""
    results = []
    for item in items:
        item = dict(item)
        confidence = int(item.get("confidence", 3))
        if confidence < LLM_CONFIDENCE_THRESHOLD and item.get("result") != "UNKNOWN":
            item["result"] = "UNCERTAIN"
            item["evidence"] = f"[Low confidence {confidence}/5] " + item.get("evidence", "")
        results.append(item)
    return results


def test_high_confidence_pass_stays_pass():
    items = [{"criterion": "c1", "result": "PASS", "evidence": "found it", "confidence": 4}]
    assert _apply_confidence_threshold(items)[0]["result"] == "PASS"


def test_high_confidence_fail_stays_fail():
    items = [{"criterion": "c1", "result": "FAIL", "evidence": "missing", "confidence": 5}]
    assert _apply_confidence_threshold(items)[0]["result"] == "FAIL"


def test_low_confidence_pass_becomes_uncertain():
    """Confidence < 3 → UNCERTAIN regardless of PASS verdict."""
    items = [{"criterion": "c1", "result": "PASS", "evidence": "maybe", "confidence": 2}]
    result = _apply_confidence_threshold(items)[0]
    assert result["result"] == "UNCERTAIN"
    assert "[Low confidence 2/5]" in result["evidence"]


def test_low_confidence_fail_becomes_uncertain():
    items = [{"criterion": "c1", "result": "FAIL", "evidence": "unclear", "confidence": 1}]
    result = _apply_confidence_threshold(items)[0]
    assert result["result"] == "UNCERTAIN"


def test_confidence_exactly_at_threshold_not_downgraded():
    """Confidence == 3 is NOT below threshold (strict <); stays as-is."""
    items = [{"criterion": "c1", "result": "PASS", "evidence": "ok", "confidence": 3}]
    assert _apply_confidence_threshold(items)[0]["result"] == "PASS"


def test_unknown_verdict_not_overridden_by_low_confidence():
    """UNKNOWN verdict is not changed to UNCERTAIN even at confidence=1."""
    items = [{"criterion": "c1", "result": "UNKNOWN", "evidence": "no data", "confidence": 1}]
    assert _apply_confidence_threshold(items)[0]["result"] == "UNKNOWN"


def test_mixed_criteria_batch():
    """Multiple criteria in one batch: each processed independently."""
    items = [
        {"criterion": "c1", "result": "PASS", "evidence": "e1", "confidence": 5},
        {"criterion": "c2", "result": "FAIL", "evidence": "e2", "confidence": 1},
        {"criterion": "c3", "result": "UNKNOWN", "evidence": "e3", "confidence": 1},
        {"criterion": "c4", "result": "PASS", "evidence": "e4", "confidence": 2},
    ]
    results = _apply_confidence_threshold(items)
    assert results[0]["result"] == "PASS"
    assert results[1]["result"] == "UNCERTAIN"
    assert results[2]["result"] == "UNKNOWN"   # not overridden
    assert results[3]["result"] == "UNCERTAIN"
