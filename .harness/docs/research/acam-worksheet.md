# ACAM Worksheet — Agent Configuration Assessment Model

Score a repo by answering the observable questions per cell. A "yes" at level N with no "yes" at N+1 = that level.

## Scoring Instructions

For each dimension, start at Basic. Move to Intermediate only if ALL Basic questions answer yes. Move to Advanced only if ALL Intermediate questions answer yes. A gap at any level caps the score at the level below.

---

## Configuration

**Basic** — Does the repo have any AI configuration file? (`.cursorrules`, `CLAUDE.md`, `.windsurfrules`, or any `.mdc` rule file)

**Intermediate** — Are there multiple rules with distinct scopes (alwaysApply vs. file-pattern vs. agent-requested)? Is there a documented rationale for WHEN each rule fires?

**Advanced** — Is there per-rule effectiveness data (ablation or eval score per rule)? Is cross-tool portability documented (AGENTS.md or equivalent format)?

---

## Workflows

**Basic** — Does the repo have any structured task lifecycle? (issue template, PR checklist, or equivalent)

**Intermediate** — Is there a hook or structural gate that blocks implementation writes until a contract or spec exists? Is there an append-only audit log (breadcrumbs or equivalent)?

**Advanced** — Does acceptance-criteria-gated implementation exist — machine-readable criteria negotiated before any write? Is there an automated eval regression suite (not manual runs)?

---

## Multi-agent

**Basic** — Is there more than one named agent or persona in use? (any two of: planner, coder, reviewer, tester)

**Intermediate** — Are agent roles defined with separate system prompts encoding distinct role identity and output format? Is there any mechanism limiting what each agent can modify?

**Advanced** — Is there trust boundary enforcement — the evaluating/reviewing agent is structurally blocked (deny hook or equivalent) from modifying source files? Is orchestration programmatic (not manual invocation)? Are context packages (structured state bundles) passed between agents rather than full history inheritance?

---

## Interaction

**Basic** — Is there any user-facing guidance on how to prompt the AI? (README section, comment, example prompts)

**Intermediate** — Is there a prompt coaching rule or skill that detects underspecified inputs? Is there any mechanism that loads current task context before the first agent turn?

**Advanced** — Is structured context delivery implemented — a sessionStart hook or equivalent that injects current task, open contracts, and recent trace into the agent's context window before the first turn? Are interaction patterns measured across sessions (prompt clarity, turns to completion)? Is there prompt versioning with a changelog and per-change hypothesis?

---

## Population Reference (Phase 2 empirical model, n≈3,200 public repos)

| Tier | ACAM profile | Estimated % |
|---|---|---|
| Tier 0 | Basic on all 4 dimensions | ~80% |
| Tier 1 | Intermediate on ≥1 dimension | ~18% |
| Tier 2 | Intermediate on ≥2 dimensions; some workflow or multi-agent structure | ~1.5% |
| Tier 3 | Intermediate on all 4 dimensions | ~0.5% |
