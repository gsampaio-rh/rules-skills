"""Tests for library/cursor/hooks/harness-dashboard.py — no network, no LLM."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "library" / "cursor" / "hooks" / "harness-dashboard.py"
HOOK_SH = REPO_ROOT / "library" / "cursor" / "hooks" / "harness-dashboard.sh"
OPTIONAL = REPO_ROOT / "library" / "cursor" / "hooks.optional.json"
DEFAULT_HOOKS = REPO_ROOT / "library" / "cursor" / "hooks.json"

# Stable section markers (must match generator)
MARKER_NOW = "Now serving"
MARKER_VITALS = "Session vitals"
MARKER_QUEUE = "Queue"
MARKER_CONTRACT = "Contract"
MARKER_ACTIVITY = "Recent activity"
MARKER_FLAGS = "Flags/gates"
MARKER_NO_HARNESS = "No harness active"
MARKER_TOKENS = "Unavailable"

CDN_RE = re.compile(
    r"""<(?:script|link)\b[^>]+(?:src|href)\s*=\s*["']https?://""",
    re.IGNORECASE,
)

JSON_KEYS = {"task", "contract", "session", "breadcrumbs", "archive", "flags"}


def run_dash(*args, root: Path, out: Path | None = None) -> subprocess.CompletedProcess:
    cmd = [sys.executable, str(SCRIPT), "--root", str(root)]
    if out is not None:
        cmd.extend(["--out", str(out)])
    cmd.extend(args)
    return subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO_ROOT))


def _setup(
    root: Path,
    *,
    state: dict | None = None,
    contract: dict | None = None,
    breadcrumbs: list[dict] | None = None,
    session_stats: dict | None = None,
    create_harness: bool = True,
):
    if not create_harness and state is None:
        return
    harness = root / ".harness"
    harness.mkdir(parents=True, exist_ok=True)
    if state is not None:
        (harness / "state.json").write_text(json.dumps(state))
    if contract is not None:
        (harness / "contract.json").write_text(json.dumps(contract))
    if breadcrumbs is not None:
        (harness / "breadcrumbs.jsonl").write_text(
            "\n".join(json.dumps(b) for b in breadcrumbs) + "\n"
        )
    if session_stats is not None:
        (harness / ".session-stats.json").write_text(json.dumps(session_stats))


def _state(tasks=None, vision="Ship a glanceable session desk", project="desk-demo"):
    return {
        "project": project,
        "schema_version": 2,
        "vision": vision,
        "tasks": tasks or [],
    }


def _task(id_="feat-dashboard-generator", name="Dashboard CLI", status="building", scope=None):
    t = {"id": id_, "name": name, "type": "feature", "status": status}
    if scope is not None:
        t["scope"] = scope
    return t


def _contract():
    return {
        "task_id": "feat-dashboard-generator",
        "feature": "Read-only Genius Bar harness session dashboard generator",
        "problem": "Scattered harness state is hard to glance",
        "proposed_solution": "Emit a self-contained session desk HTML",
        "phase": "building",
        "verified": False,
        "acceptance_criteria": ["ac1 fixture criterion", "ac2", "ac3"],
        "edge_cases": ["e1 missing harness", "e2"],
        "verification_method": "pytest tests/eval/test_harness_dashboard.py -q",
        "negotiation_rounds": 1,
        "rubrics": ["code-quality"],
        "rubric_mode": "warn",
    }


def _bc(i: int, role="builder", typ="build"):
    return {
        "ts": f"2026-08-09T10:0{i}:00Z",
        "role": role,
        "type": typ,
        "feat": "feat-dashboard-generator",
        "msg": f"breadcrumb {i} for dashboard",
        "result": "pass",
    }


class TestEmptyRoot:
    def test_empty_root_no_harness_board(self, tmp_path):
        out = tmp_path / "out.html"
        result = run_dash(root=tmp_path, out=out)
        assert result.returncode == 0
        assert out.exists()
        html = out.read_text()
        assert MARKER_NO_HARNESS in html

    def test_empty_root_json_keys(self, tmp_path):
        result = run_dash("--json", root=tmp_path, out=tmp_path / "d.html")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert JSON_KEYS.issubset(set(data))


class TestFixtureHarness:
    def test_fixture_vision_task_sections_tokens_no_cdn(self, tmp_path):
        vision = "Ship a glanceable session desk"
        active_id = "feat-dashboard-generator"
        _setup(
            tmp_path,
            state=_state(
                tasks=[
                    _task(
                        active_id,
                        "Dashboard CLI",
                        "building",
                        scope="includes: CLI + HTML; excludes: fake tokens",
                    ),
                    _task("chore-dashboard-tests", "Tests", "pending"),
                ],
                vision=vision,
            ),
            contract=_contract(),
            breadcrumbs=[_bc(i) for i in range(5)],
            session_stats={"turns": 3, "source_writes": 2},
        )
        out = tmp_path / ".harness" / "dashboard.html"
        result = run_dash(root=tmp_path, out=out)
        assert result.returncode == 0
        html = out.read_text()

        assert vision in html
        assert active_id in html
        for marker in (
            MARKER_NOW,
            MARKER_VITALS,
            MARKER_QUEUE,
            MARKER_CONTRACT,
            MARKER_ACTIVITY,
            MARKER_FLAGS,
        ):
            assert marker in html, f"missing section marker: {marker}"

        assert MARKER_TOKENS in html
        # Must not invent a numeric token count near Tokens label
        assert not re.search(r"Tokens</span>\s*</div>\s*<div class=\"vital\">\s*<span class=\"vital-value\">\d+", html)
        assert CDN_RE.search(html) is None
        assert "desk-demo" in html
        assert "Scattered harness state is hard to glance" in html
        assert "ac1 fixture criterion" in html
        assert "e1 missing harness" in html
        assert "includes: CLI + HTML; excludes: fake tokens" in html
        assert "Acceptance criteria" in html
        assert "schema v2" in html

    def test_json_stable_keys(self, tmp_path):
        _setup(
            tmp_path,
            state=_state(tasks=[_task()]),
            contract=_contract(),
            breadcrumbs=[_bc(1)],
            session_stats={"turns": 1, "source_writes": 0},
        )
        result = run_dash("--json", root=tmp_path, out=tmp_path / ".harness" / "dashboard.html")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert JSON_KEYS.issubset(set(data))
        assert data["task"]["id"] == "feat-dashboard-generator"
        assert data["contract"]["phase"] == "building"
        assert data["contract"]["acceptance_criteria"] == [
            "ac1 fixture criterion",
            "ac2",
            "ac3",
        ]
        assert data["contract"]["problem"]
        assert data["session"]["turns"] == 1
        assert data["tokens"]["label"] == MARKER_TOKENS
        assert data["tokens"]["available"] is False

    def test_no_active_task_honest_empty(self, tmp_path):
        _setup(
            tmp_path,
            state=_state(
                tasks=[
                    _task("a", "Done", "verified"),
                    _task("b", "Shipped", "committed"),
                ]
            ),
        )
        out = tmp_path / "board.html"
        result = run_dash("--json", root=tmp_path, out=out)
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["task"] is None
        html = out.read_text()
        assert "No active task" in html

    def test_corrupt_state_fail_soft(self, tmp_path):
        harness = tmp_path / ".harness"
        harness.mkdir()
        (harness / "state.json").write_text("{not-json")
        out = tmp_path / "board.html"
        result = run_dash(root=tmp_path, out=out)
        assert result.returncode == 0
        assert MARKER_NO_HARNESS in out.read_text()


class TestWiring:
    def test_optional_hook_both_events_not_in_default(self):
        optional = json.loads(OPTIONAL.read_text())
        default = DEFAULT_HOOKS.read_text()
        assert "harness-dashboard" not in default
        stop = optional["hooks"].get("stop") or []
        start = optional["hooks"].get("sessionStart") or []
        assert any("harness-dashboard" in (e.get("command") or "") for e in stop)
        assert any("harness-dashboard" in (e.get("command") or "") for e in start)

    def test_optional_hook_returns_empty_object(self, tmp_path):
        env = {**dict(**{k: v for k, v in __import__("os").environ.items()}), "HARNESS_ROOT": str(tmp_path)}
        result = subprocess.run(
            ["bash", str(HOOK_SH)],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            env=env,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == "{}"

    def test_deny_spine_unchanged(self):
        data = json.loads(DEFAULT_HOOKS.read_text())
        pre = data["hooks"].get("preToolUse") or []
        shell = data["hooks"].get("beforeShellExecution") or []
        cmds = [e.get("command", "") for e in pre + shell]
        assert any("contract-gate.sh" in c for c in cmds)
        assert any("evaluator-guard.sh" in c for c in cmds)
        assert any("pre-commit-harness.sh" in c for c in cmds)
        assert not any("harness-dashboard" in c for c in cmds)


class TestRepoSmoke:
    def test_repo_root_smoke(self):
        state = REPO_ROOT / ".harness" / "state.json"
        if not state.exists():
            return
        out = REPO_ROOT / ".harness" / "dashboard.html"
        result = run_dash(root=REPO_ROOT, out=out)
        assert result.returncode == 0
        assert out.exists()
        html = out.read_text()
        vision = json.loads(state.read_text()).get("vision")
        if vision:
            assert vision in html
