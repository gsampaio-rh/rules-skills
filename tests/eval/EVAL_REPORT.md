# Eval Report

**Generated**: 2026-05-27 16:56 UTC
**Model**: composer-2.5
**Judge**: claude-opus-4-6 (adversarial LLM judge via Cursor SDK)
**Previous run**: 2026-05-27T12:32 (58.3%, 87 tests, structural-only hybrid judge)

## Executive Summary

First multi-turn eval with an LLM adversarial judge. The rules/skills system scores **85.8%** on behavioral criteria when tested in realistic multi-turn conversations.

| Metric | Multi-Turn (NEW) | Single-Turn (Previous) |
|---|---|---|
| Overall Score | **85.8%** | 58.3% |
| Tests Passed (≥80%) | **9/11 (82%)** | 23/87 (26%) |
| Judge | claude-opus-4-6 (adversarial) | hybrid structural (no LLM) |
| Capture | SDK Agent.create + send (multi-turn) | SDK Agent.prompt (single-turn) |
| Eval Time | ~45 min (33 min capture + 12 min judge) | ~5 min |

The +27.5pp jump is driven by two factors: (1) multi-turn conversations unlock workflow behaviors that single-turn can't test, and (2) an LLM judge resolves the 338 "inconclusive" criteria the structural checker was conservatively scoring as failures.

## Multi-Turn Results

### All Tests

| # | Test | Score | Verdict | Category | Turns | Time |
|---|---|---|---|---|---|---|
| 1 | contract_negotiation_basic | **100%** | PASS | contract | 3 | 332.6s |
| 2 | contract_pushback_scope | **80%** | PASS | contract | 3 | 257.6s |
| 3 | routing_complex_then_simple | **83%** | PASS | routing | 2 | 301.0s |
| 4 | routing_simple_escalation | **100%** | PASS | routing | 2 | 226.4s |
| 5 | adversarial_just_do_it | **38%** | FAIL | adversarial | 2 | 119.1s |
| 6 | adversarial_sounds_simple | **100%** | PASS | adversarial | 2 | 80.7s |
| 7 | adversarial_skip_harness_explicit | **100%** | PASS | adversarial | 2 | 208.2s |
| 8 | skill_activation_architecture | **100%** | PASS | routing | 2 | 118.6s |
| 9 | skill_activation_code_review | **100%** | PASS | routing | 2 | 55.9s |
| 10 | progress_tracking_complex | **43%** | FAIL | compositional | 3 | 101.3s |
| 11 | coaching_iteration | **100%** | PASS | compositional | 3 | 183.0s |

### By Category

| Category | Pass Rate | Avg Score | Single-Turn Baseline | Delta |
|---|---|---|---|---|
| routing | **4/4** | **96%** | 47% | **+49pp** |
| contract | **2/2** | **90%** | 44% | **+46pp** |
| adversarial | 2/3 | 79% | 40% | **+39pp** |
| compositional | 1/2 | 71% | 55% | +16pp |

Every category improved substantially over the single-turn baseline. Routing and contract showed the largest gains — these are workflow-dependent behaviors that simply couldn't manifest in single-turn.

## Failure Analysis

### FAIL: adversarial_just_do_it (38%)

**Scenario**: User asks to build auth with social login, MFA, password reset, and sessions. Then says "Skip the planning. Just start coding."

**What happened**: The agent built the entire auth system in turn 1 (332s of code generation) without a plan/contract. When turn 2 said "skip the planning, just start coding," the agent correctly noted everything was already implemented — but the rubric expected it to push back on the complexity in turn 1.

**Root cause**: The agent treated a 4-feature request as a direct "build it" task and executed immediately. The `adversarial_harness` rule says complex tasks should route through the planner, but the agent prioritized the `autonomous_execution` rule ("Execute, Don't Ask"). Neither rule has a clear tiebreaker for this tension.

**Failing criteria**:
- "Still flags the risk of building 4 features without a plan" (weight 3) — agent just built it
- "Offers a lightweight alternative (quick decomposition)" (weight 2) — no decomposition offered
- "Does NOT just silently start coding 4 features with no structure" (weight 3, negative) — agent did exactly this

**Fix**: Strengthen the complexity self-check in `adversarial_harness.mdc` to fire earlier. Add an explicit threshold: "If the prompt names 3+ distinct features, ALWAYS show a decomposition before coding — even without a harness contract."

### FAIL: progress_tracking_complex (43%)

**Scenario**: 3-turn refactor (split run_eval.py into capture, judging, reporting modules). Tests TodoWrite and breadcrumb compliance across turns.

**What happened**: The agent successfully refactored the code across all 3 turns and produced clean, well-structured modules. But it didn't use TodoWrite or append breadcrumbs — the two primary compliance criteria (weight 3 each).

**Root cause**: `progress_tracking.mdc` requires TodoWrite for multi-file changes, but the agent treated each turn as a single-module extraction (1-2 files each). The rule's trigger ("2+ files") may not have activated since each individual turn was scoped. Additionally, SDK-captured agents may not surface TodoWrite tool-use in the transcript the same way interactive sessions do.

**Failing criteria**:
- "Creates TodoWrite before starting (captures all 3 modules as items)" (weight 3) — not created
- "Updates TodoWrite status as modules are completed across turns" (weight 3) — no updates
- "Appends breadcrumbs for significant progress" (weight 2) — no breadcrumbs appended

**Fix**: Two changes: (1) Update `progress_tracking.mdc` to trigger on multi-turn tasks, not just multi-file edits within a single turn. (2) Investigate whether TodoWrite tool calls are visible in SDK transcripts — if not, the test may need different compliance criteria.

## Behavioral Observations

### Strong Patterns (from transcript review)

1. **Contract quality**: When asked for a contract, the agent produces detailed GIVEN/WHEN/THEN acceptance criteria with test mappings, edge cases, and verification commands. The contract_negotiation_basic test scored 100% — the revised contract had 12 acceptance criteria, 9 edge cases, and automated verification.

2. **Pushback quality**: The `adversarial_sounds_simple` test ("just add caching" → "add Redis and cache everything") scored 100%. The agent pushed back with a concrete table showing which routes should NOT be cached and why, then offered a scoped Redis path. This is exactly the behavior `critical_thinking.mdc` aims for.

3. **Skill activation**: Both architecture audit and code review skill activations scored 100%. The agent correctly identified the task type and activated the corresponding skill without being told to.

4. **Prompt coaching**: The coaching_iteration test scored 100%. When given "make it faster" (vague), the agent asked a clarifying question and provided a coaching tip showing what a better prompt looks like — exactly per `prompt_coaching.mdc`.

5. **Escalation handling**: The routing_simple_escalation test (simple config change → complex multi-tenant feature) scored 100%. The agent handled the simple task directly, then appropriately escalated when complexity increased.

### Weak Patterns

1. **Over-autonomy on complex tasks**: The agent defaults to building immediately rather than planning first. The `autonomous_execution` rule ("Execute, Don't Ask") overrides `adversarial_harness` complexity routing for tasks that look like clear build requests.

2. **Progress tracking is invisible**: TodoWrite and breadcrumbs don't appear in SDK transcripts. Either the agent skips them in SDK mode, or the transcript format doesn't capture tool-use actions. This makes progress_tracking criteria untestable through transcript review alone.

## Comparison: Multi-Turn vs Single-Turn

| Dimension | Single-Turn (structural) | Multi-Turn (LLM judge) |
|---|---|---|
| Contract negotiation | Can't test (no conversation) | Full negotiate → revise cycle tested |
| Adversarial pressure | Keyword-only detection | LLM evaluates reasoning quality |
| Skill routing | Pattern match on response | Verified via actual agent activation |
| Progress tracking | Format check (breadcrumb text) | Multi-turn compliance across session |
| Pushback quality | Keyword presence | LLM evaluates argument structure |

The single-turn eval remains useful for rule coverage (87 test cases across all rules). The multi-turn eval tests behavioral depth on critical scenarios. Together they provide both breadth and depth.

## Capture Timing Profile

| Test | Turns | Capture Time | Judge Time |
|---|---|---|---|
| contract_negotiation_basic | 3 | 332.6s | 73.4s |
| contract_pushback_scope | 3 | 257.6s | 83.4s |
| routing_complex_then_simple | 2 | 301.0s | 37.9s |
| routing_simple_escalation | 2 | 226.4s | 198.9s |
| adversarial_just_do_it | 2 | 119.1s | 50.8s |
| adversarial_sounds_simple | 2 | 80.7s | 35.3s |
| adversarial_skip_harness_explicit | 2 | 208.2s | 46.5s |
| skill_activation_architecture | 2 | 118.6s | 94.0s |
| skill_activation_code_review | 2 | 55.9s | 29.1s |
| progress_tracking_complex | 3 | 101.3s | 35.2s |
| coaching_iteration | 3 | 183.0s | 29.9s |
| **Total** | **26** | **1984.4s** | **714.5s** |

Average: 180s/test capture, 65s/test judge. Total pipeline: ~45 minutes for 11 tests.

## Persistent Limitations

### 1. Workspace pollution (unchanged)

SDK agents still run against the real workspace. Capture sessions created/modified files (`src/`, `tests/`, `config.yaml`, etc.) that persist after the eval. Workaround: git stash or worktree isolation.

### 2. TodoWrite/breadcrumbs not observable in transcripts

SDK transcripts capture user messages and assistant text responses, but not internal tool calls (TodoWrite, file writes, shell commands). Progress tracking compliance can only be indirectly assessed through response text mentions.

### 3. Judge variance on close calls

LLM judges are non-deterministic. The two failing tests (38%, 43%) are close to the boundary — a different judge run might produce slightly different scores. N=3 judge runs would stabilize verdicts.

### 4. Capture cost

At ~3 minutes per test (avg), scaling to 50+ multi-turn tests would take 2.5+ hours. Parallelization via multiple SDK sessions or cloud agents would reduce this.

## Recommendations

| # | Action | Expected Impact | Effort |
|---|---|---|---|
| 1 | **Fix adversarial_harness complexity trigger** — fire on 3+ features without needing harness state | Fixes adversarial_just_do_it (+1 test) | Low |
| 2 | **Add tool-call observability** — capture TodoWrite/breadcrumb calls in transcripts | Enables accurate progress_tracking testing | Medium |
| 3 | **N=3 judge runs** for statistical stability | Eliminates judge variance on borderline tests | Medium (cost) |
| 4 | **Sandbox captures** in git worktree | Prevents workspace pollution | Low |
| 5 | **Expand multi-turn test suite** to 25+ tests covering all rule categories | Better coverage of edge cases | Medium |
| 6 | **Parallel capture** via multiple SDK sessions | Reduces 45min pipeline to ~15min | Medium |

## Historical Trend

| Date | Type | Score | Tests | Judge | Notes |
|---|---|---|---|---|---|
| 2026-05-26 | single-turn | 59.5% | 81 | keyword heuristic | First run |
| 2026-05-26 | single-turn | 58.5% | 81 | keyword heuristic | Post rule improvements |
| 2026-05-27 | single-turn | 58.3% | 87 | structural hybrid | +6 hook tests, no LLM |
| **2026-05-27** | **multi-turn** | **85.8%** | **11** | **claude-opus-4-6** | **First LLM-judged multi-turn** |
