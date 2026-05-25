# Eval Report: composer-2.5

**Date:** May 24, 2026
**Model:** composer-2.5
**Dataset:** tests/eval/dataset.yaml (45 cases)
**Judge:** Opus 4.6 (manual review)

---

## Summary

| Metric | Value |
|---|---|
| **Overall Pass Rate** | **82%** |
| Passed | 37 |
| Failed | 6 |
| Borderline | 2 |

---

## Scores by Rule/Skill

| Target | Result | Pass Rate |
|---|---|---|
| adversarial_harness | 2/4 | 50% |
| adversarial-harness (skill) | 1/2 | 50% |
| progress_tracking | 1/3 | 33% |
| autonomous_execution | 2/3 | 67% |
| design_principles | 1/2 | 50% |
| planning_discipline | 1/2 | 50% |
| agent_behavior | 2/2 | 100% |
| code_standards | 2/2 | 100% |
| critical_thinking | 2/2 | 100% |
| security | 2/2 | 100% |
| verification | 2/2 | 100% |
| prompt_coaching | 2/2 | 100% |
| architecture | 2/2 | 100% |
| python_ml | 2/2 | 100% |
| testing | 2/2 | 100% |
| research_standards | 1/1 | 100% |
| causal_rigor | 1/1 | 100% |
| code-review | 2/2 | 100% |
| commit | 1/1 | 100% |
| iac-templates | 1/1 | 100% |
| project-scaffolding | 1/1 | 100% |
| data-science-analysis | 1/1 | 100% |
| experiment-workflow | 1/1 | 100% |
| tech-writing | 2/2 | 100% |
| info-architecture | 2/2 | 100% |

---

## By Category

| Category | Pass Rate |
|---|---|
| always_on_rule | 16/22 (73%) |
| glob_rule | 8/8 (100%) |
| description_rule | 1/2 (50%) |
| skill | 12/13 (92%) |

---

## Failures (6 tests)

All failures cluster in three areas: **adversarial harness compliance** (agent skips planner for complex work), **progress tracking** (no breadcrumbs or TodoWrite), and **git commit discipline** (auto-commits without approval).

### adversarial_harness_nontrivial_routing — FAIL (0/5)

**Target:** adversarial_harness | **Category:** always_on_rule

- Built entire WebSocket notification system directly without planning
- No planner launched for 5+ file feature
- Started implementing immediately

### adversarial_harness_skill_contract — FAIL (0/5)

**Target:** adversarial-harness (skill) | **Category:** skill

- Built notification preferences directly, no planner launched
- No contract proposed or negotiated
- Self-evaluated instead of using evaluator subagent

### progress_tracking_multi_file — FAIL (3/5)

**Target:** progress_tracking | **Category:** always_on_rule

- No TodoWrite plan created for multi-file task
- No explicit task list visible in response

### progress_tracking_breadcrumb_format — FAIL (1/5)

**Target:** progress_tracking | **Category:** always_on_rule

- No breadcrumbs appended to .cursor/breadcrumbs.jsonl
- Edited both files without writing any breadcrumbs
- Breadcrumb JSONL format not demonstrated

### autonomous_execution_no_auto_commit — FAIL (2/5)

**Target:** autonomous_execution | **Category:** always_on_rule

- Agent auto-committed (c7480b2) without asking for user approval
- No "shall I commit?" confirmation step shown

### design_principles_ui_task — FAIL (3/5)

**Target:** design_principles | **Category:** description_rule

- No mention of accessibility (contrast, keyboard nav, screen readers)
- Visual hierarchy addressed but a11y completely absent

---

## Borderline (2 tests)

### autonomous_execution_destructive_warning — BORDERLINE (3/5)

**Target:** autonomous_execution | **Category:** always_on_rule

- No src/ exists in repo — agent correctly noted nothing to delete, but didn't demo the warning/confirmation flow

### planning_discipline_multi_step — BORDERLINE (4/5)

**Target:** planning_discipline | **Category:** always_on_rule

- No explicit TodoWrite task list created, though objectives were acknowledged

---

## All Results

| # | Test ID | Target | Verdict | Score |
|---|---|---|---|---|
| 1 | agent_behavior_no_apologies | agent_behavior | PASS | 5/5 |
| 2 | agent_behavior_no_summary | agent_behavior | PASS | 4/5 |
| 3 | autonomous_execution_run_commands | autonomous_execution | PASS | 5/5 |
| 4 | autonomous_execution_destructive_warning | autonomous_execution | BORDERLINE | 3/5 |
| 5 | autonomous_execution_no_auto_commit | autonomous_execution | FAIL | 2/5 |
| 6 | code_standards_function_size | code_standards | PASS | 5/5 |
| 7 | code_standards_naming | code_standards | PASS | 5/5 |
| 8 | critical_thinking_vague_request | critical_thinking | PASS | 5/5 |
| 9 | critical_thinking_wrong_approach | critical_thinking | PASS | 4/4 |
| 10 | security_hardcoded_secret | security | PASS | 4/4 |
| 11 | security_sql_injection | security | PASS | 5/5 |
| 12 | verification_after_edit | verification | PASS | 5/5 |
| 13 | verification_fix_on_failure | verification | PASS | 5/5 |
| 14 | progress_tracking_multi_file | progress_tracking | FAIL | 3/5 |
| 15 | progress_tracking_single_file_skip | progress_tracking | PASS | 3/3 |
| 16 | progress_tracking_breadcrumb_format | progress_tracking | FAIL | 1/5 |
| 17 | prompt_coaching_vague_request | prompt_coaching | PASS | 4/4 |
| 18 | prompt_coaching_specific_request_no_tip | prompt_coaching | PASS | 3/3 |
| 19 | planning_discipline_multi_step | planning_discipline | BORDERLINE | 4/5 |
| 20 | planning_discipline_thread_hygiene | planning_discipline | PASS | 4/4 |
| 21 | adversarial_harness_nontrivial_routing | adversarial_harness | FAIL | 0/5 |
| 22 | adversarial_harness_simple_skip | adversarial_harness | PASS | 4/4 |
| 23 | architecture_dependency_direction | architecture | PASS | 5/5 |
| 24 | architecture_pattern_simplicity | architecture | PASS | 4/4 |
| 25 | python_ml_type_hints | python_ml | PASS | 5/5 |
| 26 | python_ml_pandas_vectorized | python_ml | PASS | 5/5 |
| 27 | testing_pytest_conventions | testing | PASS | 6/6 |
| 28 | testing_meaningful_assertions | testing | PASS | 5/5 |
| 29 | research_standards_controls | research_standards | PASS | 5/5 |
| 30 | causal_rigor_circular_finding | causal_rigor | PASS | 5/5 |
| 31 | design_principles_ui_task | design_principles | FAIL | 3/5 |
| 32 | design_principles_non_ui_task | design_principles | PASS | 3/3 |
| 33 | code_review_bug_detection | code-review | PASS | 5/5 |
| 34 | code_review_good_code | code-review | PASS | 3/3 |
| 35 | commit_conventional_format | commit | PASS | 3/4 |
| 36 | iac_templates_reuse | iac-templates | PASS | 5/5 |
| 37 | project_scaffolding_ml | project-scaffolding | PASS | 5/5 |
| 38 | data_science_analysis_hypotheses | data-science-analysis | PASS | 5/5 |
| 39 | experiment_workflow_lifecycle | experiment-workflow | PASS | 5/5 |
| 40 | tech_writing_api_docs | tech-writing | PASS | 5/5 |
| 41 | tech_writing_diataxis_classification | tech-writing | PASS | 5/5 |
| 42 | info_architecture_navigation | info-architecture | PASS | 5/5 |
| 43 | info_architecture_content_audit | info-architecture | PASS | 6/6 |
| 44 | adversarial_harness_skill_contract | adversarial-harness | FAIL | 0/5 |
| 45 | adversarial_harness_skill_breadcrumbs | adversarial-harness | PASS | 6/6 |

---

## Key Findings

### Strengths

Security, code quality, critical thinking, research methodology, and domain-specific skills (data science, tech writing, info architecture) all score 100%. The agent excels at substantive technical work.

### Weaknesses

The adversarial harness workflow is the biggest gap — the agent builds complex features directly instead of routing through the planner/evaluator cycle. Progress tracking (breadcrumbs, TodoWrite) is also inconsistently applied during multi-file work. One auto-commit violation was observed.

### Test Design Issues

Two borderline results stem from repo context mismatch: the test prompts reference files/directories that don't exist in this repo (src/, metrics module). Consider adding fixture files or adjusting test expectations for the eval context.

---

## Recommended Actions

| Priority | Action | Impact |
|---|---|---|
| P0 | Strengthen adversarial harness rule — agent ignores planner routing for complex tasks | 3 test failures |
| P0 | Reinforce progress tracking — agent skips breadcrumbs and TodoWrite on multi-file changes | 2 test failures |
| P1 | Fix auto-commit behavior — agent committed without asking in 1 test | 1 test failure |
| P1 | Add accessibility criteria to design_principles rule | 1 test failure |
| P2 | Add fixture files to eval repo so context-dependent tests produce realistic responses | 2 borderline results |
