---
name: adversarial-harness
description: >-
  Multi-agent harness with planner/builder/evaluator subagent roles, contract
  negotiation, adversarial verification, and breadcrumbs tracing. Use when: build
  task, implement feature, harness workflow, adversarial testing, QA workflow,
  contract-first, multi-agent, complex implementation.
disable-model-invocation: false
---

# Adversarial Harness Workflow

A tiny engineering team in your IDE: `/planner` sets direction → builder and `/evaluator` negotiate a contract → you build → computational sensors gate → `/evaluator` tests the live app → breadcrumbs trace everything.

## How This Skill Works

### Mode 1: Full Harness
Multi-task workflow with planner, contract negotiation, build, and adversarial evaluation. Use for non-trivial work touching 3+ files.

### Mode 2: Resume Cycle
`.harness/state.json` has pending tasks or an unverified contract — continue negotiate → build → `/evaluator` without re-planning from scratch.

Optional rubric pass (contract `rubrics` or user ask): `references/rubrics-and-tuning.md`. Audit skills are archived; no separate standalone-audit skill mode.

## Proactive Triggers

- Non-trivial request touching 3+ files or requiring architectural decisions
- User says "build feature", "implement", "harness", "adversarial", "multi-agent"
- `.harness/state.json` exists with pending tasks — resume the workflow
- Contract exists but is unverified — continue the build/evaluate cycle

## Subagent Architecture

| Role | Subagent | Purpose |
|------|----------|---------|
| Planner | `/planner` | Turns vague prompts into high-level product specs |
| Builder | Main agent (you) | Implements tasks against the negotiated contract |
| Evaluator | `/evaluator` | Adversarial QA — negotiates contracts AND tests the actual app |

Subagent definitions live in `.cursor/agents/`. Default hooks (`library/cursor/hooks.json`) enforce the workflow:
- `sessionStart` (`harness-context`) → injects harness state into context
- `beforeSubmitPrompt` (`harness-gate`) → cold-start: sets `.harness/.routing-pending` + planner advisory; `skip harness` clears the marker
- `preToolUse` (`contract-gate`) → **denies** impl writes while routing-pending (no `state.json`, unless skip breadcrumb / 600s TTL) or building without `contract.json`
- `preToolUse` (`evaluator-guard`) → **denies** evaluator writes outside `.harness/`
- `subagentStop` (`chain-evaluator`) → phase orchestration only for empty/`planner`/`evaluator` stops (not explore/shell/etc.)
- `beforeShellExecution` (`pre-commit-harness`) → **denies** commit without approval flag; blocks staged `.env`/secret filenames
- `stop` (`verify-harness`, `enforce-progress`) → soft-blocks unverified contracts / missing breadcrumbs

Optional (`hooks.optional.json`): `secret-read-guard` (deny Read of live secrets), `security-shell` (deny download-exec pipes), `dedup-server`, `context-health`.

## Phase 1: Planning

Launch `/planner` with the user's request:

```text
/planner [paste or describe the user's request with relevant context]
```

The planner produces `.harness/state.json` (one-line vision + max 5 tasks). Trade-offs and open questions go in the planner's breadcrumb, not the state file. Present to user for confirmation.

### Pushback → Scoped Plan

When the request is vague ("make it better") or over-scoped (10 features at once), **don't stop at pushback**:

1. **Push back** — explain why the scope is too broad or vague
2. **Scope down** — propose 1-2 concrete tasks as a first phase. Update `state.json` with broken-down tasks
3. **Present to user** — show the scoped plan; ask for confirmation before Phase 1.5

Do **not** write `contract.json` in Phase 1 — that is Phase 1.5 (builder proposes, evaluator negotiates).

## Phase 1.5: Contract Negotiation

Before writing code, builder and evaluator negotiate what "done" means.

1. **Builder proposes:** Write contract to `.harness/contract.json` with `"phase": "negotiating"`. Log as breadcrumb (`type: negotiate`).
2. **Evaluator reviews:** `touch .cursor/hooks/.evaluator-active` then launch `/evaluator` in negotiation mode — pushes back on weak criteria. Evaluator logs challenge as breadcrumb.
3. **Iterate:** Max 3 rounds. Both sides log as breadcrumbs.
4. **Agreement:** Evaluator marks `"phase": "negotiated"`

### Contract format

```json
{
  "task_id": "feat-1",
  "feature": "One-line description",
  "problem": "What problem does this solve?",
  "proposed_solution": "High-level approach",
  "acceptance_criteria": ["Binary, testable assertions"],
  "edge_cases": ["At least 2 boundary conditions"],
  "verification_method": "What the evaluator should run and check",
  "rubrics": ["code-quality", "architecture"],
  "rubric_mode": "warn",
  "negotiation_rounds": 1,
  "phase": "negotiating",
  "verified": false
}
```

### Rubrics field

Contracts can reference domain rubrics (`architecture`, `code-quality`, `organization`, `design-ui`, `llm-skeptic`, `cost-efficiency`) for additional evaluation. In `strict` mode, high-severity rubric failures block verification. In `warn` mode, they're reported but don't block. Rubric definitions: `.cursor/references/rubrics/{domain}.json`.

### Phase field

| Phase | Set by | Means |
|-------|--------|-------|
| `negotiating` | Builder | Contract being negotiated |
| `negotiated` | Evaluator | Ready to build |
| `building` | Builder | Implementation in progress |
| `evaluating` | Builder | Evaluator testing the live app |

## Phase 2: Building

Work against the negotiated contract, not the original vague prompt.

1. Read `.harness/contract.json` for acceptance criteria
2. Set `"phase": "building"`, update `state.json` to `"building"`
3. Implement the task — one at a time
4. Run computational sensors (lints, types, tests, build)
5. Append breadcrumb to `.harness/breadcrumbs.jsonl`
6. Do NOT self-judge — that's the evaluator's job

## Phase 3: Evaluation

Set `"phase": "evaluating"`, then launch `/evaluator`:

```text
/evaluator Test the implementation against the contract at .harness/contract.json
```

The evaluator reads the calibration guide, tests each criterion and edge case, and produces a report at `.harness/.archive/evals/eval-{task_id}.json`.

| Result | Action |
|--------|--------|
| All PASS | Proceed to Phase 4 |
| FAIL with `fix_and_retest` | Fix issues, re-run `/evaluator` (max 2 retries) |
| `scrap_and_restart` | Log post-mortem, start fresh with different approach |

Scrap-and-restart is expected, not failure — models should discard work that isn't hill-climbing against the rubric.

## Phase 4: Checkpoint

1. Verify `contract.json` has `"verified": true`
2. Update `state.json` → `"verified"`
3. Append completion breadcrumb
4. Stage changes, ask user before committing
5. After commit, update to `"committed"`, pick next task → Phase 1.5

## State Files

| File | Purpose | Who writes |
|------|---------|------------|
| `.harness/state.json` | Single source of truth — one-line vision + max 5 tasks | Planner (init), Builder (updates) |
| `.harness/contract.json` | Active contract | Builder (proposes), Evaluator (approves) |
| `.harness/.archive/evals/eval-{id}.json` | Eval reports | Evaluator |
| `.harness/breadcrumbs.jsonl` | Append-only trace | All agents |

Strategic research and design docs go in the project's own `docs/` directory,
never `.harness/` — the harness holds working state, not prose. Trade-offs and
open questions live in `plan`-type breadcrumbs, not a dedicated file.

All state lives on the file system. Whether `.harness/` is git-tracked or gitignored depends on the project — this repo tracks it for dogfooding; consumer projects may choose to gitignore it.

## Breadcrumbs

Append-only JSONL trace. Every agent appends one line per significant action.

```jsonl
{"ts":"2026-05-23T09:49","role":"planner","type":"plan","feat":"feat-1","msg":"Created state.json with 5 tasks"}
{"ts":"2026-05-23T09:52","role":"builder","type":"negotiate","feat":"feat-1","msg":"Proposed contract: 4 criteria, 2 edge cases"}
{"ts": "2026-05-23T10:15", "role": "evaluator", "type": "evaluate", "feat": "feat-1", "msg": "PASS 6/6 criteria", "result": "pass"}
```

| Field | Required | Values |
|-------|----------|--------|
| `ts` | yes | ISO-8601 timestamp |
| `role` | yes | `planner`, `builder`, `evaluator` |
| `type` | yes | `plan`, `negotiate`, `build`, `verify`, `evaluate` (legacy: `eval`), `checkpoint`, `decision`, `scrap` |
| `feat` | no | Task ID (e.g. `feat-1`) or `null` for non-harness work |
| `msg` | yes | One-line summary |
| `result` | no | `pass`, `fail`, `blocked` |

## Output Artifacts

- `.harness/state.json` — vision + task tracking (all agents)
- `.harness/contract.json` — active contract (builder + evaluator)
- `.harness/.archive/evals/eval-{id}.json` — evaluation reports (evaluator)
- `.harness/breadcrumbs.jsonl` — append-only trace (all agents)

## Stop Conditions

- All tasks in `state.json` are `"committed"` — harness complete
- User says "skip harness" or "just do it" — exit harness, work directly
- Evaluator recommends `scrap_and_restart` after 2 retries — stop and report to user
- Contract negotiation exceeds 3 rounds — escalate to user for decision

## References

- `references/rubrics-and-tuning.md` — rubrics, model-adaptive tuning, optional rubric audit
- `references/evaluator-calibration.md` — good/bad grading examples
- `references/testing-methods.md` — domain playbooks for Mode 2
- `references/harvest.md` — post-eval harvest_recommendation signals
