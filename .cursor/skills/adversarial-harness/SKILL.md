---
name: adversarial-harness
description: >-
  Multi-agent harness with planner/builder/evaluator subagent roles, contract
  negotiation, adversarial verification, and structured traces. Use when: build
  feature, implement feature, harness workflow, adversarial testing, QA workflow,
  contract-first, multi-agent, complex implementation.
---

# Adversarial Harness Workflow

A tiny engineering team in your IDE: `/planner` sets direction → builder and `/evaluator` negotiate a contract → you build → computational sensors gate → `/evaluator` tests the live app → state persists via files → traces are reviewed.

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

| Role | Subagent | Mode | Purpose |
|------|----------|------|---------|
| Planner | `/planner` | Foreground | Turns vague prompts into high-level product specs |
| Builder | Main agent (you) | — | Implements features against the negotiated contract |
| Evaluator | `/evaluator` | Foreground | Adversarial QA — negotiates contracts AND tests the actual app |

Subagent definitions live in `.cursor/agents/`. Two hooks enforce the workflow:
- `subagentStop` → chains `/evaluator` after any subagent if a contract is unverified
- `stop` → blocks the main agent from finishing if a contract is unverified

---

## Phase 1: Planning

Launch the `/planner` subagent with the user's request.

```text
/planner [paste or describe the user's request with relevant context]
```

The planner explores the codebase and produces:
- `.cursor/harness/spec.md` — high-level product spec with user stories
- `.cursor/harness/progress.json` — feature list with statuses

The planner does NOT produce contracts. It stays at the product level.

Present the spec to the user. Get confirmation before proceeding.

---

## Phase 1.5: Contract Negotiation

Before writing a single line of code, the builder and evaluator negotiate what "done" means for the first feature. This bridges the gap between user stories (spec) and testable implementation (contract).

### How it works

1. **Builder proposes:** Read the spec for this feature. Propose a contract:
   - What you will build (proposed_solution)
   - How success will be verified (acceptance_criteria)
   - What edge cases to test
   - The verification method

2. **Evaluator reviews:** Launch `/evaluator` in negotiation mode:
   ```text
   /evaluator Review the proposed contract at .cursor/harness/contracts/current-contract.json — negotiation mode
   ```
   The evaluator pushes back on weak criteria, missing edge cases, or overly broad scope.

3. **Iterate:** The evaluator writes feedback to `.cursor/harness/contracts/negotiation.md`. The builder revises the contract. Max 3 rounds.

4. **Agreement:** When both agree, the contract is final. The evaluator marks it accepted.

### Contract format

Save to `.cursor/harness/contracts/current-contract.json`:

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
  "verified": false
}
```

### Why negotiate?

From the Anthropic talk: "The generator proposed what it would build and how success would be verified. The evaluator pushed back: 'scope too big, tests too weak, missed edge case.' They iterated via files until both agreed." This prevents the builder from writing vague criteria that it can easily pass.

---

## Phase 2: Building

You are the builder. Work against the negotiated contract, not the original vague prompt.

1. Read `.cursor/harness/contracts/current-contract.json` for acceptance criteria
2. Update `progress.json` → set the feature status to `"building"`
3. Implement the feature — one feature at a time
4. Run computational sensors before calling the evaluator:
   - Lints pass (`ReadLints` or project linter)
   - Type checks pass (if applicable)
   - Existing tests pass (if test suite exists)
   - Build succeeds (if build step exists)
5. Append progress to `.cursor/harness/progress.log`
6. Do NOT judge whether the feature works — that's the evaluator's job
7. Proceed to Phase 3

---

## Phase 3: Evaluation

Launch the `/evaluator` subagent. The `subagentStop` hook will also auto-trigger this if you forget.

```text
/evaluator Test the implementation against the contract at .cursor/harness/contracts/current-contract.json
```

The evaluator:
1. Reads the calibration guide at `.cursor/skills/adversarial-harness/references/evaluator-calibration.md`
2. Reads the contract
3. Verifies computational checks passed
4. Tests each acceptance criterion by running the actual app
5. Tests each edge case
6. Produces a report at `.cursor/harness/logs/eval-{feature_id}-{timestamp}.json`
7. Sets `verified: true` in the contract if all criteria pass

### After evaluation

| Result | Action |
|--------|--------|
| All criteria PASS | Proceed to Phase 4 |
| Some criteria FAIL with `fix_and_retest` | Fix the issues, re-run `/evaluator` (max 2 retries) |
| Recommendation: `scrap_and_restart` | Archive attempt, write post-mortem, re-plan with lessons |

### Scrap-and-Restart Protocol

When the evaluator recommends scrapping (3+ failures or no convergence after retries):

1. Evaluator writes post-mortem to `progress.log`
2. Builder archives current attempt: `mv` relevant files to `.cursor/harness/attempts/{feature_id}-{timestamp}/`
3. Builder reads the post-mortem and starts fresh — different approach, same contract (or renegotiate if the contract itself was the problem)

This is expected, not a failure. From the Anthropic talk: "It was extremely willing to throw away everything and start from scratch if it wasn't able to hill climb against the rubric."

---

## Phase 4: Checkpoint

After the evaluator passes:

1. Verify `current-contract.json` has `"verified": true`
2. Update `progress.json` → set feature status to `"verified"`
3. Append completion entry to `progress.log`
4. Archive the completed contract to `.cursor/harness/contracts/archive/`
5. Stage changes and ask user before committing
6. After commit, update status to `"committed"`
7. Pick next pending feature from `progress.json`
8. Start contract negotiation for next feature → go to Phase 1.5

---

## State Files

| File | Purpose | Who writes |
|------|---------|------------|
| `.cursor/harness/spec.md` | Product spec with user stories | Planner |
| `.cursor/harness/progress.json` | Feature list with statuses | Planner (init), Builder (updates) |
| `.cursor/harness/progress.log` | Append-only trace log | All agents |
| `.cursor/harness/contracts/current-contract.json` | Active negotiated contract | Builder (proposes), Evaluator (approves) |
| `.cursor/harness/contracts/negotiation.md` | Negotiation thread | Builder + Evaluator |
| `.cursor/harness/contracts/archive/` | Completed contracts | Builder |
| `.cursor/harness/logs/eval-*.json` | Evaluator reports with evidence | Evaluator |
| `.cursor/harness/attempts/` | Scrapped attempts (post-mortem) | Builder |
| `.cursor/harness/handoff.md` | Session resumption artifact | Builder (at session end) |

All state lives on the file system, not in context. Add `.cursor/harness/` to `.gitignore`.

---

## Handoff Artifacts for Multi-Session Work

For projects that span multiple sessions, write a handoff file before ending:

Save to `.cursor/harness/handoff.md`:

```markdown
# Handoff — [project name]

## Current State
- Feature being worked on: [id and name]
- Status: [building | evaluating | negotiating]
- Last action: [what you just did]

## What's Done
- [feat-1]: verified and committed
- [feat-2]: verified, pending commit

## What's Next
1. [Specific next step]
2. [Step after that]

## Blockers
- [Any issues that need human input]

## Key Decisions Made
- [Decision and reasoning — link to progress.log for details]
```

Future agents read `handoff.md` + `progress.log` + git log to resume without conversation memory. The file system is durable state; the context window is transient.

---

## Structured Trace Log

The `progress.log` is the project's memory. Every agent appends to it.

### Format

```markdown
## YYYY-MM-DDTHH:MM — [Role]: [summary]

- What was attempted: [description]
- Result: [PASS/FAIL/BLOCKED]
- Lessons learned: [what to do differently next time]
- Decisions made: [any choices with reasoning]
- Next step: [what should happen next]
```

### Why append-only

From the Anthropic harness: "The key insight was finding a way for agents to quickly understand the state of work when starting with a fresh context window." An append-only log gives any new agent a complete history without relying on conversation memory or compaction summaries.

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

- **Context resets**: Opus 4.6+ handles long contexts well. Use continuous sessions with compaction. Older models may need fresh context windows per feature.
- **Sprint decomposition**: Stronger models hold multi-hour builds coherently. Weaker models need explicit one-feature-at-a-time gating.
- **Evaluator frequency**: For strong models, evaluate at the end of a full build. For weaker models, evaluate after each feature.
- **Contract negotiation depth**: If the model consistently produces strong criteria on its own, reduce negotiation rounds.

The harness doesn't shrink as models improve — it moves. Strip what's no longer load-bearing, add new components for new capabilities.

---

## Invocation Examples

Full harness for a new feature:

```text
User: "Add dark mode support to the dashboard"

→ /planner Add dark mode support to the dashboard. The app uses React + Tailwind.
  Check the current theme setup in src/styles/ and component structure.

→ [planner produces spec.md and progress.json, user confirms]

→ [builder proposes contract for feat-1]

→ /evaluator Review the proposed contract — negotiation mode

→ [evaluator pushes back, builder revises, agreement reached]

→ [builder implements the feature, runs computational sensors]

→ /evaluator Test the dark mode implementation against the contract.
  Use browser tools to toggle theme, verify all components, check persistence.

→ [evaluator reports PASS/FAIL with evidence]
```

Parallel evaluators for different concerns:

```text
→ /evaluator Test functionality: all interactive elements work in dark mode
→ /evaluator Test accessibility: contrast ratios meet WCAG AA in dark mode
```
