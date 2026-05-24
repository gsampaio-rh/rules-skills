---
name: adversarial-harness
description: >-
  Multi-agent harness with planner/builder/evaluator subagent roles, contract
  negotiation, adversarial verification, and breadcrumbs tracing. Use when: build
  feature, implement feature, harness workflow, adversarial testing, QA workflow,
  contract-first, multi-agent, complex implementation.
---

# Adversarial Harness Workflow

A tiny engineering team in your IDE: `/planner` auto-decomposes complex prompts → builder and `/evaluator` negotiate a contract → you build → computational sensors gate → `/evaluator` tests the live app → breadcrumbs trace everything.

## Core Principles

1. **Self-evaluation is a trap.** Use an adversarial evaluator in a separate context. Tuning a standalone critic to be harsh is tractable; tuning a builder to be self-critical is not.
2. **File system is durable state.** The context window is transient. Write decisions, progress, and lessons to files.
3. **High-level planning, granular contracts.** The planner sets creative direction without implementation details. The builder and evaluator negotiate testable contracts. Don't over-specify up front — errors cascade.
4. **Contract negotiation bridges the gap.** Before writing code, builder and evaluator agree on what "done" means via files on disk. This turns user stories into testable assertions without the planner having to over-specify.
5. **Route, don't block.** The harness auto-routes complex prompts through the planner. It never blocks the user from interacting.
6. **Scrap and restart is expected.** If an approach isn't converging, discard it and start fresh with lessons from breadcrumbs.

## Harness Engineering Framework

This harness follows the guides/sensors taxonomy (Fowler, 2026):

| Type | Control | Purpose |
|------|---------|---------|
| **Guide** (feedforward) | Planner spec | Steers builder before it acts |
| **Guide** (feedforward) | Contract | Defines what "done" means |
| **Guide** (feedforward) | Rules files | Coding standards, security patterns |
| **Sensor** (feedback, computational) | Linter, type checker, test suite | Fast, deterministic quality gate |
| **Sensor** (feedback, inferential) | Evaluator agent | Adversarial testing of live app |

Computational sensors run first (cheap, fast). Inferential sensors run after (expensive, thorough). If computational sensors fail, don't waste evaluator tokens.

## Subagent Architecture

| Role | Subagent | Purpose |
|------|----------|---------|
| Planner | `/planner` | Turns vague prompts into high-level product specs |
| Builder | Main agent (you) | Implements features against the negotiated contract |
| Evaluator | `/evaluator` | Adversarial QA — negotiates contracts AND tests the actual app |

Subagent definitions live in `.cursor/agents/` (Cursor) or `.claude/agents/` (Claude Code). Hooks enforce the workflow:
- `sessionStart` → injects current harness state into conversation context
- `beforeSubmitPrompt` → detects non-trivial prompts and injects planner routing instructions (does NOT block)
- `subagentStop` → routes between negotiation, building, and evaluation based on `phase` field
- `stop` → blocks the main agent from finishing if a contract is unverified

---

## Phase 1: Planning

Launch the `/planner` subagent with the user's request.

```text
/planner [paste or describe the user's request with relevant context]
```

The planner explores the codebase and produces:
- `.cursor/harness/spec.md` — high-level product spec with user stories
- `.cursor/harness/state.json` — feature list with statuses

The planner does NOT produce contracts. It stays at the product level.

Present the spec to the user. Get confirmation before proceeding.

---

## Phase 1.5: Contract Negotiation

Before writing a single line of code, the builder and evaluator negotiate what "done" means for the first feature. This bridges the gap between user stories (spec) and testable implementation (contract).

### How it works

1. **Builder proposes:** Read the spec for this feature. Write a contract to `.cursor/harness/contract.json` with `"phase": "negotiating"`:
   - What you will build (proposed_solution)
   - How success will be verified (acceptance_criteria)
   - What edge cases to test
   - The verification method

2. **Evaluator reviews:** Launch `/evaluator` in negotiation mode:
   ```text
   /evaluator Review the proposed contract at .cursor/harness/contract.json — negotiation mode
   ```
   The evaluator pushes back on weak criteria, missing edge cases, or overly broad scope.

3. **Iterate:** Both sides log negotiation as breadcrumbs. The builder revises the contract. Max 3 rounds.

4. **Agreement:** When both agree, the contract is final. The evaluator marks it accepted and sets `"phase": "negotiated"`.

### Contract format

Save to `.cursor/harness/contract.json`:

```json
{
  "feature_id": "feat-1",
  "feature": "One-line description",
  "problem": "What problem does this solve?",
  "proposed_solution": "High-level approach",
  "acceptance_criteria": [
    "Each criterion is a binary, testable assertion"
  ],
  "edge_cases": [
    "At least 2 boundary conditions or error scenarios"
  ],
  "verification_method": "Exactly what the evaluator should run and check",
  "negotiation_rounds": 1,
  "phase": "negotiating",
  "verified": false
}
```

### Phase field

The `phase` field tracks where the harness is in the workflow. Hooks read it to route correctly.

| Phase | Set by | Means |
|-------|--------|-------|
| `negotiating` | Builder (on propose) | Contract is being negotiated |
| `negotiated` | Evaluator (on accept) | Negotiation complete, ready to build |
| `building` | Builder (when starting implementation) | Implementation in progress |
| `evaluating` | Builder (when launching evaluator for testing) | Evaluator is testing the live app |

### Why negotiate?

From the Anthropic talk: "The generator proposed what it would build and how success would be verified. The evaluator pushed back: 'scope too big, tests too weak, missed edge case.' They iterated via files until both agreed." This prevents the builder from writing vague criteria that it can easily pass.

---

## Phase 2: Building

You are the builder. Work against the negotiated contract, not the original vague prompt.

1. Read `.cursor/harness/contract.json` for acceptance criteria
2. Set `"phase": "building"` in `contract.json`
3. Update `state.json` → set the feature status to `"building"`
4. Implement the feature — one feature at a time
4. Run computational sensors before calling the evaluator:
   - Lints pass (`ReadLints` or project linter)
   - Type checks pass (if applicable)
   - Existing tests pass (if test suite exists)
   - Build succeeds (if build step exists)
5. Append a breadcrumb to `.cursor/breadcrumbs.jsonl`
6. Do NOT judge whether the feature works — that's the evaluator's job
7. Proceed to Phase 3

---

## Phase 3: Evaluation

Set `"phase": "evaluating"` in `contract.json`, then launch the `/evaluator` subagent. The `subagentStop` hook will also auto-trigger this if you forget.

```text
/evaluator Test the implementation against the contract at .cursor/harness/contract.json
```

The evaluator:
1. Reads the calibration guide at `.cursor/skills/adversarial-harness/references/evaluator-calibration.md`
2. Reads the contract
3. Verifies computational checks passed
4. Tests each acceptance criterion by running the actual app
5. Tests each edge case
6. Produces a report at `.cursor/harness/evals/eval-{feature_id}.json`
7. Sets `verified: true` in the contract if all criteria pass

### After evaluation

| Result | Action |
|--------|--------|
| All criteria PASS | Proceed to Phase 4 |
| Some criteria FAIL with `fix_and_retest` | Fix the issues, re-run `/evaluator` (max 2 retries) |
| Recommendation: `scrap_and_restart` | Log post-mortem as breadcrumb, start fresh with lessons |

### Scrap-and-Restart Protocol

When the evaluator recommends scrapping (3+ failures or no convergence after retries):

1. Evaluator logs post-mortem as a breadcrumb
2. Builder starts fresh — different approach, same contract (or renegotiate if the contract itself was the problem)

This is expected, not a failure. From the Anthropic talk: "It was extremely willing to throw away everything and start from scratch if it wasn't able to hill climb against the rubric."

---

## Phase 4: Checkpoint

After the evaluator passes:

1. Verify `contract.json` has `"verified": true`
2. Update `state.json` → set feature status to `"verified"`
3. Append completion breadcrumb
4. Stage changes and ask user before committing
5. After commit, update status to `"committed"`
6. Pick next pending feature from `state.json`
7. Start contract negotiation for next feature → go to Phase 1.5

---

## State Files

| File | Purpose | Who writes |
|------|---------|------------|
| `.cursor/harness/spec.md` | Product spec with user stories | Planner |
| `.cursor/harness/state.json` | Feature list with statuses | Planner (init), Builder (updates) |
| `.cursor/harness/contract.json` | Active negotiated contract | Builder (proposes), Evaluator (approves) |
| `.cursor/harness/evals/eval-{id}.json` | Evaluator reports with evidence | Evaluator |
| `.cursor/breadcrumbs.jsonl` | Append-only trace — the project's memory | All agents |

All state lives on the file system, not in context. Add `.cursor/harness/` and `.cursor/breadcrumbs.jsonl` to `.gitignore`.

---

## Breadcrumbs

The single append-only trace log. Every agent appends one JSONL line per significant action.

### Format

Each line in `.cursor/breadcrumbs.jsonl` is one JSON object:

```jsonl
{"ts":"2026-05-23T09:49","role":"planner","type":"plan","feat":"feat-1","msg":"Created spec with 5 features"}
{"ts":"2026-05-23T09:52","role":"builder","type":"negotiate","feat":"feat-1","msg":"Proposed contract: 4 criteria, 2 edge cases"}
{"ts":"2026-05-23T09:54","role":"evaluator","type":"negotiate","feat":"feat-1","msg":"Pushed back: scope too broad, missing expired token edge case"}
{"ts":"2026-05-23T10:05","role":"builder","type":"build","feat":"feat-1","msg":"Implemented JWT validation middleware"}
{"ts":"2026-05-23T10:07","role":"builder","type":"verify","feat":"feat-1","msg":"Computational checks pass: lint, types, tests"}
{"ts":"2026-05-23T10:15","role":"evaluator","type":"eval","feat":"feat-1","msg":"PASS 6/6 criteria","result":"pass"}
{"ts":"2026-05-23T10:16","role":"builder","type":"checkpoint","feat":"feat-1","msg":"Committed and archived"}
```

### Fields

| Field | Required | Values |
|-------|----------|--------|
| `ts` | yes | ISO-8601 timestamp |
| `role` | yes | `planner`, `builder`, `evaluator` |
| `type` | yes | `plan`, `negotiate`, `build`, `verify`, `eval`, `checkpoint`, `decision`, `scrap` |
| `feat` | no | Feature ID (e.g., `feat-1`) or `null` for non-harness work |
| `msg` | yes | One-line summary of what happened |
| `result` | no | `pass`, `fail`, `blocked` (only for `verify` and `eval` types) |

### Why breadcrumbs

From the Anthropic harness: "You're basically just leaving breadcrumbs for another model to come and pick up. Tried this, evaluated, found this bug, implemented this fix, this fix worked, yes, tick."

- **Append-only** — never edit past entries
- **JSONL** — models are less likely to overwrite JSON; machine-parseable for hooks
- **Greppable** — `rg '"type":"eval"'` to see all evaluations
- **Replaces** negotiation threads, archive, attempts, handoff, and progress logs in ONE file
- **Session resume** — read last N lines to understand current state

For non-harness work (general progress tracking), use `feat: null`:

```jsonl
{"ts":"2026-05-23T11:00","role":"builder","type":"build","feat":null,"msg":"Updated sync-cursor.sh to split global vs per-project"}
```

---

## Evaluator Rubrics

Tune per domain. Vague criteria produce vague critiques. Granular criteria produce actionable fixes.

### Web App

| Criterion | Weight | How to Test |
|-----------|--------|-------------|
| Functionality | 40% | All interactive elements work per contract |
| Error handling | 20% | Console clean, graceful degradation |
| Responsiveness | 15% | Mobile, tablet, desktop breakpoints |
| Accessibility | 15% | Keyboard nav, ARIA, contrast |
| Performance | 10% | No layout shifts, fast load |

### API / Backend

| Criterion | Weight | How to Test |
|-----------|--------|-------------|
| Correctness | 40% | Endpoints return expected responses |
| Error handling | 25% | Invalid inputs → proper error codes |
| Edge cases | 20% | Boundary values, empty, concurrent |
| Security | 15% | Auth enforced, input validated |

### Data / ML

| Criterion | Weight | How to Test |
|-----------|--------|-------------|
| Correctness | 35% | Output matches expected distributions |
| Reproducibility | 25% | Fixed seed → same results |
| Edge cases | 20% | Empty, NaN, extreme, single-row |
| Performance | 20% | Within time/memory budget |

---

## Model-Adaptive Tuning

Every harness component encodes an assumption about what the model can't do on its own. As models improve, re-examine assumptions:

| Component | Weaker Models | Stronger Models (Opus 4.6+) |
|---|---|---|
| Context resets | Fresh context per feature | Single continuous session + compaction |
| Sprint decomposition | One feature at a time, strictly gated | Can hold multi-hour builds coherently |
| Evaluator frequency | Run after each feature | Run at end of full build |
| Contract negotiation depth | Full 3-round negotiation | Reduce rounds if criteria are strong |
| Planner granularity | Detailed sprint breakdown | High-level creative direction is enough |

The harness doesn't shrink as models improve — it moves. Strip what's no longer load-bearing, add new components for new capabilities.

### Tuning Guidelines

- **Read traces, then tune.** The primary debugging loop is reading what the agent actually did, finding where its judgment diverged from yours, and tuning the prompt for that. Not running more experiments.
- **Evaluator harshness is tractable.** Tuning a standalone critic to be harsh is easy. Tuning a builder to be self-critical is not. Exploit this asymmetry.
- **Pivot over patch.** If the builder gets stuck on a criterion after multiple attempts, the harness should scrap and restart rather than keep patching the same approach.
- **JSON over markdown for state.** Models are less likely to overwrite JSON files than markdown. Use JSON for `state.json`, `contract.json`, `breadcrumbs.jsonl`.
- **Don't share context between builder and evaluator.** The evaluator judges output only. Sharing builder traces muddies the separation and lets the model kid itself.

---

## Automatic Routing

The `beforeSubmitPrompt` hook detects non-trivial prompts and injects routing instructions. The agent should launch `/planner` automatically — the user should never have to invoke it manually.

If the hook doesn't fire (e.g., the heuristics miss a complex prompt), the agent should still recognize non-trivial work from the always-applied rule and route through the planner.

---

## Invocation Examples

Full harness for a new feature (auto-routed):

```text
User: "Add dark mode support to the dashboard"

→ [agent detects non-trivial work, auto-launches /planner]
→ /planner Add dark mode support to the dashboard. The app uses React + Tailwind.
  Check the current theme setup in src/styles/ and component structure.

→ [planner produces spec.md and state.json]
→ [agent presents spec to user, user confirms]

→ [builder proposes contract for feat-1 with 5+ binary criteria]
→ /evaluator Review the proposed contract — negotiation mode
→ [evaluator pushes back: "scope too big, tests too weak, missed edge case"]
→ [builder revises, agreement reached]

→ [builder implements the feature, runs computational sensors]
→ /evaluator Test the dark mode implementation against the contract.
  Use browser tools to toggle theme, verify all components, check persistence.

→ [evaluator reports PASS/FAIL with evidence]
→ [PASS → commit checkpoint → next feature]
```

Simple work (no harness):

```text
User: "Fix the broken import in auth.py"

→ [agent detects simple fix, implements directly]
→ [no planner, no contract, no evaluator]
```
