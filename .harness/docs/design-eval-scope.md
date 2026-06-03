# Doc B — Eval Scope Reduction

## Problem-to-Scenario Map (all 44 scenarios)

| # | scenario_id | which_problem | redundant_with | verdict |
|---|-------------|---------------|----------------|---------|
| 1 | `routing_simple_skip` | none (negative) | — | **KEEP** |
| 2 | `routing_complex_activate` | 1+5 | `long_full_harness_cycle` | CUT |
| 3 | `routing_resume_existing` | 1+3 | — | **KEEP** |
| 4 | `routing_ambiguous_escalate` | none (routing judgment) | — | CUT |
| 5 | `routing_visual_ambiguity` | none (routing + UI) | — | CUT |
| 6 | `routing_multi_skill_overlap` | none (skill routing) | — | CUT |
| 7 | `behavioral_focused_opener` | 1 | — | **KEEP** |
| 8 | `behavioral_resume_mixed_tasks` | 1+2 | `behavioral_focused_opener` | CUT |
| 9 | `behavioral_progress_tracking` | 3 | `protocol_breadcrumbs_format` | CUT |
| 10 | `behavioral_session_boundary` | none (planning discipline) | — | **KEEP** (gap-14 open) |
| 11 | `behavioral_autonomous_execution` | none (autonomous rule) | — | CUT |
| 12 | `behavioral_verification_after_edit` | none (verification rule) | — | CUT |
| 13 | `behavioral_plan_adherence_multi_task` | 2+3 | — | **KEEP** |
| 14 | `behavioral_plan_update_on_discovery` | 2 | `behavioral_plan_adherence_multi_task` | CUT |
| 15 | `behavioral_plan_deviation_defer` | none (soft behavioral) | — | CUT |
| 16 | `behavioral_autonomy_drift` | 3+5 | `protocol_hook_gate_compliance` | CUT |
| 17 | `contract_binary_criteria` | 4 | — | **KEEP** |
| 18 | `contract_edge_cases` | 4 | — | **KEEP** (boundary quality) |
| 19 | `contract_negotiation_rounds` | 4 | — | **KEEP** |
| 20 | `contract_scope_too_broad` | 4+2 | — | **KEEP** |
| 21 | `contract_vague_pushback` | 4 | `contract_scope_too_broad` | CUT |
| 22 | `protocol_fresh_repo_bootstrap` | 1+2 | — | **KEEP** |
| 23 | `protocol_state_schema_v2` | 1+2 | `protocol_fresh_repo_bootstrap` | CUT |
| 24 | `protocol_state_task_progression` | 3 | — | **KEEP** |
| 25 | `protocol_state_integrity_after_edit` | 3 | `protocol_state_task_progression` | CUT |
| 26 | `protocol_full_lifecycle` | 3+5 | `long_full_harness_cycle` | CUT |
| 27 | `protocol_no_post_hoc_contracts` | 5 | — | **KEEP** |
| 28 | `protocol_evaluator_launch` | 5+4 | — | **KEEP** (eval report) |
| 29 | `protocol_self_judging_blocked` | 5 | `protocol_hook_gate_compliance` | CUT |
| 30 | `protocol_planner_delegation` | 2 | — | **KEEP** |
| 31 | `protocol_spike_bypasses_gate` | 5 | — | **KEEP** |
| 32 | `protocol_hook_gate_compliance` | 5 | — | **KEEP** |
| 33 | `protocol_breadcrumbs_format` | 3 | — | **KEEP** |
| 34 | `adversarial_skip_override` | none (negative) | — | **KEEP** |
| 35 | `adversarial_conflicting_instruction` | 5 | — | **KEEP** |
| 36 | `adversarial_hidden_complexity` | none (routing) | — | CUT |
| 37 | `adversarial_mid_workflow_change` | 2+4 | — | CUT |
| 38 | `skill_code_review` | none (skill) | — | CUT |
| 39 | `skill_architecture_audit` | none (skill) | — | CUT |
| 40 | `skill_commit_format` | none (skill) | — | CUT |
| 41 | `skill_frontend_design` | none (skill) | — | CUT |
| 42 | `long_full_harness_cycle` | 1-5 (E2E) | — | **KEEP** |
| 43 | `long_multi_feature_coherence` | 2+3 | `long_full_harness_cycle` | CUT |
| 44 | `long_resilience_recovery` | none + 5 (partial) | — | CUT |

---

## Survival List (20 scenarios)

| # | scenario_id | problem | justification |
|---|-------------|---------|---------------|
| 1 | `behavioral_focused_opener` | 1-SCOPE | Tests agent reads state.json on session start; simplest scope test |
| 2 | `routing_resume_existing` | 1-SCOPE + 3-STATUS | Tests mid-build resume; validates state awareness + status advance |
| 3 | `protocol_fresh_repo_bootstrap` | 1-SCOPE + 2-TASK | Tests cold-start creation of state.json with tasks |
| 4 | `protocol_planner_delegation` | 2-TASK | Tests planner produces structured task backlog |
| 5 | `contract_scope_too_broad` | 2-TASK + 4-CRITERIA | Tests narrowing broad scope into discrete tasks + contract |
| 6 | `behavioral_plan_adherence_multi_task` | 2-TASK + 3-STATUS | Tests following task order; validates lifecycle transitions |
| 7 | `protocol_state_task_progression` | 3-STATUS | Tests status advancement (pending→building→evaluating) |
| 8 | `protocol_breadcrumbs_format` | 3-STATUS | Tests breadcrumb schema compliance (format of audit trail) |
| 9 | `contract_binary_criteria` | 4-CRITERIA | Tests binary-testable acceptance criteria quality |
| 10 | `contract_negotiation_rounds` | 4-CRITERIA | Tests evaluator pushback and negotiation iteration |
| 11 | `contract_edge_cases` | 4-CRITERIA | Tests boundary-keyword quality in edge cases (gap-4 guard) |
| 12 | `protocol_no_post_hoc_contracts` | 5-ENFORCEMENT | Tests contract-before-build (not after the fact) |
| 13 | `protocol_hook_gate_compliance` | 5-ENFORCEMENT | Tests compliance with hook gates over user override |
| 14 | `protocol_spike_bypasses_gate` | 5-ENFORCEMENT | Tests type-aware gate bypass (spike/chore exception) |
| 15 | `protocol_evaluator_launch` | 5-ENFORCEMENT + 4-CRITERIA | Tests evaluator invocation and eval-report production |
| 16 | `adversarial_conflicting_instruction` | 5-ENFORCEMENT | Tests hooks block commit when contract unverified |
| 17 | `routing_simple_skip` | NEGATIVE | Tests harness does NOT activate for simple tasks |
| 18 | `adversarial_skip_override` | NEGATIVE | Tests skip-harness compliance (user opt-out works) |
| 19 | `behavioral_session_boundary` | SIGNAL (gap-14) | Regression test for open bug; kept until gap-14 resolved |
| 20 | `long_full_harness_cycle` | E2E (1-5) | Full lifecycle integration across multiple features |

---

## Coverage Matrix

| Problem | Scenarios (count) |
|---------|-------------------|
| 1. SCOPE | behavioral_focused_opener, routing_resume_existing, protocol_fresh_repo_bootstrap, long_full_harness_cycle (4) |
| 2. TASK DEFINITION | protocol_fresh_repo_bootstrap, protocol_planner_delegation, contract_scope_too_broad, behavioral_plan_adherence_multi_task, long_full_harness_cycle (5) |
| 3. STATUS TRACKING | routing_resume_existing, protocol_state_task_progression, protocol_breadcrumbs_format, behavioral_plan_adherence_multi_task, long_full_harness_cycle (5) |
| 4. ACCEPTANCE CRITERIA | contract_binary_criteria, contract_negotiation_rounds, contract_scope_too_broad, long_full_harness_cycle (4) |
| 5. CONTRACT ENFORCEMENT | protocol_no_post_hoc_contracts, protocol_hook_gate_compliance, protocol_spike_bypasses_gate, adversarial_conflicting_instruction, long_full_harness_cycle (5) |
| NEGATIVE (don't activate) | routing_simple_skip, adversarial_skip_override (2) |

All 5 problems have >= 4 scenarios. Both negative scenarios preserved.

---

## Cut Justifications (24 scenarios removed)

| scenario_id | Why safe to cut |
|-------------|-----------------|
| `routing_complex_activate` | E2E routing covered by `long_full_harness_cycle` which is more comprehensive |
| `routing_ambiguous_escalate` | Tests routing judgment, not any of the 5 problems |
| `routing_visual_ambiguity` | Tests UI/visual routing, not harness core |
| `routing_multi_skill_overlap` | Tests skill selection, not harness |
| `behavioral_resume_mixed_tasks` | Resume covered by `behavioral_focused_opener` + `routing_resume_existing`; also has gap-20 bug (nested harness_level) |
| `behavioral_progress_tracking` | Breadcrumb compliance covered by `protocol_breadcrumbs_format` |
| `behavioral_autonomous_execution` | Tests autonomous_execution.mdc rule, not harness |
| `behavioral_verification_after_edit` | Tests verification.mdc rule, not harness |
| `behavioral_plan_update_on_discovery` | Plan revision covered by `behavioral_plan_adherence_multi_task` |
| `behavioral_plan_deviation_defer` | Soft behavioral signal, not testable harness enforcement |
| `behavioral_autonomy_drift` | Overlaps `protocol_hook_gate_compliance` (don't skip eval) |
| `contract_vague_pushback` | Pushback + scoping covered by `contract_scope_too_broad` |
| `protocol_state_schema_v2` | Schema creation covered by `protocol_fresh_repo_bootstrap` |
| `protocol_state_integrity_after_edit` | Status integrity covered by `protocol_state_task_progression` |
| `protocol_full_lifecycle` | Full lifecycle covered by `long_full_harness_cycle` (more comprehensive) |
| `protocol_self_judging_blocked` | Self-judging blocked by `protocol_hook_gate_compliance` (same enforcement) |
| `adversarial_hidden_complexity` | Routing detection, not 5-problem core |
| `adversarial_mid_workflow_change` | Interesting but not protecting core; pivot handling is behavioral |
| `skill_code_review` | Skill activation, not harness |
| `skill_architecture_audit` | Skill activation, not harness |
| `skill_commit_format` | Skill activation, not harness |
| `skill_frontend_design` | Skill activation, not harness |
| `long_multi_feature_coherence` | Multi-feature covered by `long_full_harness_cycle` |
| `long_resilience_recovery` | Bug-fix routing; not testing the 5-problem system |

---

## Delta

- **Before:** 44 scenarios (41 top-level + 3 long)
- **After:** 20 scenarios (19 top-level + 1 long)
- **Reduction:** 24 scenarios cut (55% reduction)
- **Coverage:** All 5 problems >=4 scenarios, 2 negative, 1 E2E, 1 gap-14 signal
