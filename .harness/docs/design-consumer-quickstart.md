# Doc C — Consumer Quick-Start

## 5-Minute Setup (6 steps)

### Step 1: Copy hooks and rules

```bash
cp -R library/cursor/hooks/ .cursor/hooks/
cp library/cursor/hooks.lean.json .cursor/hooks.json
cp -R library/cursor/rules/ .cursor/rules/
```

### Step 2: Copy the adversarial-harness skill

```bash
mkdir -p .cursor/skills/adversarial-harness
cp library/cursor/skills/adversarial-harness/SKILL.md .cursor/skills/adversarial-harness/SKILL.md
```

### Step 3: Copy agent definitions

```bash
cp -R library/cursor/agents/ .cursor/agents/
```

### Step 4: Create `.harness/` directory

```bash
mkdir -p .harness
```

No state.json needed — the hooks detect cold-start and trigger planner routing automatically on first non-trivial prompt.

### Step 5: Add to .gitignore (optional)

```bash
echo ".cursor/" >> .gitignore
```

Consumer projects typically gitignore IDE config. `.harness/` can be tracked or ignored — your choice.

### Step 6: Test enforcement

Write any implementation file without a `.harness/state.json` and a non-trivial prompt. `contract-gate` should deny the write with a message about routing to the planner.

---

## What You Get (starter = lean profile)

| Hook | Event | What it does |
|------|-------|-------------|
| `harness-context.sh` | sessionStart | Injects harness state + pending task into agent context |
| `harness-gate.sh` | beforeSubmitPrompt | Detects non-trivial cold-start; creates `.routing-pending` marker |
| `contract-gate.sh` | preToolUse (Write) | **Denies** impl writes without contract (structural enforcement) |
| `verify-harness.sh` | stop (loop_limit: 3) | Blocks turn end until contract verified or evaluator launched |
| `enforce-progress.sh` | stop (loop_limit: 2) | Reminds agent to append breadcrumbs on multi-file changes |
| `context-health.sh` | stop (loop_limit: 1) | Suggests fresh thread on session fatigue |
| `dedup-server.sh` | beforeShellExecution | Prevents duplicate dev servers |
| `pre-commit-harness.sh` | beforeShellExecution (git commit) | **Denies** commit without user approval flag |

**Rules included:** `adversarial_harness.mdc`, `autonomous_execution.mdc`, `planning_discipline.mdc`, `progress_tracking.mdc`, `verification.mdc`, `code_standards.mdc`, `critical_thinking.mdc`, `agent_behavior.mdc`

**Agents included:** `planner.md` (produces state.json), `evaluator.md` (adversarial QA)

---

## What You DON'T Need

These are this-repo-only (dogfooding infrastructure):

- `tests/eval/` — session runner, judge, scenarios (regression testing the harness itself)
- `harness_lint.py` — validates harness file schemas
- `harness_metrics.py` — dashboard metrics (being killed)
- `.harness/audits/` — spike audit outputs
- `docs/EVAL_GUIDE.md` — eval pipeline documentation
- `docs/HARNESS_STANDARD.md` (being replaced by HARNESS_ESSENCE.md)
- `hooks.full.json` — extended profile with evaluator-guard + chain-evaluator
- `scripts/` — migration, profile switching, validation

---

## Minimum File Set (what must exist after setup)

| Path | Content | Required? |
|------|---------|-----------|
| `.cursor/hooks.json` | Hook config (copy of hooks.lean.json) | Yes |
| `.cursor/hooks/*.sh` | Hook scripts (10 shell files + hooks-lib.sh) | Yes |
| `.cursor/rules/*.mdc` | Always-on rules (8 files) | Yes |
| `.cursor/skills/adversarial-harness/SKILL.md` | Harness workflow instructions | Yes |
| `.cursor/agents/planner.md` | Planner subagent definition | Yes |
| `.cursor/agents/evaluator.md` | Evaluator subagent definition | Yes |
| `.harness/` | Directory (created empty) | Yes |
| `.harness/state.json` | Created by planner on first non-trivial task | No (auto-created) |
| `.harness/contract.json` | Created by builder before implementation | No (auto-created) |
| `.harness/breadcrumbs.jsonl` | Appended by all agents | No (auto-created) |

---

## Upgrade Path

### Starter (lean) → Full

Add evaluator isolation and chain-evaluator for adversarial eval workflow:

```bash
cp library/cursor/hooks.full.json .cursor/hooks.json
```

Full adds: `evaluator-guard.sh` (denies evaluator writing impl code) + `chain-evaluator.sh` (routes subagent completion).

### When to upgrade

- When you run `/evaluator` regularly and want isolation guarantees (evaluator-guard denies impl writes)
- When you have multiple subagents and need phase routing on completion (chain-evaluator)

### When NOT to upgrade

- Solo developer without evaluator subagent → lean is sufficient
- Quick projects with 1-2 files → skip harness entirely ("skip harness")
