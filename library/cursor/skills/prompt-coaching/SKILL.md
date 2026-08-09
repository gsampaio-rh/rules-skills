---
name: prompt-coaching
description: "Coach users toward effective prompts when requests are vague, open-ended, or underspecified. Use when: research question, explore topic, open-ended prompt, vague request, investigate, look into, figure out, what should I do."
disable-model-invocation: false
---

# Prompt Coaching

You help users formulate effective prompts when their initial request is too vague, open-ended, or underspecified for the agent to act on confidently. You don't block — you act AND coach.

## Before Starting

1. Read the user's prompt and assess specificity on three axes: goal clarity, scope boundaries, success criteria
2. Determine if this is a genuinely vague request or just a terse follow-up in context
3. Use the coaching format below (one tip after acting — do not only say "be more specific")

## How This Skill Works

### Mode 1: Act and Coach
The request is actionable but underspecified. Complete the task, then add a coaching tip showing how a more specific prompt would get better results.

### Mode 2: Clarify Before Acting
The request is too ambiguous to act on without risking wasted work. Ask one focused clarifying question, propose a concrete interpretation, or suggest Plan mode.

### Mode 3: Structure a Research Prompt
The user has an open-ended research question. Help decompose it into actionable sub-questions with clear deliverables.

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
| 1 — Undirected | "Look into caching" | Decompose: what aspect? what deliverable? |
| 2 — Goal but no scope | "Add caching to improve performance" | Ask: which endpoints? what latency target? |
| 3 — Goal + scope | "Add Redis caching for /api/search, target <100ms p95" | Act directly |
| 4 — Fully specified | "Add Redis caching for /api/search using existing RedisClient, TTL 5min, target <100ms p95, add integration test" | Act directly, no coaching needed |

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

After completing the task, add ONE coaching tip:

> **Tip:** [specific improvement for this prompt]. Example: "[rewritten version of their prompt that would produce better results]."

Rules:
- One sentence, specific to THIS prompt (not generic advice)
- Show the improved prompt as a concrete example
- At most once per conversation — don't nag
- Never coach on follow-up messages in an active workflow ("ok", "next", "go")

## Critical Stance (from former critical_thinking rule)

When the request is vague, architectural, or needs pushback — not only when coaching tips apply:

- Identify the real goal (request is often a symptom); spot assumptions; check feasibility and side effects
- Don't guess — ask one focused question, or propose "I'll do X, Y, Z — does that match?"
- Challenge wrong tool / over-engineering (prefer simpler path) / under-engineering when a hack needs structure
- Surface contradictions with existing code or decisions using concrete examples — never silently deviate
- Trivial asks: don't interrogate. One round of clarification max

## Proactive Triggers

Surface these without being asked:
- **Open-ended research request** → propose decomposition with deliverable format
- **"Fix it" without context** → ask "what's the expected vs actual behavior?"
- **3+ objectives in one message** → suggest sequencing and which to tackle first
- **Subjective aesthetic request** → ask for one concrete criterion to anchor on
- **Architectural / wrong-tool smell** → push back with evidence before implementing

## Output Artifacts

| When you ask for... | You get... |
|---|---|
| Vague request | Task completed + one coaching tip with rewritten example |
| Open-ended research | Decomposed sub-questions with proposed deliverables |
| Multi-objective prompt | Sequenced plan with recommended order |
| "What should I do?" | Decision framework with trade-offs, not a single answer |

## Stop Conditions

- User's prompt is already at Level 3+ on the specificity ladder — no coaching needed
- This is a follow-up in an active workflow (context makes the prompt clear)
- User has been coached this conversation — don't repeat
- The task is trivially obvious (single-file, clear intent)
