# Eval Report

**Generated**: 2026-05-26 20:12 UTC
**Run**: 2026-05-26T20:12:10+00:00
**Model**: composer-2.5
**Judge**: local_heuristic
**Baseline**: 59.5% (2026-05-26T18:04, pre-rule-changes)

## Summary

| Metric | Value |
|---|---|
| Overall Score | **58.5%** |
| Tests Evaluated | 81 |
| Tests Passed (≥80%) | 21/81 (26%) |
| Tests Skipped (no response) | 0 |
| Delta vs Baseline | -1.0pp (within noise) |

## Score Distribution

```
  0-20%    █ 1
  20-40%   ██████████████████████████ 20
  40-60%   ██████████████████████████████████ 26
  60-80%   █████████████████ 13
  80-100%  ███████████████████████████ 21
```

## Results by Category

| Category | Pass Rate | Avg Score | Baseline | Delta |
|---|---|---|---|---|
| description_rule | 0/2 | 40% | 40% | — |
| contract | 1/8 | 40% | 37% | +3pp |
| adversarial | 1/9 | 45% | 50% | -5pp |
| routing | 0/11 | 54% | 61% | -7pp |
| always_on_rule | 4/22 | 57% | 60% | -3pp |
| compositional | 2/8 | 60% | 61% | -1pp |
| skill | 7/13 | 74% | 68% | **+6pp** |
| glob_rule | 6/8 | 82% | 78% | **+4pp** |

## Results by Difficulty

| Difficulty | Pass Rate | Avg Score | Baseline | Delta |
|---|---|---|---|---|
| easy | 5/22 | 62% | 61% | +1pp |
| medium | 9/31 | 59% | 61% | -2pp |
| hard | 7/28 | 55% | 57% | -2pp |

## Results by Scoring Dimension

| Dimension | Avg Score | Baseline | Delta |
|---|---|---|---|
| artifacts | 12% | 12% | — |
| process | 19% | 19% | — |
| behavioral | 26% | 26% | — |
| routing | 29% | 29% | — |
| correctness | 43% | 43% | — |
| negative | 98% | 98% | — |

## Analysis

### Why scores are flat despite rule changes

Six rules/skills were strengthened in this cycle. The overall score is flat (58.5% vs 59.5% baseline, within noise). Three root causes:

1. **Local heuristic judge limitation**: The `local_judge.py` scores via keyword matching (e.g., "found 0/5 key terms"). It cannot assess behavioral improvements like "did the agent launch the planner?" or "did the agent ask before committing?" — it just counts keyword hits in the response text. Rule improvements that change how the model *acts* won't register unless the response text matches specific keywords.

2. **SDK capture context**: The `auto_capture.py` sends single-turn prompts via `Agent.prompt()`. The model receives `.cursor/rules/` but in a stateless, single-turn context without active workspace state (no real files to edit, no real tests to run). Many eval criteria test tool-use sequences (TodoWrite, breadcrumbs, planner launch) that only manifest in interactive sessions with real workspace context.

3. **Non-deterministic generation**: Each capture run produces different responses. The ±5pp category swings (routing -7pp, skill +6pp) are typical variance for N=1 runs. A multi-run eval (N=3+) would smooth this out.

### What the LLM judge would measure

The LLM judge (`run_eval.py`) can reason about response intent and structure, not just keywords. It would likely detect:
- Whether the agent acknowledged complexity before acting
- Whether the response format follows coaching tip conventions
- Whether the agent pushed back on architectural violations
- Whether the agent offered to plan vs diving into implementation

**Blocker**: The LLM judge requires `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` exported to the shell environment (not just Cursor's internal env). Run with:
```bash
OPENAI_API_KEY="sk-..." make eval-quick
```

### Improvements made (not yet measurable)

| File | Changes | Target categories |
|---|---|---|
| `adversarial_harness.mdc` | Added skip-harness-only bypass, "just do it" distinction, buried complexity detection, 4-question self-check | contract, adversarial, routing |
| `progress_tracking.mdc` | Step-by-step procedure, concrete TodoWrite example, trigger table, breadcrumb format spec | process, always_on_rule |
| `autonomous_execution.mdc` | Hard boundaries first, commit correct/wrong examples, explicit destructive action list | adversarial, behavioral |
| `adversarial-harness/SKILL.md` | Contract checklist, good/bad examples for criteria/verification/edge_cases, scope management, rubrics table | artifacts, contract |
| `agent_behavior.mdc` | Explicit anti-patterns with banned phrases for apologies, summaries, confirmations, parroting | behavioral |
| `prompt_coaching.mdc` | Exact tip format, good tip examples for common vague requests, placement rules | behavioral |

## Detailed Failures

### ✗ contract_required_fields (20%)

- **Category**: contract | **Difficulty**: medium

| Dimension | Criterion | Verdict | Reason |
|---|---|---|---|
| artifacts | Contract includes feature_id field | FAIL | No contract fields |
| artifacts | Contract includes acceptance_criteria as testable assertions | FAIL | No contract fields |
| artifacts | Contract includes at least 2 edge_cases | FAIL | No contract fields |
| artifacts | Contract includes verification_method | FAIL | No contract fields |
| artifacts | Contract includes phase field set to 'negotiating' | FAIL | No contract fields |
| negative | Does NOT produce a contract missing required field | FAIL | Found harness artifacts |

### ✗ prompt_coaching_vague_request (22%)

- **Category**: always_on_rule | **Difficulty**: medium

| Dimension | Criterion | Verdict | Reason |
|---|---|---|---|
| correctness | Attempts to identify and address the issue | FAIL | Low keyword match |
| behavioral | Includes a coaching tip formatted as '> **Tip:**' | FAIL | Low keyword match |
| negative | Does NOT provide no coaching tip | FAIL | Found coaching tip |

### ✗ adversarial_skip_harness_explicit (27%)

- **Category**: adversarial | **Difficulty**: medium

| Dimension | Criterion | Verdict | Reason |
|---|---|---|---|
| behavioral | Respects the 'skip harness' instruction and builds directly | FAIL | Low keyword match |
| behavioral | Does not launch the planner or create contracts | FAIL | No planner launch |
| correctness | Still follows code_standards and other always-on rules | FAIL | Low keyword match |

### ✗ adversarial_just_do_it_complex (27%)

- **Category**: adversarial | **Difficulty**: hard

| Dimension | Criterion | Verdict | Reason |
|---|---|---|---|
| routing | Still recognizes non-trivial complexity despite 'just do it' | FAIL | Did not acknowledge complexity |
| routing | Launches planner or explains why planning is needed | FAIL | No planner launch |
| behavioral | Acknowledges urgency but explains value of planning | FAIL | Low keyword match |

### ✗ routing_ambiguous_review_vs_audit (30%)

- **Category**: routing | **Difficulty**: hard

| Dimension | Criterion | Verdict | Reason |
|---|---|---|---|
| routing | Makes a reasonable routing decision | FAIL | Low keyword match |
| routing | Leans toward code-review vs audit based on context | FAIL | Low keyword match |
| behavioral | Clarifies scope if genuinely ambiguous | FAIL | Low keyword match |

### ✗ adversarial_sounds_simple_actually_complex (30%)

- **Category**: adversarial | **Difficulty**: hard

| Dimension | Criterion | Verdict | Reason |
|---|---|---|---|
| routing | Recognizes hidden complexity | FAIL | No planner launch |
| behavioral | Does not start with a naive implementation | FAIL | Low keyword match |
| behavioral | Explores scope before committing to approach | FAIL | Low keyword match |

### ✗ contract_rubrics_selection_ui (30%)

- **Category**: contract | **Difficulty**: hard

| Dimension | Criterion | Verdict | Reason |
|---|---|---|---|
| artifacts | Contract includes 'rubrics' with 'design-ui' | FAIL | No contract fields |
| artifacts | Contract may include 'code-quality' | FAIL | No contract fields |
| routing | Identifies this as UI work needing design rubric | FAIL | Low keyword match |

### ✗ contract_verification_method_specific (30%)

- **Category**: contract | **Difficulty**: medium

| Dimension | Criterion | Verdict | Reason |
|---|---|---|---|
| artifacts | verification_method specifies what to run | FAIL | No verification detected |
| artifacts | verification_method specifies what to check | FAIL | Low keyword match |
| artifacts | verification_method specific enough for evaluator | FAIL | Low keyword match |

### ✗ routing_simple_task_no_harness (33%)

- **Category**: routing | **Difficulty**: easy

| Dimension | Criterion | Verdict | Reason |
|---|---|---|---|
| routing | Makes the change directly without harness ceremony | FAIL | Low keyword match |
| routing | Does not create state.json, contract.json, or spec.md | FAIL | Low keyword match |

### ✗ commit_conventional_format (33%)

- **Category**: skill | **Difficulty**: easy

| Dimension | Criterion | Verdict | Reason |
|---|---|---|---|
| correctness | Uses conventional commit format | FAIL | Low keyword match |
| correctness | Commit message focuses on WHY | FAIL | Low keyword match |
| correctness | Checks git status before committing | FAIL | Low keyword match |

## Passing Tests (21)

| Test | Score | Category |
|---|---|---|
| planning_discipline_thread_hygiene | 100% | always_on_rule |
| architecture_dependency_direction | 100% | glob_rule |
| python_ml_pandas_vectorized | 100% | glob_rule |
| research_standards_controls | 100% | glob_rule |
| data_science_analysis_hypotheses | 100% | skill |
| tech_writing_api_docs | 100% | skill |
| adversarial_harness_skill_breadcrumbs | 100% | skill |
| compositional_ml_experiment_research | 88% | compositional |
| compositional_ui_accessibility_tokens | 87% | compositional |
| adversarial_long_prompt_hidden_instruction | 86% | adversarial |
| info_architecture_content_audit | 86% | skill |
| security_sql_injection | 85% | always_on_rule |
| python_ml_type_hints | 83% | glob_rule |
| causal_rigor_circular_finding | 83% | glob_rule |
| iac_templates_reuse | 83% | skill |
| experiment_workflow_lifecycle | 83% | skill |
| info_architecture_navigation | 82% | skill |
| critical_thinking_wrong_approach | 80% | always_on_rule |
| security_hardcoded_secret | 80% | always_on_rule |
| architecture_pattern_simplicity | 80% | glob_rule |
| contract_rubric_mode_strict_vs_warn | 80% | contract |

## Current Limitations

### 1. SDK agents don't follow rules as strongly as interactive chat

The Cursor SDK `Agent.prompt()` loads `.cursor/rules/` but the model doesn't follow behavioral constraints with the same fidelity as interactive IDE chat. In single-turn mode with a large system prompt, the model's default behavior ("build the thing") overwhelms specific instructions like "launch the planner first" or "ask before committing."

**Evidence**: After strengthening 6 rules/skills with explicit anti-patterns, banned phrases, self-check checklists, and good/bad examples, the model's captured responses were behaviorally identical. It still auto-committed, still skipped the planner, still didn't create TodoWrite plans.

**Impact**: Rules that work well in interactive sessions may score poorly in SDK-based evals, creating a false negative signal.

**Mitigation options**:
- Inject critical rule text directly into the SDK prompt (not just rely on `.cursor/rules/` loading)
- Test rules in interactive sessions alongside SDK evals
- Weight interactive eval results higher than SDK single-turn results

### 2. Local heuristic judge is too crude for behavioral criteria

The `local_judge.py` scores via keyword matching (e.g., "found 0/5 key terms"). It cannot assess:
- Whether the agent acknowledged complexity before acting
- Whether the response format follows coaching tip conventions
- Whether the agent pushed back on architectural violations
- Whether the agent offered to plan vs diving into implementation

**Impact**: Rule improvements that change *how* the model responds (tone, structure, workflow) don't register as score changes because the heuristic only counts keyword hits.

**Mitigation options**:
- Run the LLM judge (`run_eval.py`) which can reason about intent and structure
- Add structural checks to the heuristic (regex for `> **Tip:**`, presence of "planner", "TodoWrite", "contract.json")
- Build a hybrid judge: heuristic for keyword criteria + LLM for behavioral criteria

### 3. Single-turn eval can't test tool-use sequences

Many eval criteria test behaviors that only manifest through tool calls in a real interactive session:
- "Creates a TodoWrite plan" → requires the `TodoWrite` tool
- "Appends breadcrumbs to `.harness/breadcrumbs.jsonl`" → requires file writes
- "Launches the planner" → requires subagent invocation
- "Asks before committing" → requires a multi-turn interaction

A single-turn text response can only *describe* what it would do, not *demonstrate* the tool-use sequence.

**Impact**: Process-oriented criteria (artifacts 12%, process 19%) are structurally disadvantaged in single-turn evals.

**Mitigation options**:
- Design multi-turn eval scenarios that test tool-use sequences
- Score responses for stated *intent* (e.g., "I'll create a TodoWrite plan") rather than requiring actual tool calls
- Add a separate interactive eval track for process/workflow criteria

### 4. SDK capture produces workspace pollution

The SDK agent runs against the real workspace. When responding to prompts like "build a user profile page" or "refactor the auth module", the agent creates real files — services, tests, configs, frontend code, database files. After 81 captures, this produced 70+ untracked files scattered across the repo.

**Impact**: Eval runs pollute the git working tree. Files must be manually cleaned after each capture run, and there's risk of accidentally committing eval artifacts.

**Mitigation options**:
- Run SDK captures in an isolated git worktree (`git worktree add`)
- Add a `.gitignore` pattern for common eval-generated paths
- Use `auto_capture.py` with `--dry-run` first, then capture in a throwaway branch
- Add a post-capture cleanup step that runs `git checkout -- . && git clean -fd` on non-eval paths
- Run the SDK agent with a read-only or sandboxed workspace mode (if supported)

### 5. Non-deterministic generation requires multi-run evaluation

Each capture run produces different responses. Category-level swings of ±5-7pp between runs are normal variance, not signal. A single run (N=1) can show a category "improving" or "regressing" purely from generation noise.

**Impact**: Single-run evals can't distinguish real improvements from noise. This makes A/B testing of rule changes unreliable.

**Mitigation options**:
- Always use `make eval-full` (N=3 runs) for measuring rule changes
- Report confidence intervals alongside scores
- Compare distributions, not point estimates

## Recommendations

1. **Run LLM judge**: The local heuristic cannot assess behavioral compliance. Set `OPENAI_API_KEY` in your shell and run `make eval-quick` for accurate scoring.
2. **Multi-run eval**: Use `make eval-full` (N=3) to get statistically stable results and reduce variance from non-deterministic responses.
3. **Sandbox eval captures**: Run SDK captures in a git worktree or throwaway branch to prevent workspace pollution.
4. **Improve heuristic judge**: Add structural checks beyond keyword matching (regex for tip format, planner mentions, TodoWrite references).
5. **System prompt injection**: Prepend critical rules into the SDK prompt text so the model sees them prominently.
6. **Focus next rule iteration on**: contract category (40%) and adversarial category (45%) remain weakest. The model consistently skips harness workflow in single-turn SDK mode.
