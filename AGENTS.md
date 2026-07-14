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
| `.harness/state.json` | Project scope: one-line vision + max 5 tasks | JSON — schema_version: 2, under 50 lines |
| `.harness/contract.json` | Acceptance criteria for current build task | JSON — feature, criteria, phase |
| `.harness/breadcrumbs.jsonl` | Append-only session audit trail (auto-truncated to a rolling 30-line window) | JSONL — ts, role, type, feat, msg, result |
| `.harness/archive.jsonl` | Completed tasks (auto-archived from state.json on session start) | JSONL — same schema as state tasks |

**Breadcrumb roles:** `planner`, `builder`, `evaluator`, `system`
**Breadcrumb types:** `plan`, `negotiate`, `build`, `evaluate`, `verify`, `checkpoint`, `session_start`

### Schema v2 (simplified, post-`c9f57a4`)

`state.json` holds exactly two fields beyond `project`/`schema_version`: `vision`
(one sentence) and `tasks` (max 5, each `{id, name, type, status, scope}`).

- **No `direction`, `trade_offs`, or `open_questions` fields** — those live in
  `plan`-type breadcrumbs instead (e.g. `"msg":"...Trade-offs: <key decisions>"`).
- **No `.harness/docs/` or `.harness/audits/`** — deleted in the v2 simplification.
  Strategic research and design docs go in project `docs/`; standalone audits are
  one-off reports (write directly to the location the user requests, not a
  dedicated harness subdirectory).
- `make sync-local` actively removes `.harness/docs/` and `.harness/audits/` if
  a consumer project still has them from before the simplification.

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

## Glob-Scoped Rules (5 files, auto-loaded by file pattern)

These rules load automatically when files matching their glob pattern are open or edited. They are not always-on and do not count against the token budget.

| Rule | File | Glob pattern |
|---|---|---|
| Architecture | `architecture.mdc` | `**/*.py, **/*.ts, **/*.tsx` |
| Causal Rigor | `causal_rigor.mdc` | `experiments/**/*.{py,ipynb,md}` |
| Python / ML | `python_ml.mdc` | `*.py, *.ipynb` |
| Research Standards | `research_standards.mdc` | `experiments/**/*.{py,ipynb,md}, analysis/**/*.{py,ipynb,md}` |
| Testing | `testing.mdc` | `**/test*.py, **/tests/**/*.py` |

---

## Named Agent Personas

| Persona | Invocation | System prompt | Write access |
|---|---|---|---|
| Planner | `/planner` in chat | `library/cursor/agents/planner.md` | `.harness/state.json` only |
| Builder | (default) | Rules above | Full source |
| Evaluator | `/evaluator` in chat | `library/cursor/agents/evaluator.md` | `.harness/` only (enforced by `evaluator-guard.sh`) |

---

## Role model routing

Each role has a recommended model tier based on its failure modes. Config lives at `library/cursor/harness-model-routing.json` (distributed to `.cursor/harness-model-routing.json` via `make sync-local`).

| Role | Default | Recommended override | Why |
|---|---|---|---|
| Planner | `inherit` | `auto` (complex tasks) | Reasoning models produce cleaner task boundaries for architectural/vague prompts |
| Builder | user's IDE model | n/a — not frontmatter-settable | Builder is the main agent, not a subagent |
| Evaluator | `inherit` | `auto` (always recommended) | Stronger models resist sycophancy; evaluator runs once per task so cost is bounded |

**Three-step override path:**

1. Run `make sync-local` — creates `.cursor/agents/planner.md` and `evaluator.md`
2. Open `.cursor/agents/evaluator.md`, change `model: inherit` → `model: auto`
3. For team defaults: edit `library/cursor/agents/evaluator.md` directly so everyone who syncs inherits the routing

**Warning:** `make sync-local` overwrites `.cursor/agents/`. Personal `model:` overrides in `.cursor/agents/` do not survive sync unless `library/cursor/agents/` is also changed.

Full rationale and platform constraints for this routing were researched pre-v2
simplification; the source research doc (`.harness/docs/research/model-selection.md`)
was deleted along with `.harness/docs/` — see `git show c9f57a4~1:.harness/docs/research/model-selection.md`
for the historical version, or `.harness/archive.jsonl` for the negotiation trail.

---

## Hooks

Pre-configured hooks in `library/cursor/hooks/`. Copy to `.cursor/hooks/` to activate.

| Hook | Event | Effect |
|---|---|---|
| `harness-context.sh` | sessionStart | Injects current task, open contract, session count, last 3 breadcrumbs |
| `harness-gate.sh` | beforeSubmitPrompt | Detects non-trivial cold-start prompts; blocks impl writes until planner runs |
| `contract-gate.sh` | preToolUse (Write) | Denies source file writes if no `contract.json` exists |
| `evaluator-guard.sh` | preToolUse (Write) | Denies evaluator writes outside `.harness/` |
| `dedup-server.sh` | beforeShellExecution | Prevents duplicate dev-server processes (npm, flask, uvicorn, etc.) |
| `pre-commit-harness.sh` | beforeShellExecution | Writes a commit breadcrumb and enforces commit approval flag |
| `chain-evaluator.sh` | subagentStop | Auto-advances phase to `evaluating`, creates `.evaluator-active` flag, injects /evaluator prompt |
| `verify-harness.sh` | stop | Requires evaluator launch when contract is open and unverified |
| `enforce-progress.sh` | stop | Warns when multi-file changes lack breadcrumbs |
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

## ACAM Status (2026-07-14)

| Dimension | Level | Key evidence |
|---|---|---|
| Configuration | Intermediate | 8 scoped rules; `per_rule_effectiveness` gap — ablation code exists (`make eval-ablation`), data artifact not yet committed |
| Workflows | **Advanced** | contract-gate.sh + CI eval regression suite (feat-17) |
| Multi-agent | Intermediate | evaluator-guard.sh blocks source writes; chain-evaluator.sh auto-dispatches `/evaluator` on subagentStop (programmatic_orchestration gap closed); harvest recommendation integrated into eval reports |
| Interaction | Intermediate | harness-context.sh injects structured context; `measured_patterns` gap — `session-metrics.py` exists but lacks turns_to_completion/prompt_clarity |

Population: Tier 3+ (~top 0.5% of n≈3,200 public repos, ACAM survey June 2026).
