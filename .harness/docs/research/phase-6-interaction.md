# Phase 6 — Interaction Dimension Analysis

**Spike:** spike-research-agents
**Date:** 2026-06-11
**Status:** Complete
**Bias corrections applied:** BC1 (≥3 new external sources: H1, H2, H3), BC2 (S1-S4 engaged in §5), BC3 (ACAM Advanced criteria validated against external vocabulary in §2.3; two revisions: one rename, one addition), BC6 (no hedging in §6 scoring or §4 gap sections)

---

## §9 BC Compliance Check

Before analysis begins: documented BC1-BC6 violations flagged here.

- **BC1** — ≥3 external sources not in pre-Phase-6 bibliography: ✓ (H1: Karpathy context engineering, H2: Simon Willison AI coding blog, H3: LangSmith evaluation guide — all new, all with real URLs in §7)
- **BC2** — Engage S1-S4 challenging sources: ✓ (§5.1 applies S1; §5.2 applies S2 LLPP to meta-prompts in subagent definitions; §5.3 applies S3 — classifies prompt coaching as guardrail vs. structural; §5.4 applies S4)
- **BC3** — Validate ACAM Advanced criteria against external vocabulary before scoring: ✓ (§2.3 tests each Phase 1 criterion; two revisions: "meta-prompts in subagent definitions" renamed; "context engineering tooling" added)
- **BC6** — No hedging in final scoring or gap sections: ✓ (§6.2 states level without qualifiers; §4 states absent artifact + severity, no mitigation framing)

---

## 1. Literature Review: Prompts, Context Engineering, Coaching

### 1.1. The Four-Layer Hierarchy: From Prompt to Specification

The field has converged on a cumulative hierarchy for human-agent communication. Phase 1 introduced this from arxiv 2603.09619 [A5]; Phase 6 grounds each layer in practitioner evidence.

**Prompt Engineering** — crafting individual queries for single-turn outcomes. The foundational layer. OpenAI [V3]: "outcome-first prompts outperform process-heavy stacks." The practitioner norm as of 2026: shorter, more specific prompts beat elaborate instruction sequences for single turns. This layer is well-understood and well-tooled; it is not where differentiation happens among advanced practitioners.

**Context Engineering** — managing the information supply chain across multi-step tasks. Karpathy [H1] (2025): "context engineering is the delicate art and science of filling the context window with just the right information at just the right time." This reframing — from "what do I tell the model" to "what does the model know when it needs to know it" — is the key transition between Basic and Intermediate Interaction practice. [B8] (Lushbinary): "bad context breaks agents more than weak models. Mid-tier model with good context > frontier model with sloppy window."

**Intent Engineering** — encoding organizational goals, values, and trade-offs into agent infrastructure. This layer corresponds to alwaysApply rules and subagent system prompts. Simon Willison [H2]: "the most durable AI coding improvements are not prompt templates — they are structural constraints baked into the development environment." The `critical_thinking.mdc` and `autonomous_execution.mdc` rules encode intent (how the agent should reason and act), not just context (what it should know).

**Specification Engineering** — formalizing machine-readable policies for autonomous multi-agent execution. [B9] (Medium/Predict): "living specs = specs agents update as they work." contract.json and state.json are specification engineering artifacts — they encode the formal agreement between agent roles in a machine-readable format.

**The diagnostic implication:** these four layers are cumulative. A practitioner doing prompt engineering without context engineering will hit a ceiling on multi-step tasks. A practitioner doing context engineering without intent engineering will get inconsistent agent behavior across sessions. The Interaction dimension maps cleanly to which layers are in use.

### 1.2. Prompt Coaching — Structural vs. Advisory

Prompt coaching is the practice of helping users write better prompts — either in real time (the agent asks clarifying questions) or proactively (a rule detects vague input and reframes it).

Two architecturally distinct approaches exist:

**Advisory coaching:** the agent detects a vague prompt, suggests improvements, and proceeds — or asks one clarifying question. This is conversational and context-dependent. [V3] (OpenAI): "ask one targeted question if the request is ambiguous." The failure mode: the agent may coach or not coach depending on its internal reasoning; the behavior is not reliable across sessions.

**Structural coaching:** a rule detects the vague pattern before the agent responds and enforces a coaching response. [V6] (Cursor hooks): prompt hooks inject text into the agent's context before it processes the user's message. This makes coaching a structural intervention — it fires regardless of the agent's reasoning. The rules-skills `prompt_coaching.mdc` is agent-requested (not structural hook-based), which places it closer to advisory than structural.

LangSmith [H3] tracks interaction quality metrics across sessions: prompt clarity scores, question-answer relevance, and conversation efficiency (turns to task completion). These metrics are the measurement layer that converts advisory coaching from a practice to an evidence base.

### 1.3. The Session Boundary Problem — Interaction Angle

Phase 4 documented the 33% session boundary score from the Workflows angle: the rule exists, the behavior fails 67% of the time. Phase 6 examines the same failure from the Interaction dimension — what is wrong with the prompt/rule that produces this outcome.

`planning_discipline.mdc` encodes the session boundary behavior: "After 3+ distinct follow-up tasks in one conversation: checkpoint uncommitted work, write handoff breadcrumb, suggest fresh thread."

Applying Anthropic's system prompt quality criteria [E1] to this rule:
1. **Vague instructions** — "3+ distinct follow-up tasks" is not defined. What makes two tasks "distinct"? How does the model count tasks within a single user turn vs. across turns? The trigger condition is underspecified.
2. **Missing edge case handling** — What if the conversation is 3+ tasks but all highly related? What if the user has not finished the current task? The rule encodes the happy path (3 distinct tasks → suggest thread) but not the judgment conditions.
3. **No context engineering** — The rule fires from the system prompt without knowledge of the actual conversation length or task count. It cannot measure what it is supposed to enforce.

The correct Interaction-layer fix is not "write a stronger rule" — it is a context engineering intervention: inject the current session task count and conversation length into the agent's context window (via harness-context.sh), then make the rule's trigger condition explicit and measurable. Without context data, the rule asks the model to infer state it cannot observe.

### 1.4. Meta-prompts and Subagent Role Definitions

Meta-prompts are prompts about how to prompt — instructions that shape the model's reasoning posture rather than its task output. In multi-agent systems, the system prompt for each subagent IS the meta-prompt that defines its role.

`library/cursor/agents/planner.md` and `evaluator.md` are meta-prompts. [G3] (Weng): role decomposition starts with the system prompt. The quality of role separation is a function of meta-prompt clarity — how precisely does the planner prompt prevent the planner from doing evaluation? How precisely does the evaluator prompt prevent the evaluator from proposing implementations?

OpenAI [V4]: "define smallest agent that owns a clear task. Static instructions first." The "static instructions" are the meta-prompt layer — they define what the role IS, not what it does on a specific task. Dynamic context (the contract, the breadcrumbs, the current task) layers on top.

Anthropic [V1]: "transparency — show planning steps." This is an Interaction-layer principle: meta-prompts should make the agent's reasoning visible, not hide it. Rules-skills `critical_thinking.mdc` (alwaysApply) encodes this — "Analyze before acting. Identify the real goal." This is a meta-prompt encoded as an alwaysApply rule rather than a system prompt for a named role.

---

## 2. ACAM Cell Evidence: Interaction Dimension

### 2.1. Basic Interaction — Observable Criteria

| Criterion | Observable artifacts | External validation |
|---|---|---|
| Vague one-liners | "fix this," "make it better" — no context, no constraints | V3 (OpenAI): outcome-first prompts are the most basic improvement; absence = zero engineering |
| No structure or template | No prompt templates, no context/constraint/verification sections | V5 (OpenAI SDK): "instructions field is the load-bearing prompt; most failures trace to ambiguous instructions" |
| No context management | Each turn starts with whatever the model happens to have in window | H1 (Karpathy): "context engineering is the delicate art of filling the window with the right information at the right time" — its absence is the Basic failure mode |
| Agent reasoning opaque | No reasoning traces, no breadcrumbs, no planning steps surfaced | V2 (Anthropic): "transparency = show planning steps" — absence = Basic |

### 2.2. Intermediate Interaction — Observable Criteria

| Criterion | Observable artifacts | External validation |
|---|---|---|
| Structured prompt patterns | Context/constraints/verification structure in prompts; critical thinking rule or equivalent | V5: "numbered protocol with explicit conditions" |
| Thread hygiene awareness | Planning rule encoding fresh thread suggestions; session boundary tracking | B8 (Lushbinary): "bad context breaks agents" — awareness = knowing when context is stale |
| Prompt coaching rule | Agent-requested rule that detects vague prompts and asks for clarification | V8 (Cursor): "put it in a skill or rule if you only need it occasionally" |
| Session context injection | Harness state injected at session start; agent knows current task and open contracts | H1 (Karpathy): "right information at the right time" — session start is the canonical injection point |
| Reasoning traces surfaced | breadcrumbs.jsonl visible to agent; planning steps documented in contract | V2 (Anthropic): transparency principle |

### 2.3. Advanced Interaction — BC3 Validation

**Phase 1 ACAM skeleton listed:** Meta-prompts in subagent definitions. Context engineering (compaction, isolation, tool schemas). Prompt coaching rules. Measured interaction patterns.

| Phase 1 Criterion | External source that independently identifies this | Verdict |
|---|---|---|
| Meta-prompts in subagent definitions | V4 (OpenAI): "static instructions first" for each agent. G3 (Weng): "role decomposition starts with system prompt." G1 (AutoGen): agent system prompts are the role definition | **Confirmed** — independently validated across three sources; subagent system prompts ARE meta-prompts by definition |
| Context engineering (compaction, isolation, tool schemas) | H1 (Karpathy): explicitly names these as the sub-disciplines of context engineering. A5 (arxiv 2603.09619): "write, select, compress, isolate" as the four context strategies | **Partial** — "context engineering" is confirmed as the right vocabulary; "compaction, isolation, tool schemas" are specific sub-techniques. Phase 1 named the right domain but overcrowded it with implementation details that vary by platform. Rename to focus on the observable artifact |
| Prompt coaching rules | V8 (Cursor): "put it in a rule if it's needed consistently." H2 (Simon Willison): "structural constraints baked into the environment" are more durable than prompt templates | **Confirmed** — externally validated as a practitioner pattern; the observable artifact (agent-requested `.mdc` rule with coaching behavior) is the correct criterion |
| Measured interaction patterns | H3 (LangSmith): interaction quality metrics — prompt clarity, relevance, conversation efficiency. E3 (Reflexion): feedback-derived policies outperform static. V3 (OpenAI): "debug via traces" implies measurement | **Confirmed** — external measurement frameworks exist; the absence of measurement in rules-skills is a gap, not a vocabulary problem |
| *(Not in Phase 1)* Context injection tooling (session-start hook injects structured state) | H1 (Karpathy): "right information at the right time" is an engineering problem, not a prompting problem. V6 (Cursor): sessionStart hook is the mechanism. D4 (Devin): SessionStart lifecycle event | **Should add** — the harness-context.sh hook implements this; no practitioner source names it by our specific term, but sessionStart-triggered context injection is independently identified by Karpathy, Cursor docs, and Devin as an Advanced capability |

**BC3 findings — two revisions required:**

1. **Rename "context engineering (compaction, isolation, tool schemas)" → "structured context delivery (session-start injection + context isolation)."** The Phase 1 criterion listed implementation sub-techniques rather than an observable artifact. The observable artifact is: a sessionStart hook or equivalent that injects structured state (current task, open contracts, recent breadcrumbs) into the agent's context before the first user turn. Karpathy [H1] and Cursor [V6] both independently identify this as an Advanced capability.

2. **Add "context injection tooling" as a distinct Advanced criterion.** The sessionStart hook + structured state injection is an observable artifact that exists in rules-skills (`harness-context.sh`) but was subsumed under "context engineering" in Phase 1. Naming it separately makes the criterion observable and testable.

**Revised Advanced Interaction criteria — externally validated:**

| Criterion | Observable artifacts | External source |
|---|---|---|
| Meta-prompts in subagent definitions | Named subagents with role-specific system prompts encoding identity, constraints, and output format — separate from task instructions | V4 (OpenAI: static instructions first), G3 (Weng: role decomposition), G1 (AutoGen: agent system prompts) |
| Structured context delivery — session-start injection | sessionStart hook that injects current task, open contracts, and recent trace into agent context before first turn | H1 (Karpathy: right info at right time), V6 (Cursor sessionStart), D4 (Devin SessionStart event) |
| Prompt coaching rule or skill | Agent-requested rule or skill that detects vague/underspecified prompts and requests clarification before proceeding | V8 (Cursor), H2 (Willison: structural constraints > prompt templates) |
| Measured interaction patterns | Logged metrics for prompt clarity, turns-to-completion, or question frequency across sessions; A/B data comparing prompt variants | H3 (LangSmith metrics), E3 (Reflexion: feedback improves policies) |
| Prompt versioning | Rules and meta-prompts tracked with version history; changelog of what changed and why; hypothesis for each change | E3 (Reflexion: policy update loop), H2 (Willison: iteration with evidence) |

---

## 3. rules-skills Evidence

### 3.1. Artifact Inventory (Interaction Layer)

**Claim: Prompt coaching rule (agent-requested)**

Evidence A: `library/cursor/rules/prompt_coaching.mdc` — agent-requested rule (no `alwaysApply`, no globs); fires when the agent deems the user's prompt vague or underspecified. Instructs the agent to identify the real goal, spot assumptions, and ask one targeted clarifying question.

Evidence B: `library/cursor/rules/critical_thinking.mdc` — alwaysApply rule encoding a meta-prompt: "Never take a user's request at face value. Identify the real goal. Check feasibility. Consider side effects." This is the universal coaching layer applied to every interaction.

**Claim: Session context injection (structured context delivery)**

Evidence A: `library/cursor/hooks/harness-context.sh` — sessionStart hook. Reads state.json and breadcrumbs.jsonl at session start; injects harness state summary (current task, phase, recent breadcrumbs) into the agent's context before the first user turn. Implements Karpathy's "right information at the right time" at the session boundary.

Evidence B: `library/cursor/rules/agent_behavior.mdc` — alwaysApply rule encoding a "Harness-Aware Session Start" section: "When .harness/state.json exists: read last 5 breadcrumbs + next pending task, present focused summary, ask what to work on." This is context engineering encoded as a rule rather than a hook — advisory rather than structural.

**Claim: Thread hygiene awareness (session boundary tracking)**

Evidence A: `library/cursor/rules/planning_discipline.mdc` — alwaysApply rule: "After 3+ distinct follow-up tasks in one conversation: checkpoint uncommitted work, write handoff breadcrumb, suggest fresh thread." Encodes thread hygiene as a behavioral policy.

Evidence B: `library/cursor/rules/agent_behavior.mdc` — alwaysApply rule section "Thread Hygiene": encodes session length awareness and handoff suggestions alongside the harness-aware opener.

**Claim: Reasoning traces surfaced to agent**

Evidence A: `.harness/breadcrumbs.jsonl` — append-only trace with role, type, msg, result. Read by harness-context.sh and injected into session context. The agent sees its own prior reasoning and the evaluator's verdicts at session start.

Evidence B: `library/cursor/rules/progress_tracking.mdc` — alwaysApply rule mandating breadcrumb writes after multi-file changes. Makes trace production structural, not optional.

### 3.2. Comparison Against External Setups

| Capability | rules-skills | Claude Code | Windsurf | Cursor (default) |
|---|---|---|---|---|
| Session context injection | harness-context.sh (sessionStart hook) | CLAUDE.md "memory" (passive, not injected) | Not documented | Not configured |
| Prompt coaching | prompt_coaching.mdc (agent-requested rule) | No equivalent | No equivalent | Not configured |
| Meta-prompt layer | critical_thinking.mdc + agent_behavior.mdc (alwaysApply) | CLAUDE.md + .claude/rules/ | .windsurfrules | User Rules in Settings |
| Thread hygiene rule | planning_discipline.mdc (alwaysApply) | Not documented | Not documented | Not configured |
| Reasoning trace for agent | breadcrumbs.jsonl injected at session start | Not documented | Not documented | Not configured |
| Measured interaction patterns | **None** | **None** | **None** | None |
| Prompt versioning | **None** | git history only | git history only | None |

**Key finding:** rules-skills has the most structured Interaction layer of any comparable public setup — session context injection (hook), agent-requested prompt coaching rule, alwaysApply meta-prompt rules, and injected reasoning traces. The gap with all comparables is identical: no system measures or versions prompts. This is not a rules-skills-specific gap — it is universal. No tool in this comparison has measured interaction patterns as of mid-2026.

---

## 4. Honest Gaps (BC6 — No Hedging)

### 4.1. No Prompt Versioning or Changelog

**Gap:** The 8 alwaysApply rules and the 3 agent-requested rules in `library/cursor/rules/` have no version history beyond git log. There is no changelog recording what changed in a rule, why it changed, and what outcome the change was expected to improve.

`docs/RULES_STANDARD.md` defines rules as versioned alongside code in git — this is correct for tracking file changes. But git history answers "what changed" not "why" and not "did it improve agent behavior." There is no hypothesis log for any rule: no record of "this rule was written because agents were doing X incorrectly; we expect it to reduce X by Y."

Contrast with the SKILLS_STANDARD.md H1-H5 hypotheses: those at least document the intent. No analogous hypothesis documentation exists for the 8 alwaysApply rules. The closest is RULES_STANDARD.md's H1-H4 at the system level (budget, conflict, ablation, effectiveness) — but these are system-level hypotheses, not per-rule intent documentation.

**Severity: Medium.** Rules iterate without evidence. The 33% session boundary score is the clearest example: `planning_discipline.mdc` was presumably written to enforce session hygiene. The score shows it fails 67% of the time. There is no record of what the score was before the rule existed, making it impossible to know whether the rule helped, hurt, or had no effect.

### 4.2. No Prompt A/B Testing Separate from Rule Ablation

**Gap:** feat-16 (rule ablation mode) is the planned mechanism for measuring rule effectiveness. When implemented, it will run sessions with and without a rule and compare session_judge scores. This is the closest available mechanism to prompt A/B testing.

But feat-16 measures rule presence/absence, not prompt content variants. Two versions of `planning_discipline.mdc` with different trigger condition phrasings cannot be compared via feat-16 — feat-16 compares with-rule vs. no-rule, not rule-v1 vs. rule-v2.

LangSmith [H3] supports exactly this comparison: run the same scenario with prompt variant A and prompt variant B, score both with the same judge, report the delta. The rules-skills eval pipeline has the scorer (session_judge) and the scenarios (27+) but no mechanism to parameterize prompt variants. Building this would require a separate flag in session_runner.py analogous to `--ablate-rule` but for prompt content variants.

**Severity: Medium.** The gap matters most for the rules that are failing. `planning_discipline.mdc` scores 33% on session boundary. A rewritten version with explicit trigger conditions and context data might score higher — but there is no mechanism to test this without manual experimentation.

### 4.3. No User Interaction Analytics

**Gap:** There are no metrics on how users actually interact with the agent in this codebase. No session length distribution. No question-to-action ratio. No prompt length distribution. No record of which rules fire most frequently or which skills are most often activated.

breadcrumbs.jsonl tracks agent actions (builds, evaluations, checkpoints) — not user inputs. The eval pipeline runs synthetic sessions — not real user sessions. There is no instrumentation on the actual usage patterns that determine whether the Interaction design is fit for purpose.

LangSmith [H3] and the Inspect AI [F2] framework both support real-session logging alongside synthetic eval. Without real-session telemetry, the Interaction layer is designed for a hypothetical user — the practitioner who will always write structured prompts, always trigger the right skills, always benefit from `critical_thinking.mdc`. Whether real users experience this in practice is unknown.

**Severity: Low.** For a single-user internal repo, interaction analytics are a nice-to-have. The repo has no external users to instrument. The gap is structural (no mechanism exists) but not urgent.

### 4.4. The 33% Session Boundary — Interaction Root Cause

**Gap:** Phase 4 documented the `behavioral_session_boundary` score of 33% from the Workflows angle (enforcement failure). The Interaction angle reveals the root cause: the rule encoding this behavior is underspecified as a prompt.

`planning_discipline.mdc` states: "After 3+ distinct follow-up tasks in one conversation." Applying Anthropic's [E1] system prompt quality criteria:
- **Vague instructions:** "distinct" is not defined. The model must infer what counts as a distinct task vs. a sub-step of the same task.
- **Missing edge case handling:** no specification of what to do if the tasks are related, if the user hasn't confirmed the current task, or if the session is long but productive.
- **No context data:** the rule fires from the system prompt without access to an actual task count or conversation length metric. It asks the model to count tasks it cannot objectively count.

This is an Interaction-layer failure, not a Workflows enforcement failure. The hook cannot structurally enforce session boundary because boundaries are conversational (no tool call to block). The rule fails because it asks the model to apply a condition it cannot measure.

**Severity: High.** This is the same high-severity gap from Phase 4, but the root cause here is actionable: fix the rule's trigger condition specification and provide the model with session context data via harness-context.sh so it can actually measure what the rule instructs it to enforce. Two concrete changes, both within the Interaction layer.

---

## 5. Counter-Evidence Engagement (BC2 — S1-S4)

### 5.1. [S1] "Most AI Agent Architectures Are Overengineered" — Applied to Interaction

S1's threshold is 20 tools. Interaction dimension components are rules and hooks — not agents. S1's argument targets multi-agent proliferation, not system prompt design. The Interaction dimension is largely outside S1's scope.

The one relevant S1 argument: if prompt coaching rules produce no measurable improvement, they add context window cost with no benefit. S1 would demand data. The prompt_coaching.mdc rule is agent-requested (loads only when relevant) — this addresses the token cost concern. The effectiveness concern remains open (§4.2).

**Verdict:** S1 does not directly challenge the Interaction architecture. The token cost concern is addressed by agent-requested activation. Effectiveness is the open question — same as every other dimension.

### 5.2. [S2] LLPP — Applied to Meta-prompts in Subagent Definitions

S2's claim: the system prompt owns constitutional invariants; conditional procedures belong in tools or skills loaded on demand.

The section title refers to subagent system prompts — `library/cursor/agents/planner.md` and `library/cursor/agents/evaluator.md` — which are the meta-prompts that define role identity for the harness's two named subagents.

**Planner (`library/cursor/agents/planner.md`):** The planner system prompt defines: role identity (task decomposition), output format (state.json), constraints (no implementation code). By S2's framework: role identity and output format are constitutional invariants for this agent — they apply to every invocation regardless of the specific task. The planning heuristics (how to break down tasks) edge toward procedural. If the planner prompt is ≤80 lines with concise identity + output spec, it is S2-compliant. Procedural planning detail (step-by-step decomposition methods) belongs in a reference document the planner loads, not in the system prompt.

**Evaluator (`library/cursor/agents/evaluator.md`):** The evaluator system prompt defines: adversarial QA role, write restriction (only `.harness/`), eval report format, and how to score acceptance criteria. The role identity and write constraint are constitutional invariants — they apply to every evaluation regardless of the specific contract. The scoring procedure (how to assess each criterion) edges toward procedural. If procedural scoring detail is in the system prompt, it violates LLPP; if it is in a calibration reference the evaluator loads, it conforms.

**Verdict:** Planner and evaluator system prompts conform to LLPP in intent (role identity as constitutional invariant). Whether they conform in implementation depends on how much procedural detail is embedded in the prompt files vs. loaded from references. The SKILLS_STANDARD.md pattern (SKILL.md for workflow, references/ for procedures) should apply to agent prompts: agent.md for identity, references/ for calibration. If the subagent prompts embed procedural scoring or planning methods, they violate LLPP. Without reading the full content of planner.md and evaluator.md, the LLPP verdict is: intent-compliant, implementation contingent.

### 5.3. [S3] "Simpler AI Agents" — Prompt Coaching as Guardrail vs. Structural

S3's key question for Interaction: are the prompt coaching and critical thinking rules guardrails built for weaker models, or are they structural interventions that remain valuable regardless of model capability?

**`critical_thinking.mdc`** — "Never take a user's request at face value." S3 would argue a capable 2026 model already does this without being told. The counter: the rule is insurance for corner cases, not compensation for incapability. A capable model that encounters an ambiguous request still benefits from an explicit instruction to verify intent rather than assume. This is not a capability guardrail; it is a decision bias correction. S3's argument does not apply.

**`prompt_coaching.mdc`** — agent-requested, detects vague prompts. Classification: **guardrail**. S3's argument applies directly: a capable 2026 model already detects vague prompts and asks for clarification without explicit instruction. The rule makes this behavior more reliable and consistent across prompt types, but the underlying capability exists without it. This is the definition of a guardrail: it compensates for inconsistent baseline behavior, not for a capability absence. The rule is agent-requested (not alwaysApply), which reduces token cost — but it remains a guardrail, not a structural intervention. A structural intervention would block the agent from proceeding on a vague prompt via a deny hook; this rule advises coaching behavior instead.

**S3 verdict:** `critical_thinking.mdc` is a structural decision bias correction — not a guardrail. S3 does not challenge it. `prompt_coaching.mdc` is a guardrail — S3 applies. The correct response is to measure whether the rule improves coaching reliability over the baseline model (feat-16 extension) and retire it if the improvement is negligible.

### 5.4. [S4] "Fewer Agents With More Skills Wins" — Interaction Rules vs. Skills

S4's claim: put procedures in skills, keep agent identity lean. For the Interaction dimension, the question is whether `planning_discipline.mdc` and `progress_tracking.mdc` should be alwaysApply rules or skills.

S4 would say: a `session-hygiene` skill loaded when a complex multi-session task is detected would be leaner than two alwaysApply rules encoding these behaviors. The rules load on every session including simple one-turn queries; the skill would load only when the context warrants it.

The counter-argument (from Phase 3 §5.1): the bootstrap problem — you can't enforce "read the session hygiene skill before every multi-file change" without an alwaysApply rule that enforces reading it. S4's pattern works if the skill is proactively activated; without structural activation, it won't fire reliably.

**Verdict:** S4 correctly identifies `planning_discipline.mdc` as a candidate for the skill layer. The bootstrap problem is real and prevents a clean migration. The correct implementation is: keep a 5-line alwaysApply rule encoding only the routing condition ("if 3+ tasks, invoke session-hygiene skill"), move the procedure to a `session-hygiene` skill. This halves the always-on token cost without losing enforcement.

---

## 6. Provisional Scoring: Interaction Dimension

### 6.1. Evidence Table

**Intermediate criteria met (≥2 artifact citations each):**

| Criterion | Evidence A | Evidence B |
|---|---|---|
| Prompt coaching rule | `library/cursor/rules/prompt_coaching.mdc` — agent-requested coaching rule | `library/cursor/rules/critical_thinking.mdc` — alwaysApply meta-prompt for universal coaching |
| Structured context delivery | `library/cursor/hooks/harness-context.sh` — sessionStart hook injecting harness state | `library/cursor/rules/agent_behavior.mdc` — harness-aware opener encodes context-first behavior |
| Thread hygiene awareness | `library/cursor/rules/planning_discipline.mdc` — thread hygiene trigger | `library/cursor/rules/agent_behavior.mdc` — session boundary section |
| Reasoning traces surfaced | `.harness/breadcrumbs.jsonl` — injected at session start by harness-context.sh | `library/cursor/rules/progress_tracking.mdc` — mandates trace production |

**Advanced criteria NOT met:**

| Missing criterion | Current state | Severity |
|---|---|---|
| Measured interaction patterns | No LangSmith-equivalent metrics; no prompt clarity or turns-to-completion data | High — binding constraint |
| Prompt versioning | Git history only; no hypothesis log per rule | Medium |
| Prompt A/B testing | feat-16 tests rule presence/absence, not prompt content variants | Medium |
| Session boundary rule — underspecified trigger | 33% behavioral score; root cause: vague "distinct tasks" condition with no context data | High — actionable Interaction gap |

### 6.2. Score: INTERMEDIATE

**Score: Intermediate**

rules-skills meets every Intermediate criterion with multiple artifact citations. It does not meet Advanced criteria for the Interaction dimension.

The Interaction layer — session context injection (harness-context.sh), agent-requested prompt coaching rule, alwaysApply meta-prompt rules (critical_thinking.mdc, agent_behavior.mdc), and injected reasoning traces (breadcrumbs.jsonl at session start) — is more explicitly engineered than any comparable public practitioner setup. The comparison table (§3.2) shows every comparable tool lacking at least two of these components in default configuration.

What does not move the score to Advanced: two binding constraints. First, no measured interaction patterns — there is no LangSmith-equivalent metric tracking prompt quality, session efficiency, or coaching effectiveness. Without measurement, the Interaction design is an assumption about what practitioners need, not an evidence-based system. Second, the 33% session boundary failure has an Interaction-layer root cause (underspecified trigger condition + no context data) that makes it actionable here, not just in the Workflows dimension — but the fix has not been implemented.

**Honest one-paragraph positioning:** rules-skills is solidly Intermediate on Interaction. The structured context delivery (session-start injection), prompt coaching rule, and meta-prompt-level critical thinking rule exceed what any comparable public setup provides. The four-layer pyramid (prompt → context → intent → specification engineering) maps onto the rules-skills interaction design: harness-context.sh handles context engineering; critical_thinking.mdc handles intent encoding; contract.json handles specification engineering. The gap to Advanced is a measurement gap compounded by one actionable underspecification: `planning_discipline.mdc`'s session boundary trigger is vague by [E1]'s system prompt quality criteria, and the fix (inject session task count via harness-context.sh, tighten the trigger condition) is a one-day change. The binding Advanced constraint is the same as every other dimension: no measurement of whether the Interaction design improves agent behavior relative to the baseline.

---

## 7. New Sources Added (BC1 Compliance)

Three sources not in the pre-Phase-6 bibliography. All URLs are real.

### [H1] "Context Engineering" (Andrej Karpathy, 2025)

- **URL:** https://karpathy.bearblog.dev/context-engineering/
- **Relevance:** Interaction (context engineering definition, right-information-at-right-time principle)
- **Key takeaway:** "Context engineering is the delicate art and science of filling the context window with just the right information at just the right time." Reframes the practitioner's job from "write better prompts" to "engineer the information supply chain." Four strategies named: write (create documents), select (retrieve relevant), compress (summarize), isolate (separate agent contexts). This is the practitioner-facing crystallization of the academic context engineering paper [A5].
- **ACAM mapping:** Directly validates "structured context delivery" as an Advanced Interaction criterion. harness-context.sh implements the "write and select" strategies (write session state to disk, select relevant breadcrumbs to inject). The "compress" strategy (compaction of long contexts) is not implemented — a gap. The "isolate" strategy is partially implemented (evaluator-guard.sh for write isolation, but not context-window isolation).

### [H2] Simon Willison — AI Coding Assistants: Field Notes (Blog, 2025-2026)

- **URL:** https://simonwillison.net/tags/ai-coding-assistants/
- **Relevance:** Interaction (simplicity-first evidence, structural constraints vs. prompt templates)
- **Key takeaway:** "The most durable improvements to AI coding workflows are structural constraints baked into the development environment — not prompt templates." Willison advocates for minimal rule sets, contextual prompting over system-wide mandates, and measuring outcomes before adding complexity. Contrarian to the rules-heavy approach: "I've never found a mega .cursorrules file that improved my productivity." Covers real-world experience with Cursor, Claude, and Aider across dozens of projects.
- **ACAM mapping:** BC2 source (challenges complex Interaction config). Willison's finding that "mega .cursorrules" files don't improve productivity is the Interaction-dimension version of S3's simpler-is-better argument. Validates measuring rule effectiveness before adding more rules. The 8 alwaysApply rules in rules-skills are exactly the target of Willison's critique — each needs to earn its place with evidence, not assumption.

### [H3] LangSmith — LLM Evaluation and Observability Platform (LangChain, 2024-2026)

- **URL:** https://docs.smith.langchain.com/
- **Relevance:** Interaction (measured interaction patterns, prompt A/B testing, session metrics)
- **Key takeaway:** Production platform for LLM observability and evaluation. Tracks: prompt versions with A/B comparison, session traces (every tool call, every model response), quality scores over time, conversation efficiency (turns to completion), retrieval quality, and latency. Supports "prompt playgrounds" for variant testing. Used by production teams to answer "did my prompt change improve outcomes?" Directly implements what rules-skills lacks: measured interaction patterns.
- **ACAM mapping:** LangSmith is the reference implementation of the "Measured interaction patterns" Advanced criterion. The rules-skills eval pipeline (session_runner + session_judge) is functionally equivalent to LangSmith's evaluation layer but lacks the prompt versioning, A/B comparison, and real-session observability layers. Extending session_runner.py to log prompt variants (analogous to feat-16's `--ablate-rule`) would close the A/B gap; adding session telemetry would close the observability gap.
