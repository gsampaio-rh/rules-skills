"""
Tests for scripts/acam-score.py — static ACAM scorer.

Coverage matrix (≥12 tests):
  (a) empty repo → all dimensions none
  (b) rules-skills golden fixture match
  (c) --root missing path → exit 2
  (d-g) per-dimension ladder cap: flip one Intermediate check to false → dimension stays basic
  (h-k) per-dimension minimal fixtures: verify basic/intermediate boundary
  (l) markdown output: correct columns and 4 data rows
  (m) partial Advanced does not upgrade level past intermediate
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent
SCORER = REPO_ROOT / "scripts" / "acam-score.py"
GOLDEN_FIXTURE = REPO_ROOT / "tests" / "eval" / "fixtures" / "acam_expected_rules_skills.json"


def _run(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCORER)] + args,
        capture_output=True, text=True,
    )


def _score(tmp_path: Path) -> dict:
    result = _run(["--root", str(tmp_path)])
    assert result.returncode == 0, f"scorer exited {result.returncode}: {result.stderr}"
    return json.loads(result.stdout)


# ---------------------------------------------------------------------------
# (a) Empty repo — all none
# ---------------------------------------------------------------------------

def test_empty_repo_all_none(tmp_path):
    scorecard = _score(tmp_path)
    for dim in ("configuration", "workflows", "multi_agent", "interaction"):
        assert scorecard["dimensions"][dim]["level"] == "none", (
            f"{dim} should be none for empty repo, got {scorecard['dimensions'][dim]['level']}"
        )
        assert scorecard["dimensions"][dim]["score"] == 0


def test_empty_repo_basic_checks_all_false(tmp_path):
    scorecard = _score(tmp_path)
    for dim in ("configuration", "workflows", "multi_agent", "interaction"):
        basic_checks = [
            c for c in scorecard["dimensions"][dim]["checks"]
            if ".basic." in c["id"]
        ]
        assert basic_checks, f"{dim} should have at least one basic check"
        for c in basic_checks:
            assert c["result"] is False, f"Expected basic check {c['id']} to fail in empty repo"


# ---------------------------------------------------------------------------
# (b) rules-skills golden fixture match
# ---------------------------------------------------------------------------

def test_rules_skills_matches_golden_fixture():
    golden = json.loads(GOLDEN_FIXTURE.read_text())
    result = _run(["--root", str(REPO_ROOT)])
    assert result.returncode == 0
    scorecard = json.loads(result.stdout)

    for dim, expected in golden.items():
        actual = scorecard["dimensions"][dim]
        assert actual["level"] == expected["level"], (
            f"{dim}: expected level={expected['level']}, got {actual['level']}"
        )
        assert actual["score"] == expected["score"], (
            f"{dim}: expected score={expected['score']}, got {actual['score']}"
        )
        expected_by_id = {c["id"]: c["result"] for c in expected["checks"]}
        actual_by_id = {c["id"]: c["result"] for c in actual["checks"]}
        for check_id, exp_result in expected_by_id.items():
            assert check_id in actual_by_id, f"Check {check_id} missing from scorer output"
            assert actual_by_id[check_id] == exp_result, (
                f"Check {check_id}: expected {exp_result}, got {actual_by_id[check_id]}"
            )


def test_rules_skills_overall_intermediate():
    result = _run(["--root", str(REPO_ROOT)])
    scorecard = json.loads(result.stdout)
    assert scorecard["summary"]["overall_acam"] == "intermediate"


# ---------------------------------------------------------------------------
# (c) Missing --root → exit 2
# ---------------------------------------------------------------------------

def test_missing_root_exits_2(tmp_path):
    nonexistent = tmp_path / "does_not_exist"
    result = _run(["--root", str(nonexistent)])
    assert result.returncode == 2
    assert "does not exist" in result.stderr.lower() or "not exist" in result.stderr


# ---------------------------------------------------------------------------
# (d) Ladder cap: Configuration — remove scoped rules → drops to basic
# ---------------------------------------------------------------------------

def test_configuration_ladder_cap_to_basic(tmp_path):
    # Only alwaysApply:true rules — no alwaysApply:false → distinct_scopes check fails
    rules_dir = tmp_path / ".cursor" / "rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "rule1.mdc").write_text("---\nalwaysApply: true\n---\nContent")
    (rules_dir / "rule2.mdc").write_text("---\nalwaysApply: true\n---\nContent")
    # AGENTS.md for rationale
    (tmp_path / "AGENTS.md").write_text("# AGENTS\nRules section")
    scorecard = _score(tmp_path)
    cfg = scorecard["dimensions"]["configuration"]
    assert cfg["level"] == "basic", f"Expected basic, got {cfg['level']}"
    assert cfg["score"] == 1


# ---------------------------------------------------------------------------
# (e) Ladder cap: Workflows — gate present but no breadcrumbs → stays basic
# ---------------------------------------------------------------------------

def test_workflows_ladder_cap_to_basic(tmp_path):
    (tmp_path / ".harness").mkdir()
    (tmp_path / ".harness" / "state.json").write_text('{"tasks":[]}')
    # contract-gate.sh present but NO breadcrumbs.jsonl
    hooks_dir = tmp_path / ".cursor" / "hooks"
    hooks_dir.mkdir(parents=True)
    (hooks_dir / "contract-gate.sh").write_text("#!/bin/bash\n# contract check")
    scorecard = _score(tmp_path)
    wf = scorecard["dimensions"]["workflows"]
    assert wf["level"] == "basic", f"Expected basic, got {wf['level']}"


# ---------------------------------------------------------------------------
# (f) Ladder cap: Multi-agent — only 1 agent file → none, not basic
# ---------------------------------------------------------------------------

def test_multi_agent_none_when_single_agent(tmp_path):
    agents_dir = tmp_path / "library" / "cursor" / "agents"
    agents_dir.mkdir(parents=True)
    (agents_dir / "planner.md").write_text("You are a planner.")
    scorecard = _score(tmp_path)
    ma = scorecard["dimensions"]["multi_agent"]
    assert ma["level"] == "none", f"Expected none, got {ma['level']}"


# ---------------------------------------------------------------------------
# (g) Ladder cap: Interaction — coaching present but no context hook → basic
# ---------------------------------------------------------------------------

def test_interaction_ladder_cap_to_basic(tmp_path):
    # Has AGENTS.md (basic pass) + prompt_coaching (intermediate partial)
    # but NO harness-context.sh → context_loading check fails → stays basic
    (tmp_path / "AGENTS.md").write_text("# AGENTS.md\nGuidance here.")
    rules_dir = tmp_path / ".cursor" / "rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "prompt_coaching.mdc").write_text("---\nalwaysApply: false\n---\nCoach")
    scorecard = _score(tmp_path)
    inter = scorecard["dimensions"]["interaction"]
    assert inter["level"] == "basic", f"Expected basic, got {inter['level']}"


# ---------------------------------------------------------------------------
# (h) Configuration basic: single .cursorrules → basic
# ---------------------------------------------------------------------------

def test_configuration_basic_from_cursorrules(tmp_path):
    (tmp_path / ".cursorrules").write_text("Be helpful.")
    scorecard = _score(tmp_path)
    cfg = scorecard["dimensions"]["configuration"]
    assert cfg["level"] == "basic"
    assert cfg["score"] == 1


# ---------------------------------------------------------------------------
# (i) Workflows intermediate: state.json + contract-gate + breadcrumbs
# ---------------------------------------------------------------------------

def test_workflows_intermediate_minimum_artifacts(tmp_path):
    harness = tmp_path / ".harness"
    harness.mkdir()
    (harness / "state.json").write_text('{"tasks":[]}')
    (harness / "breadcrumbs.jsonl").write_text('{"ts":"2026-01-01","role":"builder","msg":"x"}')
    hooks_dir = tmp_path / "library" / "cursor" / "hooks"
    hooks_dir.mkdir(parents=True)
    (hooks_dir / "contract-gate.sh").write_text("#!/bin/bash\n# contract check")
    scorecard = _score(tmp_path)
    wf = scorecard["dimensions"]["workflows"]
    assert wf["level"] == "intermediate"
    assert wf["score"] == 2


# ---------------------------------------------------------------------------
# (j) Multi-agent intermediate: 2 agents + guard hook
# ---------------------------------------------------------------------------

def test_multi_agent_intermediate_minimum_artifacts(tmp_path):
    agents_dir = tmp_path / "library" / "cursor" / "agents"
    agents_dir.mkdir(parents=True)
    (agents_dir / "planner.md").write_text("You are a planner. Plan tasks.")
    (agents_dir / "evaluator.md").write_text("You are an evaluator. Evaluate code.")
    hooks_dir = tmp_path / "library" / "cursor" / "hooks"
    hooks_dir.mkdir(parents=True)
    (hooks_dir / "evaluator-guard.sh").write_text(
        '#!/bin/bash\n{"permission": "deny"}\n'
    )
    scorecard = _score(tmp_path)
    ma = scorecard["dimensions"]["multi_agent"]
    assert ma["level"] == "intermediate"
    assert ma["score"] == 2


# ---------------------------------------------------------------------------
# (k) Interaction intermediate: coaching + context hook
# ---------------------------------------------------------------------------

def test_interaction_intermediate_minimum_artifacts(tmp_path):
    (tmp_path / "AGENTS.md").write_text("# AGENTS\nPrompting guidance here.")
    rules_dir = tmp_path / ".cursor" / "rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "prompt_coaching.mdc").write_text("---\nalwaysApply: false\n---\nCoach")
    hooks_dir = tmp_path / ".cursor" / "hooks"
    hooks_dir.mkdir(parents=True)
    (hooks_dir / "harness-context.sh").write_text(
        "#!/bin/bash\n# sessionStart hook\n# injects contract and breadcrumb state"
    )
    scorecard = _score(tmp_path)
    inter = scorecard["dimensions"]["interaction"]
    assert inter["level"] == "intermediate"
    assert inter["score"] == 2


# ---------------------------------------------------------------------------
# (l) Markdown output: correct columns, exactly 4 data rows
# ---------------------------------------------------------------------------

def test_markdown_output_format():
    result = _run(["--root", str(REPO_ROOT), "--format", "markdown"])
    assert result.returncode == 0
    lines = [l for l in result.stdout.strip().splitlines() if l.startswith("|")]
    # header + separator + 4 data rows = 6 lines minimum
    assert len(lines) >= 6, f"Expected ≥6 table lines, got {len(lines)}: {result.stdout}"
    header = lines[0].lower()
    assert "dimension" in header
    assert "level" in header
    assert "key gap" in header
    # Count data rows (skip header and separator)
    data_rows = [l for l in lines[2:] if not l.startswith("|---")]
    assert len(data_rows) == 4, f"Expected 4 data rows, got {len(data_rows)}"


# ---------------------------------------------------------------------------
# (m) Partial Advanced does not upgrade: AGENTS.md alone → not Advanced Config
# ---------------------------------------------------------------------------

def test_partial_advanced_does_not_upgrade(tmp_path):
    # Has AGENTS.md (portability) + scoped rules, but no ablation data
    rules_dir = tmp_path / ".cursor" / "rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "always_rule.mdc").write_text("---\nalwaysApply: true\n---\nContent")
    (rules_dir / "optional_rule.mdc").write_text("---\nalwaysApply: false\n---\nContent")
    (tmp_path / "AGENTS.md").write_text("# AGENTS.md\nCross-tool portability.")
    scorecard = _score(tmp_path)
    cfg = scorecard["dimensions"]["configuration"]
    # portability passes but ablation is missing → must NOT be advanced
    assert cfg["level"] == "intermediate", (
        f"Partial Advanced artifacts must not upgrade level: got {cfg['level']}"
    )
