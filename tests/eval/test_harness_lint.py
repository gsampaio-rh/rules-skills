"""Tests for tests/eval/harness_lint.py — timestamp delta threshold logic."""

import json
from pathlib import Path

import pytest

from tests.eval.harness_lint import lint_breadcrumbs


def _bc(ts: str, msg: str = "test") -> str:
    return json.dumps({"ts": ts, "role": "builder", "type": "build", "msg": msg})


def _write_bc(path: Path, *timestamps: str) -> Path:
    path.write_text("\n".join(_bc(ts) for ts in timestamps) + "\n")
    return path


class TestTimestampDeltaThreshold:
    def test_drift_under_8h_produces_info_not_warning(self, tmp_path):
        bc = _write_bc(tmp_path / "breadcrumbs.jsonl", "2026-06-12T14:00:00Z", "2026-06-12T07:00:00Z")
        errors, warnings, infos = lint_breadcrumbs(bc)
        assert not errors
        assert not warnings, f"Expected no warnings for 7h drift, got: {warnings}"
        assert len(infos) == 1
        assert "7.0h" in infos[0]
        assert "suppressed" in infos[0]

    def test_drift_exactly_8h_produces_warning(self, tmp_path):
        bc = _write_bc(tmp_path / "breadcrumbs.jsonl", "2026-06-12T16:00:00Z", "2026-06-12T08:00:00Z")
        errors, warnings, infos = lint_breadcrumbs(bc)
        assert len(warnings) == 1, "Boundary of exactly 8h should WARN"
        assert "out of order" in warnings[0]
        assert not infos

    def test_drift_over_8h_produces_warning(self, tmp_path):
        bc = _write_bc(tmp_path / "breadcrumbs.jsonl", "2026-06-12T20:00:00Z", "2026-06-12T08:00:00Z")
        errors, warnings, infos = lint_breadcrumbs(bc)
        assert len(warnings) == 1
        assert not infos

    def test_drift_zero_produces_nothing(self, tmp_path):
        ts = "2026-06-12T10:00:00Z"
        bc = _write_bc(tmp_path / "breadcrumbs.jsonl", ts, ts)
        errors, warnings, infos = lint_breadcrumbs(bc)
        assert not warnings
        assert not infos

    def test_in_order_timestamps_produce_nothing(self, tmp_path):
        bc = _write_bc(tmp_path / "breadcrumbs.jsonl", "2026-06-12T10:00:00Z", "2026-06-12T11:00:00Z")
        errors, warnings, infos = lint_breadcrumbs(bc)
        assert not warnings
        assert not infos

    def test_1h_timezone_drift_is_info(self, tmp_path):
        bc = _write_bc(tmp_path / "breadcrumbs.jsonl", "2026-06-12T10:00:00+00:00", "2026-06-12T09:00:00Z")
        errors, warnings, infos = lint_breadcrumbs(bc)
        assert not warnings
        assert len(infos) == 1
        assert "1.0h" in infos[0]

    def test_mixed_in_and_out_of_order(self, tmp_path):
        entries = [
            "2026-06-12T10:00:00Z",
            "2026-06-12T11:00:00Z",
            "2026-06-12T07:00:00Z",
            "2026-06-12T12:00:00Z",
        ]
        bc = _write_bc(tmp_path / "breadcrumbs.jsonl", *entries)
        errors, warnings, infos = lint_breadcrumbs(bc)
        assert not warnings
        assert len(infos) == 1, "Only the 4h drift (12:00→07:00) should produce INFO"

    @pytest.mark.parametrize("delta_hours,expect_warn", [
        (0.5, False),
        (3.0, False),
        (7.9, False),
        (8.0, True),
        (8.1, True),
        (12.0, True),
    ])
    def test_threshold_boundary_parametrized(self, tmp_path, delta_hours, expect_warn):
        from datetime import datetime, timedelta, timezone
        base = datetime(2026, 6, 12, 20, 0, 0, tzinfo=timezone.utc)
        earlier = base - timedelta(hours=delta_hours)
        bc = _write_bc(
            tmp_path / "breadcrumbs.jsonl",
            base.isoformat(),
            earlier.isoformat(),
        )
        errors, warnings, infos = lint_breadcrumbs(bc)
        if expect_warn:
            assert warnings, f"Expected WARN for {delta_hours}h drift"
            assert not infos
        else:
            assert not warnings, f"Expected no WARN for {delta_hours}h drift"
            assert infos


class TestLintBreadcrumbsReturnShape:
    def test_returns_three_tuple(self, tmp_path):
        bc = tmp_path / "breadcrumbs.jsonl"
        bc.write_text("")
        result = lint_breadcrumbs(bc)
        assert len(result) == 3, "lint_breadcrumbs must return (errors, warnings, infos)"

    def test_missing_file_returns_three_tuple(self, tmp_path):
        bc = tmp_path / "no_such_file.jsonl"
        result = lint_breadcrumbs(bc)
        assert len(result) == 3
