# Spike: Eval Research

Research evaluation frameworks for rules, skills, agent trajectory, and LLM-as-judge reliability. Informs `feat-14` (LLM-as-judge) and `trajectory_quality` rubric design.

## §0 Baseline — What We Have Today

### Pipeline architecture

Two-tier eval pipeline:
- **Tier 1 (fast static)**: `validate.py`, `contract_lint.py`, `harness_lint.py` — deterministic, no API keys, seconds
- **Tier 3 (session scenarios)**: 28 YAML scenarios run via Cursor SDK bridge in isolated git worktrees

Tier 3 judge (`session_judge.py`, 1517 lines) has three sub-tiers:
- **Computational**: deterministic checks on `.harness/` artifacts (state.json, contract.json, breadcrumbs, hooks.log)
- **Structural**: heuristic pattern matching on file contents, validations, transcript, conversation trace
- **LLM**: `judge_with_llm()` for `negotiation_quality` + `trajectory_quality` via cursor_sdk Agent

### UNCERTAIN verdict taxonomy

Latest 19-scenario run: 116 criteria judged, 105 PASS, 4 FAIL, **7 UNCERTAIN/SKIP**.

The 7 UNCERTAIN/SKIP are distributed across **3 scenarios only** (the other 4 FAIL criteria appear in different scenarios):

| Scenario | Score | UNCERTAIN criteria | Root cause |
|----------|-------|-------------------|------------|
| `behavioral_session_boundary` | 33% | ~4 UNCERTAIN: checkpoint, fresh-thread, session boundary, silently-accept-all checks | No conversation trace; heuristic regex branches 16/17 don't match transcript wording. FAIL on follow-up feature count heuristic (separate from UNCERTAIN). |
| `adversarial_skip_override` | 71% | ~2 UNCERTAIN: behavioral autonomy, verification items | Agent skipped harness correctly but behavioral heuristics can't confirm tool usage without trace |
| `protocol_spike_bypasses_gate` | 75% | ~1 UNCERTAIN: spike-without-negotiation behavioral check | `harness_level: light` skips computational checks; behavioral item text unmatched by any branch |

Note: `adversarial_conflicting_instruction` (80%) and `contract_scope_too_broad` (80%) score below 80% due to **FAIL** criteria (compile check, feature count heuristic), not UNCERTAIN. They are scoring problems but not UNCERTAIN problems.

**Emission paths** in `session_judge.py`:
1. `check_behavioral()` line 695: `_evaluate_behavioral()` returns `False` → UNCERTAIN (not FAIL)
2. `check_long_scenario()`: coherence/multi-contract/recovery fallbacks → UNCERTAIN
3. Default fallback at line 953: `return True` (optimistic pass for unmatched criteria) — inconsistent with UNCERTAIN path

**Structural problem**: UNCERTAIN inflates the denominator without contributing to numerator. Score = pass/total, so 1 UNCERTAIN in 3 criteria drops score from 100% to 67%.

### Behavioral heuristic inventory

`_evaluate_behavioral()` has **26 explicit branches + 1 default fallback** (return True at line 953):

| # | Trigger keywords | Detection method | Fragility |
|---|-----------------|------------------|-----------|
| 1 | "no apolog" | Regex: `i'm sorry\|i apologize` | Low — narrow, deterministic |
| 2 | "autonomously" | Trace: Shell/ReadLints tool calls; fallback: keyword list | Medium — fallback is weak |
| 3 | "breadcrumbs" + "complete" | breadcrumbs >= 3 | Low — deterministic count |
| 4 | "shall i proceed" / "should i" | Regex: proceed patterns | Low |
| 5 | "directly" + "without"/"no" | Regex: same proceed patterns as #4 | Low — duplicates #4 |
| 6 | "no todowrite" | String search: "TodoWrite" not in text | Low |
| 7 | "todowrite" / "progress track" | Trace: TodoWrite tool call; fallback: build breadcrumbs >= 2 | Medium |
| 8 | "push back" / "pushback" | Regex: 12+ clarification patterns | Medium — broad regex |
| 9 | "scoped contract" | Contract exists + criteria count 2-8 | Low |
| 10 | "off-plan" / "defer" | Regex: 20+ deferral patterns | **High** — very broad regex, false positives likely |
| 11 | "abandon" / "derail" | Contract task_id matches building task | Low |
| 12 | "follow" + "priority"/"order" | Breadcrumb feat field ordering | Medium — string comparison |
| 13 | "proactively updated" + "plan" | trade_offs/direction in state.json | **High** — indirect signal |
| 14 | "did not modify" | Trace: Write/StrReplace calls == 0; fallback: files <= 1 | Medium |
| 15 | "verif" + "syntax"/"test" | Trace: pytest/tsc/ReadLints; fallback: keyword | Medium |
| 16 | "fresh thread" / "session boundary" | Regex: 15+ boundary patterns | **High** — most UNCERTAIN source |
| 17 | "silently accept all" | Regex: boundary patterns (overlaps #16) | **High** |
| 18 | "evaluator" + "not modify source" | Non-harness files == 0 | Low |
| 19 | "focused summary" | First response < 800 words | Low |
| 20 | "read breadcrumbs" + "first" | Trace: Read tool in first 10 calls; fallback: keyword | Medium |
| 21 | "full project exploration" | First response < 800 words (same as #19) | Low — duplicates #19 |
| 22 | "asked what to work on" | Regex: work patterns | Medium |
| 23 | "proposed" + "plan" | Regex: plan patterns | Medium |
| 24 | "presented" + "option" | Regex: option patterns | Medium |
| 25 | "contract" + "negotiat" | Contract exists OR regex | Low |
| 26 | "identified" + "complexity" | Regex: complexity patterns | Medium |
| 27 | DEFAULT | `return True` — optimistic pass | **Critical** — hides mismatches silently |

**Key problems**:
- The default `return True` (branch 27) means any unrecognized criterion text silently passes. This masks rubric drift and scenario-judge misalignment.
- Branches 16/17 (session boundary) are the primary UNCERTAIN source — the regex is broad but behavioral_session_boundary scenario scores 33%.
- Branches 4/5 and 19/21 are duplicates.
- High-fragility branches (10, 13, 16, 17) rely on broad regex patterns with many alternatives that can false-positive on unrelated transcript text.

### Conversation trace coverage

The SDK bridge now captures conversation traces (`transcript[].conversation` with tool calls, thinking blocks, shell commands) since gap-22 fix. Trace-aware checks in `_evaluate_behavioral()` use `_extract_tool_calls()`, `_extract_shell_commands()`, and `_has_trace()`. Without trace, many checks fall through to weaker heuristics.

### Scenario coverage against five problems

(Full matrix in `.harness/audits/eval-coverage-audit.json`)

| Problem | Scenario count | Key gaps |
|---------|---------------|----------|
| 1. Repository scope | 6 | No mid-build direction update test; no negative test for overwriting vision on resume |
| 2. Task definition | 11 | bug/gap/chore types never exercised; duplicate task id untested |
| 3. Task grouping | 6 | building_id vs first-pending ambiguity; mixed pending feature+spike selection |
| 4. Status tracking | 8 | cancelled status untested; session recovery from corrupt breadcrumbs |
| 5. Acceptance criteria | 9 | Max negotiation rounds cap untested; evaluator REJECT loop untested |

### Hook enforcement coverage

| Hook | Scenarios | Gap severity |
|------|-----------|-------------|
| `contract-gate.sh` | 3 (+2 new) | Medium — DENIED→recovery now covered |
| `pre-commit-harness.sh` | 1 (new) | Low — deny→approve→flag loop covered |
| `verify-harness.sh` | 2 | Medium — malformed contract false-positive untested |
| `enforce-progress.sh` | 0 | **High** — zero dedicated coverage |
| `evaluator-guard.sh` | 1 | Medium — hook DENIED not proven in hooks.log |
| `context-health.sh` | 1 (+1 new) | Medium — stale-thread now seeded |
| `harness-context.sh` | 2 | Low |
| `harness-gate.sh` | 3 | Low |

---

## §1 Landscape — External Frameworks

### Academic benchmarks

| Benchmark | Focus | How it judges | Relevance to us |
|-----------|-------|---------------|-----------------|
| **SWE-bench** | Software engineering — resolve real GitHub issues | Test suite pass/fail (deterministic) | Gold standard for coding agents. Verified variant saturated (~80%), Pro more reliable (~23-46%). Contamination via training data is the dominant problem. |
| **SWE-bench Pro** | Decontaminated coding | Same mechanism, private/GPL codebases | Shows what agents actually do on unseen code. Our scenarios are fresh (good). |
| **AgentBench** | Multi-domain (8 environments) | Task-specific success rate | Breadth signal, not depth. Our harness is deep on one domain (workflow compliance). |
| **GAIA** | General assistant tasks | Tool use + reasoning correctness | Tests general capability, not workflow adherence. |
| **BFCL** | Function/tool calling accuracy | Schema match + execution result | Directly relevant to our trajectory scoring — tool selection is what we measure. |
| **WebArena** | Web browsing agents | Task completion in web environment | Different domain, but sandbox isolation approach is relevant. |
| **HumanEval** | Code generation (function-level) | Unit test pass/fail | Too narrow — function generation, not agent workflow. |

**Critical finding** (Berkeley RDI audit, 2026): Every major benchmark (SWE-bench, WebArena, GAIA, OSWorld, Terminal-Bench) is exploitable to near-perfect scores via reward hacking (pytest hooks, DOM injection, VM manipulation). Agents achieve 100% scores without solving a single task. **Implication**: our evaluation environment must resist agent manipulation of the scoring process. Our current sandbox + hook-based enforcement is directionally correct because hooks fire during the agent's session (not post-hoc), but `verify-harness.sh` trusts `verified: true` set by the agent itself — a known debt.

### Industry evaluation frameworks

| Framework | Architecture | Scoring model | Agent support | What we can steal |
|-----------|-------------|---------------|---------------|-------------------|
| **Inspect AI** (UK AISI) | Tasks = datasets + solvers + scorers | Code + model-graded + human | ReAct, Deep, multi-agent, custom agents. Sandboxed (Docker/K8s/VM). Limits (time/messages/tokens/cost). | **Closest parallel** to our pipeline. Their "solver" = our scenario + agent; their "scorer" = our session_judge. Their hook system for lifecycle events, approval policies, and agent limits are mature patterns we should study. |
| **METR Task Standard** | Python class: `get_tasks()`, `get_instructions()`, `score()` | Automatic + human | Container/VM sandboxing, aux VMs, network isolation. 2000+ tasks (AI R&D, cybersecurity). | Portable task format. Our YAML scenarios could adopt a schema version field and mandatory `score()` function for deterministic verification. |
| **Braintrust** | Experiments + scorers + production monitoring | 3 types: autoevals (pre-built), LLM-as-judge (trace-level, CoT), custom code | Trace-level evaluation for full agent execution context | **Pass thresholds** per scorer for CI gating. **Online scoring** for production. **Feedback loop**: production traces → dataset → offline eval. Their CoT-enabled LLM judge design. |
| **LangSmith** | Datasets + evaluators + production monitoring | Offline + online evaluators, human annotation queues | **AgentEvals** package: trajectory matching (strict/unordered/subset/superset) + LLM judge | **Trajectory match modes** are directly implementable. Their strict/subset/superset model maps to our tool-call sequence checking. Online evaluators for drift detection. |
| **Promptfoo** | Config-driven prompt testing | Assertions (contains, regex, model-graded) | Agent support via custom providers | Lightweight alternative for rule A/B testing. Config file approach similar to our YAML scenarios. |
| **DeepEval** | Python test framework | 14 metrics + custom | DAG-based agent metrics | Deterministic DAG metrics for execution graphs. |

### Trajectory evaluation tools

| Tool | Approach | Metrics | Integration |
|------|----------|---------|-------------|
| **trajscore** | Production Python library | goal_completion, tool_accuracy, step_efficiency, reasoning_coherence, loop_detection, answer_faithfulness | Standalone |
| **trajectly** | Deterministic regression testing | Tool-call skeleton matching, ordering contracts (`require_before`), argument schema validation, execution budgets | CI gate |
| **AgentEvals** (LangSmith) | Match + LLM judge | strict/unordered/subset/superset trajectory matching | LangSmith |
| **tracecheck** | Trace scoring | Tool accuracy, context handling, failure modes (loops, context overflow) | Standalone |

### Vendor guidance synthesis

**Anthropic** (from "Demystifying evals for AI agents"):
- Three grader types: code-based (deterministic), model-based (LLM judge), human
- **"Choose deterministic graders where possible, LLM graders where necessary"** — validates our hybrid approach
- Calibrate LLM judges against human experts; give the judge an "Unknown" escape option
- Grade each dimension with an isolated LLM call, not one prompt for all dimensions
- Production monitoring + A/B testing for significant changes

**Industry consensus** (across Braintrust, LangSmith, Arize, Evidently, Langfuse):
- Binary or low-precision scoring (PASS/FAIL or 1-3 scale) is more reliable than 1-10
- Calibration against 30-50 human-labeled gold examples before trusting LLM judge
- 75-90% agreement between judge and human labels = ready to scale
- Temperature 0 for consistency; structured output (JSON) for parsing
- Cross-family judges (different model family for judge vs subject) to avoid self-preference bias

---

## §2 Rules and Skills — Effectiveness Testing

### The measurement problem

Our pipeline tests whether agents **follow harness rules** (compliance) but not whether **rules improve agent behavior** (effectiveness). We can tell if the agent created state.json, but not if the `adversarial_harness.mdc` rule is the reason it did.

### Ablation methodology

**Paired comparison** is the standard approach (prompt-eval-arena, Promptfoo, Braintrust, academic literature):

1. **Same scenario, same model**: run each scenario twice — once with full `.cursor/rules/`, once with target rule removed
2. **Measure delta**: per-criterion score difference, aggregated across scenarios
3. **Statistical test**: Wilcoxon signed-rank on paired per-scenario deltas (our 28 scenarios provide 28 paired observations per rule — marginal for formal statistics but sufficient for directional signal)
4. **Effect size**: Cohen's d alongside p-value. d < 0.2 = negligible, d > 0.5 = meaningful

**Headroom test** (from arxiv 2604.14585): Before investing in optimization, test if the rule has headroom. Generate 10-20 prompt variants, compare best to baseline. If gain < 2 points, the landscape is flat.

### Proposal: rule ablation mode for session_runner.py

```
python tests/eval/session_runner.py --ablate-rule adversarial_harness
```

Implementation:
1. Runner copies `library/cursor/` to sandbox as today
2. For ablation run, remove the target `.mdc` file from `.cursor/rules/` before agent starts
3. Run same scenario with and without the rule
4. session_judge scores both sessions
5. Report: per-criterion delta table, aggregate delta, statistical test result

**Priority rules to ablate** (highest expected impact):
- `adversarial_harness.mdc` — core harness routing behavior
- `autonomous_execution.mdc` — autonomous decision-making
- `progress_tracking.mdc` — breadcrumb writing
- `planning_discipline.mdc` — session boundaries, thread hygiene

### Skill activation

`check_skill_activation()` exists in session_judge.py but **no scenario uses `skill_activation` rubric**. The SDK bridge doesn't auto-route skills (IDE-only feature), so the agent must proactively read skill files.

**Proposal**: Create 2-3 scenarios that seed a task description matching skill keywords, then check whether the agent reads the SKILL.md and follows its instructions. This tests skill quality (does the skill produce better output?), not routing (IDE concern).

---

## §3 Trajectory — Tool-Sequence Quality Scoring

### Current state

- 3 scenarios use `trajectory_quality`, all routed to LLM judge
- Conversation trace captured per turn: tool calls (name, args, result, status), shell commands, thinking blocks
- `_extract_tool_calls()` and `_extract_shell_commands()` exist
- No deterministic trajectory scorer

### Deterministic trajectory checks

Inspired by trajscore, trajectly, and AgentEvals — **implementable without LLM calls**:

| Check | How to compute | Threshold | Tier |
|-------|---------------|-----------|------|
| **Loop detection** | Count consecutive identical tool calls (same name + args hash) | > 2 consecutive = flag | computational |
| **Step efficiency** | Total tool calls vs scenario difficulty-adjusted range | easy: 5-25, medium: 10-50, hard: 20-100 | computational |
| **Read-before-write** | For each Write/StrReplace, verify a prior Read on same file path | 100% compliance = PASS | computational |
| **Skeleton matching** | Define required tool-call subsequence per scenario (e.g., `[Read state.json, Write contract.json, Shell "make test"]`) | Subsequence present = PASS | computational |
| **Backtracking ratio** | StrReplace(same file, same region) / total edits | > 0.5 = excessive thrashing | structural |
| **Idle detection** | Consecutive response blocks without tool calls | > 3 consecutive = flag | structural |
| **Error recovery** | Shell tool call with non-zero exit → next action addresses it | Recovery within 3 steps = PASS | structural |

### Skeleton matching — the highest-value addition

Adapt trajectly's `require_before` pattern:

```yaml
# In scenario YAML
trajectory_skeleton:
  - tool: Read
    path_contains: "state.json"
  - tool: Write
    path_contains: "contract.json"
    after: "Read state.json"
  - tool: Shell
    command_contains: "test"
    after: "Write contract.json"
```

The judge checks that the skeleton appears as a subsequence in the actual trace. Missing steps = FAIL. Extra steps (agent did more than skeleton) = allowed. This is deterministic, fast, and catches the most common trajectory failures (skipping reads, writing before negotiating).

### LLM trajectory checks (keep for nuanced assessment)

| Check | When to use LLM | Why not deterministic |
|-------|-----------------|---------------------|
| Tool selection appropriateness | "Was Grep better than SemanticSearch here?" | Context-dependent judgment |
| Reasoning coherence | "Do intermediate steps lead logically to actions?" | Requires understanding intent |
| Recovery quality | "Was the error recovery strategy appropriate?" | Multiple valid recovery paths |
| Efficiency judgment | "Could the agent have solved this in fewer steps?" | Optimal path depends on context |

### Ordering metric

For scenarios with strict ordering requirements, use **Kendall's tau** to measure ordering similarity between actual and expected tool-call sequences. τ >= 0.85 = acceptable ordering for deployment-gating scenarios.

### Proposal: add trajectory tier to session_judge.py

New tier between structural and LLM:

```
computational → structural → trajectory → llm
```

Trajectory tier runs deterministic checks from the table above. This reduces LLM judge load (fewer criteria need LLM) and provides faster, more reliable signal.

---

## §4 LLM Judge — Reliability and Calibration

### Current implementation analysis

`judge_with_llm()` (lines 1326-1383) has **9 identified problems**:

| # | Problem | Severity | Impact |
|---|---------|----------|--------|
| 1 | No calibration against human labels | **Critical** | Cannot measure judge accuracy; scores are unvalidated |
| 2 | Single prompt for all criteria | High | No per-dimension rubric; complex multi-criterion prompt degrades quality |
| 3 | Transcript truncation (8KB) | High | Key moments (errors, recovery, negotiation) may be in truncated portion |
| 4 | No "Unknown" escape hatch | High | Forces PASS/FAIL on insufficient evidence; UNCERTAIN comes from elsewhere |
| 5 | No temperature control | Medium | cursor_sdk default may add variance between runs |
| 6 | No CoT prompting | Medium | Judge jumps to verdict without showing reasoning |
| 7 | Confidence score captured but unused | Medium | 1-5 confidence exists in output schema but never gates verdicts |
| 8 | Regex-based JSON parsing | Medium | Fragile; structured output would be more reliable |
| 9 | All-or-nothing error handling | Low | Any parse failure → ERROR for all criteria in the call |

### Calibration strategy (from Anthropic + Arize + academic literature)

**Phase 1 — Golden set** (prerequisite for any LLM judge improvement):
1. Select 30-50 session transcripts across rubric categories (negotiation_quality, trajectory_quality)
2. Human-label each criterion as PASS/FAIL with evidence quote
3. Run current judge on same transcripts
4. Compute agreement: Cohen's κ (target ≥ 0.6 for acceptable, ≥ 0.8 for good)
5. Analyze disagreements: are they rubric ambiguity, truncation, or judge hallucination?

**Phase 2 — Rubric refinement**:
1. Split multi-criterion prompts into per-dimension calls (Anthropic recommendation)
2. Add anchor examples (1 PASS example, 1 FAIL example per dimension)
3. Add "UNKNOWN: insufficient evidence" as valid verdict
4. Use CoT: require reasoning before verdict, then extract only the verdict

**Phase 3 — Operational calibration**:
1. Re-run golden set after each change to judge prompt, judge model, or production prompt
2. Track κ over time; alert if it drops below threshold
3. Use cross-family judges for highest-stakes decisions (different model family than subject)

### UNCERTAIN elimination strategy

Current UNCERTAIN sources and proposed fixes:

| Source | Current behavior | Proposed fix | Fix type |
|--------|-----------------|--------------|----------|
| Behavioral heuristic returns False | UNCERTAIN | Move to deterministic trajectory check | Structural |
| No conversation trace | Weak heuristic fallback | Fail scenario if no trace (trace is now standard) | Policy |
| Unmatched criterion text | Default `return True` | Log warning + UNKNOWN; require judge fallback | Hybrid |
| LLM tier not run (no API key) | Criteria never scored | Score as SKIP; separate from UNCERTAIN in reporting | Reporting |
| Truncated evidence | Judge lacks context | Smart truncation (extract salient sections) | Implementation |

### Smart truncation proposal

Instead of head-truncating transcript to 8KB:
1. Extract **first turn** (initial response, shows routing behavior)
2. Extract **all tool calls** with names and key args (compact representation)
3. Extract **error blocks** (shell commands with non-zero exit, ReadLints results)
4. Extract **harness interactions** (Read/Write of .harness/ files)
5. Append **last turn** (final state, commit discussion)

This preserves decision-critical moments while staying within token budget.

### feat-14 scope proposal

Based on this research, `feat-14` should be scoped as:

**Phase A** (high-value, low-risk):
- Build golden calibration set (30-50 labeled examples)
- Add "UNKNOWN" verdict to LLM judge
- Smart truncation for transcript input
- Confidence thresholding (confidence < 3 → UNCERTAIN)
- Per-dimension rubric prompts with anchor examples

**Phase B** (medium-value, after Phase A calibration validates):
- Deterministic trajectory tier (loop detection, read-before-write, skeleton matching)
- Move behavioral heuristics that have trace data to trajectory tier
- Reduce LLM judge scope to negotiation quality + nuanced trajectory assessment

**Phase C** (nice-to-have, deferred):
- Cross-family judge validation
- Production monitoring / online scoring
- Rule ablation mode in session_runner

---

## §5 Synthesis — Concrete Proposals

### Gap → Proposal traceability matrix

Every proposal in §2-§4 traces back to a specific §0 baseline gap:

| §0 Baseline gap | Proposal | Section |
|----------------|----------|---------|
| Default `return True` silently passes unmatched criteria (branch 27) | Kill default, require UNKNOWN/SKIP | §5 chore-uncertain-elimination |
| 7 UNCERTAIN verdicts across 3 scenarios | Confidence thresholding, UNKNOWN verdict, move to deterministic trajectory checks | §4 feat-14a |
| Behavioral heuristic branches 4/5 and 19/21 are duplicates | Merge duplicate branches | §5 gap-26 |
| High-fragility branches 10, 13, 16, 17 have broad regex | Tighten patterns, reduce false-positive surface | §5 gap-26 |
| Session boundary heuristic (branch 16) is primary UNCERTAIN source | Deterministic trace checks (skeleton matching, tool-call verification) | §3 feat-15 |
| No conversation trace → weak heuristic fallback | Policy: fail scenario if no trace (trace is now standard) | §4 UNCERTAIN elimination |
| Only 3 scenarios use trajectory_quality, all LLM-judged | 7 deterministic trajectory checks + trajectory tier | §3 feat-15 |
| No rule A/B testing — can't measure if rules improve behavior | Ablation mode with paired Wilcoxon test | §2 feat-16 |
| check_skill_activation() has no scenarios | Skill quality scenarios testing agent reads SKILL.md | §2 chore-skill-scenarios |
| LLM judge: 8KB head-truncation loses key moments | Smart truncation (first turn + tool calls + errors + last turn) | §4 feat-14a |
| LLM judge: single prompt for all criteria | Per-dimension rubric prompts with anchor examples | §4 feat-14a |
| LLM judge: no calibration against human labels | Golden calibration set of 30-50 labeled examples | §4 feat-14a |
| enforce-progress.sh has zero dedicated scenario coverage | Not directly addressed — lower priority than structural judge fixes | §0 (gap noted) |
| verify-harness self-verify bypass (agent sets verified:true) | Document as known debt; sandbox hardening proposal from Berkeley audit | §1 (noted) |

### What to steal from external frameworks

| Source | Pattern | Adaptation for our pipeline |
|--------|---------|----------------------------|
| **Inspect AI** | Hook lifecycle events + approval policies | Our hooks already do this; adopt their limit system (token/cost budgets per scenario) |
| **Inspect AI** | Task schema versioning | Add `schema_version` field to scenario YAML for backward compat |
| **METR** | Portable task format with `score()` function | Our `verify:` commands are similar; formalize into a deterministic score function per scenario |
| **Braintrust** | Pass thresholds per scorer in CI | Add `--fail-threshold 0.85` to session_judge for CI gating |
| **Braintrust** | Production traces → dataset feedback loop | Capture interesting eval failures as new scenario seeds |
| **LangSmith** | Trajectory match modes (strict/subset/superset) | Implement skeleton matching in trajectory tier |
| **LangSmith** | AgentEvals Kendall's tau for ordering | Add to trajectory tier for ordering-sensitive scenarios |
| **trajectly** | `require_before` ordering contracts | Add to scenario YAML as `trajectory_skeleton` |
| **trajscore** | Loop detection + step efficiency metrics | Add to trajectory tier as deterministic checks |
| **Anthropic** | Per-dimension rubrics with anchors | Restructure `judge_with_llm()` prompt |
| **Anthropic** | "Unknown" escape for insufficient evidence | Add UNKNOWN verdict to LLM judge |
| **Arize/Evidently** | Binary scoring + calibration against gold set | Keep PASS/FAIL; build golden calibration set |
| **prompt-eval-arena** | Paired Wilcoxon + Cohen's d | Use for rule ablation statistical testing |
| **Berkeley RDI** | Adversarial evaluation environment | Document verify-harness self-verify debt; design sandbox hardening |

### Proposed follow-up tasks for state.json

| Task ID | Type | Priority | Description |
|---------|------|----------|-------------|
| `feat-14a` | feature | 2 | LLM judge Phase A: golden calibration set + UNKNOWN verdict + smart truncation + per-dimension rubrics |
| `feat-15` | feature | 2 | Trajectory tier: deterministic tool-call checks (loop detection, read-before-write, skeleton matching, step efficiency) |
| `feat-16` | feature | 3 | Rule ablation mode: `--ablate-rule` flag in session_runner.py for paired A/B comparison |
| `chore-uncertain-elimination` | chore | 2 | Kill default `return True` in _evaluate_behavioral(); require explicit handling or UNKNOWN for unmatched criteria |
| `chore-skill-scenarios` | chore | 3 | Create 2-3 scenarios with skill_activation rubric to test skill quality |
| `gap-26` | bug | 2 | Behavioral heuristic dedup: merge branches 4/5, 19/21; reduce false-positive surface of high-fragility branches 10, 13, 16, 17 |

### Priority ordering

1. **chore-uncertain-elimination** (P2) — highest signal/effort ratio. Killing `return True` default immediately surfaces hidden failures.
2. **feat-15 trajectory tier** (P2) — deterministic trajectory checks reduce LLM judge dependency and catch loop/thrashing failures.
3. **feat-14a LLM judge Phase A** (P2) — calibration set is prerequisite for trusting any LLM judge improvements.
4. **gap-26 heuristic dedup** (P2) — reduces maintenance burden and false-positive surface.
5. **feat-16 rule ablation** (P3) — valuable but not blocking; can use manual A/B runs in the meantime.
6. **chore-skill-scenarios** (P3) — nice-to-have; skill routing is IDE-only, limited in SDK bridge.

### Architecture after implementing proposals

```
Scenario YAML (seed_files, prompts, verify, trajectory_skeleton, rubric)
        │
        ▼
sandbox.py: git init, copy .cursor/, optional rule ablation
        │
        ▼
session_runner.py: SDK bridge, agent sends, artifact capture
        │
        ▼
session_judge.py:
  ├── computational tier (existing: harness + contract checks)
  ├── structural tier (existing: artifact + behavioral heuristics)
  ├── trajectory tier (NEW: loop detection, skeleton matching, efficiency)
  └── llm tier (IMPROVED: per-dimension rubrics, UNKNOWN verdict, smart truncation)
        │
        ▼
Pass threshold gate: --fail-threshold for CI
        │
        ▼
session_report.py: 6 dimensions (harness, contract, artifact, behavioral, trajectory, negotiation)
```

---

## References

### Academic
- SWE-bench: Jimenez et al., 2023 — https://swebench.com
- SWE-bench Pro: Scale AI, 2025 — decontaminated variant
- AgentBench: Liu et al., 2023 — https://github.com/THUDM/AgentBench
- Berkeley RDI benchmark audit, 2026 — https://rdi.berkeley.edu/blog/trustworthy-benchmarks-cont/
- METR Task Standard — https://github.com/METR/task-standard
- METR Time Horizons paper, 2025-2026 — https://metr.org
- "Bias and Uncertainty in LLM-as-a-Judge Estimation" (arXiv 2605.06939)
- "Prompt Optimization Is a Coin Flip" (arXiv 2604.14585)

### Industry frameworks
- Inspect AI (UK AISI) — https://inspect.aisi.org.uk
- Braintrust — https://braintrust.dev/docs/evaluate
- LangSmith / AgentEvals — https://docs.langchain.com/langsmith/trajectory-evals
- trajscore — https://pypi.org/project/trajscore/
- trajectly — https://github.com/trajectly/trajectly
- prompt-eval-arena — https://github.com/lcosent/prompt-eval-arena

### Vendor guides
- Anthropic: "Demystifying evals for AI agents" — https://anthropic.com/engineering/demystifying-evals-for-ai-agents
- Anthropic: "Building evals" — https://platform.claude.com/cookbook/misc-building-evals
- Arize: "LLM as a Judge" — https://arize.com/llm-as-a-judge
- Evidently AI: "LLM-as-a-judge guide" — https://evidentlyai.com/llm-guide/llm-as-a-judge
- Langfuse: "LLM-as-a-Judge" — https://langfuse.com/docs/evaluation/evaluation-methods/llm-as-a-judge
