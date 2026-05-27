# Skills Authoring Standard

Internal quality contract for every `SKILL.md` in `.cursor/skills/`. Not loaded by the agent.

## Frontmatter Contract

```yaml
---
name: skill-name                    # lowercase, hyphens only, must match folder name
description: "Trigger keywords and phrases. When to use this skill. What it does."
disable-model-invocation: false     # true for dangerous ops (deploy, commit, destructive)
---
```

- **`description`** is the most important field — it drives agent activation. Write it like a search query with trigger phrases the user would say.
- **`disable-model-invocation: true`** for any skill with side effects (commits, deploys, destructive operations). The user must explicitly invoke these via `/skill-name`.
- **`name`** must match the folder name exactly.

## Directory Structure

```
library/cursor/skills/<skill-name>/
├── SKILL.md           # Under 10KB — workflow, decisions, actions
├── references/        # Deep knowledge, loaded on demand (optional)
└── templates/         # User-fillable templates (optional)
```

Cursor accesses skills via symlink: `.cursor/skills/` → `library/cursor/skills/`.

Skills that reference harness state use `.harness/` paths (e.g., `.harness/breadcrumbs.jsonl`, `.harness/contract.json`).

For Claude Code distribution, mirror skills in `library/claude/skills/` with adapted paths.

## SKILL.md Structure

Adapted from alirezarezvani's 10 patterns and PaulRBerg's agent-skills.

### Required Sections

1. **Practitioner voice** — open with expertise and goal:
   ```
   You are an expert in X. Your goal is Y.
   ```

2. **Context-first** — check for existing context before asking questions:
   ```
   ## Before Starting
   Check for `project-context.md` or similar. Use existing context, only ask for gaps.
   ```

3. **Multi-mode** — at least 2 entry points:
   ```
   ## How This Skill Works
   ### Mode 1: Build from Scratch
   ### Mode 2: Optimize Existing
   ```

4. **Core workflow** — numbered steps, each with clear actions

5. **Proactive triggers** — 3-5 issues to surface without being asked:
   ```
   ## Proactive Triggers
   - **<condition>** → <what to flag and why>
   ```

6. **Output artifacts** — table mapping requests to deliverables:
   ```
   ## Output Artifacts
   | When you ask for... | You get... |
   ```

7. **Stop conditions** — when to pause and ask for direction:
   ```
   ## Stop Conditions
   - When behavior intent is ambiguous
   - When changes require breaking public APIs
   ```

## Tone

- Practitioner voice — opinionated, direct
- "Do X" not "You might consider X"
- Frame trade-offs explicitly: "Option A gives you X at the cost of Y"
- Write as someone who has done this 100 times

## Sizing

- SKILL.md: **under 300 lines** (~10KB)
- Heavy reference content goes in `references/`
- Templates go in `templates/`
- Each reference file should be self-contained and loadable independently

## Shared References

Skills can reference shared knowledge in `.cursor/references/`:
- `.cursor/references/patterns/` — architectural patterns (clean-architecture, ddd, etc.)
- `.cursor/references/design/` — design thinking methodologies

Reference with relative paths from the skill's perspective. Load only what's relevant to the current task.

## Anti-Patterns

- Missing or vague `description` (skill never loads)
- No workflow steps (just a list of facts — that's a rule, not a skill)
- Giant monolithic SKILL.md over 300 lines (split into references)
- Passive constraints disguised as skills (those are rules)
- Not defining stop conditions (agent doesn't know when to pause)
- Asking all questions upfront instead of conversationally

## Quality Checklist

Before a skill is considered done:

- [ ] Valid frontmatter with `name`, `description`, and `disable-model-invocation`
- [ ] `name` matches folder name exactly
- [ ] `description` includes trigger keywords/phrases a user would say
- [ ] Opens with practitioner voice and clear goal
- [ ] Has at least 2 modes or a clear multi-step workflow
- [ ] SKILL.md under 300 lines (references for heavy content)
- [ ] Proactive triggers defined (3-5)
- [ ] Stop conditions defined
- [ ] Output artifacts table present
- [ ] Context-first: checks for existing docs before asking questions
