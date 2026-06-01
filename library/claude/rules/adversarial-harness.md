# Adversarial Verification Harness

## When to Use

| Complexity | Approach |
|---|---|
| Simple (1-2 files, no architectural impact) | Just do it. No ceremony. |
| Non-trivial (3+ files, user-facing, architectural) | This harness. |

## You Are the Orchestrator

You coordinate three roles via subagents. You do NOT self-evaluate.

1. **`/planner`** — Turns the user's request into a structured `state.json` (vision, direction, tasks). Does NOT produce contracts.
2. **You (builder)** — Proposes contracts to the evaluator, negotiates until agreement, then implements one task at a time. Runs computational sensors before calling the evaluator.
3. **`/evaluator`** — Two modes: (a) negotiation — challenges weak contracts before building, (b) evaluation — adversarial QA that tests the live app against the contract with evidence.

## The Flow

```
User prompt
  → /planner → state.json
  → User confirms plan
  → You propose contract for first task
  → /evaluator negotiates contract (max 3 rounds)
  → Agreement reached → you build
  → Computational sensors (lints, types, tests, build)
  → /evaluator tests live app against contract
      → PASS → commit checkpoint → next task
      → FAIL → you fix → /evaluator re-tests (max 2x)
      → scrap_and_restart → start fresh with lessons
```

## Enforcement

Four hooks back this up:
- **`SessionStart`** — Injects current harness state (active feature, phase, recent breadcrumbs) into conversation context at the start of every session.
- **`Stop`** — Blocks completion if a contract exists with `verified: false`.
- **`SubagentStop`** — Routes based on the contract's `phase` field: after negotiation → build, after building → launch evaluator, after evaluation → re-launch if unverified.
- **CLAUDE.md harness gate** — Instructs the agent to use `/planner` for non-trivial work. User can say "skip harness" to opt out.

## State Files

All state lives on the file system, not in context:

| File | Purpose |
|---|---|
| `.claude/harness/state.json` | Single source of truth — vision, direction, trade-offs, task list with statuses |
| `.claude/harness/contract.json` | Active negotiated contract |
| `.claude/harness/evals/eval-{id}.json` | Evaluator reports with evidence |
| `.claude/breadcrumbs.jsonl` | Append-only trace — the project's memory |

## Lifecycle

- **Starting new work?** Check if `.claude/harness/state.json` exists. If yes, pick the next pending task. If no, launch `/planner`.
- **Resuming a session?** Read `breadcrumbs.jsonl` + git log to understand state.
- **Task verified?** Update `state.json`, commit, pick next task.
- **All tasks done?** Clean up harness state if desired.
- **Made a significant decision?** Log it as a breadcrumb. No separate ADR needed.

## Key Rules

- One task at a time. Negotiate → build → gate → verify → commit → next.
- Commit only after `/evaluator` passes.
- The evaluator never modifies source code. It tests and reports.
- If the evaluator recommends `scrap_and_restart`, start fresh with lessons from breadcrumbs.
- "Looks correct" is not verification. Running it is.

## Durable State Principle

The file system is durable state. The context window is transient.

- Write decisions, progress, and lessons to `breadcrumbs.jsonl` — not just conversation
- Agents starting fresh sessions read files, not conversation history
- Git commits are checkpoints — descriptive messages serve as the historical record
- `breadcrumbs.jsonl` is append-only — never edit past entries, only add new ones

## Deprecated Documents

These are replaced by harness artifacts:

| Was | Replaced by |
|---|---|
| `docs/PLAN.md` | `state.json` (vision + direction + tasks) |
| `docs/PRD.md` | `state.json` (vision + direction) |
| `docs/CHANGELOG.md` | `breadcrumbs.jsonl` (append-only trace) |
| `docs/adrs/*.md` | `breadcrumbs.jsonl` (decisions inline) |
| `docs/FUTURE_EXPLORATIONS.md` | `state.json` open_questions field |
| `.claude/harness/spec.md` | `state.json` (consolidated — spec.md is eliminated) |

If a project already has these files, they can coexist. Don't delete them. But new work flows through the harness.
