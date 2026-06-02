# Harness Standard

Internal quality contract for the adversarial harness workflow, its state files, and enforcement hooks. Not loaded by the agent — the workflow itself lives in `library/cursor/skills/adversarial-harness/SKILL.md`.

## Purpose

The harness is a structured build-verify cycle that prevents the most common failure mode of AI coding agents: building against vague specs, self-evaluating, and shipping unjudged work. It separates planning, building, and evaluation into distinct roles with explicit handoffs.

## Architecture

```
User request
  → /planner (state.json)
  → Builder proposes contract ↔ /evaluator negotiates
  → Builder implements against contract
  → Computational sensors (lint, test, build)
  → /evaluator tests live app against contract
  → Checkpoint + commit
```

| Role | Agent | Responsibility |
|------|-------|----------------|
| Planner | `/planner` subagent | Decomposes vague requests into product specs |
| Builder | Main agent | Implements features against negotiated contracts |
| Evaluator | `/evaluator` subagent | Adversarial QA — negotiates criteria AND tests the live app |

Subagent definitions: `.cursor/agents/`. Workflow details: `library/cursor/skills/adversarial-harness/SKILL.md`.

## State File Schemas

All state lives on the file system in `.harness/` at the project root.

### `state.json`

Single source of truth for the project — replaces the former `spec.md` + `state.json` split.

```json
{
  "project": "project-name",
  "created": "ISO-8601 timestamp",
  "schema_version": 2,
  "vision": "1-2 sentences describing the product, purpose, audience",
  "direction": "Technical direction, constraints, architecture pattern",
  "trade_offs": [
    { "decision": "...", "alternative": "...", "reasoning": "..." }
  ],
  "open_questions": ["Unresolved items for builder/user"],
  "tasks": [
    {
      "id": "feat-1",
      "name": "Task description",
      "type": "feature|bug|spike|chore",
      "status": "pending|building|evaluating|verified|committed|cancelled",
      "scope": "Optional: what this includes/excludes"
    }
  ]
}
```

**Required fields:** `project`, `created`, `vision`, `direction`, `tasks`.
**Required per task:** `id`, `name`, `type`, `status`.
**Optional fields:** `schema_version`, `trade_offs`, `open_questions`, `tasks[].scope`, `tasks[].priority`, `tasks[].details`.

**Status enum** (lifecycle order):

| Status | Meaning |
|--------|---------|
| `pending` | Planned, not started |
| `building` | Contract negotiated, implementation in progress |
| `evaluating` | Implementation done, evaluator testing |
| `verified` | Evaluator passed, ready to commit |
| `committed` | Committed to git (terminal) |
| `cancelled` | Explicitly abandoned (terminal) |

**Type enum:**

| Type | Use for |
|------|---------|
| `feature` | User-facing deliverable |
| `bug` | Behavior gap or product defect |
| `spike` | Time-boxed investigation |
| `chore` | Docs, tooling, maintenance |

> **Migration:** v1 schemas used `features` instead of `tasks`. Consumers accept both keys during transition. Run `make migrate-harness` to upgrade.

### `contract.json`

```json
{
  "task_id": "feat-1",
  "feature": "One-line description",
  "problem": "What problem does this solve?",
  "proposed_solution": "High-level approach",
  "acceptance_criteria": ["Binary, testable assertions — not vague quality statements"],
  "edge_cases": ["At least 2 boundary conditions"],
  "verification_method": "What the evaluator should run and check",
  "rubrics": ["code-quality", "architecture"],
  "rubric_mode": "warn|strict",
  "negotiation_rounds": 1,
  "phase": "negotiating|negotiated|building|evaluating|verified",
  "verified": false
}
```

**Acceptance criteria** must be binary-testable. "Code is clean" is not a criterion. "All public functions have type annotations" is. Vague criteria produce vague critiques — granular criteria produce actionable fixes.

### `breadcrumbs.jsonl`

Append-only JSONL. One line per significant action, written by all agents.

```jsonl
{"ts":"ISO-8601","role":"planner|builder|evaluator","type":"plan|negotiate|build|verify|eval|checkpoint|decision|scrap","feat":"feat-1","msg":"One-line summary","result":"pass|fail|blocked"}
```

| Field | Required | Notes |
|-------|----------|-------|
| `ts` | yes | ISO-8601 timestamp |
| `role` | yes | Which agent wrote this |
| `type` | yes | Action category |
| `feat` | no | Feature ID, or `null` for non-feature work |
| `msg` | yes | One-line summary |
| `result` | no | Outcome, when applicable |

### `evals/eval-{task_id}.json`

```json
{
  "task_id": "feat-1",
  "feature": "Task description",
  "timestamp": "ISO-8601",
  "criteria_results": [{"criterion": "...", "result": "PASS|FAIL", "evidence": "..."}],
  "edge_case_results": [{"case": "...", "result": "PASS|FAIL", "evidence": "..."}],
  "overall": "PASS|FAIL",
  "recommendation": "proceed|fix_and_retest|scrap_and_restart"
}
```

### `negotiations/{task_id}-round-{n}-{role}.json`

Structured log of builder-evaluator negotiation rounds. Replaces the previous pattern of loose markdown files in `.harness/` root.

Builder proposal (`{task_id}-round-{n}-builder.json`):

```json
{
  "task_id": "feat-1",
  "round": 1,
  "role": "builder",
  "timestamp": "ISO-8601",
  "decisions": [
    {
      "id": "decision-slug",
      "title": "Human-readable title",
      "proposal": "What the builder proposes",
      "reasoning": "Why this approach",
      "alternatives_considered": ["alt 1", "alt 2"]
    }
  ],
  "open_questions": ["Questions for evaluator"]
}
```

Evaluator challenge (`{task_id}-round-{n}-evaluator.json`):

```json
{
  "task_id": "feat-1",
  "round": 1,
  "role": "evaluator",
  "timestamp": "ISO-8601",
  "decisions": [
    {
      "id": "decision-slug",
      "verdict": "APPROVE|CHALLENGE",
      "reasoning": "Why",
      "counter_proposal": "Alternative (only when CHALLENGE)",
      "conditions": ["Conditions for acceptance"]
    }
  ],
  "overall_verdict": "APPROVE|NEGOTIATE|REJECT"
}
```

**Required fields:** `task_id`, `round`, `role`, `timestamp`.
**Naming convention:** `{task_id}-round-{n}-{role}.json` where `n` is 1-indexed and `role` is `builder` or `evaluator`.

### `negotiations/{task_id}-deferred.json`

Items identified during evaluation that were fixed or deferred for later.

```json
{
  "task_id": "feat-1",
  "assessed_on": "ISO-8601",
  "items": [
    {
      "id": "issue-1",
      "severity": "critical|major|minor",
      "description": "What was found",
      "status": "fixed|deferred|wont-fix",
      "detail": "Fix applied or reason for deferral"
    }
  ]
}
```

### `docs/`

Strategic documents (design considerations, maturity analyses, research notes) that support planning but aren't negotiation artifacts. Written by the builder, not the planner or evaluator. Prose markdown is acceptable here — these are human-readable design docs, not machine-graded artifacts.

### Migration from loose markdown

Projects with existing `.harness/*.md` files (e.g., `builder-proposals.md`, `builder-round2.md`, `adversary-deferred.md`):

1. Create `negotiations/` directory
2. Rename `builder-proposals.md` → `negotiations/{task_id}-round-1-builder.json` and restructure content into the schema above
3. Rename `builder-round2.md` → `negotiations/{task_id}-round-2-builder.json`
4. Rename `adversary-deferred.md` → `negotiations/{task_id}-deferred.json` with `items[]` array
5. Move design docs (e.g., `design-considerations.md`) to `docs/`

## Hook Enforcement

Hooks ensure the workflow is followed, not just documented.

| Hook | Event | What it enforces |
|------|-------|-----------------|
| `contract-gate.sh` | `preToolUse` (Write) | Blocks product file writes when no contract exists |
| `verify-harness.sh` | `stop` | Blocks completion if contract exists but is unverified |
| `harness-context.sh` | `sessionStart` | Injects harness state into conversation context |
| `enforce-progress.sh` | `stop` | Requires breadcrumbs for multi-file changes |

Two hook profiles control enforcement level:

| Profile | File | Enforcement |
|---------|------|-------------|
| **lean** | `library/cursor/hooks.lean.json` | contract-gate + verify-harness + enforce-progress |
| **full** | `library/cursor/hooks.full.json` | All hooks including LLM prompt hooks |

## Design Rationale

### Generator-Evaluator Separation (Anthropic)

The builder and evaluator run in separate context windows. Self-evaluation is unreliable — tuning a standalone critic to be harsh is tractable; tuning a builder to be self-critical is not. The builder never judges its own work.

### Contract Negotiation (Anthropic)

Before building, the builder and evaluator agree on what "done" means. This is the key innovation over simple build-test loops: the evaluator challenges weak criteria during negotiation, producing stronger acceptance tests than the builder would write alone. Max 3 rounds prevents infinite debate.

### File System as Durable State (Anthropic)

JSON over markdown for state files. Models overwrite markdown more readily than structured JSON. The file system is the message bus between agents — no shared memory, no database, just files that survive session boundaries.

### Breadcrumbs Pattern (Anthropic)

"You're basically just leaving breadcrumbs for another model to come and pick up." Append-only JSONL means no agent can rewrite history. If a session dies mid-work, the next session reads breadcrumbs to understand what happened and where to resume.

### Scrap and Restart

Models should discard work that isn't hill-climbing against the rubric. Scrap-and-restart is expected, not failure. The evaluator can recommend `scrap_and_restart` when the implementation is fundamentally wrong, not just buggy.

### Guides and Sensors (Fowler)

The harness combines both: **guides** (planner spec, contract, rules) steer the builder before it acts; **computational sensors** (linters, tests) provide fast deterministic feedback; **inferential sensors** (evaluator subagent) provide expensive thorough testing. Layer them: guides first, cheap sensors second, expensive sensors last.

### Progressive Planning (DeepMind)

The planner stays at user-story level — it doesn't specify implementation details. Granular planner details cascade errors over multi-hour horizons. The contract is where specificity lives, and it's negotiated between builder and evaluator who understand the codebase.

## Hypotheses

- **H1: Separate evaluator context prevents self-evaluation bias.** A builder in the same context window as its own output will rationalize defects. A fresh evaluator context produces harsher, more accurate judgments. Measurement: eval FAIL rate (higher = more honest, not worse quality).
- **H2: Contract negotiation reduces rework cycles vs. building against vague specs.** Negotiated criteria catch misunderstandings before code is written. Measurement: `build_evaluate_cycles` in harness metrics — fewer cycles per feature = better contracts.
- **H3: Append-only breadcrumbs enable reliable session recovery.** When a session dies, the next session resumes from the last breadcrumb without losing context. Measurement: session recovery success rate, features completed across sessions.
- **H4: Hook enforcement prevents workflow shortcuts.** Without enforcement, agents skip negotiation and self-evaluate. `contract-gate.sh` and `verify-harness.sh` make this structurally impossible. Measurement: contract existence rate before first product file write.
- **H5: Scrap rate below 20% indicates healthy contract quality.** High scrap rates mean contracts are approving bad approaches. Low scrap rates mean the negotiation phase is catching problems early. Measurement: `scrap_rate` in `tests/eval/harness_metrics.py`.

## Measurement

Three evaluation tiers provide progressively deeper signal:

### Tier 1: Fast Static Checks (seconds, no API keys)

| Check | Tool | What it catches |
|-------|------|-----------------|
| Contract structure | `contract_lint.py` | Missing fields, vague criteria, insufficient edge cases |
| Breadcrumb integrity | `harness_lint.py` | Invalid JSON, missing fields, timestamp gaps |
| State consistency | `harness_lint.py` | Duplicate task IDs, stuck phases, cross-file mismatches |
| Rule/skill structure | `validate.py` | Token budget, missing sections, dead rules |

Run: `make eval-fast`

### Tier 2: Behavioral Prompt Evals (planned — not yet implemented)

> **Status**: Tier 2 was originally designed around `dataset.yaml` prompt-response pairs with a hybrid judge. That approach was removed in favor of Tier 3 session scenarios which test full agent workflows rather than isolated prompt/response pairs. A future Tier 2 may be reintroduced as an LLM-as-judge layer within Tier 3 (see feat-14 in `state.json`).

| Signal | Source | What it would tell us |
|--------|--------|----------------------|
| Negotiation quality | Session scenarios + LLM judge | Whether agents push back on vague criteria and accept strong ones |
| Builder-evaluator interaction | Session scenarios + LLM judge | Whether builders respond correctly to FAIL/scrap recommendations |
| Rule compliance | Session scenarios + structural checks | Whether rules actually change agent behavior vs. baseline |

### Tier 3: Session Scenario Evals (longer runs, requires Cursor SDK)

| Signal | Source | What it tells us |
|--------|--------|------------------|
| Harness workflow compliance | `session_judge.py` computational checks | Whether the full plan-negotiate-build-evaluate cycle occurs |
| Contract quality | `session_judge.py` computational checks | Whether real-task contracts have binary criteria and edge cases |
| Artifact quality | `session_judge.py` structural checks | Whether produced code meets scenario requirements |
| Negotiation judgment | `session_judge.py` LLM tier | Whether acceptance criteria are genuinely testable |

Run: `make eval-session` (standard, ~20 min) → `make eval-session-long` (long, ~35 min) → `make eval-session-judge` (judge)

### Harness Metrics Dashboard

| Signal | Source | What it tells us |
|--------|--------|------------------|
| Negotiation rounds | `harness_metrics.py` → `breadcrumbs` | Whether contracts converge quickly (1-2 rounds = good) |
| Build-evaluate cycles | `harness_metrics.py` → `breadcrumbs` | How many fix-retest iterations per feature (fewer = better contracts) |
| Scrap rate | `harness_metrics.py` → `breadcrumbs` | Ratio of scrapped features to total cycles (target: < 20%) |
| Tasks completed/pending | `harness_metrics.py` → `state.json` | Overall throughput and backlog |
| Completion rate | `harness_metrics.py` → `state.json` | Percentage of tasks reaching "verified" or "committed" |

Run: `make harness-metrics` or `make harness-metrics-json`

## Anti-Patterns

- **Builder self-judging** — the builder must never evaluate its own work. Always launch `/evaluator`.
- **Vague acceptance criteria** — "code is clean" is not testable. Every criterion must be binary: pass or fail with evidence.
- **Skipping negotiation** — going straight from plan to build produces weak contracts. The evaluator exists to challenge criteria.
- **Overlong negotiation** — more than 3 rounds means the feature scope is unclear. Escalate to the user.
- **Ignoring scrap recommendations** — when the evaluator says `scrap_and_restart`, the builder should comply, not patch.
- **Markdown state files** — use JSON. Models overwrite markdown structure more readily.
- **Loose markdown in `.harness/` root** — negotiation artifacts (proposals, counter-proposals, deferred items) must go in `negotiations/` as timestamped JSON. Strategic docs go in `docs/`. Nothing but `state.json`, `contract.json`, `breadcrumbs.jsonl`, and `metrics.json` should live at the `.harness/` root.
- **Post-hoc contracts** — writing a contract after building inverts the harness. Contracts must be negotiated before implementation starts.

## Quality Checklist

Before a harness session is considered complete:

- [ ] Every task in `state.json` has status `verified` or `committed`
- [ ] Every task has a corresponding `contract.json` negotiation (check breadcrumbs for `negotiate` type)
- [ ] Every task has an eval report in `.harness/evals/`
- [ ] No contract has `"verified": false` with `"phase": "evaluating"` (stuck state)
- [ ] Breadcrumbs trace covers the full lifecycle: plan → negotiate → build → verify → checkpoint
- [ ] `make harness-metrics` runs without errors and produces `.harness/metrics.json`
