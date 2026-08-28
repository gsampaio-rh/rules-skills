# Harness Essence

A file-based task system that keeps AI agents honest across sessions.

## Five Problems It Solves

1. **Scope** — `state.json` holds a one-line vision and task list so agents don't reinvent context each session.
2. **Task Definition** — Discrete tasks with `id`, `name`, `type` (`feature`/`bug`/`spike`/`chore`/`docs`), `status`, and optional `scope`.
3. **Status Tracking** — Lifecycle: `pending` → `building` → `evaluating` → `verified` → `committed` (+ `cancelled`). Breadcrumbs trace actions.
4. **Acceptance Criteria** — `contract.json` with binary-testable criteria negotiated before implementation.
5. **Contract Enforcement** — When harness is **active** (opt-in arm or pending/building/evaluating task), structural hooks deny implementation writes without a contract. Agents cannot self-grade. Idle/default work is ungated.

## Three Core Files

| File | Purpose | Created by |
|------|---------|------------|
| `.harness/state.json` | Vision + task backlog (schema_version 2, under 50 lines) | Planner |
| `.harness/contract.json` | Active acceptance contract | Builder proposes, Evaluator approves |
| `.harness/breadcrumbs.jsonl` | Append-only audit trail | All agents |

## Enforcement Model

| Workflow Step | Mechanism | Type |
|--------------|-----------|------|
| Opt-in arm | `harness-gate.sh` (sets `.routing-pending` only on `use/with harness`, `/planner`, `adversarial-harness`) + `contract-gate` deny | **paired** |
| Contract before impl (active only) | `contract-gate.sh` (preToolUse) — idle/committed-only allows free writes | **structural deny** |
| Evaluator isolation | `evaluator-guard.sh` (preToolUse) | **structural deny** |
| Verification before done | `verify-harness.sh` (stop) | side-effect-thin soft followup |
| User commit approval | `pre-commit-harness.sh` (beforeShellExecution) | **structural deny** |
| Staged secrets / `.env` | `pre-commit-harness.sh` (filename deny) | **structural deny** |
| Progress breadcrumbs | `enforce-progress.sh` (stop) | side-effect-thin soft followup |
| Phase advance | `chain-evaluator.sh` (subagentStop) | orchestration (side-effect) |
| Session context | `harness-context.sh` (sessionStart) | inject |

**Default:** free writes (no auto planner). **Opt-in:** user phrases or `/planner` / skill. **Active:** pending/building/evaluating tasks keep contract gates. **Idle:** committed/cancelled/verified-only (or no state) does not deny.

**Optional (not in default `hooks.json`):** `secret-read-guard.sh` (`beforeReadFile`, failClosed — deny live `.env`/key paths), `security-shell.sh` (`beforeShellExecution`, failClosed — deny curl/wget pipe-to-shell), `dedup-server.sh` (dev-server utility), `agents-md-nudge.sh` (`sessionStart` — one-line pointer when root AGENTS.md is missing) — see `library/cursor/hooks.optional.json`. Session fatigue/handoff (P6) is skill `session-review`, not a stop hook.

**Design principle:** Critical steps must be structurally impossible to skip (**structural deny** hooks). Soft hooks are **side-effect-thin** (flags, phase patches, short `followup_message` pointers) — not prose sermons. Semantic advisories live in skill `adversarial-harness` / `/evaluator` / `session-review`.

**Self-certification:** `verify-harness.sh` honors `verified: true` only when breadcrumbs include an evaluator pass for the contract task (builder self-set `verified` without that crumb gets a soft followup).

**Orphan contracts:** A leftover `contract.json` with `verified: true` and no `building`/`evaluating` task is treated as `NO_BUILD` (stop soft-gate skips). Clear it by a `Commit:` checkpoint breadcrumb (post-commit ADVANCE archives the contract) or delete `.harness/contract.json` manually when abandoning the task.

**Platform limitation:** `contract-gate` gates `Write`/`StrReplace` matchers as configured; shell redirects remain ungated.

## Task Schema (v2)

```json
{
  "project": "short-name",
  "schema_version": 2,
  "vision": "One sentence: what we're building and why.",
  "tasks": [
    {
      "id": "feat-1",
      "name": "Human-readable description",
      "type": "feature",
      "status": "pending",
      "scope": "optional includes/excludes"
    }
  ]
}
```

No `direction`, `trade_offs`, or `open_questions` in `state.json` — those go in `plan` breadcrumbs.

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

## Hook profile (single default)

**Default** — `library/cursor/hooks.json` (installed as `.cursor/hooks.json` by `make sync-local`):

`harness-context`, `harness-gate`, `contract-gate`, `evaluator-guard`, `pre-commit-harness`, `verify-harness`, `enforce-progress`, `chain-evaluator`.

**Optional** — merge `library/cursor/hooks.optional.json` for `secret-read-guard` + `security-shell` + `dedup-server` + `agents-md-nudge`.

There is no lean/full dual product; older `hooks.lean.json` / `hooks.full.json` names are retired.

## Consumer Adoption

1. Copy `library/cursor/{rules,skills,hooks,agents,references,templates}` (or run `./sync-cursor.sh`).
2. Install `library/cursor/hooks.json` as `.cursor/hooks.json`.
3. `mkdir -p .harness`
4. Seed project memory if missing: `scripts/adopt-agents-md.sh <project> library/cursor` (from `templates/AGENTS.md`); optionally `/agents-bootstrap` to fill Commands.
5. Everyday work stays free. Opt in with `use harness` / `/planner` when you want full planner→contract→gates.

`AGENTS.md` is **project memory**; `.harness/` + `harness-context` is **session memory**. Optional `agents-md-nudge` reminds when the former is absent.

See also skill `adversarial-harness`.

## Commit Gate

`pre-commit-harness.sh` denies `git commit` until `.cursor/hooks/.commit-approved` exists (300s TTL). Flag is deleted after successful commit.

## Maintenance

```bash
make harness-prune
python .cursor/hooks/prune-harness.py --apply
```

Session start auto-archives completed tasks and truncates breadcrumbs to a rolling ~30-line window. Forensic history lives in `.harness/.archive/archive.jsonl` (not injected into prompts). Manual prune appends breadcrumb overflow to the same `archive.jsonl` sink and clears stale flags — it does not write deprecated `.archive/breadcrumbs.jsonl` or `questions.jsonl`.

Read-only session desk (observability, not enforcement): `make harness-dashboard` or `python .cursor/hooks/harness-dashboard.py` writes a self-contained Genius Bar board to `.harness/dashboard.html` from local harness artifacts. Optional soft regenerate on `stop` / `sessionStart` lives in `hooks.optional.json` only — never injected into prompts. Tokens stay Unavailable unless a real local source exists (Cursor does not reliably expose them into `.harness/` today).

## Context package

```bash
python .cursor/hooks/context-package.py
python .cursor/hooks/context-package.py --format markdown
```

Returns lean JSON/markdown: active task, AC slice (≤5), last 3 breadcrumbs (no open-questions section). Use at handoffs — do not dump full archive into the prompt.

## Eval Scope (this repo only)

Behavioral scenarios live under `tests/eval/scenarios/`. Eval is local/opt-in infrastructure for regression-testing the harness. Consumer projects do not need it. See [`EVAL_GUIDE.md`](EVAL_GUIDE.md).
