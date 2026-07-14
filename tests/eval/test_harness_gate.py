"""Unit tests for library/cursor/hooks/harness-gate.sh.

Invokes the hook directly from a temp directory (no .harness/ files) so
Case 1 (harness active) does not fire, letting us test the glue and routing
logic in isolation.
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


# ---------------------------------------------------------------------------
# PT-BR short feature prompts must trigger HARNESS ROUTING
# ---------------------------------------------------------------------------

class TestShortPTBRPromptsRouted:
    """The three canonical short Portuguese feature prompts must NOT be
    classified as glue — they must trigger the cold-start routing message."""

    def test_refatora_tudo_triggers_routing(self, tmp_path):
        """'refatora tudo' — 13 chars, 2 words — must not be classified as glue."""
        d = run_hook("refatora tudo", tmp_path)
        assert "followup_message" in d, f"Expected routing but got: {d}"
        assert "HARNESS ROUTING" in d["followup_message"]

    def test_migra_o_banco_triggers_routing(self, tmp_path):
        """'migra o banco' — 13 chars, 3 words — must trigger routing."""
        d = run_hook("migra o banco", tmp_path)
        assert "followup_message" in d, f"Expected routing but got: {d}"
        assert "HARNESS ROUTING" in d["followup_message"]

    def test_adiciona_autenticacao_triggers_routing(self, tmp_path):
        """'adiciona autenticação' — 21 chars, 2 words — must trigger routing."""
        d = run_hook("adiciona autenticação", tmp_path)
        assert "followup_message" in d, f"Expected routing but got: {d}"
        assert "HARNESS ROUTING" in d["followup_message"]


# ---------------------------------------------------------------------------
# True glue messages must pass through silently ({})
# ---------------------------------------------------------------------------

class TestGluePassThrough:
    """Single-word and very-short two-word conversational responses must
    exit silently without injecting a routing message."""

    @pytest.mark.parametrize("prompt", ["ok", "yes", "no", "sure", "sim"])
    def test_single_word_glue(self, tmp_path, prompt):
        d = run_hook(prompt, tmp_path)
        assert d == {}, f"Expected glue pass-through {{}} but got: {d}"

    def test_got_it_is_glue(self, tmp_path):
        """'got it' — 6 chars, 2 words — must be treated as glue."""
        d = run_hook("got it", tmp_path)
        assert d == {}, f"Expected glue pass-through but got: {d}"

    def test_proceed_is_glue(self, tmp_path):
        """'proceed' — 7 chars, 1 word — must be treated as glue."""
        d = run_hook("proceed", tmp_path)
        assert d == {}, f"Expected glue pass-through but got: {d}"


# ---------------------------------------------------------------------------
# Explicit opt-out and simple queries must pass through
# ---------------------------------------------------------------------------

class TestOptOutAndSimple:
    def test_skip_harness_passes(self, tmp_path):
        """'skip harness and just code' must exit silently (Case 3)."""
        d = run_hook("skip harness and just code", tmp_path)
        assert d == {}, f"Expected silent pass-through but got: {d}"

    def test_what_question_passes(self, tmp_path):
        """'what does this function do' matches SIMPLE_PATTERNS → no routing."""
        d = run_hook("what does this function do", tmp_path)
        assert d == {}, f"Expected simple-pattern pass-through but got: {d}"

    def test_review_prompt_passes(self, tmp_path):
        """'review the auth module' matches SIMPLE_PATTERNS → no routing."""
        d = run_hook("review the auth module", tmp_path)
        assert d == {}, f"Expected simple-pattern pass-through but got: {d}"


# ---------------------------------------------------------------------------
# Harness already active — Case 1 must always pass silently
# ---------------------------------------------------------------------------

class TestHarnessActive:
    def test_state_json_present_allows_any_prompt(self, tmp_path):
        """When state.json exists, even a non-trivial prompt exits silently."""
        harness_dir = tmp_path / ".harness"
        harness_dir.mkdir()
        state = {
            "project": "test", "schema_version": 2, "vision": "v",
            "tasks": [{"id": "t1", "name": "test", "status": "pending"}],
        }
        (harness_dir / "state.json").write_text(json.dumps(state))
        d = run_hook("implementa o sistema de autenticação completo", tmp_path)
        assert d == {}, f"Expected silent pass-through with active harness but got: {d}"
