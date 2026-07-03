"""Tests for library/cursor/hooks/skill-suggest.py.

Unit tests for keyword extraction, matching, and edge cases.
Integration test for CLI invocation against real skills directory.
"""

import json
import subprocess
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "library" / "cursor" / "hooks" / "skill-suggest.py"
REAL_SKILLS = REPO_ROOT / "library" / "cursor" / "skills"

import sys
sys.path.insert(0, str(SCRIPT.parent))
import importlib
skill_suggest = importlib.import_module("skill-suggest")


def _write_skill(skills_dir: Path, name: str, description: str) -> Path:
    """Create a SKILL.md with given name and description."""
    skill_dir = skills_dir / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    content = textwrap.dedent(f"""\
        ---
        name: {name}
        description: "{description}"
        disable-model-invocation: false
        ---

        # {name}

        Skill content here.
    """)
    skill_path = skill_dir / "SKILL.md"
    skill_path.write_text(content)
    return skill_path


class TestExtractTriggers:
    def test_extracts_triggers_from_use_when(self):
        desc = "Review code for quality. Use when: review code, code review, check code."
        triggers = skill_suggest._extract_triggers(desc)
        assert "review code" in triggers
        assert "code review" in triggers
        assert "check code" in triggers

    def test_empty_description_returns_empty(self):
        assert skill_suggest._extract_triggers("") == []

    def test_no_use_when_falls_back_to_full_description(self):
        desc = "This skill does things but has no triggers."
        triggers = skill_suggest._extract_triggers(desc)
        assert len(triggers) == 1
        assert triggers[0] == "this skill does things but has no triggers"

    def test_triggers_are_lowercased(self):
        desc = "Do things. Use when: Deploy Infrastructure, CREATE Manifest."
        triggers = skill_suggest._extract_triggers(desc)
        assert "deploy infrastructure" in triggers
        assert "create manifest" in triggers


class TestParseFrontmatter:
    def test_parses_quoted_description(self):
        content = textwrap.dedent("""\
            ---
            name: test-skill
            description: "Do stuff. Use when: do stuff, make things."
            ---
            # Content
        """)
        result = skill_suggest._parse_frontmatter(content)
        assert result is not None
        assert result["name"] == "test-skill"
        assert "do stuff" in result["triggers"]

    def test_parses_multiline_description(self):
        content = textwrap.dedent("""\
            ---
            name: multi-skill
            description: >-
              Audit code for things.
              Use when: audit code, check things.
            disable-model-invocation: false
            ---
            # Content
        """)
        result = skill_suggest._parse_frontmatter(content)
        assert result is not None
        assert "audit code" in result["triggers"]

    def test_no_frontmatter_returns_none(self):
        content = "# Just a heading\nNo frontmatter here."
        assert skill_suggest._parse_frontmatter(content) is None

    def test_empty_description_returns_no_triggers(self):
        content = textwrap.dedent("""\
            ---
            name: empty-desc
            description: ""
            ---
            # Content
        """)
        result = skill_suggest._parse_frontmatter(content)
        assert result is not None
        assert result["triggers"] == []


class TestMatchPrompt:
    def test_single_match(self, tmp_path):
        _write_skill(tmp_path, "code-review", "Review code. Use when: review code, find bugs.")
        skills = skill_suggest._load_skills(tmp_path)
        matches = skill_suggest._match_prompt("please review code for issues", skills)
        assert len(matches) == 1
        assert matches[0]["name"] == "code-review"
        assert "review code" in matches[0]["matched_keywords"]

    def test_multiple_matches_ranked_by_keyword_count(self, tmp_path):
        _write_skill(tmp_path, "skill-a", "Do A. Use when: deploy, rollout, scale up.")
        _write_skill(tmp_path, "skill-b", "Do B. Use when: deploy, build.")
        skills = skill_suggest._load_skills(tmp_path)
        matches = skill_suggest._match_prompt("deploy and scale up the service", skills)
        assert len(matches) == 2
        assert matches[0]["name"] == "skill-a"
        assert len(matches[0]["matched_keywords"]) >= 2

    def test_zero_matches(self, tmp_path):
        _write_skill(tmp_path, "skill-x", "Do X. Use when: fly planes, bake bread.")
        skills = skill_suggest._load_skills(tmp_path)
        matches = skill_suggest._match_prompt("review my typescript code", skills)
        assert matches == []

    def test_max_3_cap(self, tmp_path):
        for i in range(6):
            _write_skill(tmp_path, f"skill-{i}", f"Do {i}. Use when: deploy, test.")
        skills = skill_suggest._load_skills(tmp_path)
        matches = skill_suggest._match_prompt("deploy and test", skills)
        assert len(matches) <= 3

    def test_empty_prompt_returns_empty(self, tmp_path):
        _write_skill(tmp_path, "skill-a", "Do A. Use when: anything, everything.")
        skills = skill_suggest._load_skills(tmp_path)
        matches = skill_suggest._match_prompt("", skills)
        assert matches == []

    def test_whole_word_matching_rejects_substrings(self, tmp_path):
        """'previewing' should NOT match trigger 'review' (EC6)."""
        _write_skill(tmp_path, "code-review", "Review code. Use when: review code.")
        skills = skill_suggest._load_skills(tmp_path)
        matches = skill_suggest._match_prompt("previewing my codebase", skills)
        assert matches == []

    def test_alphabetical_tiebreak(self, tmp_path):
        _write_skill(tmp_path, "z-skill", "Do Z. Use when: deploy.")
        _write_skill(tmp_path, "a-skill", "Do A. Use when: deploy.")
        skills = skill_suggest._load_skills(tmp_path)
        matches = skill_suggest._match_prompt("deploy the service", skills)
        assert len(matches) == 2
        assert matches[0]["name"] == "a-skill"
        assert matches[1]["name"] == "z-skill"


class TestLoadSkills:
    def test_missing_skills_dir(self):
        skills = skill_suggest._load_skills(Path("/nonexistent/path"))
        assert skills == []

    def test_empty_skills_dir(self, tmp_path):
        skills = skill_suggest._load_skills(tmp_path)
        assert skills == []

    def test_malformed_frontmatter_skipped(self, tmp_path):
        skill_dir = tmp_path / "bad-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("No frontmatter at all, just text.")
        _write_skill(tmp_path, "good-skill", "Do good. Use when: do good.")
        skills = skill_suggest._load_skills(tmp_path)
        assert len(skills) == 1
        assert skills[0]["name"] == "good-skill"


class TestSuggestFunction:
    def test_returns_correct_structure(self, tmp_path):
        _write_skill(tmp_path, "my-skill", "Do stuff. Use when: do stuff.")
        result = skill_suggest.suggest(tmp_path, "do stuff please")
        assert "skill_suggestions" in result
        assert len(result["skill_suggestions"]) == 1
        s = result["skill_suggestions"][0]
        assert "name" in s
        assert "path" in s
        assert "description" in s
        assert "matched_keywords" in s

    def test_nonexistent_dir_returns_empty(self):
        result = skill_suggest.suggest(Path("/nonexistent"), "anything")
        assert result == {"skill_suggestions": []}


class TestFormatSuggestionsText:
    def test_no_suggestions_returns_empty_string(self):
        assert skill_suggest.format_suggestions_text({"skill_suggestions": []}) == ""

    def test_formats_with_header_and_numbered_list(self, tmp_path):
        _write_skill(tmp_path, "code-review", "Review code for quality. Use when: review code.")
        result = skill_suggest.suggest(tmp_path, "review code")
        text = skill_suggest.format_suggestions_text(result)
        assert "SKILL SUGGESTIONS: Based on your prompt, these skills may help:" in text
        assert "code-review" in text
        assert "1." in text
        assert "(path:" in text


class TestCLI:
    def test_cli_json_output(self):
        result = subprocess.run(
            ["python3", str(SCRIPT), "--skills-dir", str(REAL_SKILLS),
             "--prompt", "review my code for bugs"],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "skill_suggestions" in data
        names = [s["name"] for s in data["skill_suggestions"]]
        assert "code-review" in names

    def test_cli_nonexistent_dir_exits_zero(self):
        result = subprocess.run(
            ["python3", str(SCRIPT), "--skills-dir", "/nonexistent",
             "--prompt", "test"],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["skill_suggestions"] == []

    def test_cli_text_format(self):
        result = subprocess.run(
            ["python3", str(SCRIPT), "--skills-dir", str(REAL_SKILLS),
             "--prompt", "review my code", "--format", "text"],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "SKILL SUGGESTIONS" in result.stdout

    def test_cli_empty_prompt(self):
        result = subprocess.run(
            ["python3", str(SCRIPT), "--skills-dir", str(REAL_SKILLS),
             "--prompt", ""],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["skill_suggestions"] == []
