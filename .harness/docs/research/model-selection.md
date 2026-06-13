# model-selection.md — Role-Based Model Routing Research

**Spike:** spike-subagent-model-mechanics + spike-model-selection
**Date started:** 2026-06-13
**Status:** Platform Mechanics complete (spike-subagent-model-mechanics). Role routing matrix pending (spike-model-selection).

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

## Open Questions (unresolved after this spike)

1. **Does the Cursor IDE surface which model a subagent actually ran on?** The SDK does not expose this in `run.conversation()` or the agent transcript. Manual verification requires checking the Cursor UI session history during an IDE session. This requires an empirical IDE test session to confirm.

2. **Does changing `evaluator.md` frontmatter affect evaluator sessions launched via `/evaluator` in the IDE?** The platform docs describe `.cursor/agents/` (project-local) as the lookup path — `library/cursor/agents/` is the distributable source; `make sync-local` copies to `.cursor/agents/`. This means the frontmatter change must be in `.cursor/agents/evaluator.md` (after sync) to take effect. The sync step is documented but easy to miss.

3. **Can eval scenarios parametrically vary subagent model?** Current answer: only indirectly (change frontmatter, re-run). A `--model-role-override evaluator=gpt-5.5` flag would require `session_runner.py` to patch the agent file before launch — possible but not in scope for this spike.

---

*Next: spike-model-selection extends this doc with a role×tier matrix and cost/quality trade-off analysis. feat-role-model-config uses §Recommendations above as its implementation spec.*
