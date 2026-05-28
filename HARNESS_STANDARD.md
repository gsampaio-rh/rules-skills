# Harness Standard

Internal quality contract for the adversarial harness workflow, its state files, and enforcement hooks. Not loaded by the agent — the workflow itself lives in `library/cursor/skills/adversarial-harness/SKILL.md`.

## Purpose

The harness is a structured build-verify cycle that prevents the most common failure mode of AI coding agents: building against vague specs, self-evaluating, and shipping unjudged work. It separates planning, building, and evaluation into distinct roles with explicit handoffs.

## Architecture

```
User request
  → /planner (spec.md + state.json)
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

```json
{
  "project": "project-name",
  "features": [
    {
      "id": "feat-1",
      "name": "Feature description",
      "status": "pending|building|evaluating|verified|committed"
    }
  ]
}
```

### `contract.json`

```json
{
  "feature_id": "feat-1",
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

### `evals/eval-{feature_id}.json`

```json
{
  "feature_id": "feat-1",
  "feature": "Feature description",
  "timestamp": "ISO-8601",
  "criteria_results": [{"criterion": "...", "result": "PASS|FAIL", "evidence": "..."}],
  "edge_case_results": [{"case": "...", "result": "PASS|FAIL", "evidence": "..."}],
  "overall": "PASS|FAIL",
  "recommendation": "proceed|fix_and_retest|scrap_and_restart"
}
```

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

| Signal | Source | What it tells us |
|--------|--------|------------------|
| Negotiation rounds | `harness_metrics.py` → `breadcrumbs` | Whether contracts converge quickly (1-2 rounds = good) |
| Build-evaluate cycles | `harness_metrics.py` → `breadcrumbs` | How many fix-retest iterations per feature (fewer = better contracts) |
| Scrap rate | `harness_metrics.py` → `breadcrumbs` | Ratio of scrapped features to total cycles (target: < 20%) |
| Features completed/pending | `harness_metrics.py` → `state.json` | Overall throughput and backlog |
| Completion rate | `harness_metrics.py` → `state.json` | Percentage of features reaching "verified" or "committed" |
| Eval FAIL distribution | `.harness/evals/` reports | Which criteria types fail most often — informs contract template improvements |

Run `make harness-metrics` or `make harness-metrics-json` to generate a report.

## Anti-Patterns

- **Builder self-judging** — the builder must never evaluate its own work. Always launch `/evaluator`.
- **Vague acceptance criteria** — "code is clean" is not testable. Every criterion must be binary: pass or fail with evidence.
- **Skipping negotiation** — going straight from plan to build produces weak contracts. The evaluator exists to challenge criteria.
- **Overlong negotiation** — more than 3 rounds means the feature scope is unclear. Escalate to the user.
- **Ignoring scrap recommendations** — when the evaluator says `scrap_and_restart`, the builder should comply, not patch.
- **Markdown state files** — use JSON. Models overwrite markdown structure more readily.

## Quality Checklist

Before a harness session is considered complete:

- [ ] Every feature in `state.json` has status `verified` or `committed`
- [ ] Every feature has a corresponding `contract.json` negotiation (check breadcrumbs for `negotiate` type)
- [ ] Every feature has an eval report in `.harness/evals/`
- [ ] No contract has `"verified": false` with `"phase": "evaluating"` (stuck state)
- [ ] Breadcrumbs trace covers the full lifecycle: plan → negotiate → build → verify → checkpoint
- [ ] `make harness-metrics` runs without errors and produces `.harness/metrics.json`
