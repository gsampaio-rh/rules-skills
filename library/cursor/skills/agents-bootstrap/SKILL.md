---
name: agents-bootstrap
description: >-
  Bootstrap or adapt root AGENTS.md with real project commands. Use when:
  bootstrap agents.md, fill AGENTS.md commands, adapt agents template, init
  agents.md without dump, seed project memory file.
disable-model-invocation: true
---

# Agents Bootstrap

You help maintain a short, portable `AGENTS.md` (project memory for coding agents).
Your goal is to fill **real commands** and keep constraints accurate — never a codebase overview dump.

## Before Starting

1. Prefer ambient context: coding agents already load root `AGENTS.md` at session start — do not re-Read it unless it is missing from context or you just adopted/rewrote it.
2. If root `AGENTS.md` is missing on disk, run `scripts/adopt-agents-md.sh . library/cursor` (or consumer equivalent) — do not invent the file by hand. After adopt, the new file is in context for the rest of the turn.
3. Read `Makefile` / `package.json` only as needed for Commands discovery (the fill script does this too).
4. Confirm the user wants adaptation (this skill is opt-in: `/agents-bootstrap`).

## How This Skill Works

### Mode 1: Fill Commands

1. Ensure `AGENTS.md` exists (adopt if needed).
2. Run `scripts/agents-bootstrap-fill.sh <project-root>` to replace the `## Commands` bash fence from Makefile `.PHONY` targets or `package.json` scripts.
3. Skim `## Security considerations` / `## See also` — edit only non-discoverable constraints; do not add Directory structure, Tech stack, or Overview sections.
4. Keep the file ≤80 lines.

### Mode 2: Refresh Existing AGENTS.md

1. Diff current Commands against Makefile/`package.json`.
2. Re-run `scripts/agents-bootstrap-fill.sh` (idempotent).
3. Remove stale aspirational prose; keep security constraints that agents still trip on.

## Proactive Triggers

- Root `AGENTS.md` still has template placeholders (`Replace with this project`) after adopt → offer fill.
- User asks to `/init` or dump a full repo map into AGENTS.md → refuse; use this skill's Commands fill instead.
- Commands section lists tools the repo does not have → refresh from Makefile/`package.json`.

## Output Artifacts

| When you ask for... | You get... |
|---|---|
| Bootstrap / fill AGENTS.md | Updated root `AGENTS.md` Commands via `scripts/agents-bootstrap-fill.sh` |
| Refresh after Makefile change | Re-run fill; no duplicate command lines |
| `/init`-style overview | Refusal + pointer to Commands/constraints-only approach |

## Stop Conditions

- User wants a full architecture dump or essay sections (tree maps, stack tours) in AGENTS.md — stop; not this file's job.
- No Makefile and no package.json scripts — stop and ask how commands should be discovered.
- Existing AGENTS.md is intentionally custom and user declines overwrite of Commands — stop.

## Anti-patterns (do not)

- Do not run `/init`-style scans that add banned overview sections (tree maps, stack tours, dump essays) into AGENTS.md.
- Do not silently create `AGENTS.md` inside the fill script — adopt first.
- Do not duplicate README content.
