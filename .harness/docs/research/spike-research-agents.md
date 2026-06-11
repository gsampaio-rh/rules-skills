# How Well-Configured Is Your AI Coding Agent?

**Spike:** spike-research-agents | **Date:** 2026-06-11 | **Status:** Final

A practitioner assessment of agent configuration sophistication using the Agent Configuration Assessment Model (ACAM). Applied to: [rules-skills](https://github.com/gsampaio/rules-skills), a public Cursor/Claude-Code configuration library.

---

## §BC-Compliance

- **BC1** — External sources cited: ✓ (60+ sources across 7 phases; labels A-, B-, V-, N-, S-, D-, E-, F-, G-, H- series used inline)
- **BC3** — ACAM criteria externally validated before scoring: ✓ (BC3 pass in all four dimension phases; criteria revised against external vocabulary in Phases 3-6)
- **BC6** — No hedging in scores or gap sections: ✓ (all four dimension scores stated without qualifiers; gaps state severity without mitigation framing)

---

## 1. What Is ACAM?

The Agent Configuration Assessment Model scores an AI agent setup across four dimensions at three maturity levels:

| Dimension | What it measures |
|---|---|
| **Configuration** | How rules, system prompts, and agent instructions are structured, scoped, and maintained |
| **Workflows** | How the agent's task lifecycle is enforced — from spec to implementation to verification |
| **Multi-agent** | How multiple specialized agents are defined, orchestrated, and kept from interfering with each other |
| **Interaction** | How the information supply chain from user → agent is engineered: prompts, context, coaching, measurement |

Three levels — Basic, Intermediate, Advanced — are defined by observable artifacts: what you would find in the repo or observe in a session. The full scoring worksheet is in `acam-worksheet.md`.

ACAM was developed inductively from a survey of ~3,200 public AI agent configuration repos (June 2026) and validated against external literature across 60+ sources (ReAct, Inspect AI, BFCL, AutoGen, LangSmith, Karpathy context engineering, and others).

---

## 2. Population Baseline

Before scoring rules-skills, the normie baseline matters. The empirical model (Phase 2, n≈3,200):

| Tier | Description | Estimated % of repos |
|---|---|---|
| Tier 0 | A single `.cursorrules` or `CLAUDE.md` — no structure, no workflow | ~80% |
| Tier 1 | Multiple rules with some scope differentiation | ~18% |
| Tier 2 | Intermediate on ≥2 dimensions; some workflow or multi-agent structure | ~1.5% |
| Tier 3 | Intermediate across all 4 dimensions | ~0.5% |

The median public repo is a single flat config file (Tier 0). The average practitioner writing "good" `.cursorrules` is Tier 1. Tier 2 requires deliberate workflow engineering. Tier 3 is where rules-skills sits.

---

## 3. ACAM Scores: rules-skills

### 3.1 Two-Axis Scorecard

| Dimension | ACAM Level | Population Tier | Key gap to Advanced |
|---|---|---|---|
| Configuration | Intermediate | Tier 3 (top ~0.5%) | No per-rule effectiveness data (ablation pending feat-16) |
| Workflows | Intermediate | Tier 3 (top ~0.5%) | No automated eval regression suite; 33% session boundary behavioral score |
| Multi-agent | Intermediate | Tier 3 (top ~0.5%) | Manual agent orchestration (feat-13 cancelled); context isolation is prompt-level only |
| Interaction | Intermediate | Tier 3 (top ~0.5%) | No measured interaction patterns; session boundary trigger underspecified |

**Both axes matter and neither cancels the other.** ACAM Intermediate means: every Intermediate criterion is met with observable artifacts; no Advanced criterion is met. Population Tier 3 means: the setup is in the top ~0.5% of public repos by architectural sophistication.

These are different claims. "Intermediate by ACAM" describes what the setup does relative to a principled maturity model. "Tier 3 by population" describes what the setup does relative to actual public practice. A setup can be Tier 3 (better than 99.5% of public repos) and Intermediate by ACAM (not Advanced) because ACAM Advanced requires quantitative evidence of effectiveness — something virtually no public repo has.

### 3.2 What Is Actually Built

**Configuration:** 8 `alwaysApply` rules + 3 agent-requested rules, scoped with explicit loading conditions, documented in `RULES_STANDARD.md` with per-rule rationale. Multi-file rule resolution with priority documentation. Cross-file consistency via linter check.

**Workflows:** `contract.json` gates implementation writes (acceptance-criteria-gated implementation). `breadcrumbs.jsonl` provides append-only traced execution. `contract-gate.sh` (preToolUse deny hook) structurally blocks writes without a contract. `verify-harness.sh` (stop hook) forces evaluator launch at session end. 27+ eval scenarios in `tests/eval/scenarios/`.

**Multi-agent:** Separate system prompts for planner (`library/cursor/agents/planner.md`) and evaluator (`library/cursor/agents/evaluator.md`). Trust boundary enforcement: `evaluator-guard.sh` blocks all evaluator writes outside `.harness/`. Phase-gated transitions via `chain-evaluator.sh`.

**Interaction:** Session-start context injection (`harness-context.sh`). Prompt coaching rule (`prompt_coaching.mdc`). Universal meta-prompt layer (`critical_thinking.mdc`, `agent_behavior.mdc`). Reasoning traces injected into session context from `breadcrumbs.jsonl`.

---

## 4. Red-Team Pass: Can rules-skills Claim Basic on Workflows?

The red-team challenge targets the Workflows dimension because it has the strongest Basic argument.

**The Basic case:**

> A workflow that fires 33% of the time across eval sessions is not a verified workflow — it is an aspirational one. The `behavioral_session_boundary` score (33%) from `tests/eval/scenarios/` shows that `planning_discipline.mdc` enforces the thread boundary less than one-third of the time. If the key behavioral workflow of the system — session boundary management — passes in only 1 out of 3 sessions, the Workflows dimension should score Basic, where "Basic" means a structured intent exists but is not reliably executed.

Additionally: zero `skill_activation` eval coverage. The 14 SKILL.md descriptions are the routing layer for skill selection. None have been tested for activation accuracy. A system with unvalidated routing is a system that may be running the wrong workflow silently.

**The rebuttal:**

The Basic argument conflates two separate things: **behavioral rules** (which run via agent inference) and **structural gates** (which run via deny hooks regardless of agent behavior).

The 33% session boundary failure is a failure of `planning_discipline.mdc` — an alwaysApply rule that asks the agent to infer when a session should end. It is a behavioral rule, not a structural gate. The Intermediate Workflows criteria that rules-skills meets are structural:

- `contract-gate.sh` blocks implementation writes without a contract. This fires at the tool call level — the agent cannot write a source file if no `contract.json` exists. This is not an inference; it is an OS-level deny.
- `verify-harness.sh` forces evaluator launch at session end when a contract is open. This fires at the stop event — the session cannot end cleanly without verification.
- `breadcrumbs.jsonl` is append-only. Traced execution is not behavioral; it is enforced by the log format.

The 33% score is a behavioral workflow gap, not a structural gap. The Intermediate criteria — contract gate, traced execution, lifecycle enforcement — are met structurally. The Advanced criterion (automated eval regression suite) is not met. Therefore: **the Basic case fails. The Workflows dimension scores Intermediate.**

However: the Basic argument correctly identifies that behavioral rules without structural enforcement have no reliability guarantee. `planning_discipline.mdc` should either be rewritten with measurable trigger conditions and context injection, or replaced by a structural deny hook for session-length violations. The 33% score is a real problem — it just does not demote the structural criteria that carry the Intermediate score.

The zero `skill_activation` eval coverage is a real gap. It does not affect the Intermediate score (skill routing is not an Intermediate criterion) but it is a binding constraint on any claim to Advanced.

**Verdict: Intermediate holds. The Basic case fails on the structural evidence. The 33% behavioral gap is a real problem with an Interaction-layer root cause (underspecified trigger), not a structural failure of the Workflows dimension.**

---

## 5. What to Steal First

For practitioners at Tier 0-1 who want to move up without building the full harness. Ordered by impact-to-effort ratio.

**1. `library/cursor/rules/critical_thinking.mdc` — one alwaysApply rule, maximum impact**
The single highest-leverage configuration artifact. An alwaysApply rule instructing the agent to identify the real goal, spot assumptions, check feasibility, and consider side effects — before writing a single line of code. Takes 10 minutes to write, applies to every session, and encodes the intent layer that separates deliberate agent behavior from reflexive generation. Copy it verbatim; adjust the domain-specific examples.

**2. `library/cursor/hooks/harness-context.sh` — session-start context injection**
A sessionStart hook that reads the current task state and injects it into the agent's context before the first user turn. Without this, each session starts cold — the agent infers from conversation history rather than from structured state. With this, the agent knows what it is working on, what the acceptance criteria are, and what the last 5 actions were. This is Karpathy's "right information at the right time" implemented in one shell script. Copy the pattern; adapt the state file format to your project.

**3. `library/cursor/rules/verification.mdc` — close the verify-then-ship loop**
An alwaysApply rule mandating that every code change is followed by a verification step: run tests if they exist, otherwise run a lint or syntax check. The default agent behavior is to write code and stop. This rule makes the verify step structural — the agent considers it part of the definition of done. No tooling required; the rule is the enforcement.

**Bonus — if you add one hook:** `contract-gate.sh`. A preToolUse deny hook that blocks source file writes if no `contract.json` exists. This takes the session from "the agent might plan first" to "the agent structurally cannot write code without a plan." The harness version is ~40 lines of shell. The effect is: every implementation session is preceded by explicit acceptance criteria.

---

## 6. BC3 Summary: ACAM Advanced Criteria (Externally Validated)

These are the Advanced criteria after BC3 revisions across all four dimension phases. Each was validated against at least one external source.

| Dimension | Advanced Criterion | External validation |
|---|---|---|
| Configuration | Per-rule effectiveness data (quantified ablation score) | E3 (Reflexion: policy update requires measurement); S2 (LLPP: constitutional vs procedural separation) |
| Configuration | Cross-tool portability (AGENTS.md or equivalent) | B4 (AGENTS.md spec); D4 (Devin SessionStart lifecycle) |
| Workflows | Acceptance-criteria-gated implementation | V1 (Anthropic: spec before implementation); V2 (Anthropic: transparency principle) |
| Workflows | Traced execution (append-only audit log) | F1 (ReAct: reasoning traces make failures observable) |
| Workflows | Eval regression suite (CI-integrated, automated) | F2 (Inspect AI: eval as CI task); E3 (Reflexion: scored improvement loops) |
| Multi-agent | Programmatic orchestration (not manual invocation) | G1 (AutoGen: GroupChatManager as canonical primitive) |
| Multi-agent | Trust boundary enforcement (evaluator cannot write source) | G3 (Weng: intentional vs accidental reading); V2 (Anthropic: role separation) |
| Multi-agent | Context package delivery (structured state, not full history) | G2 (Swarm: clean handoff = Advanced default) |
| Interaction | Structured context delivery (sessionStart injection) | H1 (Karpathy: right information at right time); V6 (Cursor sessionStart hook) |
| Interaction | Measured interaction patterns | H3 (LangSmith: prompt A/B, session metrics); F2 (Inspect AI eval architecture) |
| Interaction | Prompt versioning with changelog | E3 (Reflexion: feedback-derived policy updates require version history); H2 (Willison: iterate with evidence) |

---

## 7. Blog Series Outline

Four posts. Each is self-contained; together they tell the complete story from configuration to measurement.

### Post 1: "Your AI assistant has no idea what it's doing — and it's your fault"

**Thesis:** The default state of AI coding agent configuration is a flat text file that the agent ignores most of the time. The practitioners who get reliable results are not using better models — they are engineering the agent's information environment.

**Evidence:** (a) 80% of 3,200 public repos use a single flat config with no structure — the empirical Tier 0 baseline [N2]; (b) Karpathy's context engineering framing: the job is filling the context window correctly, not writing cleverer prompts [H1]; (c) BFCL finding: tool description quality drives routing accuracy — vague descriptions cause systematic misrouting across all models [F3].

### Post 2: "The three structural gates that make agent behavior reliable"

**Thesis:** Reliable agent behavior is not a prompt problem — it is a structural enforcement problem. Three hook patterns convert probabilistic agent behavior into structural guarantees.

**Evidence:** (a) `contract-gate.sh`: preToolUse deny blocking writes without a contract — the agent structurally cannot write code without acceptance criteria [V6]; (b) `evaluator-guard.sh`: trust boundary enforcement — the evaluator agent cannot modify source files, enforced at the tool-call level [G3]; (c) `verify-harness.sh`: stop-event enforcement — the session cannot end cleanly with an open, unverified contract; the structural lifecycle model maps directly to Inspect AI's Task/Solver/Scorer architecture [F2].

### Post 3: "Why multi-agent setups fail — and the one pattern that doesn't"

**Thesis:** Multi-agent setups fail because of context contamination and role collapse. The pattern that works is role separation enforced by structural constraints, not by asking agents to stay in their lane.

**Evidence:** (a) Weng's intentional-vs-accidental reading distinction: shared context = accidental reading; the evaluator-guard.sh implements intentional-only reading as a structural deny [G3]; (b) The S1 counter-argument applied: the three-role harness (planner + builder + evaluator) passes S1's justification test — each role has distinct data, long-running state, or adversarial validation requirement [S1]; (c) AutoGen's evaluator-optimizer pattern is structurally equivalent to the builder/evaluator pair — independently validating the role decomposition [G1]; (d) feat-13 cancellation as the honest Advanced gap: programmatic orchestration was scoped and cancelled — this is what keeps the harness at Intermediate.

### Post 4: "Intermediate is not the ceiling — here is what Advanced looks like"

**Thesis:** Every sophisticated public AI coding agent configuration scores Intermediate, not Advanced. Advanced requires something almost no team has: measurement. Here is the exact gap and two ways to close it.

**Evidence:** (a) The four-dimension ACAM scorecard for rules-skills: Intermediate across all four, Tier 3 by population — the gap between "top 0.5%" and "not Advanced" is purely a measurement gap [N2]; (b) LangSmith as the reference implementation of Advanced Interaction: prompt versioning, A/B comparison, session efficiency metrics [H3]; (c) feat-16 (rule ablation) as the specific pending work that would unlock Configuration Advanced — what it measures, how it works, what data it produces; Reflexion shows that scored improvement loops outperform static rule systems [E3]; (d) BFCL methodology as the template for skill activation measurement — seed task, correct skill target, irrelevance detection [F3].

---

## 8. Gaps Summary (No Hedging)

The following gaps are absent infrastructure. Each has a severity. None have mitigations in this document — this section records what is missing, not what compensates for it.

| Gap | Dimension | Severity | Unblocking work |
|---|---|---|---|
| Zero skill_activation eval coverage | Workflows | High | chore-skill-scenarios (pending) |
| 33% behavioral session boundary | Workflows / Interaction | High | feat-16 (ablation) + harness-context.sh trigger condition fix |
| No automated eval regression suite | Workflows | High | CI integration of session_runner.py |
| Manual agent orchestration | Multi-agent | High | feat-13 (cancelled) |
| No per-rule effectiveness data | Configuration | Medium | feat-16 (rule ablation) |
| Context isolation is prompt-level only | Multi-agent | Medium | Context package delivery (structured handoff) |
| No prompt versioning | Interaction | Medium | Rule changelog + per-rule hypothesis log |
| No prompt A/B testing | Interaction | Medium | session_runner.py prompt variant flag |
| verify-harness trusts verified field without proof | Workflows | Medium | PASS breadcrumb check before accepting verified:true |
| adversarial_harness.mdc has alwaysApply + globs | Configuration | Low | RULES_STANDARD violation — remove globs |
| negotiations/ directory unused | Multi-agent | Low | Structured per-round challenge log |
| No user interaction analytics | Interaction | Low | Real-session telemetry (not applicable for single-user repo) |
