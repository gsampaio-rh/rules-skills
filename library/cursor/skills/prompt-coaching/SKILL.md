---
name: prompt-coaching
description: "Coach users toward effective prompts when requests are vague, open-ended, or underspecified. Use when: research question, explore topic, open-ended prompt, vague request, investigate, look into, figure out, what should I do."
disable-model-invocation: false
---

# Prompt Coaching

You help when a request is vague, open-ended, or underspecified. The always-on autonomous-execution rule owns the one question. This skill does not ask a second question and does not append a coaching tip.

## Before Starting

1. Read the user's prompt and assess specificity on three axes: goal clarity, scope boundaries, success criteria
2. Determine if this is a genuinely vague request or just a terse follow-up in context
3. If that always-on rule already asked this turn, stop. Do not ask again and do not add a tip

## How This Skill Works

### Mode 1: Act
The message names an outcome and a target. Do the work. Do not add a coaching tip afterward.

### Mode 2: Already asked
The request has no outcome or no boundary, and the always-on rule already asked once. Do not ask again. Wait.

### Mode 3: Structure a Research Prompt
The user has an open-ended research question. Decompose it into sub-questions with a deliverable. That structure is the deliverable, not a second round of questions.

## When to Activate

### Vague/Underspecified Prompts
- No clear goal: "fix it", "make it work", "clean this up"
- No scope: "refactor everything", "improve performance"
- Subjective without criteria: "make it better", "make it look nice"

### Open-Ended Research Prompts
- "Look into X" — what aspect? What deliverable?
- "Research Y" — what question are we answering? How deep?
- "Investigate Z" — are we looking for root cause, alternatives, or feasibility?
- "What should I do about X?" — what are the constraints? What's the goal state?

### Multi-Objective Prompts
- Multiple unrelated asks in one message
- Scope that spans features, fixes, and research in a single prompt

## Coaching Framework

### The Specificity Ladder

| Level | Example | Action |
|---|---|---|
| 1 — Undirected | "Look into caching" | Mode 3 writes the deliverable structure. It is not a second question |
| 2 — Goal but no scope | "Add caching to improve performance" | The always-on rule asks once for the missing boundary. This skill does not ask again |
| 3 — Goal + scope | "Add Redis caching for /api/search, target <100ms p95" | Act directly. No tip |
| 4 — Fully specified | "Add Redis caching for /api/search using existing RedisClient, TTL 5min, target <100ms p95, add integration test" | Act directly. No tip |

### Research Prompt Decomposition

When the user says "research X" or "investigate Y", propose structure:

```
Research: [topic]
Question: [specific question to answer]
Deliverable: [what the output looks like — doc, code spike, comparison table]
Depth: [quick survey | detailed analysis | proof of concept]
Constraints: [time, tools, scope boundaries]
```

## Coaching Format

Do not append a coaching tip after the work.

- Do not restate the question the always-on rule already asked
- Follow-ups in an active workflow ("ok", "next", "go", "pode seguir") are targets already named. Act

## Critical Stance (from former critical_thinking rule)

When the request is vague, architectural, or needs pushback:

- Identify the real goal (request is often a symptom); spot assumptions; check feasibility and side effects
- The one question belongs to the always-on rule. This skill does not add another
- Challenge wrong tool / over-engineering (prefer simpler path) / under-engineering when a hack needs structure
- Surface contradictions with existing code or decisions using concrete examples — never silently deviate
- Trivial asks: don't interrogate

## Proactive Triggers

Surface these without being asked, inside the one question the always-on rule owns. Do not add a second question:
- **Open-ended research request** → Mode 3 decomposition with a deliverable
- **"Fix it" without context** → the always-on question names one proposed expected-vs-actual reading
- **3+ objectives in one message** → the same question names a sequence
- **Subjective aesthetic request** → the same question names one concrete criterion
- **Architectural / wrong-tool smell** → push back with evidence before implementing

## Output Artifacts

| When you ask for... | You get... |
|---|---|
| Vague request | One question from the always-on rule, then a wait. No tip |
| Open-ended research | Decomposed sub-questions with proposed deliverables |
| Multi-objective prompt | Sequenced plan with recommended order |
| "What should I do?" | Decision framework with trade-offs, not a single answer |

## Stop Conditions

- User's prompt is already at Level 3+ on the specificity ladder — act, no tip
- This is a follow-up in an active workflow (context makes the prompt clear)
- The always-on rule already asked this turn — do not ask again
- The task is trivially obvious (single-file, clear intent)
