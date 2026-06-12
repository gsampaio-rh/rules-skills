# AGENTS.md — rules-skills

Agent configuration guide for AI coding assistants working in this repository.
This file is the cross-tool portability reference: how rules-skills maps across
Cursor, Claude Code, Windsurf, and OpenAI Codex.

---

## What This Repository Is

A distributable library of AI agent configuration artifacts: rules, skills,
hooks, and a file-based adversarial verification harness. The harness solves
five problems: scope (vision in `state.json`), task definition, task tracking,
session recovery (`breadcrumbs.jsonl`), and acceptance criteria (`contract.json`).

---

## How to Work Here

This repo uses a three-role harness: **planner → builder → evaluator**.

1. **Check `.harness/state.json`** at session start. If it exists, harness-context
   injects the current task, open contract, and session count automatically.
2. **Non-trivial work** (3+ files, architectural, vague) must go through `/planner`
   before any implementation writes.
3. **Every build task** requires a `contract.json` with binary-testable acceptance
   criteria negotiated with `/evaluator` before the first `Write`.
4. **After evaluator FAIL**: write an `eval:fail` breadcrumb, fix root cause,
   retest, re-launch `/evaluator`. Only set `verified:true` after PASS.
5. **User says "skip harness"**: bypass the harness. Proceed directly.

---

## Key Artifacts

| File | Purpose | Format |
|---|---|---|
| `.harness/state.json` | Project scope, vision, task backlog | JSON — schema_version: 2 |
| `.harness/contract.json` | Acceptance criteria for current build task | JSON — feature, criteria, phase |
| `.harness/breadcrumbs.jsonl` | Append-only session audit trail | JSONL — ts, role, type, feat, msg, result |
| `.harness/archive.jsonl` | Completed tasks (archived from state.json) | JSONL — same schema as state tasks |

**Breadcrumb roles:** `planner`, `builder`, `evaluator`, `system`
**Breadcrumb types:** `plan`, `negotiate`, `build`, `evaluate`, `verify`, `checkpoint`, `session_start`

---

## Always-On Rules (8 files, ~1992/2000 token budget)

These rules load in every session. Token budget enforced by `harness_lint.py`.

| Rule | File | Purpose |
|---|---|---|
| Adversarial Harness | `adversarial_harness.mdc` | Routes non-trivial work through harness; contract gate; planner/evaluator invocation |
| Agent Behavior | `agent_behavior.mdc` | Communication style, change hygiene, harness-aware session start |
| Autonomous Execution | `autonomous_execution.mdc` | Execute without asking permission; never commit without approval |
| Code Standards | `code_standards.mdc` | Naming, sizing, DRY, single-responsibility |
| Critical Thinking | `critical_thinking.mdc` | Identify real goal; spot assumptions; challenge when appropriate |
| Planning Discipline | `planning_discipline.mdc` | TodoWrite for multi-step tasks; session boundary triggers |
| Progress Tracking | `progress_tracking.mdc` | Breadcrumbs after every 2+ file change; mandatory for multi-file work |
| Verification | `verification.mdc` | Run tests/lint after every code edit |

---

## Agent-Requested Rules (3 files, loaded on demand)

| Rule | File | Trigger condition |
|---|---|---|
| Design Principles | `design_principles.mdc` | UI/UX, accessibility, visual design tasks |
| Prompt Coaching | `prompt_coaching.mdc` | Vague or underspecified user requests |
| Security | `security.mdc` | Auth, secrets, input validation, infra tasks |

---

## Named Agent Personas

| Persona | Invocation | System prompt | Write access |
|---|---|---|---|
| Planner | `/planner` in chat | `library/cursor/agents/planner.md` | `.harness/state.json` only |
| Builder | (default) | Rules above | Full source |
| Evaluator | `/evaluator` in chat | `library/cursor/agents/evaluator.md` | `.harness/` only (enforced by `evaluator-guard.sh`) |

---

## Hooks

Pre-configured hooks in `library/cursor/hooks/`. Copy to `.cursor/hooks/` to activate.

| Hook | Event | Effect |
|---|---|---|
| `harness-context.sh` | sessionStart | Injects current task, open contract, session count, last 3 breadcrumbs |
| `contract-gate.sh` | preToolUse (Write) | Denies source file writes if no `contract.json` exists |
| `evaluator-guard.sh` | preToolUse (Write) | Denies evaluator writes outside `.harness/` |
| `chain-evaluator.sh` | stop | Advances phase to `evaluating`, creates `.evaluator-active` flag |
| `verify-harness.sh` | stop | Requires evaluator launch when contract is open and unverified |
| `context-health.sh` | stop | Warns if breadcrumbs show no progress in current session |

---

## Cross-Tool Portability

### Cursor (native)
All features work natively. Rules in `.cursor/rules/*.mdc`. Hooks in `.cursor/hooks/*.json`.
Skills in `.cursor/skills/*/SKILL.md`. Load with `library/cursor/` as source.

### Claude Code (CLAUDE.md)
Create `CLAUDE.md` at repo root. Paste always-on rule content inline (no frontmatter).
Hooks: implement as bash scripts invoked from `~/.claude/settings.json` hooks config.
Skills: not supported natively — embed skill instructions in CLAUDE.md or as slash commands.

```markdown
# CLAUDE.md excerpt
[Paste adversarial_harness.mdc, planning_discipline.mdc, etc. content here without --- frontmatter]
```

### Windsurf (.windsurfrules)
Create `.windsurfrules` at repo root. Paste always-on rule content inline.
No hook support — structural gates (contract-gate, evaluator-guard) must be enforced via rule text.

### OpenAI Codex / Assistants API (system prompt)
Concatenate always-on rule content into the system prompt.
File-based artifacts (state.json, contract.json, breadcrumbs.jsonl) work unchanged.
No hook support — describe hook behavior in the system prompt.

---

## Eval & CI

```bash
make eval-fast          # Static lints (token budget, harness lint, schema) — fast, no API
make eval-session       # Full scenario run against live agent (needs CURSOR_API_KEY)
make eval-ci-pr         # PR tier: 11 protocol scenarios
make eval-ci-nightly    # Nightly: 31 scenarios
make eval-ablation      # Per-rule ablation (set ABLATE_RULE=<rule.mdc>)
```

Baseline: `tests/eval/fixtures/eval_baseline.json`
CI: `.github/workflows/eval-fast.yml`, `eval-regression-pr.yml`, `eval-regression-nightly.yml`

---

## ACAM Status (2026-06-12)

| Dimension | Level | Key evidence |
|---|---|---|
| Configuration | Intermediate | 8 scoped rules; `per_rule_effectiveness` gap — ablation code exists (`make eval-ablation`), data artifact not yet committed |
| Workflows | **Advanced** | contract-gate.sh + CI eval regression suite (feat-17) |
| Multi-agent | Intermediate | evaluator-guard.sh blocks source writes; `programmatic_orchestration` gap — manual `/evaluator` only |
| Interaction | Intermediate | harness-context.sh injects structured context; `measured_patterns` gap — `session-metrics.py` exists but lacks turns_to_completion/prompt_clarity |

Population: Tier 3+ (~top 0.5% of n≈3,200 public repos, ACAM survey June 2026).
