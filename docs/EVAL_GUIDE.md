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

# Harness maintenance
make harness-prune          # Preview stale state to prune (dry-run)
python .cursor/hooks/prune-harness.py --apply     # Apply: archive old questions + breadcrumbs
python .cursor/hooks/context-package.py           # JSON context package for current task
python .cursor/hooks/context-package.py --format markdown  # Markdown for agent prompts
```

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                    Two-Tier Eval Pipeline                         │
├──────────────────────────────┬───────────────────────────────────┤
│         Tier 1               │         Tier 3                    │
│       Fast Static            │     Session Scenarios             │
│                              │                                   │
│  contract_lint.py            │  scenarios/*.yaml (31 scenarios)  │
│  harness_lint.py             │  session_runner.py                │
│  validate.py                 │  session_judge.py                 │
│                              │  session_report.py                │
│                              │  sandbox.py                       │
├──────────────────────────────┼───────────────────────────────────┤
│  No API keys                 │  Needs CURSOR_API_KEY             │
│  Runs in seconds             │  ~30 min for full suite           │
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
| `scripts/acam-score.py` | Static ACAM dimension scoring (configuration/workflows/multi_agent/interaction levels) |

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
| `transcript[].conversation` | Full agent trace per turn: tool calls (name, args, result), thinking blocks, shell commands |

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

Scenarios live in `tests/eval/scenarios/` (31 scenarios: 30 standard + 1 long). Each YAML file defines one scenario.

### Judging tiers

The judge (`session_judge.py`) evaluates each session at three levels:

| Tier | What it checks | How |
|------|---------------|-----|
| **Computational** | Harness compliance, contract quality | Deterministic checks on `artifacts.harness` |
| **Structural** | Artifact quality, behavioral patterns | Heuristic pattern matching on `file_contents`, `validations`, transcript |
| **LLM** | Negotiation quality, subjective criteria | LLM-as-judge with evidence-based scoring |

The structural tier uses `file_contents` to verify that specific code patterns exist (e.g., "uses `argparse`", "handles `--dry-run`"), `validations` to check that tests pass or code compiles, and **conversation traces** to verify tool usage (e.g., did the agent call TodoWrite, run Shell commands for verification, use ReadLints). Trace-aware checks fall back to heuristic pattern matching for sessions captured before trace instrumentation.

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
├── scenarios/                # 28 core scenario YAML definitions
│   ├── routing-*.yaml        # 2 routing scenarios
│   ├── contract-*.yaml       # 4 contract quality scenarios
│   ├── protocol-*.yaml       # 14 protocol lifecycle scenarios
│   ├── adversarial-*.yaml    # 3 adversarial scenarios
│   ├── behavioral-*.yaml     # 4 behavioral scenarios
│   └── long/                 # 1 long-running scenario (10-15 min)
│       └── long-full-harness-cycle.yaml
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

2. Set `harness_level` appropriately:
   - `full` (default) — all harness checks run (state.json, breadcrumbs, contract, evaluator)
   - `light` — skips contract/evaluator checks; use for behavioral/routing scenarios
   - `none` — skips ALL harness checks; use for skill-activation and non-harness scenarios

3. Run `make eval-session-dry` to verify it loads
4. Run `make eval-session` to execute
5. Run `make eval-session-judge` + `make eval-session-report` to see results

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

Three workflows are implemented in `.github/workflows/`:

| Workflow | Trigger | What it runs |
|----------|---------|-------------|
| `eval-fast.yml` | Every PR + push to `main` | `pytest tests/` + `make eval-fast` (no secrets, <2 min) |
| `eval-regression-pr.yml` | PR to `main` (paths: tests/eval, library, Makefile) | PR tier: 11 protocol scenarios (~90–120 min), regression check |
| `eval-regression-nightly.yml` | Cron 06:00 UTC + `workflow_dispatch` | Nightly tier: 31 scenarios, structural tier judge |

### Minimum scenario set (PR tier)

The **11 protocol scenarios** in `tests/eval/fixtures/ci_suites.json` (`ci_tier: pr`) are the canonical minimum set that protects the five-problem harness core:

| Scenario | Problem it protects |
|----------|-------------------|
| `protocol_fresh_repo_bootstrap` | Cold-start planner routing |
| `protocol_planner_delegation` | Scope → state.json (problem 1) |
| `protocol_planner_no_relaunch` | Planner not re-invoked mid-build |
| `protocol_chore_no_contract` | Simple tasks bypass harness |
| `protocol_spike_bypasses_gate` | Spike tasks bypass harness |
| `protocol_state_task_progression` | Status lifecycle (problem 2–3) |
| `protocol_breadcrumbs_format` | Audit trail (problem 3) |
| `protocol_no_post_hoc_contracts` | No retroactive contracts |
| `protocol_hook_gate_compliance` | Contract gate (problem 5) |
| `protocol_evaluator_launch` | Adversarial QA (problem 5) |
| `protocol_pre_commit_gate_loop` | Commit gate (problem 5) |

Any scenario set that covers all 5 problems is sufficient for a consumer project. Target: 12–15 scenarios maximum (adding back `protocol_replan_mid_build`, `protocol_eval_fail_retest`, `protocol_contract_gate_denied_recovery` from the nightly-only list covers recovery paths).

### Nightly-only scenarios (probabilistic LLM behavior)

Some scenarios test prompt-instruction compliance rather than deterministic harness mechanics. These run **nightly only** — a flaky PR gate trains teams to ignore red CI.

| Scenario | What it tests | Why nightly-only |
|----------|---------------|-----------------|
| `protocol_anti_vacuity_reject` | Evaluator rejects a `feat-` contract where every AC is file-interrogation only (vacuous feature detection) | Anti-vacuity rule is a prompt instruction in `evaluator.md` — LLM compliance is probabilistic; single-run PR gates would be flaky |

Golden fixtures for `protocol_anti_vacuity_reject` live at `tests/eval/fixtures/anti-vacuity-reject/`. Run `validate_verify_logic.py` in that directory to unit-test the scenario's verify logic without a live session.

### Baseline refresh policy

`tests/eval/fixtures/eval_baseline.json` is the regression gate. Rules:

1. **Who can update**: maintainers only (enforced via `CODEOWNERS`)
2. **How to update**: run `python tests/eval/eval_regression_check.py --update-baseline --run-dir tests/eval_results/<latest> --tier pr` on a green local run; commit the updated file with a PR labeled `baseline-refresh`
3. **When to update**: after a legitimate score improvement (e.g., new rule improves a scenario), not to mask regressions
4. **Null baselines**: initial values are `null` — CI skips regression check until the first real run seeds real values
5. **Review**: `baseline-refresh` PRs require maintainer approval and a comment explaining why scores changed

```bash
# Seed baseline after first green CI run:
python tests/eval/eval_regression_check.py --update-baseline --run-dir tests/eval_results/<latest> --tier pr
git add tests/eval/fixtures/eval_baseline.json
git commit -m "chore: seed PR tier regression baseline"
```

---

## Measurement Cadence Runbook

When to run each eval tier, how to capture a dated ACAM snapshot, how to interpret baselines, and how to compare measurements over time.

### Cadence

| When | Command | What it covers |
|------|---------|----------------|
| Every PR / daily | `make eval-fast` | Static lints (contract, harness, ACAM score) — no API key required |
| On PR merge to `main` | `make eval-ci-pr` | 11 protocol scenarios + regression check vs `eval_baseline.json` |
| Weekly / nightly | `make eval-ci-nightly` | 31 scenarios + ACAM dimension rollup + baseline comparison |

Run `make eval-fast` as the minimum check before every commit. The full session tiers require `CURSOR_API_KEY`.

### Snapshot Capture

A snapshot is a dated record of static ACAM scores plus any available session scores. Take one at least weekly (or after any significant rule/skill change) to enable trend comparison.

1. Run `make eval-fast` to confirm the repo is structurally clean (contract lint, harness lint, ACAM score).
2. Save the dated ACAM scorecard: `python scripts/acam-score.py > .harness/snapshots/acam-$(date +%Y-%m-%d).json`
3. If session eval results exist from a recent run, save the summary: `cp tests/eval_results/$(ls -t tests/eval_results/ | head -1)/summary.json .harness/snapshots/session-summary-$(date +%Y-%m-%d).json`
4. Commit the snapshot: `git add .harness/snapshots/ && git commit -m "chore: ACAM snapshot $(date +%Y-%m-%d)"`

Snapshots live in `.harness/snapshots/` (create the directory if absent). Commit them — they are the historical record.

**When `CURSOR_API_KEY` is unavailable**: a static-only snapshot (`make eval-fast` + `python scripts/acam-score.py`) is valid and still produces a comparable ACAM scorecard without the session tier. Note in the commit message: `chore: ACAM static snapshot <date> (no session tier — API key unavailable)`.

### Interpreting `behavioral_baseline.json`

`tests/eval/fixtures/behavioral_baseline.json` lists criteria-level expectations for behavioral scenarios. Each entry has three fields:

```json
{
  "scenario_id": "behavioral_context_health_stale_thread",
  "criterion": "Agent wrote a handoff breadcrumb summarizing current state and next steps",
  "expected_bool": false
}
```

**`expected_bool: false`** marks a **known failure** — a behavioral gap accepted at baseline-seed time. It means the current model does not reliably satisfy this criterion, and that gap is acknowledged rather than hidden. These entries do **not** trigger a CI failure and are not regressions.

**`expected_bool: true`** marks a required behavior. If the agent fails this criterion in a future eval run, it is flagged as a regression.

To add a new known failure: append an entry with `expected_bool: false` and open a PR with a `baseline-refresh` label. The PR description must explain why this behavioral gap is accepted (e.g., model limitation, out-of-scope for current harness version).

### Interpreting `eval_baseline.json`

`tests/eval/fixtures/eval_baseline.json` records aggregate scores per tier:

```json
{
  "pr":      { "aggregate_score": 0.86, "scenarios": { "protocol_breadcrumbs_format": { "score": 0.86 }, ... } },
  "nightly": { "aggregate_score": null, "scenarios": {} }
}
```

**`aggregate_score: null`** (unseeded) means the tier has never produced a green CI run. The regression check exits 0 with a warning (`unseeded baseline — skipping regression gate`) rather than failing hard. This is intentional: a null baseline is not a failure, it is a signal to seed it.

Seed after the first green CI run:

```bash
python tests/eval/eval_regression_check.py --update-baseline --run-dir tests/eval_results/<latest> --tier pr
git add tests/eval/fixtures/eval_baseline.json
git commit -m "chore: seed PR tier regression baseline"
```

### Trend Comparison

To compare ACAM scores across two dated snapshots:

```bash
# Diff raw ACAM scorecards
diff .harness/snapshots/acam-2026-06-01.json .harness/snapshots/acam-2026-06-15.json

# Compare per-ACAM-dimension session rates across two session summaries
python - <<'EOF'
import json
a = json.load(open(".harness/snapshots/session-summary-2026-06-01.json"))
b = json.load(open(".harness/snapshots/session-summary-2026-06-15.json"))
for dim in ["configuration", "workflows", "multi_agent", "interaction"]:
    ra = a.get("acam_dimensions", {}).get(dim, {}).get("rate")
    rb = b.get("acam_dimensions", {}).get(dim, {}).get("rate")
    delta = f"{(rb - ra):+.2f}" if ra is not None and rb is not None else "n/a"
    print(f"{dim:20}  {str(ra):6} → {str(rb):6}  delta={delta}")
EOF
```

**Noise warnings**: snapshots more than ~30 days apart, or captured across a major rule change or model version upgrade, may show score differences unrelated to harness improvements. Prefer comparing snapshots from the same model version. After a model version change, re-seed `eval_baseline.json` from a fresh green run before interpreting deltas as signal.

### Full Measurement Pass

For a complete static measurement pass (no API key required, runs in seconds):

```bash
make eval-fast
```

This runs in sequence: `tests/validate.py` → `tests/eval/contract_lint.py` → `tests/eval/harness_lint.py` → `scripts/acam-score.py`. All must exit 0.

For the full pipeline including session scenarios (requires `CURSOR_API_KEY`):

```bash
make eval-ci-nightly   # 31 scenarios + ACAM dimension rollup + regression check
```

To run only the PR-tier scenarios (faster, ~90 min):

```bash
make eval-ci-pr        # 11 protocol scenarios + regression check
```
