#!/usr/bin/env python3
"""Validate Cursor rules and skills against authoring standards.

Checks:
- Rules: valid frontmatter, line limits, activation mode, no dead rules
- Skills: valid frontmatter, name matches folder, required sections, line limits
- Budget: total always-on rules under token limit
"""

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

RULES_DIR = Path("library/cursor/rules")
SKILLS_DIR = Path("library/cursor/skills")

MAX_RULE_LINES = 200
MAX_SKILL_LINES = 300
MAX_ALWAYS_ON_TOKENS = 2000  # words * ~1.3 ≈ tokens
MAX_ALWAYS_ON_WORDS = int(MAX_ALWAYS_ON_TOKENS / 1.3)

REQUIRED_SKILL_SECTIONS = [
    "Proactive Triggers",
    "Stop Conditions",
    "Output Artifacts",
]

VALID_RULE_ACTIVATIONS = [
    "alwaysApply_only",
    "globs_only",
    "description_only",
    "globs_and_description",
]


@dataclass
class ValidationResult:
    file: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return len(self.errors) == 0


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)", text, re.DOTALL)
    if not match:
        return {}, text

    fm_text, body = match.group(1), match.group(2)
    fm: dict[str, str] = {}
    for line in fm_text.strip().splitlines():
        if ":" in line:
            key, val = line.split(":", 1)
            fm[key.strip()] = val.strip().strip('"').strip("'")
    return fm, body


def classify_activation(fm: dict[str, str]) -> str:
    always = fm.get("alwaysApply", "false").lower() == "true"
    has_globs = bool(fm.get("globs", ""))
    has_desc = bool(fm.get("description", ""))

    if always and not has_globs:
        return "alwaysApply_only"
    if has_globs and not always:
        if has_desc:
            return "globs_and_description"
        return "globs_only"
    if has_desc and not has_globs and not always:
        return "description_only"
    if always and has_globs:
        return "alwaysApply_with_globs"
    return "dead"


def validate_rule(path: Path) -> ValidationResult:
    result = ValidationResult(file=str(path))
    text = path.read_text()
    lines = text.splitlines()
    fm, _ = parse_frontmatter(text)

    if not fm:
        result.errors.append("Missing or invalid frontmatter")
        return result

    if len(lines) > MAX_RULE_LINES:
        result.errors.append(f"Exceeds {MAX_RULE_LINES} line limit ({len(lines)} lines)")

    activation = classify_activation(fm)
    if activation == "dead":
        result.errors.append(
            "Dead rule: no alwaysApply, no globs, no description — rule will never load"
        )
    elif activation == "alwaysApply_with_globs":
        result.warnings.append("alwaysApply=true with globs — globs are ignored when alwaysApply is true")
    elif activation not in VALID_RULE_ACTIVATIONS:
        result.errors.append(f"Invalid activation mode: {activation}")

    return result


def validate_skill(path: Path) -> ValidationResult:
    skill_dir = path.parent
    result = ValidationResult(file=str(path))
    text = path.read_text()
    lines = text.splitlines()
    fm, body = parse_frontmatter(text)

    if not fm:
        result.errors.append("Missing or invalid frontmatter")
        return result

    name = fm.get("name", "")
    if not name:
        result.errors.append("Missing 'name' in frontmatter")
    elif name != skill_dir.name:
        result.errors.append(
            f"Name mismatch: frontmatter says '{name}', folder is '{skill_dir.name}'"
        )

    if not fm.get("description", ""):
        result.errors.append("Missing 'description' in frontmatter")

    if "disable-model-invocation" not in fm:
        result.warnings.append("Missing 'disable-model-invocation' in frontmatter")

    if len(lines) > MAX_SKILL_LINES:
        result.errors.append(f"Exceeds {MAX_SKILL_LINES} line limit ({len(lines)} lines)")

    for section in REQUIRED_SKILL_SECTIONS:
        if section.lower() not in body.lower():
            result.errors.append(f"Missing required section: '{section}'")

    mode_count = len(re.findall(r"###\s+Mode\s+\d", body))
    if mode_count < 2:
        result.warnings.append(f"Expected at least 2 modes, found {mode_count}")

    return result


def check_token_budget(rules_dir: Path) -> ValidationResult:
    result = ValidationResult(file="[always-on budget]")
    total_words = 0
    always_on_files: list[str] = []

    for path in sorted(rules_dir.glob("*.mdc")):
        text = path.read_text()
        fm, body = parse_frontmatter(text)
        if fm.get("alwaysApply", "false").lower() == "true":
            word_count = len(body.split())
            total_words += word_count
            always_on_files.append(f"{path.name} ({word_count} words)")

    estimated_tokens = int(total_words * 1.3)

    if estimated_tokens > MAX_ALWAYS_ON_TOKENS:
        result.errors.append(
            f"Always-on token budget exceeded: ~{estimated_tokens} tokens "
            f"(limit: {MAX_ALWAYS_ON_TOKENS}). Files: {', '.join(always_on_files)}"
        )
    else:
        result.warnings.append(
            f"Always-on budget: ~{estimated_tokens}/{MAX_ALWAYS_ON_TOKENS} tokens "
            f"({len(always_on_files)} rules)"
        )

    return result


def main() -> int:
    results: list[ValidationResult] = []

    if RULES_DIR.exists():
        for path in sorted(RULES_DIR.glob("*.mdc")):
            results.append(validate_rule(path))
        results.append(check_token_budget(RULES_DIR))

    if SKILLS_DIR.exists():
        for skill_dir in sorted(SKILLS_DIR.iterdir()):
            skill_file = skill_dir / "SKILL.md"
            if skill_file.exists():
                results.append(validate_skill(skill_file))

    has_errors = False
    for r in results:
        if r.errors or r.warnings:
            status = "FAIL" if r.errors else "WARN"
            print(f"\n{'❌' if r.errors else '⚠️'}  {r.file} [{status}]")
            for e in r.errors:
                print(f"   ERROR: {e}")
            for w in r.warnings:
                print(f"   WARN:  {w}")
            if r.errors:
                has_errors = True
        else:
            print(f"✅ {r.file}")

    total_errors = sum(len(r.errors) for r in results)
    total_warnings = sum(len(r.warnings) for r in results)
    print(f"\n{'─' * 50}")
    print(f"Results: {total_errors} errors, {total_warnings} warnings")

    if has_errors:
        print("FAILED")
        return 1

    print("PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
