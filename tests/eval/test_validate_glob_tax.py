"""Glob-tax helpers in tests/validate.py — warn-only, never fails exit on over-budget."""

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
VALIDATE_PATH = REPO_ROOT / "tests" / "validate.py"


def _load_validate():
    spec = importlib.util.spec_from_file_location("validate_mod", VALIDATE_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def validate():
    return _load_validate()


class TestGlobMatches:
    def test_src_py_matches_architecture_style(self, validate):
        globs = (
            "src/**/*.{py,ts,tsx}, app/**/*.{py,ts,tsx}, "
            "backend/**/*.{py,ts,tsx}, frontend/**/*.{py,ts,tsx}, "
            "services/**/*.{py,ts,tsx}"
        )
        assert validate.glob_matches(globs, "src/foo.py")
        assert validate.glob_matches(globs, "app/main.ts")
        assert not validate.glob_matches(globs, "library/cursor/hooks/x.sh")

    def test_experiments_match_research_globs(self, validate):
        globs = "experiments/**/*.{py,ipynb,md}, analysis/**/*.{py,ipynb,md}"
        assert validate.glob_matches(globs, "experiments/run.py")
        assert not validate.glob_matches(globs, "src/foo.py")

    def test_test_globs(self, validate):
        globs = "**/test*.py, **/tests/**/*.py"
        assert validate.glob_matches(globs, "tests/eval/x.py")
        assert validate.glob_matches(globs, "tests/eval/test_foo.py")


class TestGlobTaxBudget:
    def test_check_glob_tax_warns_not_errors_on_library(self, validate):
        result = validate.check_glob_tax(REPO_ROOT / "library" / "cursor" / "rules")
        assert result.passed, result.errors
        assert any("glob-tax" in w for w in result.warnings)

    def test_over_budget_is_warning_only(self, validate, tmp_path):
        rules = tmp_path
        # Fat always-on + fat glob rule that matches src/
        (rules / "always.mdc").write_text(
            "---\nalwaysApply: true\n---\n\n" + ("word " * 400)
        )
        (rules / "arch.mdc").write_text(
            '---\nglobs: "src/**/*.py"\nalwaysApply: false\n---\n\n' + ("word " * 400)
        )
        result = validate.check_glob_tax(rules)
        assert result.passed, "glob-tax must not set errors"
        assert any("over budget" in w and "src/foo.py" in w for w in result.warnings)

    def test_main_exits_zero_when_glob_tax_warns(self, validate, monkeypatch, tmp_path):
        """Over-budget glob-tax must keep validate exit code 0."""
        rules = tmp_path / "rules"
        rules.mkdir()
        (rules / "always.mdc").write_text(
            "---\nalwaysApply: true\n---\n\n" + ("word " * 50)
        )
        (rules / "arch.mdc").write_text(
            '---\nglobs: "src/**/*.py"\nalwaysApply: false\n---\n\n' + ("word " * 800)
        )
        skills = tmp_path / "skills"
        skills.mkdir()
        monkeypatch.setattr(validate, "RULES_DIR", rules)
        monkeypatch.setattr(validate, "SKILLS_DIR", skills)
        assert validate.main() == 0
