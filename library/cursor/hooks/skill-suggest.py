#!/usr/bin/env python3
"""
Suggest relevant skills based on prompt keyword matching.

Reads SKILL.md files from a skills directory, extracts trigger keywords
from the YAML frontmatter 'description' field (after "Use when:"), and
matches them against the user's prompt. Returns the top N matches as JSON.

Usage:
    python skill-suggest.py --skills-dir .cursor/skills --prompt "review my code"
    python skill-suggest.py --skills-dir .cursor/skills --prompt "deploy to openshift"

Output (JSON):
    {"skill_suggestions": [{"name": "...", "path": "...", "description": "...", "matched_keywords": [...]}]}
"""

import argparse
import json
import re
import sys
from pathlib import Path

MAX_SUGGESTIONS = 3

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)

_USE_WHEN_RE = re.compile(r"Use when:\s*(.+?)\.?\s*$", re.IGNORECASE | re.DOTALL)

_NAME_RE = re.compile(r"^name:\s*(.+)$", re.MULTILINE)

_DESC_RE = re.compile(
    r'^description:\s*(?:>-\s*\n((?:[ \t]+.+\n?)+)|["\'](.+?)["\']|(.+))$',
    re.MULTILINE,
)


def _parse_frontmatter(content: str) -> dict | None:
    """Extract name and description from YAML frontmatter."""
    match = _FRONTMATTER_RE.match(content)
    if not match:
        return None

    fm_text = match.group(1)

    name_match = _NAME_RE.search(fm_text)
    name = name_match.group(1).strip().strip("'\"") if name_match else None

    desc_match = _DESC_RE.search(fm_text)
    if not desc_match:
        return {"name": name, "description": "", "triggers": []}

    if desc_match.group(1):
        desc = " ".join(line.strip() for line in desc_match.group(1).splitlines() if line.strip())
    elif desc_match.group(2):
        desc = desc_match.group(2)
    else:
        desc = desc_match.group(3).strip().strip("'\"")

    return {"name": name, "description": desc, "triggers": _extract_triggers(desc)}


def _extract_triggers(description: str) -> list[str]:
    """Extract trigger phrases from the 'Use when:' section of a description.

    If no 'Use when:' marker exists, the entire description is treated
    as a single trigger phrase (fallback behavior per EC8).
    """
    match = _USE_WHEN_RE.search(description)
    if not match:
        cleaned = description.strip().rstrip(".")
        return [cleaned.lower()] if cleaned else []

    raw = match.group(1).strip().rstrip(".")
    triggers = [t.strip().lower() for t in raw.split(",") if t.strip()]
    return triggers


def _load_skills(skills_dir: Path) -> list[dict]:
    """Load all SKILL.md files and extract metadata."""
    if not skills_dir.is_dir():
        return []

    skills = []
    for skill_md in sorted(skills_dir.glob("*/SKILL.md")):
        try:
            content = skill_md.read_text(encoding="utf-8")
        except OSError:
            continue

        parsed = _parse_frontmatter(content)
        if parsed is None:
            continue

        if not parsed.get("name"):
            parsed["name"] = skill_md.parent.name

        parsed["path"] = str(skill_md.parent.name)
        skills.append(parsed)

    return skills


def _phrase_matches(phrase: str, prompt_words: set[str]) -> bool:
    """Check if all words in a trigger phrase appear as whole words in the prompt."""
    phrase_words = phrase.split()
    return all(w in prompt_words for w in phrase_words)


def _tokenize_prompt(prompt: str) -> set[str]:
    """Split prompt into lowercase word tokens (alphanumeric + hyphens)."""
    return set(re.findall(r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?", prompt.lower()))


def _match_prompt(prompt: str, skills: list[dict]) -> list[dict]:
    """Match prompt against skill triggers using whole-word matching.

    Ranking: primary sort by number of matching trigger phrases (desc),
    tie-break by skill name (ascending alphabetical).
    """
    if not prompt or not prompt.strip():
        return []

    prompt_words = _tokenize_prompt(prompt)

    matches = []
    for skill in skills:
        triggers = skill.get("triggers", [])
        if not triggers:
            continue

        matched = [t for t in triggers if _phrase_matches(t, prompt_words)]
        if matched:
            matches.append({
                "name": skill["name"],
                "path": skill["path"],
                "description": skill.get("description", ""),
                "matched_keywords": matched,
            })

    matches.sort(key=lambda m: (-len(m["matched_keywords"]), m["name"]))
    return matches[:MAX_SUGGESTIONS]


def suggest(skills_dir: Path, prompt: str) -> dict:
    """Main entry point: load skills, match prompt, return suggestions."""
    skills = _load_skills(skills_dir)
    matches = _match_prompt(prompt, skills)
    return {"skill_suggestions": matches}


def format_suggestions_text(result: dict) -> str:
    """Format suggestions as human-readable text for injection into context.

    Format per AC5: header line followed by numbered list with name, first
    sentence of description, and path.
    """
    suggestions = result.get("skill_suggestions", [])
    if not suggestions:
        return ""

    lines = ["SKILL SUGGESTIONS: Based on your prompt, these skills may help:", ""]
    for i, s in enumerate(suggestions, 1):
        desc = s.get("description", "")
        short_desc = desc.split("Use when:")[0].strip().rstrip(".")
        path = s.get("path", "")
        lines.append(f"{i}. **{s['name']}** — {short_desc} (path: {path}/SKILL.md)")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Suggest relevant skills based on prompt keyword matching."
    )
    parser.add_argument(
        "--skills-dir", type=Path, default=Path(".cursor/skills"),
        help="Path to skills directory (default: .cursor/skills)",
    )
    parser.add_argument(
        "--prompt", type=str, default="",
        help="User prompt text to match against skill triggers",
    )
    parser.add_argument(
        "--format", choices=["json", "text"], default="json",
        help="Output format (default: json)",
    )
    args = parser.parse_args()

    result = suggest(args.skills_dir, args.prompt)

    if args.format == "text":
        text = format_suggestions_text(result)
        if text:
            print(text)
    else:
        print(json.dumps(result, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
