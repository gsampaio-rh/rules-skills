"""Tests for session-review skill deterministic checker (feat-rca-p4)."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
REVIEW_PY = REPO_ROOT / "library" / "cursor" / "skills" / "session-review" / "review.py"
FIXTURES = REPO_ROOT / "tests" / "eval" / "fixtures" / "session-review"


def _run_review(root: Path) -> str:
    result = subprocess.run(
        [sys.executable, str(REVIEW_PY), "--root", str(root)],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    assert result.returncode == 0, result.stderr
    assert "Traceback" not in result.stderr
    return result.stdout


def test_planted_p2_p6_flags():
    out = _run_review(FIXTURES / "planted-p2-p6")
    assert re.search(r"\| P2 breadcrumbs \| FLAG \|", out)
    assert re.search(r"\| P6 handoff/rework \| FLAG \|", out)
    for pat in (
        r"\| P1 guidelines drift \| FLAG \|",
        r"\| P3 SVG friction \| FLAG \|",
        r"\| P4 number/facts \| FLAG \|",
        r"\| P5 gate misfire \| FLAG \|",
    ):
        assert not re.search(pat, out), pat


def test_clean_fixture_passes():
    out = _run_review(FIXTURES / "clean")
    assert len(re.findall(r"\| P[1-6] .* \| FLAG \|", out)) == 0


def test_no_harness_na_rows():
    out = _run_review(FIXTURES / "no-harness")
    assert re.search(r"\| P2 breadcrumbs \| N/A \|", out)
    assert re.search(r"\| P5 gate misfire \| N/A \|", out)
    assert re.search(r"\| P6 handoff/rework \| N/A \|", out)
    assert "no harness" in out.lower()
    assert len(re.findall(r"\| P[1-6] .* \| FLAG \|", out)) == 0


def test_review_help_exposes_root():
    result = subprocess.run(
        [sys.executable, str(REVIEW_PY), "--help"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    assert result.returncode == 0
    assert "--root" in result.stdout
