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
| Progress breadcrumbs | `enforce-progress.sh` (stop, loop_limit: 2) | soft-block (`PROGRESS BLOCKED` when `source_writes>=2` without valid breadcrumb; skips if `contract.json` present — harness owns that path) |
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


## Maintenance

The harness accumulates state over time: resolved open_questions in `state.json`, growing `breadcrumbs.jsonl`, and stale flag files from crashed sessions. `prune-harness.py` is distributed to `.cursor/hooks/` via `make sync-local` — run it periodically to keep the harness lean.

```bash
# Preview what would be pruned (no files modified)
make harness-prune                              # if you have this repo's Makefile
python .cursor/hooks/prune-harness.py           # or invoke directly (works in any project)

# Apply: archive resolved questions, old breadcrumbs, remove stale flags
python .cursor/hooks/prune-harness.py --apply
```

> **Consumer projects** (no `Makefile` from this repo): invoke directly via `python .cursor/hooks/prune-harness.py`. Both `prune-harness.py` and `context-package.py` are distributed to `.cursor/hooks/` by `make sync-local` and work standalone — no Makefile required.

### What gets pruned

| Artifact | Condition | Destination |
|---|---|---|
| `open_questions` entries | Starts with `RESOLVED` or `DEFERRED` | `.harness/.archive/questions.jsonl` |
| `breadcrumbs.jsonl` lines | Beyond retention window (see below) | `.harness/.archive/breadcrumbs.jsonl` |
| `.harness/.routing-pending` | mtime > 30 minutes | Deleted |
| `.cursor/hooks/.evaluator-active` | `contract.json phase ≠ "evaluating"` | Deleted |
| `.cursor/hooks/.commit-approved` | No task in `status: building` | Deleted |

### Breadcrumb retention policy

Keep whichever of these two policies retains **more** lines:
- **Last 50** — always keep the 50 most recent entries
- **Within 7 days** — keep all entries timestamped in the last 7 days

Example: 100 entries all from yesterday → age policy keeps all 100 (> last-50's 50) → 0 archived.
Example: 100 entries all from 10 days ago → last-50 keeps 50 (> age policy's 0) → 50 archived.

### Archive location

Archives live in `.harness/.archive/` — gitignored by default. Active harness state (state.json, breadcrumbs.jsonl, contract.json) remains git-tracked; overflow is ephemeral.

### Archive format

`.harness/.archive/questions.jsonl` — one JSON object per line:
```json
{"question": "RESOLVED: ...", "archived_at": "2026-06-12T03:00:00+00:00"}
```

`.harness/.archive/breadcrumbs.jsonl` — same format as `breadcrumbs.jsonl` (raw JSONL lines appended).

## Context package

`context-package.py` (distributed to `.cursor/hooks/` via `make sync-local`) produces a lean, ready-to-inject JSON summary of current harness state. Use it at session start or before agent handoffs to provide focused context without exposing the full state.json/breadcrumbs history.

```bash
# JSON output (default)
python .cursor/hooks/context-package.py

# Markdown for pasting into a prompt
python .cursor/hooks/context-package.py --format markdown

# Write JSON to disk (for hooks or CI)
python .cursor/hooks/context-package.py --write .harness/context-package.json
```

### JSON schema

```json
{
  "task":          { "id": "feat-1", "name": "...", "status": "building" },
  "contract":      { "task_id": "feat-1", "acceptance_criteria": [...], "phase": "building", "verified": false },
  "breadcrumbs":   [ { "ts": "...", "role": "builder", "type": "build", "msg": "..." } ],
  "open_questions": [ "Unresolved: ..." ]
}
```

### Active task selection rule

The `task` field contains the **first task** in `state.json tasks[]` whose status is `pending`, `building`, or `evaluating`. When no such task exists (empty array, or all tasks verified/committed/cancelled), `task` is `null`.

### Filtering

- `open_questions`: entries starting with `RESOLVED` or `DEFERRED` are excluded (same rule as `prune-harness.py`). `SUPERSEDED`, `Unresolved`, and plain strings are kept.
- `breadcrumbs`: last ≤8 valid JSONL entries. Blank lines and invalid JSON lines are skipped.
- `contract`: `null` when `contract.json` is missing.

### CLI flags

| Flag | Default | Description |
|---|---|---|
| `--format json\|markdown` | `json` | Output format |
| `--write PATH` | (none) | Write JSON to file (same content as stdout) |
| `--root PATH` | auto-detected | Repository root (for testing with fixture directories) |
