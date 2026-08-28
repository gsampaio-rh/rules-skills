"""Unit tests for library/cursor/hooks/harness-gate.sh (opt-in default).

Invokes the hook directly from a temp directory (no .harness/ files) so
Case 1 (harness active) does not fire, letting us test free-default and opt-in.
"""

import json
import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
HOOK = REPO_ROOT / "library" / "cursor" / "hooks" / "harness-gate.sh"

_PYENV_ROOT = os.environ.get("PYENV_ROOT", str(Path.home() / ".pyenv"))
_HOOK_PATH = (
    f"{_PYENV_ROOT}/shims:{_PYENV_ROOT}/bin:"
    "/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
)


def run_hook(prompt: str, cwd: Path) -> dict:
    """Run harness-gate.sh from cwd with no .harness/ files present."""
    env = {
        "PATH": _HOOK_PATH,
        "HOME": str(Path.home()),
    }
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


class TestFreeDefaultNoAutoArm:
    """Long / feature prompts must NOT arm routing-pending without opt-in."""

    def test_refatora_tudo_is_free(self, tmp_path):
        d = run_hook("refatora tudo", tmp_path)
        assert d == {}, f"Expected free default but got: {d}"
        assert not (tmp_path / ".harness" / ".routing-pending").exists()

    def test_long_auth_prompt_is_free(self, tmp_path):
        d = run_hook(
            "implement a new authentication service with OAuth2 across microservices",
            tmp_path,
        )
        assert d == {}, f"Expected free default but got: {d}"
        assert not (tmp_path / ".harness" / ".routing-pending").exists()

    def test_review_prompt_is_free(self, tmp_path):
        d = run_hook("review the auth module", tmp_path)
        assert d == {}, f"Expected free default but got: {d}"
        assert not (tmp_path / ".harness" / ".routing-pending").exists()

    def test_what_question_is_free(self, tmp_path):
        d = run_hook("what does this function do", tmp_path)
        assert d == {}, f"Expected free default but got: {d}"
        assert not (tmp_path / ".harness" / ".routing-pending").exists()


class TestGluePassThrough:
    @pytest.mark.parametrize("prompt", ["ok", "yes", "no", "sure", "sim"])
    def test_single_word_glue(self, tmp_path, prompt):
        d = run_hook(prompt, tmp_path)
        assert d == {}, f"Expected glue pass-through {{}} but got: {d}"

    def test_got_it_is_glue(self, tmp_path):
        d = run_hook("got it", tmp_path)
        assert d == {}, f"Expected glue pass-through but got: {d}"


class TestOptInArms:
    @pytest.mark.parametrize(
        "prompt",
        [
            "use harness to implement OAuth2",
            "with harness refactor auth",
            "/planner break this into tasks",
            "follow adversarial-harness skill to plan",
            "USE HARNESS for this feature",
        ],
    )
    def test_opt_in_phrases_arm(self, tmp_path, prompt):
        d = run_hook(prompt, tmp_path)
        assert "followup_message" in d, f"Expected opt-in arm but got: {d}"
        assert (tmp_path / ".harness" / ".routing-pending").is_file()


class TestOptOutAndActive:
    def test_skip_harness_passes(self, tmp_path):
        d = run_hook("skip harness and just code", tmp_path)
        assert d == {}, f"Expected silent pass-through but got: {d}"

    def test_state_json_present_allows_any_prompt(self, tmp_path):
        harness_dir = tmp_path / ".harness"
        harness_dir.mkdir()
        state = {
            "project": "test",
            "schema_version": 2,
            "vision": "v",
            "tasks": [{"id": "t1", "name": "test", "status": "pending"}],
        }
        (harness_dir / "state.json").write_text(json.dumps(state))
        d = run_hook("implementa o sistema de autenticação completo", tmp_path)
        assert d == {}, f"Expected silent pass-through with active harness but got: {d}"
