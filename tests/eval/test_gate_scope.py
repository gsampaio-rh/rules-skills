"""P5 gate-scope regressions: verify-harness / contract-gate / harness-gate.

Covers negotiated contract feat-rca-p5-gate-scope AC1–AC5 + EC1/EC3/EC4/EC5.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
VERIFY_HARNESS = REPO_ROOT / "library" / "cursor" / "hooks" / "verify-harness.sh"
CONTRACT_GATE = REPO_ROOT / "library" / "cursor" / "hooks" / "contract-gate.sh"
HARNESS_GATE = REPO_ROOT / "library" / "cursor" / "hooks" / "harness-gate.sh"

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


def _parse_stdout(result: subprocess.CompletedProcess) -> dict:
    assert result.returncode == 0, f"hook failed: {result.stderr}\n{result.stdout}"
    raw = result.stdout.strip()
    assert raw, f"empty stdout; stderr={result.stderr}"
    return json.loads(raw)


def _harness(cwd: Path) -> Path:
    d = cwd / ".harness"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _write_state(cwd: Path, tasks: list[dict]) -> None:
    (_harness(cwd) / "state.json").write_text(
        json.dumps(
            {
                "project": "gate-scope-fixture",
                "schema_version": 2,
                "vision": "P5 gate scope fixture",
                "tasks": tasks,
            },
            indent=2,
        )
        + "\n"
    )


def _write_contract(
    cwd: Path,
    *,
    task_id: str = "feat-rca-p5-gate-scope",
    phase: str = "building",
    verified: bool = False,
) -> None:
    (_harness(cwd) / "contract.json").write_text(
        json.dumps(
            {
                "task_id": task_id,
                "feature": "gate scope fixture",
                "phase": phase,
                "verified": verified,
            },
            indent=2,
        )
        + "\n"
    )


def _write_breadcrumbs(cwd: Path) -> None:
    (_harness(cwd) / "breadcrumbs.jsonl").write_text(
        json.dumps(
            {
                "ts": "2026-07-16T10:00:00Z",
                "role": "builder",
                "type": "build",
                "feat": "feat-rca-p5-gate-scope",
                "msg": "fixture breadcrumb",
                "result": "pass",
            }
        )
        + "\n"
    )


def _pending_task(task_id: str = "feat-rca-p5-gate-scope") -> dict:
    return {
        "id": task_id,
        "name": "Scope gates",
        "type": "feature",
        "status": "pending",
        "scope": "fixture",
    }


def _building_task(task_id: str = "feat-rca-p5-gate-scope") -> dict:
    t = _pending_task(task_id)
    t["status"] = "building"
    return t


def _write_payload(path: str) -> str:
    return json.dumps({"input": {"path": path}})


# ── AC1 / AC5 / EC1 / EC2 — verify-harness ───────────────────────────────────


class TestVerifyHarnessScope:
    def test_ac1_qa_stale_contract_returns_empty(self, tmp_path: Path) -> None:
        tid = "feat-rca-p5-gate-scope"
        _write_state(tmp_path, [_pending_task(tid), _pending_task("feat-other")])
        _write_contract(tmp_path, task_id=tid, phase="building", verified=False)
        _write_breadcrumbs(tmp_path)

        result = _run_hook(VERIFY_HARNESS, tmp_path, "{}")
        out = _parse_stdout(result)
        assert out == {}, f"expected {{}}, got {out}"
        raw = result.stdout
        assert "HARNESS GATE" not in raw
        assert "CONTRACT REQUIRED" not in raw
        assert "HARNESS ENFORCEMENT" not in raw

    def test_ac5_building_unverified_still_gates(self, tmp_path: Path) -> None:
        tid = "feat-rca-p5-gate-scope"
        _write_state(tmp_path, [_building_task(tid)])
        _write_contract(tmp_path, task_id=tid, phase="building", verified=False)
        _write_breadcrumbs(tmp_path)

        result = _run_hook(VERIFY_HARNESS, tmp_path, "{}")
        assert result.returncode == 0
        out = _parse_stdout(result)
        msg = out.get("followup_message", "")
        assert "HARNESS GATE" in msg, f"expected HARNESS GATE, got {out}"

    @pytest.mark.parametrize("phase", ["negotiating", "negotiated"])
    def test_ec1_pre_build_returns_empty(self, tmp_path: Path, phase: str) -> None:
        tid = "feat-rca-p5-gate-scope"
        _write_state(tmp_path, [_building_task(tid)])
        _write_contract(tmp_path, task_id=tid, phase=phase, verified=False)
        _write_breadcrumbs(tmp_path)

        out = _parse_stdout(_run_hook(VERIFY_HARNESS, tmp_path, "{}"))
        assert out == {}

    @pytest.mark.parametrize("phase", ["idle", "committed"])
    def test_ec2_stale_auto_cleans(self, tmp_path: Path, phase: str) -> None:
        tid = "feat-rca-p5-gate-scope"
        _write_state(tmp_path, [_pending_task(tid)])
        _write_contract(tmp_path, task_id=tid, phase=phase, verified=False)
        _write_breadcrumbs(tmp_path)

        out = _parse_stdout(_run_hook(VERIFY_HARNESS, tmp_path, "{}"))
        assert out == {}
        assert not (tmp_path / ".harness" / "contract.json").exists()

    def test_post_commit_does_not_advance_on_evaluator_pass_alone(
        self, tmp_path: Path
    ) -> None:
        """Regression: evaluator PASS must not archive contract / mark committed."""
        tid = "chore-agent-audit-fix"
        _write_state(
            tmp_path,
            [
                {
                    "id": tid,
                    "name": "audit fix",
                    "type": "chore",
                    "status": "verified",
                    "scope": "fixture",
                }
            ],
        )
        _write_contract(tmp_path, task_id=tid, phase="evaluating", verified=True)
        (_harness(tmp_path) / "breadcrumbs.jsonl").write_text(
            json.dumps(
                {
                    "ts": "2026-08-09T02:07:11Z",
                    "role": "evaluator",
                    "type": "evaluate",
                    "feat": tid,
                    "msg": "Retest PASS: 15/15 AC",
                    "result": "pass",
                }
            )
            + "\n"
        )

        out = _parse_stdout(_run_hook(VERIFY_HARNESS, tmp_path, "{}"))
        assert "POST-COMMIT" not in json.dumps(out)
        assert (tmp_path / ".harness" / "contract.json").exists()
        state = json.loads((tmp_path / ".harness" / "state.json").read_text())
        assert state["tasks"][0]["status"] == "verified"

    def test_post_commit_advances_on_commit_checkpoint(self, tmp_path: Path) -> None:
        tid = "chore-agent-audit-fix"
        _write_state(
            tmp_path,
            [
                {
                    "id": tid,
                    "name": "audit fix",
                    "type": "chore",
                    "status": "verified",
                    "scope": "fixture",
                }
            ],
        )
        _write_contract(tmp_path, task_id=tid, phase="evaluating", verified=True)
        (_harness(tmp_path) / "breadcrumbs.jsonl").write_text(
            "\n".join(
                [
                    json.dumps(
                        {
                            "ts": "2026-08-09T02:07:11Z",
                            "role": "evaluator",
                            "type": "evaluate",
                            "feat": tid,
                            "msg": "PASS",
                            "result": "pass",
                        }
                    ),
                    json.dumps(
                        {
                            "ts": "2026-08-09T02:12:00Z",
                            "role": "builder",
                            "type": "checkpoint",
                            "feat": tid,
                            "msg": "Commit: chore-agent-audit-fix (12 files)",
                            "result": "pass",
                        }
                    ),
                ]
            )
            + "\n"
        )

        out = _parse_stdout(_run_hook(VERIFY_HARNESS, tmp_path, "{}"))
        assert "POST-COMMIT" in out.get("followup_message", "")
        assert not (tmp_path / ".harness" / "contract.json").exists()
        state = json.loads((tmp_path / ".harness" / "state.json").read_text())
        assert state["tasks"][0]["status"] == "committed"


# ── AC2 / AC3 / AC4 / EC3 / EC5 — contract-gate ───────────────────────────────


class TestContractGateScope:
    def test_ac2_building_no_contract_source_denied(self, tmp_path: Path) -> None:
        _write_state(tmp_path, [_building_task()])
        result = _run_hook(
            CONTRACT_GATE,
            tmp_path,
            _write_payload("library/cursor/hooks/example.sh"),
        )
        out = _parse_stdout(result)
        assert out.get("permission") == "deny"
        msg = out.get("agent_message", "")
        assert any(k in msg.upper() for k in ("WRITE BLOCKED", "CONTRACT")), msg

    @pytest.mark.parametrize("status", ["pending", "building"])
    def test_ac3_docs_soft_warn(self, tmp_path: Path, status: str) -> None:
        task = _pending_task() if status == "pending" else _building_task()
        _write_state(tmp_path, [task])
        result = _run_hook(CONTRACT_GATE, tmp_path, _write_payload("docs/notes.md"))
        out = _parse_stdout(result)
        assert out.get("permission") != "deny", out
        blob = json.dumps(out)
        assert any(k in blob.lower() for k in ("docs", "soft", "documentation")), out

    def test_ac4_pending_source_still_denied(self, tmp_path: Path) -> None:
        _write_state(tmp_path, [_pending_task()])
        result = _run_hook(CONTRACT_GATE, tmp_path, _write_payload("library/foo.py"))
        out = _parse_stdout(result)
        assert out.get("permission") == "deny"
        msg = out.get("agent_message", "")
        assert any(k in msg.upper() for k in ("WRITE BLOCKED", "CONTRACT")), msg

    def test_ec3_harness_contract_write_allowed(self, tmp_path: Path) -> None:
        _write_state(tmp_path, [_building_task()])
        result = _run_hook(
            CONTRACT_GATE,
            tmp_path,
            _write_payload(".harness/contract.json"),
        )
        out = _parse_stdout(result)
        assert out.get("permission") != "deny", out

    def test_ec5_strreplace_docs_soft_warn(self, tmp_path: Path) -> None:
        _write_state(tmp_path, [_pending_task()])
        # Same path extraction shape; tool name not required by hooks_extract_path
        payload = json.dumps({"input": {"path": "docs/report.md"}})
        result = _run_hook(CONTRACT_GATE, tmp_path, payload)
        out = _parse_stdout(result)
        assert out.get("permission") != "deny", out
        blob = json.dumps(out)
        assert any(k in blob.lower() for k in ("docs", "soft", "documentation")), out


# ── EC4 — harness-gate ───────────────────────────────────────────────────────


class TestHarnessGateScope:
    def test_ec4_qa_with_leftover_contract_no_gate_or_routing(
        self, tmp_path: Path
    ) -> None:
        tid = "feat-rca-p5-gate-scope"
        _write_state(tmp_path, [_pending_task(tid)])
        _write_contract(tmp_path, task_id=tid, phase="building", verified=False)
        _write_breadcrumbs(tmp_path)

        result = _run_hook(
            HARNESS_GATE,
            tmp_path,
            json.dumps({"prompt": "what does verify-harness.sh do?"}),
        )
        assert result.returncode == 0
        raw = result.stdout
        assert "HARNESS GATE" not in raw, raw
        assert "HARNESS ROUTING" not in raw, raw
