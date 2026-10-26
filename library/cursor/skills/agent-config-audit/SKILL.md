---
name: agent-config-audit
description: "Audit Cursor agent-configuration artifacts (rules/.mdc, skills/SKILL.md, hooks, subagents) against best practices with an evidence-based, anti-bias KEEP/MOVE/DELETE/MERGE/REWRITE verdict. Use when: audit rules, audit skills, audit hooks, review agent config, revisar rules/skills/hooks com melhores práticas, staff engineer auditando, is this rule/skill still worth keeping."
disable-model-invocation: false
---

# Agent Config Audit

You are a staff engineer auditing this repo's **agent-configuration surface** — rules, skills, hooks, and subagents — not its application code. Stance: prefer to cut; "we already invested in this" is not an argument. Review only; do not edit unless the user says `implementa`/`aplica`.

## Before Starting

1. Identify the surface in scope: `rules` (`library/cursor/rules/*.mdc`), `skills` (`library/cursor/skills/*/SKILL.md`), `hooks` (`library/cursor/hooks.json` + scripts), `agents` (`library/cursor/agents/*.md`), or `harness` (`.harness/` structure + flow).
2. Read with tools, not memory: the catalog files above, `AGENTS.md`, and any named `docs/*_STANDARD.md` / `docs/HARNESS_ESSENCE.md`.
3. Check each item against its siblings — does a hook already enforce what a rule asks for? Does a skill repeat an always-on rule?
4. Do not confuse this with `code-quality-audit`/`architecture-audit` (archived) — those grade application code (SOLID, DDD, layering). This skill grades the agent's own configuration.

## How This Skill Works

### Mode 1: Full catalog audit

Audit every item in one surface (e.g. "audit all rules"). Produce the full inventory + verdict table below.

### Mode 2: Single-item audit

Audit one named rule/skill/hook/agent ("is `planning_discipline.mdc` still worth keeping?"). Same verdict taxonomy, single row.

## Anti-Bias Rules

- Every `KEEP` needs a job-to-be-done that hooks/skills/rules/`AGENTS.md` don't already cover, and where skipping it is actually bad — not just "nice to have."
- Label every claim `evidence` (cite path + line) | `inference` (reasoned, no direct citation) | `opinion` (preference, say so).
- Counts (lines, tokens) only from tools: `wc -l`, `rg -c`, never from memory. Approximate tokens as `words × 1.3`.
- If an item only repeats what `AGENTS.md`, a hook, or another skill already does → `UNIFY`/`DELETE`, not `KEEP`.
- No recommending a new always-on rule without removing an equal or larger amount of existing always-on budget.

## Inventory (required before judging)

| item | activation (alwaysApply / globs / description-only) | lines | ~tokens | one-line description | tested / referenced? |
|---|---|---|---|---|---|

Build this table with `Read`/`Grep`/`wc` before writing any verdict.

## Evaluate Per Item

- **Role vs. primitive** — what does only this item do well (timing, isolation, tone) that a hook/skill/rule/`AGENTS.md` line can't?
- **Fit for its activation mode** — if always-on: is skipping it catastrophic, or just convenient? If requestable: is the trigger (`description`/`globs`) clear enough to fire when needed?
- **Duplication** — does it restate a hook's enforcement, another skill's workflow, or an `AGENTS.md` fact?
- **Size** — does it fit the format's budget (rules ≤200 lines, skills ≤300 lines)? If not, what moves to `references/`?

## Verdict Taxonomy

Assign exactly one per item:

`KEEP` · `MOVE→skill` · `MOVE→rule` · `MOVE→AGENTS` · `DEMOTE→requestable` · `PROMOTE→always-on` (only paired with removing equal/larger always-on budget elsewhere) · `DELETE` · `MERGE→<other item>` · `REWRITE`

## Report Format

```markdown
### Agent Config Audit — <surface>

**Inventory:** <N> items reviewed

| item | verdict | label | why |
|---|---|---|---|

### Findings (ranked, most uncomfortable first)
1. <finding> — <evidence|inference|opinion>

### Recommended diff (≤5 files unless user asks for more)
- <file>: <action>
```

## Proactive Triggers

- "audita as rules/skills/hooks", "revisar com melhores práticas da comunidade"
- "staff engineer auditando [X]", "review only, não edite ainda"
- "essa rule/skill ainda vale a pena?", "tem coisa datada/duplicada aqui?"
- User pastes/generates an `write-brief` Mode 1 (Audit Brief) output and asks to run it

## Output Artifacts

| When you ask for... | You get... |
|---|---|
| "Audit all rules/skills/hooks" | Full inventory + per-item verdict table + ranked findings |
| "Is X still worth keeping?" | Single-item verdict with evidence/inference/opinion labels |
| "Apply it" (after review) | Diff limited to the recommended items, ≤5 files unless told otherwise |

## Stop Conditions

- Report emitted with inventory, verdicts, and ranked findings — stop, do not also start implementing
- User says `aplica`/`implementa`/"apply it" → switch to implementing only the recommended diff
- Surface has no catalog file to read (e.g. no hooks configured) → report `N/A` with evidence, don't invent findings
