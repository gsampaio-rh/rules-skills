# Evaluation Guide

How we test that the rules, skills, and harness actually work.

## Quick Reference

```
make eval-fast              # Tier 1: seconds, no API keys
make eval-session-dry       # Tier 3: preview scenario plan
make eval-session           # Tier 3: ~1min per scenario, needs CURSOR_API_KEY
make eval-session-judge     # Tier 3: judge completed sessions
make eval-session-report    # Tier 3: aggregated report table
make eval                   # Both: Tier 1 + Tier 3

make eval-session-long      # Long scenarios (~10-15 min each)
make eval-session-long-dry  # Preview long scenario plan
make eval-session-long-judge # Judge long scenario results
```

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                    Two-Tier Eval Pipeline                         │
├──────────────────────────────┬───────────────────────────────────┤
│         Tier 1               │         Tier 3                    │
│       Fast Static            │     Session Scenarios             │
│                              │                                   │
│  contract_lint.py            │  scenarios/*.yaml (27 scenarios)  │
│  harness_lint.py             │  session_runner.py                │
│  validate.py                 │  session_judge.py                 │
│                              │  session_report.py                │
│                              │  sandbox.py                       │
├──────────────────────────────┼───────────────────────────────────┤
│  No API keys                 │  Needs CURSOR_API_KEY             │
│  Runs in seconds             │  ~20 min for full suite           │
│  Checks local .harness/      │  Runs real agent in isolated      │
│  files are well-formed       │  temp git repo via SDK bridge     │
└──────────────────────────────┴───────────────────────────────────┘
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

## Tier 3: Session Scenario Evals

**What it tests**: Can the agent complete a realistic multi-step task while following the harness workflow?

**How to run**:

```bash
make eval-session              # Run all scenarios
make eval-session-judge        # Judge results (computational + structural)
make eval-session-judge-full   # Judge with LLM tier too
make eval-session-report       # Aggregated report
```

**Needs**: `CURSOR_API_KEY`. The LLM judging tier uses the same `CURSOR_API_KEY` via `cursor_sdk`.

### How it works

```
Scenario YAML
  → session_runner.py creates an isolated git worktree
  → library/cursor/ is copied into worktree's .cursor/
  → Agent receives the task prompts and works autonomously
  → Before teardown: git diff captured, changed files read, verify commands run
  → Session JSON saved to tests/eval_results/<timestamp>/sessions/<model>/<scenario_id>.json
  → session_judge.py scores the session against the scenario's rubric
  → Judgment JSON saved to tests/eval_results/<timestamp>/judgments/<model>/<scenario_id>.json
  → session_report.py produces summary.json + console table
```

### Isolation: the sandbox

Each scenario runs in a fresh temp directory via `CaptureWorkspace` (in `tests/eval/sandbox.py`) + `CursorClient.launch_bridge()`. This means:

- A fresh `git init` temp repo is created per scenario
- `seed_files` from the YAML are written before the agent starts
- `.cursor/` config is copied from `library/cursor/` (rules, skills, agents)
- The SDK bridge runs against this temp workspace — fully isolated from the main repo
- After the agent finishes, artifacts are collected before the temp dir is destroyed
- The base SHA is captured after seeding, so diffs show only agent-produced changes

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
id: routing_complex_activate
name: "Complex feature — harness MUST activate"
difficulty: hard
estimated_duration: 8m

seed_files:
  app.py: |
    from flask import Flask
    app = Flask(__name__)
    # ... starter code the agent builds upon
  requirements.txt: |
    flask==3.0.0

initial_prompt: >
  Build a REST API with user authentication (JWT), rate limiting, and logging.

follow_up_prompts:
  - "Commit the changes"

verify:
  - command: "test -f .harness/state.json && echo PASS || echo FAIL"
    timeout_s: 5
  - command: "test -f .harness/contract.json && echo PASS || echo FAIL"
    timeout_s: 5

post_hoc_rubric:
  harness_compliance:
    - "Agent created .harness/state.json with tasks"
    - "Contract negotiation occurred"
  artifact_quality:
    - "JWT auth implementation exists"
    - "Rate limiting logic present"
  behavioral:
    - "No apologies in transcript"
    - "Agent ran commands autonomously"
  negotiation_quality:
    - "Acceptance criteria are binary-testable"
```

Scenarios live in `tests/eval/scenarios/` (27 scenarios). Each YAML file defines one scenario.

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

## Long Scenarios (~10-15 min each)

Standard scenarios test 2-8 minute tasks. Long scenarios test whether the agent can sustain coherent work over 10-15 minutes across multiple phases (plan, negotiate, build, evaluate, iterate, recover from errors).

### How to run

```bash
make eval-session-long                                    # Run all long scenarios (~35 min)
make eval-session-long-judge                              # Judge results
```

To run a single long scenario, use the runner directly:

```bash
python tests/eval/session_runner.py --long --scenario long_full_harness_cycle
```

Or directly:

```bash
python tests/eval/session_runner.py --long                # All long scenarios
python tests/eval/session_runner.py --long --no-timeout   # No timeout cap
python tests/eval/session_runner.py --long --list         # List available
```

### What they test

Each long scenario exercises:

1. **Full harness cycle** — agent must plan, negotiate a contract, build, and get evaluated
2. **Multi-feature** — at least 2 features in sequence (tests coherence over time)
3. **Deliberate errors** — seeded bugs or incomplete requirements that force iteration

### Scenarios

| Scenario | Duration | What it tests |
|----------|----------|---------------|
| `long-full-harness-cycle` | ~10 min | CLI with plugin system, 2 features, full contract lifecycle |
| `long-multi-feature-coherence` | ~12 min | REST API with 4 incremental features, coherence across features |
| `long-resilience-recovery` | ~12 min | Seeded bugs → fix → then add feature with harness |

### Additional judge checks

Long scenarios add checks beyond the standard rubric:

| Check | What it verifies |
|-------|-----------------|
| **Coherence** | Later features don't break earlier ones |
| **Breadcrumb density** | Enough breadcrumbs across the session (not just 1-2) |
| **Multi-contract** | Each feature had its own contract negotiation cycle |
| **Recovery** | Agent detects and fixes issues without user prompting (resilience scenario) |

### YAML format additions

Long scenarios use the standard YAML format plus:

```yaml
timeout_s: 900       # Per-scenario timeout (default for long: 15 min)
tier: long           # Marker for documentation/filtering

post_hoc_rubric:
  long_scenario:     # Additional long-specific checks
    coherence:
      - "Second feature integrates with first"
    breadcrumb_density:
      min_entries: 4
      description: "At least 4 breadcrumbs across session"
    multi_contract:
      - "Each feature had its own contract cycle"
    recovery:         # Only for resilience scenarios
      - "Agent detected errors before being told"
```

## File Layout

```
tests/eval/
├── contract_lint.py          # Tier 1: contract quality
├── harness_lint.py           # Tier 1: harness state consistency
├── sandbox.py                # Tier 3: isolated temp repo manager
├── session_runner.py         # Tier 3: scenario execution via SDK bridge
├── session_judge.py          # Tier 3: post-hoc judging (computational + structural + LLM)
├── session_report.py         # Tier 3: aggregated reporting
├── harness_metrics.py        # Harness effectiveness dashboard
├── scenarios/                # 27 standard scenario YAML definitions
│   ├── routing-*.yaml        # 6 routing scenarios
│   ├── contract-*.yaml       # 5 contract quality scenarios
│   ├── protocol-*.yaml       # 3 protocol lifecycle scenarios
│   ├── adversarial-*.yaml    # 4 adversarial scenarios
│   ├── behavioral-*.yaml     # 5 behavioral scenarios
│   ├── skill-*.yaml          # 4 skill activation scenarios
│   └── long/                 # 3 long-running scenarios (10-15 min each)
│       ├── long-full-harness-cycle.yaml
│       ├── long-multi-feature-coherence.yaml
│       └── long-resilience-recovery.yaml

tests/eval_results/           # Output (gitignored)
└── <timestamp>/
    ├── sessions/<model>/<scenario>.json
    ├── judgments/<model>/<scenario>.json
    └── summary.json
```

## Data Flow

```
Scenario YAML (seed_files, prompts, verify, rubric)
        │
        ▼
sandbox.py: git init temp dir, write seed_files, copy .cursor/
        │
        ▼
session_runner.py: CursorClient.launch_bridge(workspace=tmp)
        │                    → agent.send(initial_prompt)
        │                    → agent.send(follow_ups...)
        ▼
Artifacts collected: git diff, file_contents, .harness/ state, verify commands
        │
        ▼
tests/eval_results/<ts>/sessions/<model>/<id>.json
        │
        ▼
session_judge.py: computational + structural + LLM scoring
        │
        ▼
tests/eval_results/<ts>/judgments/<model>/<id>.json
        │
        ▼
session_report.py: console table + summary.json
```

## Adding a New Scenario

1. Create a YAML file in `tests/eval/scenarios/`:

```yaml
id: my_new_scenario
name: "Description of the task"
difficulty: easy|medium|hard
estimated_duration: 5m

seed_files:
  main.py: |
    # starter code the agent will work with

initial_prompt: >
  The task prompt the agent will receive.

follow_up_prompts:
  - "Optional follow-up 1"

verify:
  - command: "test -f .harness/contract.json && echo PASS || echo FAIL"
    timeout_s: 5

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

## Known Limitations

### SDK bridge hook and skill support

When the agent runs via `CursorClient.launch_bridge()`:

- **Hooks fire**: `contract-gate.sh` (preToolUse), `verify-harness.sh` (stop), `harness-context.sh` (sessionStart), `enforce-progress.sh` (stop), and `context-health.sh` (stop) all execute in SDK bridge sessions. The sandbox copies `.cursor/hooks.json` and hook scripts into the workspace, and the bridge loads them from `local.cwd`.
- **preToolUse contract-gate blocks writes**: When `state.json` exists without `contract.json`, the agent cannot write implementation files — it must create the contract first. This is deterministic enforcement.
- **Skills are not auto-routed**: The IDE's skill activation system does not run. The agent has `.cursor/` in its workspace but doesn't proactively read skill files unless its system prompt references them.
- **Subagents (`/planner`, `/evaluator`) are not available**: These are IDE features that don't exist in the SDK bridge. The agent simulates the evaluator role internally.

**What works in the bridge:**
- Rules in `.cursor/rules/` are loaded (always-on rules are injected)
- Hooks fire and enforce the harness protocol (contract gate, verification gate, progress tracking)
- `sessionStart` injects harness context (current feature, contract status, recent breadcrumbs)
- Pre-seeded `.harness/` state IS detected and hooks respond to it
- Behavioral compliance (no apologies, autonomous execution) works
- The agent CAN read skill files if asked

### Implications for eval design

The eval now measures **enforced protocol compliance** — hooks block bad behavior and force the agent to follow the contract workflow:

| What we CAN test | What we CANNOT test (yet) |
|-----------------|--------------------------|
| Agent follows rules (behavioral) | Skill auto-routing from keywords |
| Hook-enforced contract gate | /planner subagent launch |
| Hook-enforced verification gate | /evaluator as a separate subagent |
| Agent resumes existing harness state | Multi-round negotiation with real evaluator |
| Agent respects "skip harness" | |
| Agent writes working code | |
| Negative cases (no harness when simple) | |

### Future improvements

1. **Pre-seed more state**: Scenarios like `routing_resume_existing` work well because they pre-seed `.harness/`. More scenarios could pre-seed partial state to test mid-workflow behavior.
2. **IDE-mode testing**: Run evals through the actual IDE (not SDK bridge) to test skill routing and real subagent launch — requires different infrastructure.

## CI Integration

Recommended pipeline:

```yaml
# Fast gate (every PR)
- run: make eval-fast

# Session eval (nightly or on release)
- run: make eval-session
- run: make eval-session-judge
- run: make eval-session-report
```

Tier 1 runs in seconds with no API keys — it should block every PR. Tier 3 needs `CURSOR_API_KEY` and takes ~25 min for the full 27-scenario suite.
