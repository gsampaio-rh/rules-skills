---
name: write-brief
description: "Turn a one-line ask into a reusable, copy-pasteable prompt instead of doing the work now. Use when: me dá um prompt, quero um prompt para, write me a prompt to, draft a prompt for, give me a prompt to investigate/audit/review, preciso de um prompt."
disable-model-invocation: false
---

# Write Brief

You are a prompt engineer. The user is not asking you to do the work — they're asking you to produce the **prompt text** they (or a future session) will run to do the work. Your deliverable is a markdown block, not an analysis.

## Before Starting

1. Confirm this is a "give me a prompt" ask, not a "do the thing" ask. Signal: the verb is `dá`/`quero`/`write`/`draft`/`give me` + `prompt`, not the task verb itself.
2. Classify the target:
   - **Audits an existing artifact** (rule, skill, hook, agent, repo structure) against best practices → Mode 1 (Audit Brief).
   - **Investigates/compares/scopes something not yet decided** (feasibility, external research, RCA, "qual abordagem") → Mode 2 (Research Brief).
3. If genuinely ambiguous, default to Mode 2 — it's the broader template.

## How This Skill Works

### Mode 1: Audit Brief

Use for: "quero um prompt pra revisar X com melhores práticas", "me dá um prompt pra auditar Y".

```markdown
# Audit: [surface] ([repo/project])

You are a staff engineer auditing [surface] in this repo.
Stance: prefer to cut; "we already invested in this" is not an argument.
Review only — do not edit yet.

## Context (read with tools, not memory)
1. [catalog path, e.g. library/cursor/rules/*.mdc]
2. [related docs, e.g. AGENTS.md, docs/*_STANDARD.md]
3. [sibling surface to check for duplication, e.g. hooks.json, other skills]

## Anti-bias
- Every KEEP needs a job-to-be-done that hooks/skills/rules/AGENTS.md don't
  already cover, and where skipping it is actually bad.
- Label every claim: `evidence` | `inference` | `opinion`.
- Counts only via `wc`/`rg` — never from memory.
- If an item only repeats AGENTS.md / a hook / another skill → UNIFY or
  DELETE, not KEEP.

## Inventory (required, before judging)
| item | trigger (alwaysApply/globs/desc) | lines | ~tokens | one-line description | tested/referenced? |

## Verdict per item
`KEEP` | `MOVE→skill` | `MOVE→rule` | `MOVE→AGENTS` | `DEMOTE→requestable` |
`PROMOTE→always-on` (only with an equal/larger trade elsewhere) | `DELETE` |
`MERGE→<other>` | `REWRITE`

## Constraints
- [scope: what not to touch, e.g. "don't evaluate the Devin port"]
- [budget/limits if relevant, e.g. always-on token budget]
```

Fill every bracket from what the user told you; don't leave placeholders in the output.

### Mode 2: Research Brief

Use for: "quero um prompt pra investigar/pesquisar/comparar X", "me dá um prompt pra gente decidir Y".

```markdown
Research: [topic]

Question: [the one specific question this must answer]

Context:
- [what's already known / already decided]
- [constraint or preference that shapes the answer, e.g. "prefer deterministic over LLM"]

Deliverable: [exact output shape — decision memo, comparison table, spike, report]

Depth: [quick survey | detailed analysis | proof of concept]

Constraints: [scope boundaries, non-goals, tools/budget limits]

Sources: [where to look — repo paths, specific docs/URLs, "official docs only"]
```

Drop any field the user didn't give you enough signal for rather than inventing content — a short, honest brief beats a padded one.

## Relationship to Sibling Skills

| Skill | When it fires | What it gives you |
|---|---|---|
| `prompt-coaching` | Your own request is vague ("look into X") | Decomposes it so *you* can act now |
| `write-brief` (this) | You explicitly ask for a prompt, vague or not | A prompt artifact to paste later or hand to a subagent |
| `agent-config-audit` | You ask to *run* an audit now | Executes the Mode 1 template directly instead of just writing it |

## Proactive Triggers

- "me dá um prompt pra..." / "eu quero um prompt para..." / "quero um prompt pra gente..."
- "write me a prompt to..." / "draft a prompt for..." / "give me a prompt to investigate/audit/review..."
- User names a topic and a future action ("pra gente implementar depois", "pra rodar numa sessão nova") instead of asking for the action now

## Output Artifacts

| When you ask for... | You get... |
|---|---|
| A prompt to audit/review a rule, skill, hook, or agent | Filled Audit Brief (Mode 1) |
| A prompt to investigate, compare, or scope something undecided | Filled Research Brief (Mode 2) |
| "I'm not sure which" | Research Brief by default, with a one-line note on why |

## Stop Conditions

- The brief is produced as a single copy-pasteable block — stop there, do not also start executing it
- User says "roda isso" / "go" / "pode executar" → switch out of this skill and do the work (or hand off to `agent-config-audit` for Mode 1 content)
- The ask is already a complete, ready-to-run prompt (not a request for one) → nothing to do, proceed with the task itself
