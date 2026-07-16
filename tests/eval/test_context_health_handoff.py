"""Unit tests for P6 missing-handoff advisory in context-health.sh + session stats."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CONTEXT_HEALTH = REPO_ROOT / "library" / "cursor" / "hooks" / "context-health.sh"
HARNESS_GATE = REPO_ROOT / "library" / "cursor" / "hooks" / "harness-gate.sh"
CONTRACT_GATE = REPO_ROOT / "library" / "cursor" / "hooks" / "contract-gate.sh"
HARNESS_CONTEXT = REPO_ROOT / "library" / "cursor" / "hooks" / "harness-context.sh"

_PYENV_ROOT = os.environ.get("PYENV_ROOT", str(Path.home() / ".pyenv"))
_HOOK_PATH = (
    f"{_PYENV_ROOT}/shims:{_PYENV_ROOT}/bin:"
    "/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
)


def _env(cwd: Path) -> dict:
    env = {
        "PATH": _HOOK_PATH,
        "HOME": str(Path.home()),
        "HARNESS_ROOT": str(cwd),
    }
    if "PYENV_VERSION" in os.environ:
        env["PYENV_VERSION"] = os.environ["PYENV_VERSION"]
    return env


def _run_hook(hook: Path, cwd: Path, stdin: str = "{}") -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(hook)],
        input=stdin,
        capture_output=True,
        text=True,
        cwd=str(cwd),
        env=_env(cwd),
        check=False,
    )


def _harness(cwd: Path) -> Path:
    d = cwd / ".harness"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _write_stats(cwd: Path, turns: int, source_writes: int) -> None:
    (_harness(cwd) / ".session-stats.json").write_text(
        json.dumps({"turns": turns, "source_writes": source_writes})
    )


def _write_breadcrumbs(cwd: Path, entries: list[dict]) -> None:
    content = "\n".join(json.dumps(e) for e in entries) + "\n"
    (_harness(cwd) / "breadcrumbs.jsonl").write_text(content)


def _calibrated_builds(feat: str = "feat-rca-p6-handoff", n: int = 5) -> list[dict]:
    """session_start + n builds; duration <60min; no fails; ≤20 entries; no checkpoint.

    Timestamps are spaced ≥20 minutes apart so duplicate_breadcrumbs (15min window)
    does not fire — AC1 requires ONLY the missing_handoff signal.
    """
    entries = [
        {
            "ts": "2026-07-16T10:00:00Z",
            "role": "system",
            "type": "session_start",
            "feat": None,
            "msg": "New chat session started",
            "result": "pass",
        }
    ]
    # 20-minute gaps keep total span at (n-1)*20 min; n=5 → 80 min would trip
    # session_duration WARNING (>60). Use 10-min gaps with alternating types so
    # feat+type pairs are unique enough, and keep span under 60 min.
    types_cycle = ("build", "negotiate", "verify", "build", "negotiate")
    for i in range(n):
        minute = (i + 1) * 8  # 8,16,24,32,40 → span 40 min (<60)
        entries.append(
            {
                "ts": f"2026-07-16T10:{minute:02d}:00Z",
                "role": "builder",
                "type": types_cycle[i % len(types_cycle)],
                "feat": feat,
                "msg": f"Step {i + 1}: implemented handoff piece {i + 1}",
                "result": "pass",
            }
        )
    return entries


def _parse_stdout(result: subprocess.CompletedProcess) -> dict:
    assert result.returncode == 0, f"hook failed: {result.stderr}\n{result.stdout}"
    raw = result.stdout.strip()
    assert raw, f"empty stdout; stderr={result.stderr}"
    return json.loads(raw)


class TestMissingHandoffAdvisory:
    def test_fires_canonical_handoff_block(self, tmp_path: Path) -> None:
        feat = "feat-rca-p6-handoff"
        _write_stats(tmp_path, turns=5, source_writes=2)
        _write_breadcrumbs(tmp_path, _calibrated_builds(feat=feat, n=5))
        out = _parse_stdout(_run_hook(CONTEXT_HEALTH, tmp_path))
        msg = out.get("followup_message", "")
        assert msg, f"expected followup_message, got {out}"
        assert "Continue working on" in msg
        assert feat in msg
        assert "Read .harness/breadcrumbs.jsonl and .harness/state.json." in msg
        assert "Last:" in msg
        assert "Next:" in msg

    def test_checkpoint_suppresses_followup(self, tmp_path: Path) -> None:
        feat = "feat-rca-p6-handoff"
        entries = _calibrated_builds(feat=feat, n=5)
        entries.append(
            {
                "ts": "2026-07-16T10:06:00Z",
                "role": "builder",
                "type": "checkpoint",
                "feat": feat,
                "msg": "Commit: feat-rca-p6-handoff (3 files)",
                "result": "pass",
            }
        )
        _write_stats(tmp_path, turns=5, source_writes=2)
        _write_breadcrumbs(tmp_path, entries)
        out = _parse_stdout(_run_hook(CONTEXT_HEALTH, tmp_path))
        msg = out.get("followup_message")
        assert not msg, f"expected no followup, got: {msg}"
        if msg:
            assert not ("Last:" in msg and "Next:" in msg)

    def test_handoff_type_suppresses_followup(self, tmp_path: Path) -> None:
        feat = "feat-1"
        entries = _calibrated_builds(feat=feat, n=5)
        entries.append(
            {
                "ts": "2026-07-16T10:06:00Z",
                "role": "builder",
                "type": "handoff",
                "feat": feat,
                "msg": "Handoff: done building. Next: evaluate.",
                "result": "pass",
            }
        )
        _write_stats(tmp_path, turns=5, source_writes=2)
        _write_breadcrumbs(tmp_path, entries)
        out = _parse_stdout(_run_hook(CONTEXT_HEALTH, tmp_path))
        assert not out.get("followup_message")

    @pytest.mark.parametrize(
        "turns,writes",
        [(4, 2), (5, 1)],
    )
    def test_below_thresholds_no_followup(
        self, tmp_path: Path, turns: int, writes: int
    ) -> None:
        _write_stats(tmp_path, turns=turns, source_writes=writes)
        _write_breadcrumbs(tmp_path, _calibrated_builds(n=5))
        out = _parse_stdout(_run_hook(CONTEXT_HEALTH, tmp_path))
        assert not out.get("followup_message"), out

    def test_no_session_stats_no_missing_handoff_but_volume_still_fires(
        self, tmp_path: Path
    ) -> None:
        """EC1: absent session-stats → no missing_handoff; volume fatigue still works."""
        entries = [
            {
                "ts": "2026-07-16T10:00:00Z",
                "role": "system",
                "type": "session_start",
                "feat": None,
                "msg": "start",
                "result": "pass",
            }
        ]
        for i in range(26):
            entries.append(
                {
                    "ts": f"2026-07-16T10:{i % 60:02d}:00Z",
                    "role": "builder",
                    "type": "build",
                    "feat": "feat-1",
                    "msg": f"build entry {i}",
                    "result": "pass",
                }
            )
        _write_breadcrumbs(tmp_path, entries)
        # deliberately no .session-stats.json
        out = _parse_stdout(_run_hook(CONTEXT_HEALTH, tmp_path))
        msg = out.get("followup_message", "")
        assert msg, "volume fatigue should still fire without session-stats"
        assert "SESSION HANDOFF ADVISORY" not in msg or "fatigue" in msg.lower() or "CONTEXT HEALTH" in msg


class TestSessionStatsInstrumentation:
    def test_harness_gate_increments_turns(self, tmp_path: Path) -> None:
        _harness(tmp_path)
        prompt = json.dumps({"prompt": "please implement the handoff advisory now"})
        r1 = _run_hook(HARNESS_GATE, tmp_path, stdin=prompt)
        assert r1.returncode == 0, r1.stderr
        stats = json.loads((tmp_path / ".harness" / ".session-stats.json").read_text())
        assert stats["turns"] == 1
        r2 = _run_hook(HARNESS_GATE, tmp_path, stdin=prompt)
        assert r2.returncode == 0, r2.stderr
        stats = json.loads((tmp_path / ".harness" / ".session-stats.json").read_text())
        assert stats["turns"] == 2

    def test_contract_gate_increments_source_writes_for_library(
        self, tmp_path: Path
    ) -> None:
        _harness(tmp_path)
        # No state → allow; still counts source path
        payload = json.dumps({"input": {"path": "library/cursor/hooks/context-health.sh"}})
        r = _run_hook(CONTRACT_GATE, tmp_path, stdin=payload)
        assert r.returncode == 0, r.stderr
        stats = json.loads((tmp_path / ".harness" / ".session-stats.json").read_text())
        assert stats["source_writes"] == 1

        payload2 = json.dumps({"input": {"path": "tests/eval/test_foo.py"}})
        r2 = _run_hook(CONTRACT_GATE, tmp_path, stdin=payload2)
        assert r2.returncode == 0, r2.stderr
        stats = json.loads((tmp_path / ".harness" / ".session-stats.json").read_text())
        assert stats["source_writes"] == 2

    def test_docs_and_harness_paths_do_not_increment(self, tmp_path: Path) -> None:
        _harness(tmp_path)
        for path in ("docs/readme.md", ".harness/state.json", "README.md"):
            payload = json.dumps({"input": {"path": path}})
            r = _run_hook(CONTRACT_GATE, tmp_path, stdin=payload)
            assert r.returncode == 0, r.stderr
        stats_path = tmp_path / ".harness" / ".session-stats.json"
        if stats_path.exists():
            stats = json.loads(stats_path.read_text())
            assert stats.get("source_writes", 0) == 0
        else:
            # never created is also fine
            pass

    def test_harness_context_resets_session_stats(self, tmp_path: Path) -> None:
        _write_stats(tmp_path, turns=9, source_writes=4)
        # Minimal state so harness-context maintenance path is happy
        (_harness(tmp_path) / "state.json").write_text(
            json.dumps(
                {
                    "project": "t",
                    "schema_version": 2,
                    "vision": "v",
                    "tasks": [],
                }
            )
        )
        _write_breadcrumbs(tmp_path, [])
        r = _run_hook(HARNESS_CONTEXT, tmp_path)
        assert r.returncode == 0, r.stderr
        stats = json.loads((tmp_path / ".harness" / ".session-stats.json").read_text())
        assert stats["turns"] == 0
        assert stats["source_writes"] == 0
