"""
Behavioral tests for fix-breadcrumb-window: _load_breadcrumbs in context-package.py
filters session_start system noise before building the 3-entry window.

Imports _load_breadcrumbs directly from library/cursor/hooks/context-package.py
(canonical source, not the deployed .cursor/ copy).
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent
_spec = importlib.util.spec_from_file_location(
    "context_package",
    REPO_ROOT / "library" / "cursor" / "hooks" / "context-package.py",
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

_load_breadcrumbs = _mod._load_breadcrumbs
BREADCRUMB_WINDOW = _mod.BREADCRUMB_WINDOW


def _write(tmp_path: Path, entries: list[dict]) -> Path:
    p = tmp_path / "breadcrumbs.jsonl"
    p.write_text("\n".join(json.dumps(e) for e in entries) + "\n")
    return p


def _noise(ts: str) -> dict:
    return {"ts": ts, "role": "system", "type": "session_start", "feat": None, "msg": "s"}


def _signal(ts: str, type_: str = "build") -> dict:
    return {"ts": ts, "role": "builder", "type": type_, "feat": "task-1", "msg": "x"}


# ---------------------------------------------------------------------------
# AC1 — ≥3 non-noise entries: window contains only non-noise
# ---------------------------------------------------------------------------

def test_window_excludes_noise_when_enough_signal(tmp_path):
    entries = [
        _noise("T01"), _noise("T02"),
        _signal("T03"), _signal("T04"), _signal("T05"),
    ]
    result = _load_breadcrumbs(_write(tmp_path, entries))

    assert len(result) == BREADCRUMB_WINDOW
    for e in result:
        assert not (e["role"] == "system" and e["type"] == "session_start"), (
            f"Noise entry leaked into window: {e}"
        )


def test_window_is_last_3_non_noise_chronologically(tmp_path):
    entries = [_signal(f"T0{i}", "build") for i in range(1, 6)]
    entries += [_noise("T06")]

    result = _load_breadcrumbs(_write(tmp_path, entries))

    assert [e["ts"] for e in result] == ["T03", "T04", "T05"]


# ---------------------------------------------------------------------------
# AC2 — k non-noise (0 < k < 3): pad with most-recent noise in chronological order
# ---------------------------------------------------------------------------

def test_window_pads_with_noise_when_few_signal(tmp_path):
    # 1 signal + 5 noise; window should be [signal, noise4, noise5]
    noise_entries = [_noise(f"N0{i}") for i in range(1, 6)]
    signal = _signal("S01")
    entries = noise_entries + [signal]  # signal is most recent

    # only 1 non-noise, pad_needed=2 → noise[-2:] = [N04, N05]
    result = _load_breadcrumbs(_write(tmp_path, entries))

    assert len(result) == 3
    assert result[0]["ts"] == "S01"   # non-noise first
    assert result[1]["ts"] == "N04"   # most-recent noise (2nd-to-last)
    assert result[2]["ts"] == "N05"   # most-recent noise (last)


def test_window_2_signal_1_noise_pad(tmp_path):
    entries = [_noise("N01"), _signal("S01"), _signal("S02")]

    result = _load_breadcrumbs(_write(tmp_path, entries))

    assert len(result) == 3
    assert result[0]["ts"] == "S01"
    assert result[1]["ts"] == "S02"
    assert result[2]["ts"] == "N01"   # only available noise


# ---------------------------------------------------------------------------
# AC3 — zero non-noise: returns parsed[-3:] (original behavior)
# ---------------------------------------------------------------------------

def test_all_noise_falls_back_to_last_3(tmp_path):
    entries = [_noise(f"N0{i}") for i in range(1, 7)]  # 6 noise entries

    result = _load_breadcrumbs(_write(tmp_path, entries))

    assert len(result) == 3
    assert [e["ts"] for e in result] == ["N04", "N05", "N06"]


# ---------------------------------------------------------------------------
# AC4 — BREADCRUMB_WINDOW constant unchanged
# ---------------------------------------------------------------------------

def test_breadcrumb_window_constant_is_3():
    assert BREADCRUMB_WINDOW == 3


# ---------------------------------------------------------------------------
# EC1 — empty file
# ---------------------------------------------------------------------------

def test_empty_file_returns_empty(tmp_path):
    p = tmp_path / "breadcrumbs.jsonl"
    p.write_text("")
    assert _load_breadcrumbs(p) == []


def test_missing_file_returns_empty(tmp_path):
    assert _load_breadcrumbs(tmp_path / "nonexistent.jsonl") == []


# ---------------------------------------------------------------------------
# EC2 — exactly 3 entries, all noise
# ---------------------------------------------------------------------------

def test_exactly_3_noise_returns_all_3(tmp_path):
    entries = [_noise("N01"), _noise("N02"), _noise("N03")]

    result = _load_breadcrumbs(_write(tmp_path, entries))

    assert len(result) == 3
    assert [e["ts"] for e in result] == ["N01", "N02", "N03"]


# ---------------------------------------------------------------------------
# EC3 — 1 non-noise + 10 noise: window = [non_noise, noise[-2], noise[-1]]
# ---------------------------------------------------------------------------

def test_1_signal_10_noise_exact_window(tmp_path):
    noise_entries = [_noise(f"N{i:02d}") for i in range(1, 11)]
    signal = _signal("S01")
    entries = noise_entries + [signal]

    result = _load_breadcrumbs(_write(tmp_path, entries))

    assert len(result) == 3
    assert result[0]["ts"] == "S01"   # index 0: the non-noise entry
    assert result[1]["ts"] == "N09"   # index 1: noise[-2]
    assert result[2]["ts"] == "N10"   # index 2: noise[-1]
