"""Cold-start skip + routing-pending TTL (feat-cold-start-skip)."""

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
HARNESS_GATE = REPO_ROOT / "library" / "cursor" / "hooks" / "harness-gate.sh"
CONTRACT_GATE = REPO_ROOT / "library" / "cursor" / "hooks" / "contract-gate.sh"

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


def _run(hook: Path, cwd: Path, stdin: str) -> dict:
    result = subprocess.run(
        ["bash", str(hook)],
        input=stdin,
        capture_output=True,
        text=True,
        cwd=str(cwd),
        env=_env(cwd),
        check=False,
    )
    assert result.returncode == 0, f"stderr={result.stderr}\nstdout={result.stdout}"
    raw = result.stdout.strip()
    assert raw, f"empty stdout; stderr={result.stderr}"
    return json.loads(raw)


def _write_payload(path: str) -> str:
    return json.dumps({"input": {"path": path}})


def _marker(cwd: Path, *, age_sec: int | None = None) -> Path:
    h = cwd / ".harness"
    h.mkdir(parents=True, exist_ok=True)
    p = h / ".routing-pending"
    p.write_text("2026-08-09T00:00:00Z\n")
    if age_sec is not None:
        past = time.time() - age_sec
        os.utime(p, (past, past))
    return p


class TestSkipHarnessClearsRoutingPending:
    def test_skip_harness_clears_routing_pending(self, tmp_path: Path) -> None:
        """AC1: skip harness removes marker; stdout {}."""
        _marker(tmp_path)
        out = _run(
            HARNESS_GATE,
            tmp_path,
            json.dumps({"prompt": "skip harness and just fix the typo"}),
        )
        assert out == {}
        assert "followup_message" not in out
        assert not (tmp_path / ".harness" / ".routing-pending").exists()

    def test_skip_harness_without_marker_stays_absent(self, tmp_path: Path) -> None:
        """EC1."""
        out = _run(
            HARNESS_GATE,
            tmp_path,
            json.dumps({"prompt": "skip harness please"}),
        )
        assert out == {}
        assert not (tmp_path / ".harness" / ".routing-pending").exists()


class TestContractGateColdStartSkipAndTtl:
    def test_skip_breadcrumb_allows_library_write(self, tmp_path: Path) -> None:
        """AC2: Skipped harness in tail-5 allows library write."""
        _marker(tmp_path, age_sec=10)
        bc = tmp_path / ".harness" / "breadcrumbs.jsonl"
        bc.write_text(
            json.dumps(
                {
                    "ts": "2026-08-09T00:00:00Z",
                    "role": "builder",
                    "type": "decision",
                    "msg": "Skipped harness: one-line typo",
                    "result": "pass",
                }
            )
            + "\n"
        )
        out = _run(
            CONTRACT_GATE,
            tmp_path,
            _write_payload("library/cursor/hooks/example.sh"),
        )
        assert out.get("permission") != "deny", out
        assert (tmp_path / ".harness" / ".routing-pending").exists()

    def test_stale_routing_pending_ttl_allows_and_removes(
        self, tmp_path: Path
    ) -> None:
        """AC3: marker older than 600s → allow + remove."""
        _marker(tmp_path, age_sec=601)
        out = _run(
            CONTRACT_GATE,
            tmp_path,
            _write_payload("library/cursor/hooks/example.sh"),
        )
        assert out.get("permission") != "deny", out
        assert not (tmp_path / ".harness" / ".routing-pending").exists()

    def test_fresh_routing_pending_denies_library_write(self, tmp_path: Path) -> None:
        """AC4: sacred cold-start deny."""
        _marker(tmp_path, age_sec=30)
        out = _run(
            CONTRACT_GATE,
            tmp_path,
            _write_payload("library/cursor/hooks/example.sh"),
        )
        assert out.get("permission") == "deny"
        assert "cold start" in out.get("agent_message", "").lower()
        assert (tmp_path / ".harness" / ".routing-pending").exists()

    def test_skip_outside_tail5_still_denies(self, tmp_path: Path) -> None:
        """EC2: sixth-from-last Skipped harness does not bypass."""
        _marker(tmp_path, age_sec=30)
        lines = []
        lines.append(
            json.dumps(
                {
                    "ts": "2026-08-09T00:00:00Z",
                    "role": "builder",
                    "type": "decision",
                    "msg": "Skipped harness: old",
                    "result": "pass",
                }
            )
        )
        for i in range(5):
            lines.append(
                json.dumps(
                    {
                        "ts": f"2026-08-09T00:0{i+1}:00Z",
                        "role": "builder",
                        "type": "build",
                        "msg": f"later entry {i} with enough length",
                        "result": "pass",
                    }
                )
            )
        (tmp_path / ".harness" / "breadcrumbs.jsonl").write_text(
            "\n".join(lines) + "\n"
        )
        out = _run(
            CONTRACT_GATE,
            tmp_path,
            _write_payload("library/cursor/hooks/example.sh"),
        )
        assert out.get("permission") == "deny", out

    def test_fresh_marker_allows_harness_paths(self, tmp_path: Path) -> None:
        """EC3."""
        _marker(tmp_path, age_sec=30)
        out = _run(
            CONTRACT_GATE,
            tmp_path,
            _write_payload(".harness/contract.json"),
        )
        assert out.get("permission") != "deny", out


class TestColdStartSkipE2E:
    def test_cold_start_then_skip_then_contract_gate_allows(
        self, tmp_path: Path
    ) -> None:
        """AC5: routing → skip clears → contract-gate allows without breadcrumb."""
        routed = _run(
            HARNESS_GATE,
            tmp_path,
            json.dumps({"prompt": "migra o banco de dados agora"}),
        )
        assert "HARNESS ROUTING" in routed.get("followup_message", "")
        assert (tmp_path / ".harness" / ".routing-pending").is_file()

        skipped = _run(
            HARNESS_GATE,
            tmp_path,
            json.dumps({"prompt": "skip harness — just a small fix"}),
        )
        assert skipped == {}
        assert not (tmp_path / ".harness" / ".routing-pending").exists()

        out = _run(
            CONTRACT_GATE,
            tmp_path,
            _write_payload("library/foo.sh"),
        )
        assert out.get("permission") != "deny", out
