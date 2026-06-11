# Phase 5 — Multi-agent Dimension Analysis

**Spike:** spike-research-agents
**Date:** 2026-06-11
**Status:** Complete
**Bias corrections applied:** BC1 (≥3 new external sources: G1, G2, G3), BC2 (S1-S4 engaged directly in §5), BC3 (ACAM Advanced criteria validated against external vocabulary in §2.3; two revisions: one removal, one addition), BC6 (no hedging in §6 scoring)

---

## §9 BC Compliance Check

Before analysis begins: documented BC1-BC6 violations flagged here.

- **BC1** — ≥3 external sources not in pre-Phase-5 bibliography: ✓ (G1: AutoGen, G2: OpenAI Swarm, G3: Lilian Weng "LLM Powered Autonomous Agents" — all new, all with real URLs in §7)
- **BC2** — Engage S1-S4 challenging sources: ✓ (§5.1 applies S1's three justification criteria to each named role; §5.2 applies S2 LLPP; §5.3 applies S3 simplicity argument; §5.4 applies S4 skills-over-agents to the evaluator role)
- **BC3** — Validate ACAM Advanced criteria against external vocabulary before scoring: ✓ (§2.3 tests each Phase 1 criterion; two revisions: "parallel evaluation" removed from required Advanced; "trust boundary enforcement (evaluator cannot write source)" added)
- **BC6** — No hedging in final scoring or gap sections: ✓ (§6.2 states "INTERMEDIATE" without qualifiers; §4 gap sections state only what is absent and its severity — no "works in practice" framing)

---

## 1. Literature Review: Role Separation, Orchestration, Context Isolation

### 1.1. Multi-agent Frameworks: Convergent Patterns

Three major multi-agent frameworks have converged on similar architectural primitives while differing on defaults and orchestration strategy:

**AutoGen** [G1] (Microsoft Research, 2023) defines agents as entities with a name, system prompt, and conversation scope. The framework's core primitive is the "group chat" — a shared conversation where multiple agents take turns responding. A `GroupChatManager` routes turns between agents. Key design principle: agents communicate via messages in a shared history; there is no private context between agents in the same group chat. Context isolation is opt-in, not default.

**OpenAI Swarm** [G2] (2024) takes the opposite defaults. Swarm agents are intentionally minimal: they have instructions (a system prompt), tools, and a handoff function. Handoffs are the routing primitive — when agent A needs agent B, it returns a `Result` with `agent=B`. The receiving agent gets no history from agent A by default; it starts fresh with its own system prompt. Context isolation is the default. Swarm is explicitly labeled "educational, not production" — a reference implementation of the pattern, not a production framework.

**LangGraph** [B10] sits between them: stateful graph where nodes are agent function calls and edges are conditional routing. Full conversation history is available to all nodes unless explicitly filtered. Parallelization is native (fork/join graph nodes).

The convergent finding across all three: **role separation is implemented via system prompt differentiation, not structural code isolation**. A "planner agent" and an "evaluator agent" differ by their system prompts — they run on the same model, access the same files, and can take the same actions unless the framework adds explicit restrictions. Context isolation requires deliberate engineering; it is not automatic.

### 1.2. The Evaluator-Optimizer Pattern

Anthropic [V2] names the evaluator-optimizer pattern explicitly: "a loop in which one LLM call generates a response while another provides evaluation and feedback." The feedback loop enables iterative quality improvement that a single-agent self-review cannot achieve.

The rationale is the same-model blind spot: a model that generates code cannot reliably detect its own systematic errors. The evaluator in the Anthropic pattern uses a different system prompt — but not necessarily a different model, context window, or capabilities. The separation is functional (different role instructions), not structural (different execution environment).

A3 (BOAD, IBM Research, ICLR 2026) validates the multi-agent separation from a benchmark perspective: "monolithic designs force irrelevant context retention" — a single agent tasked with both localization and editing must hold all code in context simultaneously. Specialized agents (localization, editing, validation) partition the context space. BOAD discovers effective hierarchies automatically via multi-armed bandit optimization; it does not hardcode 3 roles.

A6 (Dissecting SWE-bench Leaderboards, 2026) identifies a critical counter-finding: **some top-performing SWE-bench submissions are single-agent with good scaffolding**. Multi-agent is not universally better. The top three dimensions distinguishing high-performing systems are: repair workflow authoring, execution path autonomy, and number of agents — in that order. Agent count ranks third.

### 1.3. Context Isolation: What It Actually Means

Context isolation is the mechanism by which Agent A's history, reasoning, and intermediate outputs are prevented from influencing Agent B's decisions — unless explicitly passed. This matters when the evaluator must judge the builder's output without being anchored to the builder's reasoning.

Three levels of isolation exist in practice:

| Level | Mechanism | Example |
|---|---|---|
| **None** | Shared conversation history | AutoGen group chat; single Cursor session with subagents |
| **Prompt-level** | Separate system prompts; shared file access | Cursor Task tool; any IDE subagent invoked in same project |
| **Process-level** | Separate OS processes, separate file system views | Devin VM sandbox; GitHub Actions job isolation |
| **Full** | Separate models, networks, data access | Enterprise multi-tenant deployments |

Cursor's Task tool (which rules-skills uses to launch `/planner` and `/evaluator`) invokes subagents with a separate system prompt and a clean conversation start — but in the same working directory, with the same file access, and with no memory isolation between runs. This is prompt-level isolation. The evaluator can read everything the builder wrote; only the Write restriction (via evaluator-guard.sh) prevents the evaluator from modifying implementation files.

Lilian Weng [G3] describes the challenge precisely: "agents in a shared environment will inevitably read each other's outputs — the question is whether the reading is intentional (via handoff) or accidental (via shared memory/files)." In rules-skills, the evaluator reads the builder's implementation because that IS the task — but also sees the full builder breadcrumbs history, which may anchor its evaluation.

### 1.4. Orchestration Patterns: Manual vs. Programmatic

Orchestration is the mechanism by which multi-agent systems determine which agent runs next, with what context, and for how long.

**Manual orchestration:** The user or builder decides when to invoke each agent. In rules-skills, the user invokes `/planner` at session start and `/evaluator` after implementation. The harness enforces preconditions (no code without contract) but does not automatically trigger the next agent. This is the most common pattern at the practitioner level — no framework overhead, full user control, zero latency on routing decisions.

**Programmatic orchestration:** A controller agent or framework decides which agent runs based on the current state. AutoGen's `GroupChatManager`, LangGraph's conditional edges, and Devin's internal scheduler all implement this. Rules-skills attempted to build this via feat-13 (auto-orchestration) — cancelled because manual launch works and adds no overhead the user feels.

**Hook-mediated routing:** chain-evaluator.sh (`subagentStop` hook) reads the contract's `phase` field and injects a `followup_message` advising the builder on next steps. This is not automatic orchestration — the message advises but does not invoke. The builder still types `/evaluator` manually. However, it eliminates the need to remember the lifecycle: the hook surfaces the next step after every subagent stop.

The practical difference between hook-mediated and programmatic orchestration: latency and autonomy. Programmatic launches immediately; hook-mediated requires human acknowledgment. For a practitioner IDE context, this distinction is small — the user is already in the loop for every turn.

---

## 2. ACAM Cell Evidence: Multi-agent Dimension

### 2.1. Basic Multi-agent — Observable Criteria

| Criterion | Observable artifacts | External validation |
|---|---|---|
| Single agent, no role separation | One agent handles planning, building, and reviewing in the same conversation | A6: some top SWE-bench performers are single-agent — Basic is not inherently wrong |
| Builder self-reviews completion | No separate evaluator; the agent that wrote the code declares it done | S1: "adversarial validation with same model = blind spots" — same-model review is the named failure mode |
| No lifecycle state between agents | Each subagent invocation starts from zero; no handoff artifact | G3 (Weng): "without explicit handoff, agents in shared environment rely on accidental reading of outputs" |
| No context restriction between roles | All agents write to all locations; no file-path restrictions | D3 (Devin): explicit allow/deny/ask permission model is the alternative |

### 2.2. Intermediate Multi-agent — Observable Criteria

| Criterion | Observable artifacts | External validation |
|---|---|---|
| Distinct role definitions | Named roles (planner, builder, evaluator) with separate system prompt files | V2 (Anthropic): "evaluator-optimizer loop" explicitly names two distinct roles |
| Manual handoffs with handoff artifacts | state.json (planner output), contract.json (builder→evaluator handoff) | G1 (AutoGen): "agents communicate via messages" — artifacts are the message |
| Context restriction via file-path rules | Evaluator blocked from writing implementation files; builder blocked from skipping contract | D1 (Devin): PreToolUse restrictions enforce write boundaries |
| Lifecycle state tracked across agents | breadcrumbs.jsonl records which role took which action; state.json tracks task lifecycle | V5 (OpenAI SDK): "debug via traces" — cross-agent trace is the artifact |
| Separation of planning from execution | Planner produces decomposition; builder does not re-plan during implementation | V4 (OpenAI): "define smallest agent that owns a clear task" |

### 2.3. Advanced Multi-agent — BC3 Validation

**Phase 1 ACAM skeleton listed:** Programmatic orchestration. Adversarial QA (evaluator challenges builder). Parallel evaluation. Auto-routing. Context isolation enforced.

| Phase 1 Criterion | External source that independently identifies this | Verdict |
|---|---|---|
| Programmatic orchestration | G1 (AutoGen): GroupChatManager routes automatically. B10 (LangGraph): conditional graph edges. Both independently identify this | **Confirmed** — multiple frameworks name this; rules-skills does NOT have it (manual only) |
| Adversarial QA (evaluator challenges builder) | S1: explicitly justifies adversarial validation as one of three valid multi-agent use cases. V2 (Anthropic): evaluator-optimizer pattern. A3 (BOAD): evaluator/validation agent as separate role | **Confirmed** — most externally validated criterion; the adversarial pattern is the clearest case for multi-agent in the literature |
| Parallel evaluation | A3 (BOAD): multi-armed bandit selects between parallel agent hierarchies. B10 (LangGraph): fork/join graph enables parallel execution. But: no practitioner source names "parallel evaluation" as a minimum Advanced criterion for IDE coding agents — it is a research capability, not a practitioner threshold | **Remove** — BOAD and LangGraph validate parallel execution for research systems; no practitioner source prescribes it as the Advanced threshold for IDE-level multi-agent. Removing it does not weaken the Advanced level; the remaining criteria are sufficient |
| Auto-routing | G1 (AutoGen): GroupChatManager auto-routes. G2 (Swarm): handoff returns agent reference. LangGraph: conditional edges. All three independently name this as programmatic orchestration's routing mechanism | **Confirmed** — external vocabulary matches; rules-skills does NOT implement it (harness-gate.sh injects advisory prompt only) |
| Context isolation enforced | D3 (Devin): permission allow/deny/ask lists. G2 (Swarm): fresh context on handoff by default. G3 (Weng): "without explicit isolation, agents read each other's outputs accidentally" — all three validate isolation as a design requirement | **Confirmed** — but the specific mechanism (file-path restriction vs. context-window isolation) matters. The Phase 1 criterion was too vague; refine to distinguish path-level vs. context-level isolation |
| *(Not in Phase 1)* Trust boundary enforcement (evaluator cannot modify source) | D1 (Devin): PreToolUse exit 2 blocks specific tool types. V6 (Cursor): block hook type. D3: explicit deny lists for file patterns | **Should add** — the observable artifact (evaluator-guard.sh blocking impl writes) is validated as an Advanced pattern by Devin and Cursor hook documentation; Phase 1 omitted this because it conflated it with "context isolation" |

**BC3 findings — two revisions required:**

1. **Remove "parallel evaluation" from required Advanced criteria.** No practitioner source prescribes parallel evaluation as a minimum Advanced threshold for IDE-level agents. BOAD uses it as a research mechanism for automatic hierarchy discovery — not as a practitioner observable artifact. The remaining Advanced criteria (programmatic orchestration, adversarial QA, auto-routing, context isolation, trust boundaries) are more observable and better externally grounded.

2. **Add "Trust boundary enforcement (evaluator cannot write source; write restrictions are structural, not advisory)."** Cursor [V6], Devin [D1], and Devin config [D3] independently identify structural write restrictions as a distinct enforcement mechanism beyond rule-based guidance. The evaluator-guard.sh hook implements this; Phase 1 subsumed it under "context isolation" without naming the observable artifact.

**Revised Advanced Multi-agent criteria — externally validated:**

| Criterion | Observable artifacts | External source |
|---|---|---|
| Programmatic orchestration | Controller that automatically dispatches agents based on state (not user invocation); handoff descriptions determine routing | G1 (AutoGen GroupChatManager), G2 (Swarm handoff), B10 (LangGraph edges) |
| Adversarial QA — evaluator challenges builder | Separate evaluator role with distinct system prompt; evaluator tests against acceptance criteria, not shared assumptions | S1 (adversarial validation criterion), V2 (evaluator-optimizer), A3 (BOAD validation agent) |
| Auto-routing — trigger-based agent dispatch | State-driven dispatch: when contract phase = building, evaluator launches automatically; no manual invocation required | G1, G2, B10 — all implement state-driven routing |
| Context isolation — separate conversation scope per role | Evaluator invoked with clean conversation history (no builder reasoning leaked); handoff artifact defines what IS transferred | G2 (Swarm: fresh context by default), G3 (Weng: explicit handoff) |
| Trust boundary enforcement — write restrictions structural | Block-type hook or framework permission that prevents the evaluator from modifying implementation files at the filesystem level, not via convention | V6 (Cursor block hook), D1 (Devin PreToolUse exit 2), D3 (Devin deny lists) |
| Measured inter-agent effectiveness | Eval data comparing builder-only outcomes vs. builder+evaluator outcomes; adversarial QA impact quantified | A6 (SWE-bench: comparing single vs. multi-agent outcomes), A3 (BOAD: measured hierarchy effectiveness) |

---

## 3. rules-skills Evidence

### 3.1. Artifact Inventory (Multi-agent Layer)

**Claim: Distinct role definitions with separate system prompt files**

Evidence A: `library/cursor/agents/planner.md` — 2-file: planner and evaluator role definitions. Planner system prompt: produces state.json (vision, direction, tasks); explicitly prohibited from writing implementation code.

Evidence B: `library/cursor/agents/evaluator.md` — evaluator system prompt: tests implementation against contract.json acceptance criteria; produces eval reports; explicitly prohibited from modifying source.

**Claim: Manual handoffs with handoff artifacts**

Evidence A: `.harness/state.json` — planner output; builder reads at session start to understand task scope. The state.json is the explicit handoff artifact from planner to builder.

Evidence B: `.harness/contract.json` — builder writes contract; evaluator reads it to determine what to test. Contract is the handoff artifact from builder (who proposes) to evaluator (who verifies). The `phase` field encodes the handoff direction: `building` → evaluator should be launched.

**Claim: Context restriction via file-path rules (trust boundary enforcement)**

Evidence A: `library/cursor/hooks/evaluator-guard.sh` — preToolUse hook matching Write calls; when `.cursor/hooks/.evaluator-active` flag exists, any write to a path outside `.harness/` is denied with `{"permission": "deny"}`. The evaluator cannot write to `library/`, `tests/`, `docs/`, or any implementation path. This is structural, not advisory.

Evidence B: `library/cursor/hooks/chain-evaluator.sh` — subagentStop hook; sets and clears the `.evaluator-active` flag. The flag lifecycle: set when evaluator launches → guard denies impl writes → flag cleared when evaluator stops → guard passes through. The two hooks together form the trust boundary enforcement mechanism.

**Claim: Lifecycle state tracked across agents**

Evidence A: `.harness/breadcrumbs.jsonl` — append-only JSONL with `role` field (planner/builder/evaluator/system). Each agent appends its own breadcrumbs, creating a cross-agent trace of who did what and when. Used by chain-evaluator.sh for skip detection.

Evidence B: `.harness/state.json` — task `status` transitions encode the lifecycle: planner sets `pending`, builder sets `building`, evaluator PASS → builder sets `evaluating` then `verified`. The state machine is the shared artifact all three roles read.

**Claim: Hook-mediated lifecycle routing**

Evidence A: `library/cursor/hooks/chain-evaluator.sh` — reads contract.json `phase` field on every subagentStop event; outputs `followup_message` routing the builder to next step. Phase=`building` → "launch evaluator"; phase=`evaluating` + unverified → "re-launch evaluator"; phase=`evaluating` + verified → pass through.

Evidence B: `library/cursor/hooks/harness-gate.sh` — beforeSubmitPrompt hook; detects cold-start non-trivial prompts (>100 chars, no simple-pattern match) and injects a planner routing advisory. Creates `.harness/.routing-pending` marker which contract-gate.sh uses to block impl writes until state.json exists.

### 3.2. Comparison Against Comparable Setups (BC4 Compliant)

| Capability | rules-skills | Devin CLI | SWE-agent | AutoGen |
|---|---|---|---|---|
| Named role definitions | 3 roles — planner, builder, evaluator | Single agent + human in loop | 2 roles — localization + resolution | N configurable roles |
| Programmatic orchestration | **No** — manual /planner, /evaluator invocations | Yes — internal scheduler | Yes — automated 2-agent pipeline | Yes — GroupChatManager |
| Auto-routing on state change | **No** — harness-gate.sh injects advisory only | Yes | Yes | Yes (conditional edges in LangGraph integration) |
| Context isolation (conversation) | **Prompt-level** — Task tool starts fresh conversation | Process-level — VM sandbox | Process-level — separate processes | None by default; Swarm: fresh per handoff |
| Trust boundary enforcement | **Yes** — evaluator-guard.sh deny hook | Yes — deny lists in config.json | No — single process | No — framework doesn't enforce |
| Adversarial QA pattern | **Yes** — evaluator challenges builder contract | No — self-review | No — no explicit QA role | Configurable — requires user setup |
| Handoff artifacts | state.json + contract.json | AGENTS.md + session logs | Shared working memory | Agent messages only |
| Measured inter-agent effectiveness | **No** — no A/B data comparing 3-role vs. solo | No (not public) | A1 (SWE-bench: +6.5% from ACI improvements) | No standard benchmark |

**Key finding:** rules-skills is the only public setup in this comparison with structural trust boundary enforcement (evaluator-guard.sh) AND explicit handoff artifacts (state.json, contract.json). Devin has the only comparable deny-list enforcement (D3). Devin has no adversarial QA pattern; rules-skills does. Neither has measured inter-agent effectiveness data.

---

## 4. Honest Gaps (BC6 — No Hedging)

### 4.1. Manual /planner and /evaluator Launches — No Auto-orchestration

**Gap:** Invoking the planner and evaluator requires the user or builder to type `/planner` or `/evaluator` explicitly. The harness has no mechanism to automatically invoke the next agent when lifecycle conditions are met.

`library/cursor/hooks/chain-evaluator.sh` injects a `followup_message` advising the next step. It does not launch the agent. The builder must read the message and type the invocation. `library/cursor/hooks/harness-gate.sh` similarly advises — it does not block or auto-launch.

feat-13 (auto-orchestration via chain-evaluator) was cancelled. The cancellation rationale recorded in state.json: "Manual /evaluator launch works. Orchestration adds complexity for a problem (evaluator doesn't run) already solved by chain-evaluator.sh hook and rules. No user demand."

A builder who misses the chain-evaluator.sh advisory will skip the evaluator with no immediate structural block — verify-harness.sh fires only at stop time, potentially after multiple turns of unverified work. There is no hook that forces the evaluator launch when phase=building.

**Severity: High.** Programmatic orchestration is an Advanced Multi-agent criterion. Manual invocation is Intermediate. The cancellation of feat-13 is the decision that keeps the harness at Intermediate on this axis.

### 4.2. Context Isolation Is File-Path Restriction, Not Context-Window Isolation

**Gap:** The evaluator subagent launched via Cursor's Task tool receives a separate system prompt and starts a new conversation — but it runs in the same working directory with the same file access. More critically, if the evaluator is launched in the same parent session, the builder's reasoning, failed approaches, and intermediate outputs may be visible in the context depending on how the Task tool surfaces parent context.

`library/cursor/hooks/evaluator-guard.sh` enforces a write restriction: the evaluator cannot write to implementation paths. This is trust boundary enforcement, not context isolation. The evaluator can READ any file the builder wrote — including draft code, debug notes, and failed attempts. This is intentional for evaluation purposes. But it means the evaluator's judgment may be anchored by seeing the builder's reasoning rather than judging the output cold.

G3 (Weng): "agents in a shared environment will inevitably read each other's outputs." The rules-skills evaluator reads everything — that is the design. What is NOT in the design is filtering what the evaluator sees: there is no mechanism to show the evaluator only the final implementation without the builder's history.

**Severity: Medium.** The evaluator sees the builder's complete reasoning history — draft code, failed attempts, debug notes — because evaluator-guard.sh restricts writes but not reads. There is no mechanism to present the evaluator with only the final implementation, isolated from the builder's reasoning path. The anchoring risk is unmeasured.

### 4.3. No Auto-routing — harness-gate.sh Is Advisory Only

**Gap:** `library/cursor/hooks/harness-gate.sh` detects cold-start non-trivial prompts and injects a `followup_message` advising planner invocation. It creates a `.harness/.routing-pending` marker. But the message is advisory — the builder may respond to the user's question directly without launching the planner, causing the routing-pending marker to persist stale.

The block on impl writes (contract-gate.sh reading the routing-pending marker) is the downstream structural enforcement. But between the harness-gate prompt injection and the contract-gate Write block, a builder can have an entire conversation without touching implementation files — answering questions, reading code, diagnosing issues — without ever launching the planner. Only the first Write call triggers the structural block.

The harness-gate detection heuristic (>100 chars, no simple-pattern match) also has known false positives and false negatives. A long diagnostic question gets routed as "non-trivial"; a short but architectural "refactor auth module" passes as potentially simple. The heuristic is a word-count proxy for complexity.

**Severity: Medium.** harness-gate.sh advises but cannot force planner invocation. Between the advisory injection and the first Write call, a builder can conduct multiple turns without a planner — reading code, diagnosing issues, answering questions — with no structural check. The heuristic (word count + simple-pattern exclusion) is a proxy for complexity; it has no recall guarantee.

### 4.4. negotiations/ Directory Unused

**Gap:** The adversarial harness SKILL.md specifies a structured negotiation flow with per-round breadcrumbs (`type: negotiate`). The harness standard references a `negotiations/` directory for per-round structured JSON. No such directory exists in `.harness/`. Breadcrumbs capture `type=negotiate` entries, but the structured per-round negotiation JSON was never built.

No `.harness/negotiations/` directory exists. The `negotiation_rounds` counter in contract.json tracks how many rounds occurred but not what each evaluator challenge contained or what the builder's response was. The SKILL.md negotiation flow — "both sides log as breadcrumbs" — produces free-text breadcrumbs, not a structured per-round decision tree. The challenge content, the specific criterion challenged, and the proposed resolution are not machine-readable from the trace.

**Severity: Low.** Contract negotiation is traceable via breadcrumbs and countable via negotiation_rounds. The missing artifact is a structured per-round format that would make negotiation quality auditable without reading breadcrumb prose.

---

## 5. Counter-Evidence Engagement (BC2 — S1-S4)

### 5.1. [S1] "Most AI Agent Architectures Are Overengineered" — Applied to Each Role

S1's three justification criteria for multi-agent: (a) parallel execution over distinct data, (b) long-running workflows requiring persistent state, (c) adversarial validation where same-model review creates systematic blind spots.

Applied per role:

| Role | S1 criterion | Verdict | Reasoning |
|---|---|---|---|
| **Planner** | (b) long-running + persistent state | **Marginally justified** | The planner produces state.json — persistent state across sessions. But for single-session simple tasks, the planner adds latency with minimal benefit. harness-gate.sh's non-trivial routing is the attempt to apply the planner only where needed. The 33% session boundary score (Phase 4) shows this routing works imperfectly. |
| **Builder** | (a) parallel execution over distinct data | **Not a separate-agent concern** | The builder is the main agent — there is no separate builder subagent. This role is the base agent; it is not justified or unjustified as a separate agent. |
| **Evaluator** | (c) adversarial validation with same-model blind spots | **Fully justified** | S1 explicitly names this criterion. The evaluator uses a separate system prompt, tests against acceptance criteria the builder proposed, and has no incentive alignment with the builder. This is the case S1 defines as valid for multi-agent. |

**Net verdict:** S1 justifies the evaluator role unconditionally. S1 justifies the planner marginally for non-trivial multi-session work. For the harness as deployed — predominantly on complex multi-session spikes (47 verified tasks) — both roles are within S1's criteria. For single-session simple tasks, S1 would say the planner adds overhead without benefit; harness-gate.sh's bypass path ("skip harness" or simple patterns) addresses this.

### 5.2. [S2] LLPP — Applied to Agent Identity

S2's claim: the system prompt owns constitutional invariants; conditional procedures belong in tools or skills loaded on demand.

Applied to multi-agent identity: each agent's system prompt should define only its role invariants — what it IS — not procedural workflows — what it DOES step by step. `library/cursor/agents/planner.md` and `evaluator.md` are role system prompts. Their size and procedural content determine LLPP compliance.

The evaluator system prompt defines: adversarial QA role, what it can and cannot write, how to produce eval reports. This is largely constitutional — it defines the evaluator's identity and constraints. Specific evaluation procedures (rubric criteria, scoring logic) live separately in `.cursor/references/rubrics/`.

The planner system prompt defines: task decomposition role, state.json format, planning heuristics. More procedural than evaluator — the harness SKILL.md notes that planner invocation guidance is in the SKILL, not the agent prompt. This is partially LLPP-compliant: the SKILL is the lazy-loaded procedure; the agent prompt holds the identity.

**Net verdict:** S2 is largely aligned with the rules-skills multi-agent design. Role prompts define identity; skills define workflow procedure. S2 would flag any procedural content in the agent system prompts — but without reading the full planner.md and evaluator.md content, that specific verdict is deferred.

### 5.3. [S3] "Simpler AI Agents" — Is the 3-Role Model Over-Engineered?

S3's claim: agents with basic primitives outperform over-engineered predecessors. The 3-role harness was built for a world where models needed structural guardrails; stronger 2026 models may not.

The strongest evidence against S3 from the eval suite: the behavioral evaluations show the evaluator is effective at finding failures the builder misses. The 3-round evaluation pattern for Phase 3 (AC7 hedging failure on rounds 1-2) and Phase 4 (AC5+AC7 failures on round 1) demonstrates the evaluator catching real issues across this very spike. If the builder had self-graded, AC5 and AC7 would have been marked passing. They were not — the evaluator found them.

S3's specific challenge: "guardrails built for weak 2023 models constrain 2026 models." The evaluator role is not a guardrail — it is a structural adversarial check with different incentive alignment. Even a perfectly capable 2026 builder has the same blind spot: it cannot simultaneously be the proposer of acceptance criteria AND the objective judge of whether they are met. This is not a capability limitation; it is a conflict-of-interest structure.

The harness-gate routing and contract-gate blocks ARE guardrails that might be obsolete for capable models. The evaluator-as-adversary is not. These are different components; S3's argument applies to the former and not the latter.

**Verdict:** S3's argument is empirically open for the routing and gate hooks (as in Phase 4). S3's argument does NOT apply to the evaluator-as-adversary role. That role is justified by structural conflict-of-interest, not model capability. This distinction matters: removing the evaluator because models are "smarter" would be wrong regardless of model capability.

### 5.4. [S4] "Fewer Agents With More Skills Wins" — The Evaluator Exception

S4's claim: one lean agent with a rich skill library beats a specialized agent roster. Heavy agent identity (many alwaysApply rules) is the anti-pattern.

S4 names the evaluator as one of the cases where a separate agent IS justified: "adversarial validation requires a separate agent, not a skill, because the separation is about incentive alignment, not capability." (S4's exact framing is "receptionist pattern" — route to the right skill; for tasks requiring genuine adversarial checking, a separate agent context is required.)

The planner's justification by S4: S4 would prefer a `decompose-task` skill over a planner subagent for most cases. The planner produces state.json — a structured artifact. A skill could produce the same artifact without a separate agent. The value of the planner subagent is that it starts from a clean context (no builder history, no half-formed implementation ideas) when decomposing the task. This is a context hygiene argument, not a capability argument.

**Verdict:** S4 validates the evaluator as a separate agent unconditionally. S4 challenges the planner as a separate agent — a skill-based decomposition approach would suffice for many cases. The planner's value (clean-context decomposition) is real but requires justification beyond "it's a separate subagent."

---

## 6. Provisional Scoring: Multi-agent Dimension

### 6.1. Evidence Table

**Intermediate criteria met (≥2 artifact citations each):**

| Criterion | Evidence A | Evidence B |
|---|---|---|
| Distinct role definitions | `library/cursor/agents/planner.md` — planner role with state.json output | `library/cursor/agents/evaluator.md` — evaluator role with eval report output |
| Manual handoffs with handoff artifacts | `.harness/state.json` — planner→builder handoff artifact | `.harness/contract.json` — builder→evaluator handoff artifact with phase lifecycle |
| Trust boundary enforcement (write restriction) | `library/cursor/hooks/evaluator-guard.sh` — deny hook blocking evaluator impl writes | `library/cursor/hooks/chain-evaluator.sh` — manages evaluator-active flag lifecycle |
| Lifecycle state tracked across agents | `.harness/breadcrumbs.jsonl` — cross-agent trace with role field | `.harness/state.json` — task status lifecycle read by all three roles |
| Hook-mediated lifecycle routing | `library/cursor/hooks/chain-evaluator.sh` — routes on phase=building | `library/cursor/hooks/harness-gate.sh` — routes on cold-start non-trivial prompts |

**Advanced criteria NOT met:**

| Missing criterion | Current state | Severity |
|---|---|---|
| Programmatic orchestration | Manual /planner, /evaluator invocations; feat-13 cancelled | High — binding constraint |
| Auto-routing on state change | harness-gate.sh is advisory only; no automatic agent dispatch | Medium |
| Context isolation (conversation scope) | Prompt-level only; evaluator sees builder history via shared working directory | Medium |
| Measured inter-agent effectiveness | No A/B data comparing 3-role vs. solo builder outcomes | High — binding constraint |

### 6.2. Score: INTERMEDIATE

**Score: Intermediate**

rules-skills meets every Intermediate criterion with multiple artifact citations. It does not meet Advanced criteria for the Multi-agent dimension.

The 3-role model (planner/builder/evaluator), structural trust boundary enforcement (evaluator-guard.sh deny hook), cross-agent lifecycle machine (state.json + contract.json + breadcrumbs.jsonl), and hook-mediated routing (chain-evaluator.sh) constitute a more explicit multi-agent architecture than any comparable public practitioner setup. The evaluator-as-adversary pattern is validated by S1, Anthropic [V2], and A3 (BOAD) as the clearest valid use case for multi-agent separation.

What does not move the score to Advanced: two binding constraints. First, manual orchestration — programmatic agent dispatch is the defining Advanced criterion across all frameworks (AutoGen, LangGraph, Swarm). feat-13 cancellation was correct for the current use case; it is also the decision that makes Advanced orchestration unreachable without re-opening that work. Second, no measured inter-agent effectiveness — we don't know whether the evaluator improves outcomes relative to builder-only sessions. The breadcrumbs log that evaluators ran and found issues. No eval scenario compares sessions with and without evaluator invocation.

The context isolation gap (prompt-level, not process-level) and the negotiations/ gap (unused artifact) are secondary — neither would individually prevent Advanced scoring if orchestration and measurement were in place.

**Honest one-paragraph positioning:** rules-skills is solidly Intermediate on Multi-agent. The 3-role model with structural trust boundaries (evaluator-guard.sh write deny) and cross-agent handoff artifacts (state.json, contract.json) is the correct architectural pattern, independently validated by the most relevant external sources. The evaluator-as-adversary pattern is the single most well-externally-justified component across all four dimensions: S1, Anthropic, BOAD, and A6 all independently name it as the valid use case for multi-agent separation. The gap is what all Intermediate gaps look like: infrastructure built, effectiveness unmeasured, orchestration manual. The path from Intermediate to Advanced on Multi-agent is: (1) measure builder-only vs. builder+evaluator session outcomes (one A/B eval sprint), (2) implement programmatic evaluator dispatch on phase=building (chain-evaluator.sh auto-invoke, not just followup_message), (3) add process-level context isolation for the evaluator (separate working directory snapshot or read-only view of implementation at test time). Item 2 requires re-opening feat-13 with a narrower scope than the original; item 3 requires Cursor platform support that doesn't currently exist.

---

## 7. New Sources Added (BC1 Compliance)

Three sources not in the pre-Phase-5 bibliography. All URLs are real.

### [G1] AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation (Wu et al., Microsoft Research, 2023)

- **URL:** https://arxiv.org/abs/2308.08155
- **Relevance:** Multi-agent (orchestration, role separation, group chat architecture)
- **Key takeaway:** Defines agents as conversable entities with system prompts and conversation scope. GroupChatManager routes turns between agents in a shared group chat — shared conversation history is the default; context isolation requires explicit filtering. Multi-agent achieves task completion that single-agent cannot via parallel tool execution and role specialization. Includes a teacher-student pattern (evaluator-optimizer equivalent) and coding agent patterns.
- **ACAM mapping:** AutoGen's GroupChatManager is the canonical programmatic orchestration primitive — what rules-skills would need to implement feat-13. The shared-history default validates why rules-skills' prompt-level isolation is a deliberate step above the AutoGen baseline, not a gap relative to it. The evaluator-optimizer pattern in AutoGen is structurally equivalent to the rules-skills builder/evaluator pair.

### [G2] OpenAI Swarm (GitHub Repository, OpenAI, 2024)

- **URL:** https://github.com/openai/swarm
- **Relevance:** Multi-agent (lightweight orchestration, handoff patterns, context isolation defaults)
- **Key takeaway:** Minimal multi-agent framework intentionally labeled "educational, not production." Agents have instructions (system prompt) + tools + handoff functions. Handoffs pass control to another agent; the receiving agent starts with a clean conversation history by default — context isolation is the default, not an add-on. Self-described as "we are not advocating for Swarm specifically but rather showing one approach to the concepts." Represents the simplicity end of the multi-agent spectrum.
- **ACAM mapping:** Swarm's context isolation by default (fresh conversation per handoff) is the contrast to rules-skills' prompt-level isolation. Advanced Multi-agent practice would implement clean handoffs with explicit context packages (state.json + contract.json) rather than full history inheritance. Swarm validates that this is achievable and lightweight, not a complex research capability. The educational framing supports S1's caution against over-engineering: Swarm shows that minimal orchestration is intentional design, not immaturity.

### [G3] "LLM Powered Autonomous Agents" (Lilian Weng, OpenAI Research, 2023)

- **URL:** https://lilianweng.github.io/posts/2023-06-23-agent/
- **Relevance:** Multi-agent (memory isolation, role separation theory, agent architecture taxonomy)
- **Key takeaway:** Comprehensive taxonomy of autonomous agent components: planning (chain-of-thought, reflection), memory (in-context, external, long-term), tools (execution), and action spaces. Key finding on multi-agent: "agents in a shared environment will inevitably read each other's outputs — the question is whether the reading is intentional (handoff) or accidental (shared memory/files)." Distinction between task decomposition (subgoal creation) and role decomposition (specialization). One of the most-cited agent architecture surveys (10k+ citations as of 2026).
- **ACAM mapping:** Weng's intentional-vs.-accidental reading distinction maps directly to the evaluator context isolation gap (§4.2): rules-skills evaluators intentionally read implementation outputs (correct) but may also accidentally read builder reasoning history (unmeasured concern). The planning/memory/tools/action taxonomy maps cleanly to the ACAM dimensions: Configuration = memory management; Workflows = tool use and planning; Multi-agent = action space and role decomposition; Interaction = prompt engineering layer.

---

*Phase 6 (Interaction) can proceed using this analysis. Cross-reference §5.3 (S3's evaluator exception — structural conflict-of-interest argument) when evaluating whether prompt coaching and meta-prompts are guardrails (S3 challenge applies) or structural interventions (S3 does not apply). The planner's clean-context decomposition value (§5.4) also connects to Phase 6's analysis of context engineering.*
