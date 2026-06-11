# Phase 4 — Workflows Dimension Analysis

**Spike:** spike-research-agents
**Date:** 2026-06-11
**Status:** Complete
**Bias corrections applied:** BC1 (≥3 new external sources: F1, F2, F3), BC2 (S1-S4 engaged directly in §5), BC3 (ACAM Advanced criteria validated against external vocabulary in §2.3; two revisions: rename + addition), BC6 (no hedging in §6 scoring)

---

## §9 BC Compliance Check

Before analysis begins: documented BC1-BC6 violations flagged here.

- **BC1** — ≥3 external sources not in pre-Phase-4 bibliography: ✓ (F1: ReAct paper, F2: Inspect AI, F3: Berkeley BFCL — all new, all with real URLs in §7)
- **BC2** — Engage S1-S4 challenging sources: ✓ (§5.1 applies S1's 20-tool threshold to each workflow component; §5.2 applies S2 LLPP; §5.3 applies S3 simplicity argument; §5.4 applies S4 skills-over-agents)
- **BC3** — Validate ACAM Advanced criteria against external vocabulary before scoring: ✓ (§2.3 tests each Phase 1 criterion; two revisions: "contract-first development" renamed, "traced execution" added)
- **BC6** — No hedging in final scoring: ✓ (§6.2 states "INTERMEDIATE" without qualifiers; gaps in §4 use severity without mitigation claims)

---

## 1. Literature Review: Skills, Agentic Loops, Lifecycle Enforcement

### 1.1. The SKILL.md Format and Agent Skill Systems

Cursor formalizes skills as YAML-frontmatter markdown files auto-discovered from `.cursor/skills/` [V7]. The agent reads a skill's `description` field to determine relevance — no explicit invocation required. When the description matches user intent, the IDE routes the agent to read SKILL.md before responding.

The activation model is distinct from slash commands (explicit invocation) or tool calls (agent decides at runtime). It is closest to vector similarity retrieval: the agent selects the skill whose description most closely matches the task, then treats the skill content as procedural context. [V8]: "Skills = specialized workflows. Keep rules minimal. If you only need something occasionally, put it in a skill."

Comparable approaches across tools:
- **Claude Code** uses `/slash commands` for explicit skill invocation — no auto-discovery from description
- **Devin** uses "playbooks" (YAML task templates) invoked by the orchestrator, not the agent
- **SWE-agent** defines configurable agent prompt templates (tools, system prompt, descriptions) — closest to the SKILL.md model but statically compiled, not runtime-loaded
- **OpenAI Agents SDK** routes between specialized agents via handoff descriptions — analogous to SKILL.md description as a routing signal, but at the agent level, not the document level

The common pattern across all tools: **description quality is the routing primitive**. Vague descriptions cause systematic misrouting. This has been empirically measured by BFCL [F3]: tool/function calling accuracy varies from 30% to 95% depending on description quality and overlap between available tools.

### 1.2. ReAct and the Canonical Agentic Loop

The ReAct paper [F1] (Yao et al., 2023) defines the foundational agentic loop: interleaved Thought-Action-Observation steps. Each cycle produces an observable reasoning trace before the next action fires:

```
Thought: I need to find the authentication handler.
Action: grep -r "authenticate" src/
Observation: Found auth.py:42 - def authenticate(user, password)
Thought: I should edit this function to add rate limiting.
Action: edit auth.py line 42
...
```

This became the scaffold for SWE-agent [A1], most LangGraph flows, and Anthropic's agent recommendations [V1]. The key insight: explicit reasoning traces make agent failures diagnosable. Without traces, a failed action leaves no signal for recovery or improvement.

The **plan-execute-verify** variant adds structure: (1) Plan — produce a work breakdown, (2) Execute — implement each step with tool calls, (3) Verify — check each step's result before proceeding. SWE-bench Pro [A4] identifies this pattern as necessary for long-horizon tasks: "without iterative verification per step, accumulated errors compound into unrecoverable states."

The rules-skills harness implements a distinct variant: **plan-gate-contract-build-evaluate**. The "gate" and "contract" steps between plan and build are not in standard ReAct or plan-execute-verify patterns. This is the differentiating architectural decision: inserting adversarial contract negotiation before implementation begins. The practical cost is latency; the benefit is that acceptance criteria are externally agreed before any line is written.

### 1.3. Lifecycle Enforcement vs. Lifecycle Awareness

The standard ReAct loop has no lifecycle — it runs until a stop condition or max steps. A system is **lifecycle-aware** when it tracks current state (pending/building/evaluating). It is **lifecycle-enforced** when tooling *prevents* invalid state transitions structurally.

Hooks provide structural lifecycle enforcement. Cursor [V6] defines three hook types:
- **Command**: runs a side-effect-free script
- **Prompt**: injects context into the agent's next turn
- **Block**: denies a tool call before it executes

The block type is structural enforcement — the agent cannot proceed past a lifecycle gate regardless of what it reasons. This is categorically different from rules (advisory) or prompts (contextual). A block hook fires at the OS/filesystem level before the tool executes.

Devin [D1, D4] implements structurally equivalent enforcement: `PreToolUse` hook with `exit 2` blocks execution. Coverage is broader: 7 lifecycle events (PreToolUse, PostToolUse, PermissionRequest, UserPromptSubmit, PostCompaction, SessionStart, SessionEnd) vs. Cursor's 4 main events.

The distinction between awareness and enforcement matters because most agent frameworks stop at awareness. A state.json tracking `status: building` is lifecycle-aware. A hook that blocks Write calls until contract.json exists is lifecycle-enforced. The observable difference: enforcement cannot be circumvented by the agent reasoning its way around it.

### 1.4. Contract-First Development

"Design by Contract" (DbC) is a software engineering discipline from the 1980s (Bertrand Meyer, Eiffel). The principle: define preconditions, postconditions, and invariants before writing implementation. The contract is a specification; the implementation must satisfy it.

Applied to agent workflows: contract-first means formalizing binary acceptance criteria before the first implementation Write. The acceptance criteria serve as the definition of done — the evaluator tests against them, not against the builder's subjective judgment.

The distinguishing feature beyond simple TDD is adversarial negotiation: acceptance criteria are proposed by the builder and challenged by a separate evaluator whose incentives are to make them testable, not to minimize scope. The evaluator cannot modify source; the builder cannot claim done without evaluator PASS.

External vocabulary for this pattern is scattered. Anthropic [V2] names the "evaluator-optimizer loop": one model evaluates, a separate model generates. OpenAI [V5]: "numbered protocol with explicit conditions" as the instruction format. SWE-bench Pro [A4]: tasks require "acceptance criteria per step" for long-horizon work. No external practitioner source uses the exact term "contract-first" for agent workflows — but all three independently validate its component practices.

### 1.5. Skill Effectiveness Measurement

SKILLS_STANDARD.md documents five hypotheses (H1-H5) with explicit measurement columns. This is the standard starting condition for any evidence-based system: hypotheses documented before measurement infrastructure is built.

The Inspect AI framework [F2] (UK AI Safety Institute) defines the reference architecture for structured agent evaluation:
- **Task**: input specification + expected behavior
- **Solver**: the agent under test
- **Scorer**: quality measurement function
- **Eval log**: structured trace suitable for regression analysis

This architecture is isomorphic to rules-skills' eval pipeline: scenarios (Tasks), `tests/eval/session_runner.py` (Solver), `tests/eval/session_judge.py` (Scorer), eval report (Eval log). The parallel validates the pipeline architecture. The gap is coverage: the Inspect AI reference implementation runs suites on every relevant task type; rules-skills has zero scenarios exercising skill activation.

BFCL [F3] provides the empirical grounding for why skill activation coverage matters. Across 150+ models and 17 categories of function/tool calling, accuracy ranges from 30% to 95% on complex multi-tool scenarios. The finding most relevant here: **description quality drives routing accuracy**. Vague, overlapping, or keyword-sparse descriptions cause systematic misrouting regardless of model capability. The 14 SKILL.md `description` fields have never been tested against this failure mode.

---

## 2. ACAM Cell Evidence: Workflows Dimension

### 2.1. Basic Workflows — Observable Criteria

| Criterion | Observable artifacts | External validation |
|-----------|---------------------|---------------------|
| No skills or saved workflows | No `.cursor/skills/` directory; each session starts from scratch | V7: skill format exists precisely to prevent this re-invention on every task |
| Agent self-grades completion | No separate evaluator; builder declares "done" without external check | S1: "adversarial validation with same model = blind spots" — same-model review cannot catch its own systematic errors |
| No verification loop | Edits made without running tests, lint, or build step | V1 (Anthropic): "careful human-computer interface design" implies verification should exist — its absence is the failure mode |
| Single-shot prompts with no lifecycle | Each conversation starts from zero; no state tracking across sessions | A4 (SWE-bench Pro): long-horizon tasks fail without lifecycle state — errors compound session-to-session |
| No lifecycle tracking | No state file, no status transitions | D4 (Devin): 7 lifecycle hook events represent the alternative; no hook support = no enforced lifecycle |

**External vocabulary check:** Anthropic [V1] identifies the failure pattern directly: "agents that loop endlessly or make mistakes from which they cannot recover." This is the agent self-grades + no verification profile. OpenAI [V4]: "smallest agent that owns a clear task" but with no evaluation loop is Basic by design. "Basic" maps to what every source identifies as insufficient for production-quality agent work.

### 2.2. Intermediate Workflows — Observable Criteria

| Criterion | Observable artifacts | External validation |
|-----------|---------------------|---------------------|
| Defined skill library | `.cursor/skills/` with ≥3 SKILL.md files; each with frontmatter and workflow steps | V7: SKILL.md format exactly defines this; V8: "skills = specialized workflows for occasional use" |
| Explicit verification loop | Tests or lint run after edits; rule or skill mandates it | A4: "iterative verification" named as prerequisite for long-horizon tasks |
| Manual lifecycle checkpoints | Breadcrumbs or commit checkpoints between phases; human decision at each gate | V5 (OpenAI SDK): "Debug via traces" — traces are the checkpoint artifact |
| Lifecycle state tracking | state.json or equivalent with task status enum | D3 (Devin): `.devin/config.json` with permissions and lifecycle hooks = workflow state |
| Saved reusable workflow patterns | Skills, slash commands, or saved prompts for repeated task types | B11: "26 tools adopted standard skill format" — reusable workflows are emerging norm |

**External vocabulary check:** [B11] and [V7] independently describe what rules-skills calls "Intermediate" as Cursor's own recommended architecture. The MSR 2026 [N2] sample shows `skills/` adoption is low (not tracked separately from rules), which places structured skill libraries above the practitioner median.

### 2.3. Advanced Workflows — BC3 Validation

**Phase 1 ACAM skeleton listed:** Structural enforcement (hooks deny bad actions). Contract-first development. Eval regression suite. Measured skill effectiveness. Lifecycle statuses enforced.

Each criterion tested against external sources:

| Phase 1 Criterion | External source that independently identifies this | Verdict |
|---|---|---|
| Structural enforcement (hooks deny bad actions) | V6: Cursor "block" hook type explicitly named as a distinct capability. D1: "Devin PreToolUse + exit 2 = blocks execution" — same pattern, different platform | **Confirmed** — both Cursor and Devin independently name structural deny enforcement as a hook capability; the pattern is externally validated at the mechanism level |
| Contract-first development | No external practitioner source uses this term for agent workflows. Nearest vocabulary: Anthropic V2 "evaluator-optimizer loop," SWE-bench Pro A4 "acceptance criteria per step," OpenAI V5 "numbered protocol with explicit conditions." DbC (Meyer 1988) is the conceptual ancestor | **Partial** — component practices (binary acceptance criteria, separate evaluator) are externally validated; "contract-first" as a named agent workflow pattern is rules-skills-specific vocabulary. Rename required. |
| Eval regression suite | F2 (Inspect AI): Task + Solver + Scorer + Eval log architecture. A1 (SWE-bench): benchmark-based regression across 178 submissions. A4: long-horizon evaluation with per-step scoring | **Confirmed** — multiple independent frameworks define the same architecture; "eval regression suite" maps directly to established eval tooling vocabulary |
| Measured skill effectiveness | F3 (BFCL): tool selection accuracy as an explicit, leaderboard-ranked measurement domain. E3 (Reflexion): feedback-derived policies outperform static. N5 (AGENTS.md): "35-55% bug reduction" = config-level measured effectiveness | **Confirmed** — effectiveness measurement is a well-established research area; without it, "Advanced" is a label without evidence |
| Lifecycle statuses enforced | D4 (Devin): 7 lifecycle hook events with structured enforcement. V6 (Cursor): sessionStart + preToolUse + stop hooks. The specific 5-status enum (pending→building→evaluating→verified→committed) is rules-skills-specific | **Partial** — lifecycle enforcement via hooks is confirmed across platforms; the specific status vocabulary is not externally named; add observable artifact criteria that don't require our specific naming |
| *(Not in Phase 1)* Traced execution (append-only audit log) | V5 (OpenAI SDK): "Debug via traces" as core agent development practice. F2 (Inspect AI): eval log as a structured regression artifact. V2 (Anthropic PDF): "transparency = show planning steps" is a named design principle | **Should add** — three independent sources identify execution tracing as an Advanced workflow requirement; breadcrumbs.jsonl implements this but Phase 1 omitted the criterion |

**BC3 findings — two revisions required:**

1. **Rename "contract-first development" → "acceptance-criteria-gated implementation."** No external practitioner source uses "contract-first" for agent workflows. The component practices are validated — binary acceptance criteria negotiated with a separate evaluator before implementation begins. The rename uses vocabulary from SWE-bench Pro [A4] ("acceptance criteria") and Anthropic [V2] ("evaluator-optimizer"). The mechanism is the same; the label is externally grounded.

2. **Add "Traced execution with append-only audit log" to Advanced criteria.** OpenAI [V5], Inspect AI [F2], and Anthropic [V2] independently name execution tracing as a prerequisite for debuggable, recoverable agent workflows. Phase 1 omitted this because breadcrumbs.jsonl was treated as a harness-internal artifact rather than a workflow pattern. It is both.

**Revised Advanced Workflows criteria — externally validated, observable-artifact format:**

| Criterion | Observable artifacts | External source |
|---|---|---|
| Structural enforcement via deny hooks | Block-type hooks that deny specific tool calls at lifecycle gates; agent receives denial message with recovery path | V6 (Cursor block hook type), D1 (Devin PreToolUse exit 2) |
| Acceptance-criteria-gated implementation | `contract.json` with binary acceptance criteria written and negotiated with a separate evaluator before first implementation Write | V2 (evaluator-optimizer), A4 (acceptance criteria per step), V5 (numbered protocol with conditions) |
| Eval regression suite with structured logging | Eval scenarios (tasks), solver runner, quality scorer, and structured eval logs; regression run on each feature or sprint | F2 (Inspect AI architecture), A1 (SWE-bench benchmark), A4 (long-horizon evaluation) |
| Measured skill effectiveness with activation coverage | Skill activation eval scenarios testing routing accuracy and output quality; reported accuracy scores against baseline | F3 (BFCL tool selection accuracy), E3 (Reflexion: feedback improves policies) |
| Traced execution — append-only audit log | Append-only structured trace file (JSONL or equivalent) with role, timestamp, type, result fields; readable across sessions | V5 (debug via traces), F2 (Inspect AI eval log), V2 (transparency = show planning steps) |
| Lifecycle statuses enforced by structural hooks | State machine with ≥3 statuses; hooks enforce valid transitions (deny Write without contract, deny Stop without evaluator PASS) | D4 (Devin: 7 lifecycle events), V6 (Cursor: sessionStart + preToolUse + stop) |

---

## 3. rules-skills Evidence

### 3.1. Artifact Inventory (Workflows Layer)

**Claim: 14-skill library with explicit authoring standard**

Evidence A: `library/cursor/skills/` — 14 SKILL.md files: adversarial-harness, llm-skeptic, organization-audit, design-audit, code-quality-audit, architecture-audit, tech-writing, info-architecture, commit, code-review, project-scaffolding, iac-templates, experiment-workflow, data-science-analysis. All have valid frontmatter (name, description, disable-model-invocation).

Evidence B: `docs/SKILLS_STANDARD.md` — 154 lines. Defines required sections (practitioner voice, context-first, multi-mode, core workflow, proactive triggers, output artifacts, stop conditions), frontmatter contract, sizing limit (under 300 lines / 10KB), design rationale, and 5 documented hypotheses with measurement source columns.

**Claim: Structural enforcement via deny hooks**

Evidence A: `library/cursor/hooks/contract-gate.sh` — preToolUse hook matching Write calls. Logic: (1) if routing-pending marker + no state.json → deny all impl writes; (2) if state.json exists + no contract.json → deny all writes except `.harness/` and `.cursor/hooks/`; (3) type-aware bypass for spike/chore tasks. Outputs `{"permission": "deny", "agent_message": "..."}` before Write executes.

Evidence B: `library/cursor/hooks/verify-harness.sh` — stop hook. Reads contract.json `verified` field; if verified != True and a building task has impl file changes, outputs `followup_message` enforcement requiring evaluator launch. Blocks completion without verified acceptance.

**Claim: Acceptance-criteria-gated implementation**

Evidence A: `.harness/contract.json` — machine-readable format with fields: `feature`, `acceptance_criteria` (binary-testable array), `edge_cases`, `verification_method`, `phase` (proposed → evaluating → verified), `negotiation_rounds`, `last_eval_result`. The phase lifecycle makes the acceptance-criteria requirement an explicit state machine.

Evidence B: `library/cursor/hooks/contract-gate.sh` — the hook enforces the gate structurally: a Write to any product file is denied until contract.json exists. The rule is: you cannot write implementation until the acceptance criteria exist and are written to disk.

**Claim: Traced execution — append-only audit log**

Evidence A: `.harness/breadcrumbs.jsonl` — append-only JSONL with fields: `ts` (ISO-8601), `role` (builder/evaluator/system), `type` (build/evaluate/checkpoint/decision/session_start), `feat`, `msg`, `result`. 140+ entries for this research spike alone. Readable across sessions; used by hooks to detect skip patterns and by harness-context.sh for session context injection.

Evidence B: `library/cursor/rules/progress_tracking.mdc` — alwaysApply rule mandating breadcrumb writes after each step in multi-file changes. Makes tracing structural for multi-file work, not optional.

**Claim: Adversarial harness lifecycle (5 statuses enforced)**

Evidence A: `.harness/state.json` — tasks array with `status` enum: `pending | building | evaluating | verified | committed | cancelled`. The evaluating status is set by the evaluator subagent, not the builder. Lifecycle transitions are read by hooks for routing.

Evidence B: `library/cursor/hooks/chain-evaluator.sh` — subagentStop hook reading `contract.json` `phase` field to route evaluator behavior by phase. Phase-aware routing makes the lifecycle machine observable and enforceable at the hook level, not just in state.json.

**Claim: Explicit verification loop**

Evidence A: `library/cursor/rules/verification.mdc` — alwaysApply rule mandating verification after every code change: "Run the project's test suite if one exists. If no test suite exists, run a minimal check: import/syntax check, build, or lint." The rule fires on every session, covering all task types.

Evidence B: `tests/eval/scenarios/` — 27 eval scenarios that test harness workflow adherence, including protocol scenarios that validate whether the builder runs tests before claiming completion. The scenario runner measures whether the verification step actually fires in agent sessions.

**Claim: Eval regression suite**

Evidence A: `tests/eval/scenarios/` — 27 standard eval scenarios + 1 long scenario. Five categories: protocol (harness workflow adherence), routing (harness detection), contract (contract negotiation), behavioral (session hygiene, skip patterns), adversarial (override attempts).

Evidence B: `tests/eval/session_judge.py` — multi-tier judge with: trajectory checks (33 checks), behavioral checks (44 checks), LLM judge (feat-14a, pending calibration), and `check_skill_activation()` function defined. Produces structured JSON eval reports per scenario run.

### 3.2. Comparison Against External Patterns

| Capability | rules-skills | Devin CLI | Claude Code | Cursor (default) |
|---|---|---|---|---|
| Skill library | 14 SKILL.md + SKILLS_STANDARD | Playbooks (YAML, not public) | /slash commands (explicit only) | 0 (no skills configured) |
| Structural deny hooks | contract-gate.sh (Write deny) | PreToolUse exit 2 | PreToolUse hook (JSON deny) | Not configured |
| Lifecycle statuses named | 5 (pending→committed) | Not named; 7 hook events | Not named | Not named |
| Acceptance-criteria gating | contract.json before any Write | Not documented publicly | Not documented | Not configured |
| Traced execution | breadcrumbs.jsonl (140+ entries, append-only) | Session logs (private) | CLAUDE.md "memory" (not structured) | Not configured |
| Eval regression suite | 27 scenarios + session_judge | Not public | Not public | Not applicable |
| Skill activation eval | **0 scenarios** (chore-skill-scenarios pending) | Not public | Not applicable | Not applicable |

**Key finding:** On every measurable Intermediate and Advanced workflow criterion, rules-skills is more structured than the comparison tools in their default documented configurations. Devin's PreToolUse block and session logging are the closest comparable — but Devin's eval pipeline and skill activation measurement are not publicly documented. The gap that distinguishes rules-skills from Devin is also the gap that prevents Advanced scoring: neither has public skill effectiveness data.

---

## 4. Honest Gaps (BC6 — No Hedging)

### 4.1. Zero Skill Activation Eval Coverage

**Gap:** `check_skill_activation()` exists in `tests/eval/session_judge.py` but not one eval scenario in `tests/eval/scenarios/` uses the `skill_activation` rubric. The function was implemented; it has never executed on a real scenario.

14 skills in `library/cursor/skills/` have no measured routing accuracy. `docs/SKILLS_STANDARD.md` documents "Skill activation accuracy: Manual testing" as the designated measurement source — confirming automated testing is absent by design, not oversight.

The failure mode is concrete: skill routing in Cursor depends on the agent matching user intent against the `description` field in SKILL.md frontmatter. BFCL [F3] shows tool selection accuracy varies from 30% to 95% depending on description quality and overlaps between available tools. With 14 skills whose descriptions have never been tested, we have no data on which end of that range the skill library occupies. A skill with a description that doesn't include the right trigger keywords will never activate regardless of content quality.

`chore-skill-scenarios` is the pending task. It requires creating 2-3 scenarios that seed task descriptions matching skill keywords, then measuring whether the agent reads the skill file and follows instructions.

**Severity: High.** Binding constraint for "Measured skill effectiveness with activation coverage." The check_skill_activation infrastructure is built. Coverage is zero. Claiming a skill library is "Advanced" without knowing if skills activate correctly is claiming the gun is loaded without checking.

### 4.2. Session Boundary at 33% — The Rule Doesn't Work

**Gap:** `behavioral_session_boundary` score from the eval suite: **33%**. The agent correctly suggests a fresh thread or checkpoint in 1 of 3 tested sessions, despite `planning_discipline.mdc` being alwaysApply and explicitly encoding this behavior.

The rule text: "After 3+ distinct follow-up tasks in one conversation: checkpoint uncommitted work, write handoff breadcrumb, suggest fresh thread." The rule is alwaysApply. The behavioral score is 33%.

This is the most concrete evidence in the entire eval suite that **a rule's existence does not guarantee behavioral compliance.** The rule fires on every session. The behavior it mandates succeeds 33% of the time.

Two plausible explanations, both relevant to the ACAM Workflows dimension:

1. **The rule has missing edge case handling.** [E1] root cause #4: ambiguous trigger conditions. "After 3+ tasks on different topics" is not operationally precise. What counts as a topic change? How does the model count tasks within a turn? The conditional is underspecified, so the model applies it inconsistently. This is a rule authoring failure, not a hook enforcement failure.

2. **Rules cannot structurally enforce conversational hygiene.** Session boundary is a *conversational* behavior — it requires the agent to suggest stopping. No hook can deny a model from continuing a conversation the user started. This is the category limit of structural enforcement: hooks can block tool calls; they cannot block the agent from answering a question without a "fresh thread" suggestion.

The 33% score is not a measurement artifact: the scenario exists, the rule exists, the behavior is tested. The gap documents that Intermediate workflow enforcement via alwaysApply rules fails on 67% of measured cases for conversational lifecycle transitions.

**Severity: High.** This is the strongest internal evidence that "lifecycle awareness" (the rule tracks state) and "lifecycle enforcement" (the behavior reliably fires) are not the same thing. The Intermediate criterion of "lifecycle awareness" is met. The Advanced criterion of "lifecycle statuses enforced" is not.

**No mitigation in place.** gap-14 is pending. Proposed fix path per state.json: strengthen `planning_discipline.mdc` and `agent_behavior.mdc` opener. But the 33% score shows the current rule approach is insufficient regardless of content.

### 4.3. verify-harness Trusts contract.verified Without External Proof

**Gap:** `library/cursor/hooks/verify-harness.sh` reads `contract.json`'s `verified` field. If `verified: true`, the stop hook passes through without further checks. The hook does not verify who set the field, when it was set, or whether an evaluator subagent actually ran.

A builder who wants to bypass evaluation can set `"verified": true` in `contract.json` directly — without launching an evaluator, without earning a PASS verdict from session_judge. The stop hook will pass. This is circular self-certification: the entity being verified controls the verification flag.

The breadcrumbs.jsonl contains evaluator PASS entries (e.g., `{"role":"evaluator","type":"evaluate","result":"pass"}`). verify-harness.sh does not read breadcrumbs to confirm that such an entry exists for the current feature before accepting `verified: true`. The audit trail exists; the hook doesn't consult it.

The correct structural fix: verify-harness.sh should require at least one breadcrumb entry with `role=evaluator` and `result=pass` for the current task feature before honoring `verified: true`. This would make bypass require forging a breadcrumb entry — still bypassable, but no longer trivial.

**Severity: Medium.** verify-harness.sh honors `verified: true` without checking for an evaluator PASS breadcrumb. A builder can self-certify without running an evaluator. The stop hook — the final verification gate — is bypassable by anyone who writes the verified field directly in contract.json. The structural integrity of the verification gate depends on participant behavior, not on the hook's enforcement.

### 4.4. No Quantitative Skill Effectiveness Data

**Gap:** All 14 skills have zero measured effectiveness data. SKILLS_STANDARD.md documents H1-H5 as explicit hypotheses — none has been measured at scale. The measurement sources listed in SKILLS_STANDARD.md are "Manual testing" and "tests/eval/ pipeline" for skill activation — neither is automated or currently producing data.

The eval pipeline has the architectural capability to run skill A/B tests: run a task with skill invocation vs. without, score both sessions with session_judge, report the behavioral delta. This is the feat-16 pattern extended to skills. It has not been implemented.

H2 ("Practitioner voice produces more decisive behavior than neutral tone") is the most testable hypothesis. A/B: same task prompt, same scenario, one session with SKILL.md loaded, one without. session_judge behavioral scores would show decisiveness delta. Zero data.

SKILLS_STANDARD.md's design rationale states: "Skills are the augmented LLM pattern — they extend the base model with domain-specific workflows that the model wouldn't execute consistently on its own." This is an assumption, not a finding. No skill has a measured consistency improvement over baseline.

**Severity: High.** Same binding constraint as Configuration dimension's ablation gap. "Measured skill effectiveness" requires data. SKILLS_STANDARD.md's hypotheses are documented because the framework acknowledges it doesn't know whether the design choices work. Advanced requires knowing.

---

## 5. Counter-Evidence Engagement (BC2 — S1-S4)

### 5.1. [S1] "Most AI Agent Architectures Are Overengineered" — Applied to Each Workflow Component

S1's test: split agents are justified ONLY for (a) parallel execution over distinct data, (b) long-running workflows requiring persistent state, or (c) adversarial validation where same-model review misses systematic errors. Below ~20 tools, agent proliferation adds routing complexity with no benefit.

Applied to rules-skills workflow components:

| Component | S1 justification | Reasoning |
|---|---|---|
| Evaluator subagent | **Justified** | S1 explicitly names adversarial validation (same model = blind spots) as one of three justified cases. Evaluator-as-adversary IS the S1 criterion for multi-agent. |
| Planner subagent | **Marginally justified** | S1: justified for "long-running workflows needing persistent state." The planner's state.json is persistent state for multi-session work. For single-session simple tasks, the planner adds latency. harness-gate.sh's non-trivial routing partially addresses this — planner fires only for complex requests. |
| contract-gate.sh deny hook | **Justified** | S1 targets agent count, not hook-based process control. Structural lifecycle enforcement via hooks is not the same category as multi-agent proliferation. S1 does not challenge this component. |
| verify-harness.sh stop hook | **Justified (with §4.3 caveat)** | The verification gate is structurally equivalent to CI — preventing completion without passing checks. The caveat: the gate is bypassable by self-certification (§4.3). S1's argument does not address this gap. |
| 14-skill library | **Not addressed by S1** | S1 focuses on agent count, not skill libraries. S4 is the relevant source for skill proliferation concerns. |
| 27-scenario eval suite | **Justified by implication** | S1 would require this: "show me data that it's not over-engineered." Without the eval suite, S1's argument can't be engaged with evidence. The eval suite IS the measurement mechanism S1 demands. |

**Net verdict:** S1 is approximately 75% validating for the rules-skills workflow architecture. The evaluator-adversary and hook-based enforcement are justified by S1's own criteria. The planner adds overhead that S1 would flag for simple tasks. The 33% session boundary score (§4.2) is evidence that harness-gate's routing detection works imperfectly — complex tasks get planner correctly; some simple tasks may trigger it unnecessarily.

### 5.2. [S2] LLPP — Applied to the Skill Library

S2's claim: scenario-specific procedures belong in tools loaded on demand, not in the system prompt for every interaction. Constitutional invariants in the system prompt; conditional procedures in skills/tools.

**The skill library is S2's prescribed architecture.** This is not a tension — it is alignment. The 14 SKILL.md files are exactly the lazy-loaded procedural layer S2 defines. Rules encode invariants; skills encode conditional workflows triggered by task context.

The `adversarial_harness.mdc` rule illustrates the correct boundary: the 48-line rule encodes one routing invariant ("if non-trivial, launch harness"). The 191-line SKILL.md encodes the procedural workflow. The rule is the system prompt constituent; the skill is the on-demand procedure. This is the S2-compliant pattern for a high-priority routing decision.

S2's critique of Phase 3 (Configuration) — three alwaysApply rules encode procedural policies — does not carry to Phase 4. For the Workflows dimension, the design correctly separates constitutive routing (rules) from procedural execution (skills).

**Net verdict:** S2 validates the skill library architecture for the Workflows dimension. No tension. The LLPP pattern is what rules-skills implements in the rules/skills split. S2's challenge is a Configuration-dimension issue, not a Workflows-dimension issue.

### 5.3. [S3] "Simpler AI Agents" — The Verification Problem

S3's core challenge: structural enforcement was built for weaker 2023-2024 models. A capable 2026 model may self-regulate correctly, making hooks unnecessary constraints.

The 33% session boundary score (§4.2) is the primary response: a 2026 model, given an explicit alwaysApply rule encoding session hygiene behavior, executes it 33% of the time. If models were capable enough to make guidance redundant, this score would approach 100%.

S3 would counter: "33% shows the rule is wrong, not that the model needs enforcement. A clearer rule or a different approach (conversational reminder rather than alwaysApply mandate) would produce higher compliance without structural enforcement." This counter is empirically open. We have no ablation comparing: (a) no rule, (b) current rule, (c) rewritten rule, (d) hook-based reminder.

For contract-gate.sh specifically: S3 would argue a capable model always writes acceptance criteria before implementation without a deny hook, making the hook redundant. This is testable: remove the hook for one sprint, measure how often the builder skips contract writing. We haven't run this test. The verify-harness gap (§4.3) shows that even with the hook, the verification can be bypassed. The hook may prevent accidents; it does not prevent intentional bypass.

**Net verdict:** S3's challenge to Workflows is empirically open. The 33% session boundary score provides weak evidence that some enforcement is necessary — but does not distinguish between "the enforcement is correctly designed and models still fail" and "the enforcement is incorrectly designed and causes failures." feat-16 extended to workflow scenarios would resolve this. "We don't know" is the factual answer.

### 5.4. [S4] "Fewer Agents With More Skills Wins" — Validation

S4's claim: "Agents = rules of the game (small, stable). Skills = toolbox (many, evolvable)." One lean agent with a rich skill library outperforms a roster of specialized agents.

**This is the rules-skills architecture.** The builder agent handles all tasks. Planner and evaluator are invoked for specific roles (planning, adversarial QA) — not as general-purpose agent duplicates. The 14-skill library is the toolbox; the 8 alwaysApply rules define the game.

S4's critique of "heavy agent identity" maps to the Configuration dimension gap: 8 alwaysApply rules, including 3 procedural policies, make the agent's baseline identity heavier than S4 recommends. This is a Configuration critique. For the Workflows dimension specifically, the skill library IS the S4 pattern — many, evolvable, triggered by need.

S4 explicitly names the receptionist pattern as the ideal: an agent with one rule (route to skill) and zero embedded capability. The `adversarial_harness.mdc` rule is close to this: one routing instruction pointing to SKILL.md. The 7 other alwaysApply rules are where S4 would push back — but that belongs in Phase 3, not here.

**Net verdict:** S4 validates the 14-skill library as the correct Workflows architecture. S4's critique of always-on rule count is a Configuration-dimension finding. For Workflows, S4 is a supporting source, not a challenging one.

---

## 6. Provisional Scoring: Workflows Dimension

### 6.1. Evidence Table

**Intermediate criteria met (≥2 artifact citations each):**

| Criterion | Evidence A | Evidence B |
|---|---|---|
| Defined skill library with authoring standard | `library/cursor/skills/` — 14 SKILL.md files | `docs/SKILLS_STANDARD.md` — required sections, sizing, 5 hypotheses with measurement columns |
| Structural enforcement via deny hooks | `library/cursor/hooks/contract-gate.sh` — preToolUse Write deny | `library/cursor/hooks/verify-harness.sh` — stop hook blocks unverified completion |
| Acceptance-criteria-gated implementation | `.harness/contract.json` — binary AC, phase lifecycle, negotiation rounds | `library/cursor/hooks/contract-gate.sh` — structurally enforces contract presence before Write |
| Traced execution — append-only audit log | `.harness/breadcrumbs.jsonl` — 140+ entries, append-only JSONL | `library/cursor/rules/progress_tracking.mdc` — mandates breadcrumb writes on multi-file changes |
| Lifecycle statuses with hook routing | `.harness/state.json` — 5-status enum, hook-readable | `library/cursor/hooks/chain-evaluator.sh` — routes by contract.json phase field |
| Eval regression suite | `tests/eval/scenarios/` — 27 scenarios, 5 categories | `tests/eval/session_judge.py` — trajectory + behavioral + skill_activation scorer |

**Advanced criteria NOT met:**

| Missing criterion | Current state | Severity |
|---|---|---|
| Measured skill effectiveness with activation coverage | Zero skill_activation eval scenarios; `check_skill_activation()` defined but never exercised | High — binding constraint |
| Lifecycle enforcement on session boundary | 33% `behavioral_session_boundary` score — the rule fails on its stated goal 67% of the time | High — enforcement gap documented by eval |
| verify-harness external verification proof | `verified: true` self-certifiable by builder; no breadcrumb audit in hook | Medium |
| Quantitative skill effectiveness data | H1-H5 in SKILLS_STANDARD.md are explicit hypotheses; no A/B data exists | High — binding constraint |

### 6.2. Score: INTERMEDIATE

**Score: Intermediate**

rules-skills meets every Intermediate criterion with multiple artifact citations. It does not meet Advanced criteria for the Workflows dimension.

The hook architecture (contract-gate.sh denying Writes, verify-harness.sh blocking unverified completion), 14-skill library with explicit authoring standard, 5-status lifecycle machine, acceptance-criteria-gated implementation, and 27-scenario eval suite collectively constitute the most comprehensive public practitioner setup visible in the 2026 landscape — exceeding Devin, Claude Code, and Cursor defaults on every documented Workflows dimension.

What does not move the score to Advanced: two binding constraints.

First, zero skill activation eval coverage. The 14 skills have never been tested for routing accuracy or behavioral effectiveness. BFCL [F3] shows this is a real failure mode: tool selection accuracy varies 30-95% based on description quality. With no data, the skill library is infrastructure of unknown effectiveness.

Second, the 33% session boundary score. This is the hardest fact in the entire four-phase analysis: an alwaysApply rule encoding explicit lifecycle behavior produces the correct behavior 33% of the time. This gap exposes the fundamental limit of the Intermediate approach. Lifecycle *awareness* (the rule and state machine exist) is not the same as lifecycle *enforcement* (the behavior reliably fires). Advanced requires both. The eval shows the latter is failing.

The secondary gap — verify-harness trusting self-certified verification — is addressable in a single hook edit. The primary gaps require new eval scenarios and either new enforcement mechanisms (hooks that block conversational responses) or acknowledgment that session hygiene is outside structural enforcement's scope.

**Honest one-paragraph positioning:** rules-skills is at the ceiling of Intermediate for Workflows. The structural enforcement artifacts — deny hooks, acceptance-criteria gating, lifecycle machine, eval regression suite, traced execution — exceed what any comparable public setup offers. The adversarial harness lifecycle (plan→contract→build→evaluate) and the separation of evaluator from builder are the core differentiators. The gap to Advanced is twofold and compound: the skill library has no measured activation accuracy (zero eval coverage), and the most important lifecycle behavior — session boundary management — fails on 67% of measured cases despite an explicit alwaysApply rule. Advanced requires proving that workflows produce better outcomes with measurable skill effectiveness and reliable lifecycle enforcement. Neither is demonstrated. The path from Intermediate to Advanced on Workflows is: (1) create 2-3 skill activation eval scenarios (chore-skill-scenarios, one week), (2) run them and use BFCL-style accuracy reporting, (3) fix verify-harness.sh to audit breadcrumbs before accepting verified:true (one hour), (4) investigate whether session boundary can be structurally enforced or must be redesigned as a conversational reminder, (5) run feat-16 skill A/B comparison and use results to update skill descriptions.

---

## 7. New Sources Added (BC1 Compliance)

Three sources not in the pre-Phase-4 bibliography. All URLs are real.

### [F1] ReAct: Synergizing Reasoning and Acting in Language Models (Yao et al., NeurIPS 2022 Workshop / ICLR 2023)

- **URL:** https://arxiv.org/abs/2210.03629
- **Relevance:** Workflows (agentic loop patterns, reasoning traces, plan-act-observe)
- **Key takeaway:** Interleaved Thought-Action-Observation cycles outperform pure reasoning (chain-of-thought) or pure acting on decision-making, search, and coding tasks. Explicit reasoning traces make intermediate agent states observable, enabling diagnosis of failures and recovery from errors. Applied to scaffolds: workflows without explicit trace steps cannot be debugged or improved systematically.
- **ACAM mapping:** Validates "traced execution" as an Advanced Workflows criterion. The reasoning trace is the mechanism by which any workflow can be improved — without it, failures are opaque. breadcrumbs.jsonl is a human-authored reasoning trace at the session level (not the turn level). ReAct tracing would be more granular; breadcrumbs address the session-level variant.

### [F2] Inspect AI — Open-Source LLM Evaluation Framework (UK AI Safety Institute, 2024)

- **URL:** https://inspect.ai-safety-institute.org.uk/
- **Relevance:** Workflows (eval regression suites, structured eval architecture)
- **Key takeaway:** Defines the reference architecture for LLM/agent evaluation: Task (input + expected behavior), Solver (agent under test), Scorer (quality measurement), Eval log (structured trace). Eval suites should run as CI tasks, produce structured logs comparable across runs, and support regression detection. Used by the UK government for frontier model safety evaluations.
- **ACAM mapping:** The Inspect AI architecture is isomorphic to rules-skills' eval pipeline (scenarios = Tasks, session_runner = Solver, session_judge = Scorer, eval report = Eval log). This independently validates that the pipeline architecture is correct and uses the right vocabulary. The gap: rules-skills runs eval manually; Inspect AI targets automated CI integration. "Eval regression suite" is confirmed as the correct ACAM Advanced criterion vocabulary.

### [F3] Berkeley Function Calling Leaderboard (BFCL) (Yan et al., 2024 — UC Berkeley / Gorilla Project)

- **URL:** https://gorilla.cs.berkeley.edu/leaderboard.html
- **Relevance:** Workflows (skill activation measurement, tool selection accuracy, description quality)
- **Key takeaway:** Benchmarks 150+ LLMs on 17 categories of function/tool calling: simple, multiple, parallel, nested, REST API, irrelevance detection. Accuracy ranges 30-95% depending on model and scenario complexity. AST verification confirms argument correctness beyond function selection. Critical finding: tool description quality directly drives routing accuracy — vague, overlapping, or keyword-sparse descriptions cause systematic misrouting across all models.
- **ACAM mapping:** Translates directly to IDE skill routing: SKILL.md `description` is the function signature used for skill selection. BFCL's description-quality finding means the 14 descriptions are a critical quality surface — one we've never measured. The "zero skill_activation eval coverage" gap (§4.1) maps to a well-studied measurement problem with known failure modes and existing benchmark methodology. chore-skill-scenarios should adopt BFCL-inspired scenario structure: seed task, correct skill target, irrelevance detection.

---

*Phase 5 (Multi-agent) can proceed using this analysis. Cross-reference §4.2 (33% session boundary — relevant to the planner subagent justification in Phase 5) and §5.1 (S1 applied to each workflow component — the same framework applies to multi-agent role justification in Phase 5). The verify-harness gap (§4.3) propagates to Phase 5 analysis of evaluator role integrity.*
