# Cursor Rules & Skills

A curated library of AI coding assistant rules, skills, hooks, and an adversarial verification harness for Cursor and Claude Code.

## Architecture

This repo separates three concerns:

| Layer | Location | Purpose |
|-------|----------|---------|
| **Project state** | `.harness/` | Tracked harness state — contracts, evals, breadcrumbs, specs |
| **IDE config** | `.cursor/` | Local copies from `library/cursor/` via `make setup` (gitignored) |
| **Product library** | `library/` | The distributable rules, skills, hooks, agents, references |

```
rules-skills/
├── .harness/                    # This project's harness state (git-tracked)
├── .cursor/                     # IDE config (local copies, gitignored)
│   └── (populated by make setup from library/cursor/)
├── library/
│   ├── cursor/                  # Cursor config library
│   │   ├── rules/              # 16 .mdc rule files
│   │   ├── skills/             # 13 skill workflows
│   │   ├── agents/             # Planner + evaluator definitions
│   │   ├── hooks/              # 11 enforcement scripts
│   │   └── references/         # Patterns, design, rubrics
│   └── claude/                  # Claude Code config (parallel port)
├── scripts/                     # Dev tooling
├── tests/eval/                  # Behavioral eval pipeline
└── sync-cursor.sh               # Distribute to other projects
```

## Quick Start

### Developing rules/skills (working on this repo)

```bash
git clone <this-repo>
# Lean profile is default — no harness enforcement fires
# Edit library/cursor/rules/*.mdc, library/cursor/skills/*/SKILL.md directly
```

Run `make setup` to populate `.cursor/` with copies from `library/cursor/`. After editing rules/skills, run `make validate` then `make sync-local` to update the IDE config.

### Installing in your project

```bash
# Automated (syncs rules, hooks, references to all ~/redhat projects)
./sync-cursor.sh

# Manual (single project)
cp -R library/cursor/rules/ /path/to/project/.cursor/rules/
cp -R library/cursor/hooks/ /path/to/project/.cursor/hooks/
cp -R library/cursor/references/ /path/to/project/.cursor/references/
cp library/cursor/hooks.full.json /path/to/project/.cursor/hooks.json
mkdir -p /path/to/project/.harness/{evals,audits}
```

## Rules (`library/cursor/rules/`)

| Rule | Activation | What it does |
|------|-----------|--------------|
| `agent_behavior` | Always on | Communication style, change management |
| `autonomous_execution` | Always on | Act without asking, fix errors, pause on destructive ops |
| `code_standards` | Always on | Explicit > implicit, SRP, naming, DRY |
| `critical_thinking` | Always on | Analyze requests, challenge assumptions |
| `planning_discipline` | Always on | Structured task tracking, thread hygiene |
| `progress_tracking` | Always on | Breadcrumbs, TodoWrite for multi-file work |
| `prompt_coaching` | Scoped | Coach users toward effective prompts |
| `security` | Scoped | Input validation, secrets, supply chain |
| `verification` | Always on | Test/lint/build after every code change |
| `adversarial_harness` | `src/**,app/**,lib/**,...` | Planner/evaluator workflow for non-trivial features |
| `architecture` | `*.py, *.ts, *.tsx` | SOLID, dependency direction, pattern trade-offs |
| `python_ml` | `*.py, *.ipynb` | Type hints, pandas, ML conventions |
| `testing` | `**/test*.py` | Pytest conventions, contract testing |
| `research_standards` | `experiments/**` | Pre-registration, statistical rigor |
| `causal_rigor` | `experiments/**` | 5-test framework for non-circular findings |
| `design_principles` | Agent-loaded | Dieter Rams, BJ Fogg, Jony Ive design philosophy |

## Skills (`library/cursor/skills/`)

| Skill | What it does |
|-------|-------------|
| `adversarial-harness` | Multi-agent planner/builder/evaluator workflow |
| `code-review` | Multi-category review with severity model |
| `commit` | Conventional commits with pre-flight checks |
| `experiment-workflow` | 6-phase experiment lifecycle |
| `data-science-analysis` | Hypothesis generation, feature engineering |
| `architecture-audit` | DDD, Clean Architecture, Hexagonal compliance |
| `code-quality-audit` | SOLID, complexity, coupling analysis |
| `design-audit` | Accessibility, design tokens, visual hierarchy |
| `organization-audit` | File structure, module boundaries, cohesion |
| `iac-templates` | Infrastructure-as-Code template management |
| `project-scaffolding` | Multi-mode project structure generation |
| `info-architecture` | Information architecture patterns |
| `tech-writing` | Technical writing page patterns |

## Hooks (`library/cursor/hooks/`)

| Hook | Event | What it does |
|------|-------|-------------|
| `harness-context.sh` | `sessionStart` | Injects harness state into conversation |
| `harness-gate.sh` | `beforeSubmitPrompt` | Fast-path routing for complexity |
| (LLM prompt) | `beforeSubmitPrompt` | Classifies non-trivial work |
| `contract-gate.sh` | `preToolUse` (Write) | Blocks impl writes without a contract |
| `evaluator-guard.sh` | `preToolUse` (Write) | Sandboxes evaluator to harness paths |
| `dedup-server.sh` | `beforeShellExecution` | Prevents duplicate dev servers |
| `pre-commit-harness.sh` | `beforeShellExecution` | Requires commit approval |
| `verify-harness.sh` | `stop` | Blocks completion if contract unverified |
| `enforce-progress.sh` | `stop` | Enforces breadcrumbs + harness usage |
| `context-health.sh` | `stop` | Detects session fatigue signals |
| (LLM prompt) | `stop` | Checks harness compliance |
| `chain-evaluator.sh` | `subagentStop` | Routes between harness phases |
| `validate-hooks.sh` | (manual) | Validates hook configuration |

## Hook Profiles

Two profiles control which hooks are active:

| Profile | Use case | Active hooks |
|---------|----------|-------------|
| **lean** (default here) | Rules/skills development | dedup-server, enforce-progress (Tier 1), context-health |
| **full** | Real projects, dogfooding | All 11 scripts + 2 LLM prompt hooks |

```bash
scripts/hooks-profile.sh lean     # no harness enforcement
scripts/hooks-profile.sh full     # full enforcement
scripts/hooks-profile.sh status   # show current
```

## Harness Workflow (`.harness/`)

The adversarial harness is a structured build/verify cycle:

1. **Plan** — `/planner` decomposes work into spec + features
2. **Negotiate** — Builder proposes contract, evaluator challenges
3. **Build** — Implement one feature at a time
4. **Verify** — `/evaluator` tests against contract with evidence
5. **Commit** — Only after evaluator passes

State lives in `.harness/` (git-tracked):
- `state.json` — feature list with statuses
- `contract.json` — negotiated acceptance criteria
- `breadcrumbs.jsonl` — append-only decision trace
- `evals/` — evaluator reports (quality evidence)
- `audits/` — rubric audit results

## Eval Pipeline (`tests/eval/`)

Behavioral testing that verifies rules actually change agent behavior.

```bash
pip install -r tests/eval/requirements.txt
export CURSOR_API_KEY="cursor_..."
export OPENAI_API_KEY="sk-..."

python tests/eval/auto_capture.py --dry-run    # preview
python tests/eval/auto_capture.py              # capture responses
python tests/eval/run_eval.py                  # judge with hybrid evaluator
```

| Component | Purpose |
|-----------|---------|
| `dataset.yaml` | 87 test cases with prompts and rubrics |
| `auto_capture.py` | SDK-based capture with context injection |
| `hybrid_judge.py` | Structural checks (Tier 1) + LLM fallback (Tier 2) |
| `local_judge.py` | Orchestrates evaluation runs |

## Sync (`sync-cursor.sh`)

Distributes `library/cursor/` content to all projects under `~/redhat`:

```bash
./sync-cursor.sh              # interactive sync
./sync-cursor.sh --dry-run    # preview changes
./sync-cursor.sh --yes        # skip confirmation
```

**Per-project** (`.cursor/`): rules, references, hooks (scripts + full hooks.json)
**Global** (`~/.cursor/`): agents, skills

## Design Lineage

The harness implements specific patterns from Anthropic ("Build Agents That Run for Hours"), OpenAI, DeepMind, and Fowler's guides/sensors taxonomy. See [`DESIGN_LINEAGE.md`](DESIGN_LINEAGE.md) for the full mapping of concepts to repo artifacts.

## Authoring Standards

- [`RULES_STANDARD.md`](RULES_STANDARD.md) — how to write `.mdc` rules
- [`SKILLS_STANDARD.md`](SKILLS_STANDARD.md) — how to write `SKILL.md` skills
