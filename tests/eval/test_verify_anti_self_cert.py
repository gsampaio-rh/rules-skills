"""Anti-self-cert soft followup for verify-harness.sh.

verified:true without an evaluator pass breadcrumb must soft-followup.
With a matching evaluator pass crumb, the hook returns {}.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
VERIFY = REPO_ROOT / "library" / "cursor" / "hooks" / "verify-harness.sh"

_PYENV_ROOT = os.environ.get("PYENV_ROOT", str(Path.home() / ".pyenv"))
_HOOK_PATH = (
    f"{_PYENV_ROOT}/shims:{_PYENV_ROOT}/bin:"
    "/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
)


def _env(cwd: Path) -> dict:
    env = {"PATH": _HOOK_PATH, "HOME": str(Path.home()), "HARNESS_ROOT": str(cwd)}
    if "PYENV_VERSION" in os.environ:
        env["PYENV_VERSION"] = os.environ["PYENV_VERSION"]
    return env


def _run(cwd: Path) -> dict:
    result = subprocess.run(
        ["bash", str(VERIFY)],
        input="{}",
        capture_output=True,
        text=True,
        cwd=str(cwd),
        env=_env(cwd),
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout.strip() or "{}")


def _seed(cwd: Path, *, verified: bool, with_eval_pass: bool) -> None:
    harness = cwd / ".harness"
    harness.mkdir(parents=True, exist_ok=True)
    (harness / "state.json").write_text(
        json.dumps(
            {
                "project": "anti-self-cert",
                "schema_version": 2,
                "vision": "fixture",
                "tasks": [
                    {
                        "id": "chore-anti-self-cert",
                        "name": "fixture",
                        "type": "chore",
                        "status": "building",
                    }
                ],
            },
            indent=2,
        )
        + "\n"
    )
    (harness / "contract.json").write_text(
        json.dumps(
            {
                "task_id": "chore-anti-self-cert",
                "feature": "anti self cert fixture",
                "phase": "building",
                "verified": verified,
            },
            indent=2,
        )
        + "\n"
    )
    crumbs = [
        {
            "ts": "2026-08-09T00:00:00Z",
            "role": "builder",
            "type": "build",
            "feat": "chore-anti-self-cert",
            "msg": "implemented fixture long enough",
            "result": "pass",
        }
    ]
    if with_eval_pass:
        crumbs.append(
            {
                "ts": "2026-08-09T00:01:00Z",
                "role": "evaluator",
                "type": "evaluate",
                "feat": "chore-anti-self-cert",
                "msg": "all criteria passed",
                "result": "pass",
            }
        )
    (harness / "breadcrumbs.jsonl").write_text(
        "".join(json.dumps(c) + "\n" for c in crumbs)
    )


def test_verified_without_evaluator_pass_soft_blocks(tmp_path: Path) -> None:
    _seed(tmp_path, verified=True, with_eval_pass=False)
    out = _run(tmp_path)
    msg = out.get("followup_message", "")
    assert "HARNESS GATE" in msg, out
    assert "evaluator" in msg.lower(), out


def test_verified_with_evaluator_pass_returns_empty(tmp_path: Path) -> None:
    _seed(tmp_path, verified=True, with_eval_pass=True)
    out = _run(tmp_path)
    assert out == {}, out


def test_unverified_active_contract_soft_points_to_evaluator(tmp_path: Path) -> None:
    _seed(tmp_path, verified=False, with_eval_pass=False)
    out = _run(tmp_path)
    msg = out.get("followup_message", "")
    assert "HARNESS GATE" in msg, out
    assert "evaluator" in msg.lower(), out
