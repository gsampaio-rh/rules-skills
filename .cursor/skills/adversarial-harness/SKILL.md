---
name: adversarial-harness
description: >-
  Multi-agent harness with planner/builder/evaluator subagent roles, contract-first
  development, and adversarial verification. Use when: build feature, implement
  feature, harness workflow, adversarial testing, QA workflow, contract-first,
  multi-agent, complex implementation.
---

# Adversarial Harness Workflow

A tiny engineering team in your IDE: `/planner` defines direction → you build → `/evaluator` tests against a contract → state is persisted → traces are reviewed.

## Subagent Architecture

| Role | Subagent | Mode | Purpose |
|------|----------|------|---------|
| Planner | `/planner` | Foreground | Turns vague prompts into testable contracts |
| Builder | Main agent (you) | — | Implements features against the contract |
| Evaluator | `/evaluator` | Foreground | Adversarial QA — tests the actual app, not the diff |

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
- `.cursor/harness/progress.json` — feature list with statuses
- `.cursor/harness/current-contract.json` — contract for the first feature

Present the contract to the user. Get confirmation before building.

---

## Phase 2: Building

You are the builder. Work against the contract, not the original vague prompt.

1. Read `.cursor/harness/current-contract.json` for acceptance criteria
2. Update `progress.json` → set the feature status to `"building"`
3. Implement the feature — one feature at a time
4. Run basic checks: lints, type checks, import checks
5. Do NOT judge whether the feature works — that's the evaluator's job
6. Proceed to Phase 3

---

## Phase 3: Evaluation

Launch the `/evaluator` subagent. The `subagentStop` hook will also auto-trigger this if you forget.

```text
/evaluator Test the implementation against the contract at .cursor/harness/current-contract.json
```

The evaluator:
- Reads the contract
- Tests each acceptance criterion by running the actual app
- Tests each edge case
- Produces a report at `.cursor/harness/logs/eval-{feature_id}-{timestamp}.json`
- Sets `verified: true` in the contract if all criteria pass

### After evaluation

| Result | Action |
|--------|--------|
| All criteria PASS | Proceed to Phase 4 |
| Some criteria FAIL with `fix_and_retest` | Fix the issues, re-run `/evaluator` (max 2 retries) |
| Recommendation: `scrap_and_restart` | Inform user, re-run `/planner` with lessons learned |

---

## Phase 4: Checkpoint

After the evaluator passes:

1. Verify `current-contract.json` has `"verified": true`
2. Update `progress.json` → set feature status to `"verified"`
3. Stage changes and ask user before committing
4. After commit, update status to `"committed"`
5. Pick next pending feature from `progress.json`
6. Create new `current-contract.json` for next feature → go to Phase 2

---

## State Files

| File | Purpose |
|------|---------|
| `.cursor/harness/progress.json` | Feature list with statuses |
| `.cursor/harness/current-contract.json` | Active contract (single source of truth) |
| `.cursor/harness/logs/eval-*.json` | Evaluator reports with evidence |
| `.cursor/harness/breadcrumbs.json` | Decisions and lessons for long-lived projects |

All JSON. Add `.cursor/harness/` to `.gitignore` (already covered by `.cursor/`).

---

## Evaluator Rubrics

Tune per domain. Vague criteria → vague critiques. Granular criteria → actionable fixes.

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

## Breadcrumbs for Long Projects

For projects spanning multiple sessions:

```json
// .cursor/harness/breadcrumbs.json
{
  "decisions": [
    { "date": "2026-05-22", "decision": "WebSocket over polling", "reason": "Lower latency" }
  ],
  "issues_found": [
    { "date": "2026-05-22", "issue": "Canvas lag at 256 colors", "fix": "requestAnimationFrame batching", "result": "PASS" }
  ]
}
```

Future agents read these to resume without relying on conversation memory.

---

## Invocation Examples

Full harness for a new feature:

```text
User: "Add dark mode support to the dashboard"

→ /planner Add dark mode support to the dashboard. The app uses React + Tailwind. Check the current theme setup in src/styles/ and component structure in src/components/.

→ [planner produces contract, user confirms]

→ [you build the feature]

→ /evaluator Test the dark mode implementation against .cursor/harness/current-contract.json. Use browser tools to toggle the theme, verify all components respond, check for flash of unstyled content, test persistence across page reloads.

→ [evaluator reports PASS/FAIL with evidence]
```

Parallel evaluators for different concerns:

```text
→ /evaluator Test functionality: all interactive elements work in dark mode
→ /evaluator Test accessibility: contrast ratios meet WCAG AA in dark mode
```
