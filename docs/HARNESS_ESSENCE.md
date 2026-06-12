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

**Self-certification bypass (fixed):** `verify-harness.sh` requires a breadcrumb with `role=evaluator, result=pass` (or builder `build+pass` for simple 1-2 file tasks that legitimately bypass the full harness) before honoring `verified: true`. See `fix-verify-harness` in the archive.

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
  "phase": "negotiating|negotiated|building|evaluating|verified",
  "verified": false
}
```

`phase` values: `negotiating` (evaluator reviewing), `negotiated` (approved, not started), `building` (impl in progress — chain-evaluator.sh auto-advances to `evaluating` when subagent stops), `evaluating` (evaluator testing), `verified` (evaluator PASS).

**`negotiations/` directory: deprecated.** Use `type=negotiate` breadcrumbs instead. The directory added schema burden with no practical benefit; the breadcrumb trail already captures negotiation history.

## Eval Scope (this repo)

20 scenarios testing the 5 problems: see `tests/eval/scenarios/`. Each scenario maps to at least one problem. Coverage: >=4 scenarios per problem, 2 negative (harness should NOT activate), 1 E2E integration.

Eval is this-repo infrastructure for regression-testing the harness itself. Consumer projects do not need it.

## Hook Profiles

**Lean profile (default for consumers — 4 hooks):**

| Hook | Type | Enforces |
|------|------|---------|
| `contract-gate.sh` | preToolUse/Write deny | No code without contract |
| `verify-harness.sh` | stop | No marking done without evaluator PASS |
| `harness-context.sh` | sessionStart | Injects harness state + session boundary advisory |
| `pre-commit-harness.sh` | beforeShellExecution deny | No commit without user approval |

**Full profile (this repo only — 8 hooks):** adds `chain-evaluator.sh` (auto-advance building→evaluating), `evaluator-guard.sh` (deny eval writes to impl), `context-health.sh` (stale context advisory), `harness-gate.sh` (cold-start routing advisory).

**Decision:** ship lean profile only for consumers. Full profile is dogfooding infrastructure for this repo. Consumer projects do not need evaluator isolation or context health monitoring to get value from the five-problem harness.

## Consumer Adoption

See `.harness/docs/design-consumer-quickstart.md` for the 6-step setup. Minimum: copy hooks + rules + skill + agents → `mkdir .harness` → harness activates on first non-trivial task.

## Commit Gate

`pre-commit-harness.sh` denies `git commit` until `.cursor/hooks/.commit-approved` exists. Flag has 300s TTL — stale flags from crashed sessions are rejected. Flag is deleted after successful commit.
