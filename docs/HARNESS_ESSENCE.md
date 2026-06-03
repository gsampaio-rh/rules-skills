# Harness Essence

A file-based task system that keeps AI agents honest across sessions.

## Five Problems It Solves

1. **Scope** — `state.json` holds vision, direction, trade-offs, and task list so agents don't reinvent context each session.
2. **Task Definition** — Discrete tasks with `id`, `name`, `type` (feature/bug/gap/spike/chore), and `status`.
3. **Status Tracking** — Lifecycle: `pending` → `building` → `evaluating` → `verified` → `committed` (+ `cancelled`). Breadcrumbs trace every action.
4. **Acceptance Criteria** — `contract.json` with binary-testable criteria negotiated before implementation.
5. **Contract Enforcement** — Structural hooks deny implementation writes without a contract. Agents cannot self-grade.

## Three Core Files

| File | Purpose | Created by |
|------|---------|------------|
| `.harness/state.json` | Vision + task backlog | Planner (init), Builder (updates) |
| `.harness/contract.json` | Active acceptance contract | Builder (proposes), Evaluator (approves) |
| `.harness/breadcrumbs.jsonl` | Append-only audit trail | All agents |

## Enforcement Model

| Workflow Step | Mechanism | Type |
|--------------|-----------|------|
| Contract before impl | `contract-gate.sh` (preToolUse/Write) | **structural deny** |
| Cold-start routing | `harness-gate.sh` (advisory) + `contract-gate.sh` (deny) | paired |
| Verification before done | `verify-harness.sh` (stop, loop_limit: 3) | soft-block |
| User commit approval | `pre-commit-harness.sh` (beforeShellExecution) | **structural deny** |
| Progress breadcrumbs | `enforce-progress.sh` (stop, loop_limit: 2) | advisory |
| Session health | `context-health.sh` (stop, loop_limit: 1) | advisory |
| Evaluator isolation | `evaluator-guard.sh` (preToolUse/Write, full only) | **structural deny** |

**Design principle:** Critical steps must be structurally impossible to skip (deny hooks), not merely advised. Advisory hooks are acceptable for non-critical quality signals.

**Known gap-23 debt:** `verify-harness.sh` checks `contract.json` `verified: true` without verifying evaluator actually ran. Agent can self-set the field. Breadcrumbs provide audit evidence but not enforcement.

**Platform limitation:** `contract-gate` only gates the `Write` tool. `StrReplace` and shell redirects are ungated (Cursor platform constraint).

## Task Schema

```json
{
  "id": "feat-1",
  "name": "Human-readable description",
  "type": "feature|bug|gap|spike|chore",
  "status": "pending|building|evaluating|verified|committed|cancelled",
  "priority": 1,
  "group": "optional-grouping-string",
  "scope": "optional scope description",
  "details": "optional implementation details"
}
```

Optional `group` field enables filtering and dedup detection across related tasks.

## Contract Schema

```json
{
  "task_id": "feat-1",
  "feature": "One-line description",
  "acceptance_criteria": ["Binary, testable assertions"],
  "edge_cases": ["Boundary conditions"],
  "verification_method": "What evaluator runs",
  "phase": "negotiating|negotiated|building|evaluating",
  "verified": false
}
```

## Eval Scope (this repo)

20 scenarios testing the 5 problems: see `tests/eval/scenarios/`. Each scenario maps to at least one problem. Coverage: >=4 scenarios per problem, 2 negative (harness should NOT activate), 1 E2E integration.

Eval is this-repo infrastructure for regression-testing the harness itself. Consumer projects do not need it.

## Consumer Adoption

See `.harness/docs/design-consumer-quickstart.md` for the 6-step setup. Minimum: copy hooks + rules + skill + agents → `mkdir .harness` → harness activates on first non-trivial task.

## Commit Gate

`pre-commit-harness.sh` denies `git commit` until `.cursor/hooks/.commit-approved` exists. Flag has 300s TTL — stale flags from crashed sessions are rejected. Flag is deleted after successful commit.
