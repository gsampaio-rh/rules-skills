# model-selection.md — Role-Based Model Routing Research

**Spike:** spike-subagent-model-mechanics + spike-model-selection
**Date started:** 2026-06-13
**Status:** Complete (both spikes verified).

---

## Platform Mechanics

### How `model:` frontmatter works in Cursor subagents

Cursor subagent files (`.cursor/agents/*.md`) support a `model:` field in YAML frontmatter. Two values are valid:

| Value | Behavior |
|---|---|
| `inherit` (default) | The subagent uses the same model as the parent agent. If the parent runs on `composer-2.5`, the subagent also runs on `composer-2.5`. |
| A specific model ID (e.g. `composer-2.5`, `gpt-5.5`) | The subagent uses exactly that model, regardless of what the parent uses. |

**Current state of this harness:**

Both `library/cursor/agents/planner.md` and `library/cursor/agents/evaluator.md` have `model: inherit`. This means:
- If a user runs the builder session on a fast/cheap model, the planner and evaluator also run on that model.
- If the user switches to a high-reasoning model in the IDE, planner and evaluator inherit that — no per-role differentiation.

Setting a specific model ID in the agent file decouples that role from the parent model entirely.

### When Cursor overrides the configured model

Cursor honors the `model:` field in subagent frontmatter unless one of three conditions applies:

1. **Team admin restrictions** — An organization admin has blocked the specified model at the account level. The subagent falls back to a compatible model.
2. **Max Mode required** — The configured model requires Max Mode and the user does not have it enabled. On legacy request-based plans without Max Mode, subagents run using Composer regardless of any `model` field.
3. **Plan limitations** — The model is not available on the user's current Cursor plan.

**Important implication for this harness:** if a consumer copies `library/cursor/agents/evaluator.md` with `model: gpt-5.5` and their plan doesn't include GPT-5.5, the evaluator silently falls back. There is no error surface — just a model substitution. Config defaults in `feat-role-model-config` must document this and recommend `model: inherit` as the safe distributable default, with specific model IDs as an opt-in override.

### Cross-reference with Phase 5 findings

Phase 5 multi-agent analysis (`phase-5-multi-agent.md`, §1.3) established that Cursor's Task tool provides **prompt-level isolation** — each subagent starts with a clean conversation context but shares the same working directory and file access. The platform docs confirm this:

> "Subagents start with a clean context. The parent agent includes relevant information in the prompt since subagents don't have access to prior conversation history."

No contradiction found. The `model:` field is a new surface not covered in Phase 5 (that research predates the Cursor subagent docs being expanded). The context isolation level (prompt-level, not process-level) remains unchanged.

**New finding from platform docs:** Built-in subagents (`explore`, `bash`, `browser`) use faster models by default — the `explore` subagent explicitly "uses a faster model to run many parallel searches." This validates the routing hypothesis: Cursor itself already routes by role capability, not by inheriting the parent model uniformly.

---

## Eval Fidelity

### What the eval sandbox can and cannot observe

The rules-skills eval pipeline (`tests/eval/session_runner.py`) launches agents programmatically via the Cursor SDK:

```python
Agent.prompt("...", AgentOptions(model="composer-2.5", ...))
```

The SDK's `model=` parameter sets the **outer (builder) agent's model**. This is a different path from the IDE Task tool invocation that reads subagent frontmatter.

| Path | Model determination |
|---|---|
| IDE Task tool (`/planner`, `/evaluator`) | Reads `model:` from agent frontmatter; falls back per plan/admin/Max Mode conditions |
| SDK `Agent.prompt(model=)` | Sets the outer agent model; subagents invoked by that outer agent inherit or use their frontmatter `model:` |
| `eval-model-matrix` scenarios | Can vary the **outer builder model** via `MODEL=` Makefile var or `AgentOptions`; subagent model follows frontmatter |

**What eval CAN observe:**
- Whether builder behavior changes across outer model assignments (does `gpt-5.5` as builder produce better contracts than `composer-2.5`?)
- Whether scenarios pass/fail at different rates with different outer models
- Harness compliance pass rate as a function of outer model

**What is BLOCKED by platform constraints:**
- Eval cannot independently verify which model the planner or evaluator subagent actually ran on during a session — the SDK does not surface subagent model in the run transcript
- Eval cannot force a subagent to use a specific model if the user's plan blocks it — the fallback is silent
- If a scenario invokes `/planner` inside the session, the planner's model is determined by `library/cursor/agents/planner.md` frontmatter as loaded by the IDE — not by the SDK's `model=` parameter

**Scope boundary for `feat-eval-role-model-matrix`:**

The matrix can compare **builder-level model assignments** and measure harness compliance outcomes. It cannot directly compare "evaluator running on model X vs model Y" because the evaluator's model follows frontmatter, not the SDK's outer model parameter. The practical test is: change the frontmatter, re-run scenarios, compare harness compliance. This requires at least two distinct runs, not a parametric sweep.

---

## Role Capability Requirements

Analysis of what each role needs from a model, based on what failures look like in practice (breadcrumbs evidence + Phase 5 S1-S4 analysis).

### Planner

**Core task:** Decompose a vague user request into discrete tasks with explicit scope boundaries. Write to `state.json`. Terminate without implementing.

**Failure modes observed:**
- Producing implementation details when scope should stay high-level (violations of "What You Do NOT Do" in planner.md)
- Adding tasks that duplicate existing pending tasks (requires reading state.json and reasoning about overlap)
- Producing tasks without explicit scope inclusions/exclusions (boundary under-specification)

**Model requirements:**
- Instruction following — must honor termination protocol and write-restriction
- Structured output — state.json is JSON; the model must produce valid JSON without fabrication
- Task decomposition quality — the primary value-add; this benefits from stronger reasoning

**Routing signal:** task type + complexity. For a simple 1-file fix, a fast model is adequate. For architectural decomposition (3+ files, vague scope), a reasoning model is better. The harness-gate.sh heuristic (word count proxy for complexity) is already the routing signal — if it were wired to model selection, it would pick fast for simple prompts and strong for complex ones.

### Builder

**Core task:** Implement one task at a time against a negotiated contract. Broad tool access. Longest context window consumer.

**Failure modes observed (from eval scenarios):**
- Skipping contract gate (writing without contract.json)
- Self-grading (marking verified without evaluator PASS)
- Not writing breadcrumbs
- Post-hoc contract writing (writing contract after implementation)

**Model requirements:**
- Rule following under tool pressure — the harness protocol is a set of meta-rules the model must follow while also doing the primary work
- Code generation quality — the actual deliverable
- Long context — builder sessions span multiple tool calls, file reads, test runs

**Routing signal:** this is the user's choice in the IDE — the builder model is whatever model the user has configured for their chat session. The harness cannot route this without programmatic SDK invocation (feat-13b territory).

### Evaluator

**Core task:** Adversarially test an implementation against contract acceptance criteria. Produce a binary PASS/FAIL per criterion with evidence. NEVER write to source files.

**Failure modes observed:**
- Sycophancy — marking criteria PASS without running the actual verification command
- Partial credit — reporting "mostly works" instead of binary PASS/FAIL
- Deferring failures — "can fix later" framing
- Insufficient evidence — "looks correct" without command output

**Model requirements:**
- Anti-sycophancy — the evaluator.md has explicit anti-sycophancy rules. A model that is strongly biased toward approval is a liability here. Larger/reasoning models are observed to be more willing to FAIL outputs.
- Evidence generation — must run verification commands and cite specific output
- Write restriction compliance — must not attempt to write to implementation paths (structurally enforced by evaluator-guard.sh, but the model should not even try)

**Routing signal:** evaluation mode (always the same role, always adversarial). The evaluator should consistently use a model that resists sycophancy. A frontier reasoning model is the candidate.

---

## Recommendations for `feat-role-model-config`

### Distributable defaults (safe for all plans)

```yaml
# library/cursor/agents/planner.md
model: inherit
```

```yaml
# library/cursor/agents/evaluator.md  
model: inherit
```

**Rationale:** `inherit` is the safe distributable default. It works on all plans, requires no admin approval, and avoids silent fallback surprises. Consumers who want per-role routing opt in by changing the field.

### Opt-in overrides (documented in AGENTS.md)

If the user wants the evaluator to use a different model than the builder, they change the frontmatter:

```yaml
# .cursor/agents/evaluator.md (consumer local copy, not library)
model: gpt-5.5   # or whatever frontier model they want for adversarial QA
```

The `library/cursor/harness-model-routing.json` (to be created by `feat-role-model-config`) should document:

```json
{
  "roles": {
    "planner": {
      "default": "inherit",
      "rationale": "Planner task length is moderate; inherit keeps cost proportional to user's chosen model. Override to a reasoning model for architectural decomposition work.",
      "suggested_override": "composer-2.5"
    },
    "evaluator": {
      "default": "inherit",
      "rationale": "Evaluator needs anti-sycophancy. If the parent model has strong approval bias, override to a frontier reasoning model. inherit works when parent is already a strong model.",
      "suggested_override": "auto"
    },
    "builder": {
      "default": "user-configured (not frontmatter-settable)",
      "rationale": "Builder is the main agent; its model is the user's IDE session model. Not a subagent — no frontmatter to set.",
      "suggested_override": "n/a"
    }
  },
  "override_path": "Copy library/cursor/agents/[role].md to .cursor/agents/[role].md and change model: field. Distributable defaults stay as inherit in library/."
}
```

### Available model IDs (as of 2026-06-13)

Per Cursor SDK skill (`@cursor/sdk`): `composer-2.5` is the current default for most integrations. `auto` lets the server pick. `Cursor.models.list()` returns valid IDs per account.

**Do not hardcode frontier model IDs** (e.g., `gpt-5.5`, `claude-4.6-sonnet`) in the library defaults — these change, require specific plans, and may trigger the admin-restriction silent fallback.

---

## Role × Tier Matrix

### Tier definitions

| Tier | Characteristics | When to use | Example models |
|---|---|---|---|
| **fast** | Small, low latency, low cost. Good for structured output and simple instruction-following. | Simple tasks with clear scope, no architectural reasoning required. | `composer-2.5` in fast mode |
| **balanced** | Mid-tier quality and cost. Good code generation + instruction following. | Default for most harness phases. | `composer-2.5` |
| **reasoning** | Frontier model with extended thinking. Highest cost, best adversarial resistance and complex decomposition. | Adversarial evaluation, architectural planning. | `auto` (server-resolved frontier) |
| **user_controlled** | The user's IDE session model. Not configurable via frontmatter. | Builder (main agent — not a subagent). | Varies |

Tier labels are stable; specific model IDs evolve. The `model_routing_matrix.json` machine-readable artifact uses tier labels, not model IDs, to avoid hardcoding volatile names.

### Matrix

| Role | Recommended tier | Fallback tier | Primary failure mode | Routing signal | Frontmatter-settable? |
|---|---|---|---|---|---|
| **Planner** | `balanced` | `fast` | Scope creep into implementation details; duplicate task proposals | Task complexity (simple → fast, architectural → reasoning) | Yes — `.cursor/agents/planner.md` |
| **Builder** | `user_controlled` | `balanced` | Protocol skip under tool pressure (no contract, self-grading, missing breadcrumbs) | User's IDE session model | No — builder is the main agent |
| **Evaluator** | `reasoning` | `balanced` | Sycophancy, partial credit, deferring failures | Always adversarial — no signal-based routing needed | Yes — `.cursor/agents/evaluator.md` |

### Per-role reasoning

**Planner — balanced default, routing on complexity**

The planner's job is decomposition, not code generation. A `balanced` model handles the primary output (state.json as structured JSON) well. The failure modes (scope creep, boundary under-specification, duplicate tasks) correlate with instruction-following quality more than raw reasoning. For simple tasks (harness-gate.sh bypass path), a `fast` model is adequate. For architectural/vague prompts (3+ files, cross-system impact), the reasoning model's superior decomposition quality is worth the cost.

The routing signal already exists: harness-gate.sh uses word count + pattern matching as a complexity proxy. If this were wired to model selection, it would be: short simple prompts → `fast`; long complex prompts → `reasoning`. For now, `balanced` as a static default is a reasonable middle ground.

**Builder — user_controlled, not harness-routable (yet)**

The builder is the main agent, not a subagent. Its model is the user's IDE session choice. Harness compliance scores from the eval suite show the primary failure modes are protocol-related (skipping contract gate, self-grading, missing breadcrumbs). These failure modes are not strongly model-gated — a `fast` model that is well-prompted follows protocol better than a `reasoning` model given ambiguous instructions.

This is the one role where model routing via frontmatter does not apply. Programmatic routing (feat-13b, SDK-based orchestration) is the only path to builder model control. Not in scope for `feat-role-model-config`.

**Evaluator — reasoning, always adversarial**

The evaluator's failure mode is sycophancy — approving work it should reject. The anti-sycophancy rules in `evaluator.md` are explicit, but their effectiveness depends on the model's tendency toward approval bias. Stronger reasoning models are empirically less sycophantic: they are more willing to produce FAIL with specific evidence rather than "mostly works."

Unlike the planner, there is no signal-based routing for the evaluator — it is always in adversarial mode. The recommendation is a static `reasoning` tier override, not a conditional signal. Cost justification: the evaluator runs once per build task (not per turn), so the per-session cost delta is bounded.

---

## Subagent vs Skill

The question applies primarily to the **planner** — Phase 5 §5.4 (S4 counter-evidence) explicitly challenges the planner as a separate subagent and validates only the evaluator unconditionally.

### S4's argument against the planner as subagent

S4 ("Fewer agents with more skills wins"): a `decompose-task` skill could produce the same `state.json` artifact without the overhead of a separate subagent invocation. Skills don't require a clean context window, don't have startup overhead, and don't consume separate tokens for context-gathering. S4 names the evaluator as the exception (structural conflict-of-interest justifies a separate agent) but challenges the planner.

### The counterargument: context hygiene

The planner's value as a subagent is not capability — it is **context hygiene**. When a user invokes `/planner` mid-session (after failed implementation attempts, partial code, a confusing conversation), the planner starts from a clean context. It reads `state.json` and the user's prompt without being contaminated by the builder's prior reasoning, failed approaches, and half-formed decisions.

If the planner were a skill, it would execute in the same conversation context as the builder session — contaminated by everything that came before. The decomposition output would be anchored to the builder's failed approaches rather than starting from first principles.

This is a real benefit when `/planner` is invoked to restart a session that went wrong. It is not a real benefit when invoked at cold start (no contamination to avoid).

### Verdict: keep as subagent, conditional on use case

| Invocation context | Subagent justified? | Reason |
|---|---|---|
| Cold start, simple task (harness-gate bypass) | No | No contamination to avoid; skill overhead is lower |
| Cold start, complex architectural task | Yes | Clean context + reasoning model benefit for decomposition |
| Mid-session restart (failed implementation) | **Yes — primary use case** | Context hygiene is the primary value; a skill cannot provide this |
| Session recovery (reading state.json after long gap) | Marginal | state.json already encodes scope; clean context adds little |

**Recommendation:** Keep planner as subagent. The mid-session restart case is the most common explicit trigger for `/planner` — that's when context hygiene matters. For cold-start simple tasks, harness-gate.sh already provides a bypass. S4's argument applies to the bypass case (already handled), not the mid-session restart case.

**What would falsify this:** eval data showing no harness compliance difference between planner-as-subagent and planner-as-skill across session recovery scenarios. That data doesn't exist — it's a gap for `feat-eval-role-model-matrix`.

### Evaluator: subagent — unconditional

Phase 5 §5.3 (S3 counter-evidence): the evaluator's justification is structural conflict-of-interest, not model capability. A model that proposes acceptance criteria AND judges whether they are met cannot be objective regardless of capability tier. This argument is independent of model selection and does not change with stronger models.

**Recommendation:** Keep evaluator as subagent. No signal-based condition applies.

---

## Workflow Integration

The harness workflow is **unchanged** by model routing. What changes is which model executes at each role invocation.

### Current flow (with model tier annotations)

```
vague prompt
  → harness-gate.sh advisory (simple bypass path)
  → /planner  ← [model: balanced — or reasoning for complex architectural tasks]
  → state.json confirmed by user
  → builder proposes contract.json  ← [model: user_controlled]
  → /evaluator negotiates (max 3 rounds)  ← [model: reasoning]
  → builder implements  ← [model: user_controlled]
  → /evaluator tests against contract  ← [model: reasoning, same as negotiation]
  → PASS → commit → next task
```

### Model routing is a one-time configuration, not a per-session action

1. On first setup (`make sync-local`), `.cursor/agents/planner.md` and `evaluator.md` are created with `model: inherit`.
2. Practitioner optionally overrides `model:` in `.cursor/agents/` (see IDE Configuration below).
3. Every subsequent `/planner` and `/evaluator` invocation silently uses the configured tier — zero per-session friction.

### What does NOT change

- The `/planner` and `/evaluator` invocation syntax
- Contract negotiation flow and breadcrumb lifecycle
- evaluator-guard.sh write restriction
- Eval scenario suite (scenarios test harness compliance, not model identity)

### What improves with recommended tier assignment

| Phase | Current risk (inherit on weak model) | With recommended tier |
|---|---|---|
| Planning — complex architectural tasks | Scope creep to implementation details | `reasoning` tier produces clean task boundaries with explicit scope |
| Evaluation — adversarial testing | Sycophancy on weak evidence | `reasoning` tier resists approval bias, requires specific command output as evidence |
| Building | Protocol skip under tool pressure | No change — builder model is user-controlled |

### sync-local overwrite risk

`make sync-local` copies `library/cursor/agents/` → `.cursor/agents/` and **overwrites** customized files. This is the one friction point. Mitigations documented in IDE Configuration §Step 5.

---

## IDE Configuration

### Step-by-step: setting per-role models

**Prerequisites:** Cursor IDE, harness installed, `make sync-local` run at least once.

**Step 1 — Verify agent files exist**

```bash
ls .cursor/agents/
# Expected: planner.md  evaluator.md
# If missing: run make sync-local
```

**Step 2 — Edit the evaluator's model (highest-value change)**

Open `.cursor/agents/evaluator.md` and change the `model:` field:

```yaml
# Before (distributable default):
---
name: evaluator
description: Adversarial QA critic...
model: inherit
---

# After (reasoning tier — recommended for adversarial evaluation):
---
name: evaluator
description: Adversarial QA critic...
model: auto
---
```

`auto` lets Cursor resolve the best available frontier model for your plan. Avoids hardcoding a volatile model ID.

**Step 3 — Edit the planner's model (optional)**

For architectural decomposition work, override to a reasoning model:

```yaml
---
name: planner
description: Turns vague prompts into high-level specs...
model: auto
---
```

For a dedicated fast model on simple tasks, leave as `inherit` — the harness-gate.sh bypass path handles simple tasks without the planner.

**Step 4 — Protect against sync overwrite**

`make sync-local` will overwrite `.cursor/agents/` on next run. Three options:

| Option | When to use |
|---|---|
| **Edit `library/cursor/agents/` directly** | Team default — everyone who syncs gets the routing. Best for team deployments. |
| **Accept overwrite, re-apply after sync** | Personal preference only — you remember to re-apply. Simplest. |
| **Skip syncing agent files** | Advanced — modify `make sync-local` to exclude agent files with non-inherit model values. Not yet implemented. |

**Recommended for this repo:** edit `library/cursor/agents/evaluator.md` model field once the team agrees on a default. Personal routing preferences that differ from the team default use the accept-overwrite pattern.

**Step 5 — Verify in Cursor**

After saving, open a new Cursor chat. Type `/evaluator`. The model the subagent uses will be the one in its frontmatter. To confirm empirically, ask the evaluator at the start of a session: `What model are you running on?` — most frontier models report this.

### Reference: `harness-model-routing.json`

Machine-readable routing config, to be created by `feat-role-model-config` at `library/cursor/harness-model-routing.json`. The eval-facing companion created by this spike is `tests/eval/fixtures/model_routing_matrix.json`.

---

## Open Questions (after both spikes)

1. **Does the Cursor IDE surface which model a subagent ran on?** SDK does not expose this in the run transcript. Manual verification via IDE session history UI. An empirical test session is needed to confirm the frontmatter change takes effect.

2. **sync-local overwrite protection** — how to preserve local `model:` overrides across `make sync-local` runs without coupling the sync script to file content. Unresolved.

3. **Parametric eval sweep** — `feat-eval-role-model-matrix` needs a way to vary subagent model without manually editing frontmatter per run. A `--model-role-override` flag for `session_runner.py` would enable this. Deferred to that task.

4. **Empirical validation gap** — tier recommendations are based on failure mode analysis and platform docs, not measured A/B data. The recommendations are informed hypotheses. `feat-eval-role-model-matrix` closes this gap.

