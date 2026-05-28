# Evaluation Guide

How we test that the rules, skills, and harness actually work. The eval system has three tiers — each progressively more realistic, slower, and costlier.

## Quick Reference

```
make eval-fast              # Tier 1: seconds, no API keys
make eval-behavioral        # Tier 2: ~minutes, needs CURSOR_API_KEY + OPENAI_API_KEY
make eval-session --dry-run # Tier 3: preview scenarios
make eval-session           # Tier 3: ~5-10min per scenario, needs CURSOR_API_KEY
make eval-session-judge     # Tier 3: judge completed sessions
make eval-session-report    # Tier 3: aggregated report table
```

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                    Three-Tier Eval Pipeline                       │
├──────────────────┬───────────────────┬───────────────────────────┤
│    Tier 1        │     Tier 2        │        Tier 3             │
│  Fast Static     │  Behavioral       │    Session Scenarios      │
│                  │  Prompt Evals     │                           │
│  contract_lint   │  dataset.yaml     │  scenarios/*.yaml         │
│  harness_lint    │  auto_capture.py  │  session_runner.py        │
│  validate.py     │  run_eval.py      │  session_judge.py         │
│                  │                   │  session_report.py        │
├──────────────────┼───────────────────┼───────────────────────────┤
│  No API keys     │  Needs SDK +      │  Needs SDK, runs real     │
│  Runs in seconds │  judge model      │  agent in isolated        │
│  Local files     │  Single prompts   │  git worktree             │
│  only            │                   │                           │
└──────────────────┴───────────────────┴───────────────────────────┘
```

## Tier 1: Fast Static Checks

**What it tests**: Are harness state files well-formed? Are contracts binary-testable?

**How to run**: `make eval-fast`

**No API keys needed.** Runs in seconds against local `.harness/` files.

### Tools

| Script | What it checks |
|--------|----------------|
| `tests/validate.py` | Rules/skills structural compliance (frontmatter, token budget, required sections) |
| `tests/eval/contract_lint.py` | Contract structure, criteria quality, vague-language detection |
| `tests/eval/harness_lint.py` | Breadcrumb integrity, state.json consistency, cross-file coherence |

### When to run

- Before every commit (catches malformed harness state)
- In CI as the first gate
- After any harness-related code change

### What "pass" means

All checks return exit code 0. Any FAIL indicates a structural problem that must be fixed before the harness can work correctly.

## Tier 2: Behavioral Prompt Evals

**What it tests**: Does the agent follow our rules when given specific prompts?

**How to run**: `make eval-behavioral`

**Needs**: `CURSOR_API_KEY` for capture, `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` for judging.

### How it works

1. **Dataset** (`tests/eval/dataset.yaml`): ~50+ test cases, each with a prompt, target rules/skills, and a rubric with weighted criteria
2. **Capture** (`auto_capture.py`): Sends each prompt to the agent via Cursor SDK, saves the response
3. **Judge** (`run_eval.py`): An LLM judge scores each response against the rubric criteria
4. **Report** (`report.py`): Aggregates scores into a markdown report

### Dataset structure

```yaml
- id: agent_behavior_no_apologies
  targets: [agent_behavior]
  category: always_on_rule
  difficulty: easy
  prompt: "I think I messed up the database migration..."
  rubric:
    correctness:
      - criterion: "Investigates the issue directly"
        weight: 2
    behavioral:
      - criterion: "Does not apologize"
        weight: 3
    negative:
      - criterion: "Does NOT open with an apology"
        weight: 3
```

### What it measures

- **Rule compliance**: Does the agent follow `agent_behavior`, `code_standards`, etc.?
- **Skill activation**: When triggered, does the agent follow skill instructions?
- **Negotiation quality**: Are contracts binary-testable? Do edge cases make sense?
- **Anti-patterns**: Apologies, unsolicited summaries, vague outputs

### Limitations

Single prompt → single response. Cannot test multi-step workflows, file creation, or tool use. That's what Tier 3 is for.

## Tier 3: Session Scenario Evals

**What it tests**: Can the agent complete a realistic multi-step task while following the harness workflow?

**How to run**:

```bash
make eval-session              # Run all scenarios
make eval-session-judge        # Judge results (computational + structural)
make eval-session-judge-full   # Judge with LLM tier too
make eval-session-report       # Aggregated report
```

**Needs**: `CURSOR_API_KEY`. For LLM judging tier, also needs `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`.

### How it works

```
Scenario YAML
  → session_runner.py creates an isolated git worktree
  → library/cursor/ is copied into worktree's .cursor/
  → Agent receives the task prompts and works autonomously
  → Before teardown: git diff captured, changed files read, verify commands run
  → Session JSON saved to tests/eval/sessions/<model>/<scenario_id>.json
  → session_judge.py scores the session against the scenario's rubric
  → Judgment JSON saved to tests/eval/judgments/<model>/<scenario_id>.json
  → session_report.py produces summary.json + console table
```

### Isolation: the sandbox

Each scenario runs in a fresh `git worktree` created by `CaptureWorkspace` (in `tests/eval/sandbox.py`). This means:

- The agent sees a realistic repo structure (git history, file tree)
- But changes are isolated — nothing pollutes the main working directory
- `.cursor/` config is copied from `library/cursor/` (the source of truth), not from the local `.cursor/` copy
- `.harness/` is initialized clean so the agent starts fresh
- After the agent finishes, artifacts are collected before the worktree is destroyed

### Artifact capture

When the agent finishes, the runner captures:

| Artifact | What it contains |
|----------|------------------|
| `git_diff_stat` | Summary of changes (files changed, insertions, deletions) |
| `git_diff` | Full unified diff of all changes vs HEAD |
| `file_contents` | Full text of every changed/new file (up to 100KB per file, 512KB total) |
| `files` | List of all files in the workspace |
| `harness` | Contents of `.harness/state.json`, `contract.json`, `breadcrumbs.jsonl` |
| `validations` | Results of verify commands (exit code, stdout, stderr) |
| `transcript` | Full prompt/response exchange with the agent |

Files in `.git/`, `.cursor/`, `node_modules/`, `__pycache__/`, and similar are excluded from content capture.

### Scenario YAML format

```yaml
id: build_cli_tool
name: "Build a CLI file organizer"
difficulty: medium
estimated_duration: 5m
seed_project: null

initial_prompt: >
  Build a Python CLI tool that organizes files by extension...

follow_up_prompts:
  - "Add a --recursive flag"
  - "Commit the changes"

verify:
  - command: "python -m py_compile *.py"
    timeout_s: 10

post_hoc_rubric:
  harness_compliance:
    - "Agent created .harness/state.json with features"
    - "Contract negotiation occurred"
  artifact_quality:
    - "Main Python file exists with argparse CLI"
    - "Script handles --dry-run flag"
  behavioral:
    - "No apologies in transcript"
    - "Agent ran commands autonomously"
  negotiation_quality:
    - "Acceptance criteria are binary-testable"
```

Scenarios live in `tests/eval/scenarios/`. Each YAML file defines one scenario.

### Judging tiers

The judge (`session_judge.py`) evaluates each session at three levels:

| Tier | What it checks | How |
|------|---------------|-----|
| **Computational** | Harness compliance, contract quality | Deterministic checks on `artifacts.harness` |
| **Structural** | Artifact quality, behavioral patterns | Heuristic pattern matching on `file_contents`, `validations`, transcript |
| **LLM** | Negotiation quality, subjective criteria | LLM-as-judge with evidence-based scoring |

The structural tier now uses `file_contents` to verify that specific code patterns exist (e.g., "uses `argparse`", "handles `--dry-run`") and `validations` to check that tests pass or code compiles.

### Reporting

`session_report.py` reads all judgment files and produces:

1. **Console table**: per-scenario breakdown across 5 dimensions (harness, contract, artifact, behavioral, negotiation)
2. **`summary.json`**: structured data for CI/tooling

Dimensions are derived from the judgment results:

| Dimension | What it covers |
|-----------|---------------|
| harness | state.json, breadcrumbs, evaluator launched |
| contract | Acceptance criteria, edge cases, verification method |
| artifact | File existence, code patterns, test results |
| behavioral | No apologies, autonomous execution, progress tracking |
| negotiation | Criteria quality (LLM-judged) |

Run `make eval-session-report` to see the table.

## File Layout

```
tests/eval/
├── dataset.yaml              # Tier 2 test cases
├── contract_lint.py          # Tier 1: contract quality
├── harness_lint.py           # Tier 1: harness state consistency
├── auto_capture.py           # Tier 2: SDK-based prompt capture
├── run_eval.py               # Tier 2: LLM judge for single prompts
├── report.py                 # Tier 2: markdown report
├── sandbox.py                # Tier 3: isolated worktree manager
├── session_runner.py         # Tier 3: scenario execution
├── session_judge.py          # Tier 3: post-hoc judging
├── session_report.py         # Tier 3: aggregated reporting
├── harness_metrics.py        # Harness effectiveness dashboard
├── scenarios/                # Tier 3 scenario definitions
│   ├── build-cli-tool.yaml
│   └── refactor-module.yaml
├── sessions/                 # Tier 3 session outputs (gitignored)
│   └── <model>/<scenario>.json
├── judgments/                 # Tier 3 judgment outputs (gitignored)
│   └── <model>/<scenario>.json
└── summary.json              # Aggregated report (gitignored)
```

## Data Flow

```
library/cursor/  ──copy──→  .cursor/ (in temp worktree)
                                │
                          Agent works here
                                │
                          ┌─────▼──────────┐
                          │  Artifacts      │
                          │  • git diff     │
                          │  • file_contents│
                          │  • harness state│
                          │  • validations  │
                          └─────┬──────────┘
                                │
                     sessions/<model>/<id>.json
                                │
                     session_judge.py scores it
                                │
                     judgments/<model>/<id>.json
                                │
                     session_report.py aggregates
                                │
                        summary.json + console table
```

## Adding a New Scenario

1. Create a YAML file in `tests/eval/scenarios/`:

```yaml
id: my_new_scenario
name: "Description of the task"
difficulty: easy|medium|hard
estimated_duration: 5m
seed_project: null  # or path to template directory

initial_prompt: >
  The task prompt the agent will receive.

follow_up_prompts:
  - "Optional follow-up 1"

verify:
  - command: "python -m pytest tests/"
    timeout_s: 30

post_hoc_rubric:
  harness_compliance:
    - "What the agent should do with the harness"
  artifact_quality:
    - "What files/code should exist"
  behavioral:
    - "How the agent should behave"
  negotiation_quality:
    - "What contract quality looks like"
```

2. Run `make eval-session-dry` to verify it loads
3. Run `make eval-session` to execute
4. Run `make eval-session-judge` + `make eval-session-report` to see results

## CI Integration

Recommended pipeline:

```yaml
# Fast gate (every PR)
- run: make eval-fast

# Behavioral gate (nightly or on tag)
- run: make eval-behavioral

# Session eval (weekly or on release)
- run: make eval-session
- run: make eval-session-judge
- run: make eval-session-report
```

Tier 1 runs in seconds with no API keys — it should block every PR. Tier 2 and 3 need API keys and are better suited for scheduled runs.
