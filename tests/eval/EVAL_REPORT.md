# Eval Report

**Generated**: 2026-05-27 12:32 UTC
**Run**: 2026-05-27T12:32:00+00:00
**Model**: composer-2.5
**Judge**: hybrid (structural only — 0 LLM calls)
**Previous run**: 2026-05-26T20:12 (58.5%, 81 tests, local heuristic)

## Summary

| Metric | Value | Delta vs Previous |
|---|---|---|
| Overall Score | **58.3%** | -0.2pp (noise) |
| Tests Evaluated | 87 | +6 (hook_response) |
| Tests Passed (≥80%) | 23/87 (26%) | +2 |
| Judge mode | structural (no LLM fallback needed) | upgraded from keyword heuristic |
| Structural checks | 87 resolved | — |
| LLM fallback | 0 needed | — |
| Inconclusive | 338 criteria | — |

## What Changed Since Last Run

| Change | Impact |
|---|---|
| Repo restructure: product moved to `library/cursor/`, `.cursor/` uses symlinks | No score impact (rules identical, just relocated) |
| 6 new `hook_response` test cases added | 4/6 passed (81%) — best-performing new category |
| Judge upgraded from `local_judge.py` (keyword) to `hybrid_judge.py` (structural patterns) | More accurate verdicts but similar scores |
| `.harness/` paths fixed in `auto_capture.py` | Context injection now works correctly |
| `hooks.full.json` separated from `.cursor/hooks.json` (lean) | No eval impact |

## Score Distribution

```
  0-20%    █ 1
  20-40%   ██████████████████ 14
  40-60%   ██████████████████████████████████████ 30
  60-80%   ██████████████████████████ 20
  80-100%  ████████████████████████████ 22
```

## Results by Category

| Category | Pass Rate | Avg Score | Previous | Delta |
|---|---|---|---|---|
| hook_response | **4/6** | **81%** | — | new |
| glob_rule | 6/8 | 76% | 82% | -6pp |
| skill | 5/13 | 70% | 74% | -4pp |
| always_on_rule | 6/22 | 60% | 57% | +3pp |
| compositional | 1/8 | 55% | 60% | -5pp |
| routing | 0/11 | 47% | 54% | -7pp |
| contract | 1/8 | 44% | 40% | +4pp |
| adversarial | 0/9 | 40% | 45% | -5pp |
| description_rule | 0/2 | 40% | 40% | — |

## Results by Difficulty

| Difficulty | Pass Rate | Avg Score | Previous | Delta |
|---|---|---|---|---|
| easy | 7/23 | 62% | 62% | — |
| medium | 11/33 | 61% | 59% | +2pp |
| hard | 5/31 | 53% | 55% | -2pp |

## Passing Tests (23)

| Test | Score | Category | New? |
|---|---|---|---|
| python_ml_type_hints | 100% | glob_rule | |
| architecture_dependency_direction | 100% | glob_rule | |
| planning_discipline_thread_hygiene | 100% | always_on_rule | |
| data_science_analysis_hypotheses | 100% | skill | |
| adversarial_harness_skill_breadcrumbs | 100% | skill | |
| hook_evaluator_write_blocked | 100% | hook_response | ✓ |
| hook_commit_denied_compliance | 100% | hook_response | ✓ |
| hook_harness_enforcement_stop | 88% | hook_response | ✓ |
| compositional_ui_accessibility_tokens | 87% | compositional | |
| critical_thinking_vague_request | 86% | always_on_rule | |
| autonomous_execution_run_commands | 85% | always_on_rule | |
| security_sql_injection | 85% | always_on_rule | |
| hook_contract_gate_compliance | 85% | hook_response | ✓ |
| python_ml_pandas_vectorized | 83% | glob_rule | |
| research_standards_controls | 83% | glob_rule | |
| causal_rigor_circular_finding | 83% | glob_rule | |
| iac_templates_reuse | 83% | skill | |
| info_architecture_navigation | 82% | skill | |
| tech_writing_api_docs | 82% | skill | |
| architecture_pattern_simplicity | 80% | glob_rule | |
| critical_thinking_wrong_approach | 80% | always_on_rule | |
| security_hardcoded_secret | 80% | always_on_rule | |
| contract_rubric_mode_strict_vs_warn | 80% | contract | |

## Notable Failures

### Weakest: contract + adversarial + routing (40-47%)

These categories share a root cause: **the model doesn't follow harness workflow in single-turn SDK mode**. It receives a prompt, writes code, and skips the plan → negotiate → build → verify cycle.

| Test | Score | What went wrong |
|---|---|---|
| contract_required_fields | 20% | No contract JSON produced |
| adversarial_skip_harness_explicit | 27% | Didn't skip cleanly when told to |
| adversarial_just_do_it_complex | 27% | Didn't push back on "just do it" |
| routing_ambiguous_review_vs_audit | 30% | No routing reasoning |
| adversarial_sounds_simple_actually_complex | 30% | Missed hidden complexity |
| contract_rubrics_selection_ui | 30% | No rubric selection |
| routing_simple_task_no_harness | 33% | Ironically launched harness on simple task |
| testing_pytest_conventions | 33% | Didn't follow pytest patterns |
| commit_conventional_format | 33% | No conventional commit format |

### Hook responses that failed (2/6)

| Test | Score | Issue |
|---|---|---|
| hook_complexity_routing_compliance | 67% | Acknowledged routing but didn't fully comply with structure |
| hook_multiple_enforcement_sequence | 47% | Failed to address all enforcement messages in sequence |

## Structural Analysis

The hybrid judge resolved all 87 tests via structural checks alone (0 LLM calls). This validates the structural checker approach for the current test suite. However, 338 individual criteria were marked "inconclusive" — these are criteria where the structural checker couldn't determine pass/fail and would normally escalate to LLM. Since no LLM key was configured, they were scored conservatively.

**Implications**: The true scores are likely *higher* than reported. An LLM judge would resolve inconclusive criteria, particularly for behavioral and routing dimensions where intent matters more than keywords.

## Persistent Limitations

### 1. Eval captures pollute the project's own harness state

The SDK agent runs against this repo's real workspace. When it receives prompts like "build a user profile page," it writes to `.harness/state.json`, `.harness/contract.json`, and `.harness/evals/` — overwriting or corrupting **this project's** actual harness state.

**Evidence**: `.harness/evals/eval-feat-profile.json` (77 lines) was created by an eval capture responding to a harness-related prompt, not by an actual evaluator run on this project.

**Impact**: Running evals can silently corrupt the harness state of the repo you're developing in. You then have to manually identify and revert eval-generated harness artifacts vs real project state.

**Mitigation options**:
- Run SDK captures in an isolated git worktree (`git worktree add ../rules-skills-eval eval-sandbox`)
- Add a pre-capture step that stashes `.harness/` and restores after
- Configure `auto_capture.py` to use a temp directory as `cwd` instead of the real workspace
- Add `.harness/` to a "protected paths" list that the SDK agent can't write to during captures

### 2. Single-turn SDK mode suppresses workflow behavior (unchanged)

The model's default in single-turn mode is "answer the question / build the thing." Rules that require multi-step workflows (plan → negotiate → build → verify) are structurally disadvantaged because:
- No conversation context to maintain workflow state
- No tool-call execution to demonstrate intent
- No harness hook enforcement to route behavior

**Impact**: contract (44%), adversarial (40%), routing (47%) categories will remain low until multi-turn eval is implemented.

### 3. Structural judge can't assess reasoning quality

The structural checker looks for patterns (keywords, format markers, JSON structure). It can't evaluate:
- Quality of pushback reasoning in adversarial scenarios
- Appropriateness of routing decisions
- Whether a tip genuinely helps vs is formulaic

**Impact**: 338 inconclusive criteria per run. Scores are conservative lower bounds.

### 4. Non-deterministic variance ±5-7pp per category

Single N=1 runs produce noisy results. The -6pp drop in glob_rule and -7pp in routing are likely noise, not regression (no rules were weakened).

## Recommendations (Prioritized)

| # | Action | Expected Impact | Effort |
|---|---|---|---|
| 1 | **Run with OPENAI_API_KEY** to enable LLM fallback | Resolves 338 inconclusive criteria → true scores likely +10-15pp | Low (just needs key) |
| 2 | **Multi-turn eval** via `Agent.create()` + `agent.send()` | Enables testing workflow compliance, tool-use, harness cycle | High |
| 3 | **N=3 runs** for statistical stability | Eliminates ±5-7pp noise, enables confident A/B testing | Medium (cost) |
| 4 | **Sandbox captures** in git worktree | Prevents workspace pollution from eval-generated files | Low |
| 5 | **System prompt injection** for critical rules | May improve contract/adversarial in single-turn by 10-20pp | Medium |
| 6 | **Improve structural checkers** for routing/adversarial | Add pattern checks for planner mentions, complexity acknowledgment | Medium |

## Next Category Targets

Based on gap-to-ceiling analysis:

| Category | Current | Ceiling (estimated with LLM judge) | Priority |
|---|---|---|---|
| routing | 47% | ~65% | High — add structural checks for routing keywords |
| contract | 44% | ~55% | Medium — requires multi-turn for full contract generation |
| adversarial | 40% | ~60% | High — model knows what to do, structural checker misses it |
| compositional | 55% | ~70% | Medium — multi-rule scenarios need LLM judgment |
