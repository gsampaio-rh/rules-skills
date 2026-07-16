"""P2 enforce-progress hard-block: source_writes gate + breadcrumb quality.

Covers negotiated contract feat-rca-p2-enforce-progress AC1–AC4 + EC1–EC4.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ENFORCE_PROGRESS = REPO_ROOT / "library" / "cursor" / "hooks" / "enforce-progress.sh"

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


def _run_hook(cwd: Path, stdin: str = "{}") -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(ENFORCE_PROGRESS)],
        input=stdin,
        capture_output=True,
        text=True,
        cwd=str(cwd),
        env=_env(cwd),
        check=False,
    )


def _parse_stdout(result: subprocess.CompletedProcess) -> dict:
    assert result.returncode == 0, f"hook failed: {result.stderr}\n{result.stdout}"
    raw = result.stdout.strip()
    assert raw, f"empty stdout; stderr={result.stderr}"
    return json.loads(raw)


def _harness(cwd: Path) -> Path:
    d = cwd / ".harness"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _git_init(cwd: Path) -> None:
    subprocess.run(
        ["git", "init"],
        cwd=str(cwd),
        capture_output=True,
        check=True,
    )


def _write_stats(cwd: Path, source_writes: int, turns: int = 0) -> None:
    (_harness(cwd) / ".session-stats.json").write_text(
        json.dumps({"turns": turns, "source_writes": source_writes})
    )


def _write_breadcrumbs(cwd: Path, entries: list[dict]) -> None:
    content = "\n".join(json.dumps(e) for e in entries) + "\n"
    (_harness(cwd) / "breadcrumbs.jsonl").write_text(content)


def _valid_bc(msg: str = "Implemented enforce-progress hard-block gate") -> dict:
    assert len(msg) >= 20
    return {
        "ts": "2026-07-16T12:00:00Z",
        "role": "builder",
        "type": "build",
        "feat": "feat-rca-p2-enforce-progress",
        "msg": msg,
        "result": "pass",
    }


def test_ac1_blocks_on_source_writes_without_valid_breadcrumb(tmp_path: Path) -> None:
    """AC1: source_writes=2, no valid breadcrumb → PROGRESS BLOCKED."""
    _git_init(tmp_path)
    _write_stats(tmp_path, source_writes=2)
    out = _parse_stdout(_run_hook(tmp_path))
    assert "followup_message" in out
    assert "PROGRESS BLOCKED" in out["followup_message"]
    assert "PROGRESS CHECK" not in out["followup_message"]


def test_ac2_passes_with_valid_breadcrumb(tmp_path: Path) -> None:
    """AC2: source_writes=2 + valid last breadcrumb → {}."""
    _git_init(tmp_path)
    _write_stats(tmp_path, source_writes=2)
    _write_breadcrumbs(tmp_path, [_valid_bc()])
    out = _parse_stdout(_run_hook(tmp_path))
    assert out == {}


def test_ac3_single_write_exception(tmp_path: Path) -> None:
    """AC3: source_writes=1, no breadcrumbs → {}."""
    _git_init(tmp_path)
    _write_stats(tmp_path, source_writes=1)
    out = _parse_stdout(_run_hook(tmp_path))
    assert out == {}


def test_ac4_docs_only_exception(tmp_path: Path) -> None:
    """AC4: source_writes=0, no breadcrumbs → {}."""
    _git_init(tmp_path)
    _write_stats(tmp_path, source_writes=0)
    out = _parse_stdout(_run_hook(tmp_path))
    assert out == {}


def test_ec1_missing_session_stats_fail_open(tmp_path: Path) -> None:
    """EC1: missing .session-stats.json → {}."""
    _git_init(tmp_path)
    _harness(tmp_path)
    out = _parse_stdout(_run_hook(tmp_path))
    assert out == {}


def test_ec2_msg_length_boundary(tmp_path: Path) -> None:
    """EC2: msg len 19 → BLOCKED; msg len 20 → pass."""
    _git_init(tmp_path)
    _write_stats(tmp_path, source_writes=2)

    msg19 = "x" * 19
    assert len(msg19) == 19
    _write_breadcrumbs(
        tmp_path,
        [
            {
                "ts": "2026-07-16T12:00:00Z",
                "role": "builder",
                "type": "build",
                "feat": None,
                "msg": msg19,
                "result": "pass",
            }
        ],
    )
    blocked = _parse_stdout(_run_hook(tmp_path))
    assert "PROGRESS BLOCKED" in blocked.get("followup_message", "")

    msg20 = "x" * 20
    assert len(msg20) == 20
    _write_breadcrumbs(
        tmp_path,
        [
            {
                "ts": "2026-07-16T12:00:00Z",
                "role": "builder",
                "type": "build",
                "feat": None,
                "msg": msg20,
                "result": "pass",
            }
        ],
    )
    passed = _parse_stdout(_run_hook(tmp_path))
    assert passed == {}


def test_ec3_contract_skip_retained(tmp_path: Path) -> None:
    """EC3: contract.json present → {} even with source_writes=2 and no breadcrumb."""
    _git_init(tmp_path)
    _write_stats(tmp_path, source_writes=2)
    (_harness(tmp_path) / "contract.json").write_text(
        json.dumps(
            {
                "task_id": "feat-x",
                "phase": "building",
                "verified": False,
                "acceptance_criteria": ["x"],
            }
        )
    )
    out = _parse_stdout(_run_hook(tmp_path))
    assert out == {}


def test_ec4_tier2_lean_no_regression(tmp_path: Path) -> None:
    """EC4: lean profile + valid breadcrumb + 4 git files → {} (no HARNESS CHECK)."""
    _git_init(tmp_path)
    _write_stats(tmp_path, source_writes=2)
    _write_breadcrumbs(tmp_path, [_valid_bc()])
    for i in range(4):
        (tmp_path / f"file_{i}.py").write_text(f"# file {i}\n")
    # lean is default when .cursor/.hooks-profile is absent
    out = _parse_stdout(_run_hook(tmp_path))
    assert out == {}
    assert "HARNESS CHECK" not in json.dumps(out)
