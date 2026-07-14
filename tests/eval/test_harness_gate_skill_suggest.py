"""Unit tests for skill-suggest integration in harness-gate.sh (Case 5).

Verifies that harness-gate.sh injects SKILL SUGGESTIONS via followup_message
for non-glue prompts that match a known skill trigger — both when the harness
is active (mid-session) and on cold-start simple prompts.

These tests use SKILLS_DIR pointed at the library skills so they work without
a local make sync-local having been run.
"""

import json
import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
HOOK = REPO_ROOT / "library" / "cursor" / "hooks" / "harness-gate.sh"
SKILLS_DIR = str(REPO_ROOT / "library" / "cursor" / "skills")

_PYENV_ROOT = os.environ.get("PYENV_ROOT", str(Path.home() / ".pyenv"))
_HOOK_PATH = (
    f"{_PYENV_ROOT}/shims:{_PYENV_ROOT}/bin:"
    "/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
)


def run_hook(prompt: str, cwd: Path, skills_dir: str | None = SKILLS_DIR) -> dict:
    """Run harness-gate.sh from cwd, optionally setting SKILLS_DIR."""
    env = {
        "PATH": _HOOK_PATH,
        "HOME": str(Path.home()),
    }
    if skills_dir is not None:
        env["SKILLS_DIR"] = skills_dir
    if "PYENV_VERSION" in os.environ:
        env["PYENV_VERSION"] = os.environ["PYENV_VERSION"]
    result = subprocess.run(
        ["bash", str(HOOK)],
        input=json.dumps({"prompt": prompt}),
        capture_output=True,
        text=True,
        cwd=str(cwd),
        env=env,
    )
    assert result.returncode == 0, f"Hook exited non-zero:\n{result.stderr}"
    raw = result.stdout.strip()
    assert raw, f"Hook produced empty stdout\nstderr: {result.stderr}"
    return json.loads(raw)


def _write_state(path: Path) -> None:
    state = {
        "project": "test", "schema_version": 2, "vision": "v",
        "tasks": [{"id": "t1", "name": "x", "status": "pending"}],
    }
    harness = path / ".harness"
    harness.mkdir(parents=True, exist_ok=True)
    (harness / "state.json").write_text(json.dumps(state))


# ---------------------------------------------------------------------------
# AC1: Mid-session (harness active) + skill-triggering prompt → SKILL SUGGESTIONS
# ---------------------------------------------------------------------------

class TestMidSessionSkillSuggest:
    def test_review_prompt_with_active_harness_returns_skill_suggestions(self, tmp_path):
        """Harness active + 'review my code' → followup_message contains SKILL SUGGESTIONS.

        This is the core regression: previously Case 1 exited {} immediately.
        """
        _write_state(tmp_path)
        d = run_hook("review my code", tmp_path)
        assert d != {}, "Expected skill suggestions but got empty pass-through"
        assert "followup_message" in d
        assert "SKILL SUGGESTIONS" in d["followup_message"]

    def test_followup_message_does_not_contain_harness_routing_mid_session(self, tmp_path):
        """Mid-session skill suggestions must never inject HARNESS ROUTING (harness is active)."""
        _write_state(tmp_path)
        d = run_hook("review my code", tmp_path)
        assert "HARNESS ROUTING" not in d.get("followup_message", "")


# ---------------------------------------------------------------------------
# AC2: Cold-start + simple prompt + skill match → SKILL SUGGESTIONS, no routing
# ---------------------------------------------------------------------------

class TestColdStartSimpleSkillSuggest:
    def test_review_prompt_cold_start_returns_skill_suggestions(self, tmp_path):
        """Cold start + 'review my code' → SKILL SUGGESTIONS (simple pattern, no routing)."""
        d = run_hook("review my code", tmp_path)
        assert "followup_message" in d, f"Expected skill suggestions but got: {d}"
        assert "SKILL SUGGESTIONS" in d["followup_message"]

    def test_cold_start_simple_skill_prompt_does_not_also_route(self, tmp_path):
        """SKILL SUGGESTIONS and HARNESS ROUTING must not appear simultaneously."""
        d = run_hook("review my code", tmp_path)
        assert "HARNESS ROUTING" not in d.get("followup_message", "")


# ---------------------------------------------------------------------------
# AC3: Glue still suppressed even when skills dir is present and harness is active
# ---------------------------------------------------------------------------

class TestGlueStillSuppressedWithSkills:
    def test_ok_glue_with_active_harness_and_skills(self, tmp_path):
        """'ok' must exit {} regardless of SKILLS_DIR or harness state."""
        _write_state(tmp_path)
        d = run_hook("ok", tmp_path)
        assert d == {}, f"Expected glue pass-through but got: {d}"


# ---------------------------------------------------------------------------
# AC4: Cold-start routing takes precedence — no skill suggestions after routing exit
# ---------------------------------------------------------------------------

class TestRoutingPrecedenceOverSkills:
    def test_nontrivial_cold_start_routes_not_suggests(self, tmp_path):
        """'migra o banco' from cold start → HARNESS ROUTING, never SKILL SUGGESTIONS."""
        d = run_hook("migra o banco", tmp_path, skills_dir=None)
        assert "followup_message" in d
        assert "HARNESS ROUTING" in d["followup_message"]
        assert "SKILL SUGGESTIONS" not in d["followup_message"]


# ---------------------------------------------------------------------------
# AC5: No skill match → silent pass-through {} (no noise for unmatched prompts)
# ---------------------------------------------------------------------------

class TestNoSkillMatchPassThrough:
    def test_unmatched_prompt_with_active_harness_returns_empty(self, tmp_path):
        """'translate this to french' matches no skill → {} (no false positives)."""
        _write_state(tmp_path)
        d = run_hook("translate this to french", tmp_path)
        assert d == {}, f"Expected empty pass-through for unmatched prompt but got: {d}"


# ---------------------------------------------------------------------------
# EC1: SKILLS_DIR unset + no .cursor/skills → graceful {}
# ---------------------------------------------------------------------------

class TestNoSkillsDirGracefulFallback:
    def test_no_skills_dir_exits_cleanly(self, tmp_path):
        """When no SKILLS_DIR and no .cursor/skills in CWD → {} with returncode 0."""
        result = subprocess.run(
            ["bash", str(HOOK)],
            input=json.dumps({"prompt": "review my code"}),
            capture_output=True,
            text=True,
            cwd=str(tmp_path),
            env={
                "PATH": _HOOK_PATH,
                "HOME": str(Path.home()),
                **({"PYENV_VERSION": os.environ["PYENV_VERSION"]} if "PYENV_VERSION" in os.environ else {}),
            },
        )
        assert result.returncode == 0, f"Non-zero exit:\n{result.stderr}"
        assert "Traceback" not in result.stderr, "Python traceback in stderr"
        d = json.loads(result.stdout.strip())
        assert d == {}, f"Expected graceful {{}} but got: {d}"


# ---------------------------------------------------------------------------
# EC3: Empty SKILLS_DIR (dir exists, no SKILL.md files) → {}
# ---------------------------------------------------------------------------

class TestEmptySkillsDirGraceful:
    def test_empty_skills_dir_exits_cleanly(self, tmp_path):
        """SKILLS_DIR exists but has no SKILL.md files → {} without error."""
        empty_skills = tmp_path / "skills"
        empty_skills.mkdir()
        _write_state(tmp_path)
        d = run_hook("review my code", tmp_path, skills_dir=str(empty_skills))
        assert d == {}, f"Expected empty result with empty skills dir but got: {d}"
