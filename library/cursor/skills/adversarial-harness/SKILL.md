---
name: adversarial-harness
description: >-
  Multi-agent harness with planner/builder/evaluator subagent roles, contract
  negotiation, adversarial verification, and breadcrumbs tracing. Use when: build
  feature, implement feature, harness workflow, adversarial testing, QA workflow,
  contract-first, multi-agent, complex implementation.
disable-model-invocation: false
---

# Adversarial Harness Workflow

A tiny engineering team in your IDE: `/planner` sets direction → builder and `/evaluator` negotiate a contract → you build → computational sensors gate → `/evaluator` tests the live app → breadcrumbs trace everything.

## How This Skill Works

### Mode 1: Full Harness
Multi-feature workflow with planner, contract negotiation, build, and adversarial evaluation. Use for non-trivial features touching 3+ files.

### Mode 2: Standalone Audit
Launch a rubric audit without a full feature build. Uses the evaluator in rubric-only mode.

## Proactive Triggers

- Non-trivial feature request touching 3+ files or requiring architectural decisions
- User says "build feature", "implement", "harness", "adversarial", "multi-agent"
- `.harness/state.json` exists with pending features — resume the workflow
- Contract exists but is unverified — continue the build/evaluate cycle

## Subagent Architecture

| Role | Subagent | Purpose |
|------|----------|---------|
| Planner | `/planner` | Turns vague prompts into high-level product specs |
| Builder | Main agent (you) | Implements features against the negotiated contract |
| Evaluator | `/evaluator` | Adversarial QA — negotiates contracts AND tests the actual app |

Subagent definitions live in `.cursor/agents/`. Hooks enforce the workflow:
- `sessionStart` → injects harness state into context
- `beforeSubmitPrompt` → blocks non-trivial prompts when no harness is active
- `subagentStop` → routes based on `phase` field
- `stop` → blocks if contract is unverified

## Phase 1: Planning

Launch `/planner` with the user's request:

```text
/planner [paste or describe the user's request with relevant context]
```

The planner produces `.harness/spec.md` (product spec) and `.harness/state.json` (feature list). Present to user for confirmation.

## Phase 1.5: Contract Negotiation

Before writing code, builder and evaluator negotiate what "done" means.

1. **Builder proposes:** Write contract to `.harness/contract.json` with `"phase": "negotiating"`
2. **Evaluator reviews:** Launch `/evaluator` in negotiation mode — pushes back on weak criteria
3. **Iterate:** Max 3 rounds. Both sides log as breadcrumbs.
4. **Agreement:** Evaluator marks `"phase": "negotiated"`

### Contract format

```json
{
  "feature_id": "feat-1",
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

Contracts can reference domain rubrics (`architecture`, `code-quality`, `organization`, `design-ui`) for additional evaluation. In `strict` mode, high-severity rubric failures block verification. In `warn` mode, they're reported but don't block. Rubric definitions: `.cursor/references/rubrics/{domain}.json`.

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
3. Implement the feature — one at a time
4. Run computational sensors (lints, types, tests, build)
5. Append breadcrumb to `.harness/breadcrumbs.jsonl`
6. Do NOT self-judge — that's the evaluator's job

## Phase 3: Evaluation

Set `"phase": "evaluating"`, then launch `/evaluator`:

```text
/evaluator Test the implementation against the contract at .harness/contract.json
```

The evaluator reads the calibration guide, tests each criterion and edge case, and produces a report at `.harness/evals/eval-{feature_id}.json`.

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
5. After commit, update to `"committed"`, pick next feature → Phase 1.5

## State Files

| File | Purpose | Who writes |
|------|---------|------------|
| `.harness/spec.md` | Product spec | Planner |
| `.harness/state.json` | Feature list with statuses | Planner (init), Builder (updates) |
| `.harness/contract.json` | Active contract | Builder (proposes), Evaluator (approves) |
| `.harness/evals/eval-{id}.json` | Eval reports | Evaluator |
| `.harness/breadcrumbs.jsonl` | Append-only trace | All agents |

All state lives on the file system. Add `.harness/` to `.gitignore`.

## Breadcrumbs

Append-only JSONL trace. Every agent appends one line per significant action.

```jsonl
{"ts":"2026-05-23T09:49","role":"planner","type":"plan","feat":"feat-1","msg":"Created spec with 5 features"}
{"ts":"2026-05-23T09:52","role":"builder","type":"negotiate","feat":"feat-1","msg":"Proposed contract: 4 criteria, 2 edge cases"}
{"ts":"2026-05-23T10:15","role":"evaluator","type":"eval","feat":"feat-1","msg":"PASS 6/6 criteria","result":"pass"}
```

| Field | Required | Values |
|-------|----------|--------|
| `ts` | yes | ISO-8601 timestamp |
| `role` | yes | `planner`, `builder`, `evaluator` |
| `type` | yes | `plan`, `negotiate`, `build`, `verify`, `eval`, `checkpoint`, `decision`, `scrap` |
| `feat` | no | Feature ID or `null` for non-harness work |
| `msg` | yes | One-line summary |
| `result` | no | `pass`, `fail`, `blocked` |

## Output Artifacts

- `.harness/spec.md` — product spec (planner)
- `.harness/state.json` — feature tracking (all agents)
- `.harness/contract.json` — active contract (builder + evaluator)
- `.harness/evals/eval-{id}.json` — evaluation reports (evaluator)
- `.harness/breadcrumbs.jsonl` — append-only trace (all agents)

## Stop Conditions

- All features in `state.json` are `"committed"` — harness complete
- User says "skip harness" or "just do it" — exit harness, work directly
- Evaluator recommends `scrap_and_restart` after 2 retries — stop and report to user
- Contract negotiation exceeds 3 rounds — escalate to user for decision

## References

For evaluator rubrics (per-domain criteria tables), model-adaptive tuning guidance, and invocation examples, see `references/rubrics-and-tuning.md`. For evaluator calibration, see `references/evaluator-calibration.md`.
