# Phase 1 — Methodology, ACAM Framework & Repo Inventory

**Spike:** spike-research-agents
**Date:** 2026-06-11
**Status:** Complete

## 1. Research Question

> What do average users ("normies") do vs. what advanced practitioners do across AI agent configuration — and where does rules-skills honestly sit on that spectrum?

## 2. Scope & Target

**Output format:** Practitioner reference guide — suitable for a conference talk or multi-part blog series. NOT academic (no IRB, no controlled experiment, no peer review).

**Audience:** Teams adopting AI coding assistants (Cursor, Claude Code, Aider, Copilot) who want to know what "good" looks like beyond default settings.

**What this is NOT:** A benchmarking study, a product comparison, or a sales pitch for the rules-skills repo.

## 3. Terminology

### 3.1. "Normie" vs "Advanced" — Operational Definitions

We avoid stereotypes. Every level is defined by **observable artifacts and behaviors**, not by self-identification.

| Term | Observable signals |
|------|-------------------|
| **Normie** | Uses IDE defaults. Zero or one config file. No custom rules. Copy-pasted `.cursorrules` from a template. Single-shot prompts. Agent self-grades completion. No verification loop. |
| **Practitioner** | Multiple rule files with globs/scoping. Defined workflows (skills or saved prompts). Some verification (tests, lints). Thread hygiene awareness. |
| **Advanced** | Versioned config library. Structural enforcement (hooks deny bad actions). Multi-agent separation (planner/evaluator). Eval regression suite. Data-driven iteration on rules. Measured effectiveness. |

### 3.2. Dimensions of Analysis

We consolidated 6 original dimensions into **4** to eliminate overlap:

| Dimension | Covers | Consolidation rationale |
|-----------|--------|------------------------|
| **Configuration** | Rules, system prompts, `.cursorrules`, `.mdc`, `CLAUDE.md`, `.claude/rules/`, `CONVENTIONS.md`, platform config layers, token budgets | Rules ARE user-level system prompts. Platform vs user config is a sub-layer, not a separate dimension. |
| **Workflows** | Skills, agentic loops, lifecycle enforcement, hooks, contract-first dev, verification loops | Skills define workflows within the agent loop. Separating them creates an artificial boundary. |
| **Multi-agent** | Subagents, orchestration, context isolation, role separation, handoffs | Natural grouping — how agents collaborate on complex tasks. |
| **Interaction** | User prompts, meta-prompts, prompt coaching, context engineering, structured input | How humans communicate intent to agents. Context engineering subsumes prompt engineering (Karpathy, 2025; arxiv 2603.09619). |

### 3.3. Four-Layer Maturity Pyramid (from literature)

The field has converged on a cumulative hierarchy (arxiv 2603.09619, Chandrayan 2026):

1. **Prompt Engineering** — Crafting individual queries for single-turn outcomes
2. **Context Engineering** — Managing the information supply chain (RAG, memory, tool schemas, rules, cache states) across multi-step tasks
3. **Intent Engineering** — Encoding organizational goals, values, and trade-offs into agent infrastructure
4. **Specification Engineering** — Formalizing machine-readable policies (AGENTS.md, contract.json) for autonomous multi-agent execution

This pyramid informs our ACAM levels but is not identical to them — ACAM measures *what a practitioner has built*, not theoretical capability.

## 4. ACAM — Agent Configuration Assessment Model

### 4.1. Design Principles

- **3 levels, not 5.** CMMI-style 5-level models invite hair-splitting. 3 levels with clear behavioral markers are more practical and adoptable.
- **Observable artifacts only.** Each cell in the matrix describes something you can find in a repo or observe in a session — not subjective quality judgments.
- **Cumulative.** Advanced includes everything in Intermediate. Intermediate includes everything in Basic.
- **Dimension-independent.** A project can be Advanced on Configuration but Basic on Multi-agent. The overall score is the profile, not an average.

### 4.2. ACAM Matrix (skeleton — filled in Phase 7)

| Dimension | Basic | Intermediate | Advanced |
|-----------|-------|--------------|----------|
| **Configuration** | Zero config or single monolithic file. Copy-pasted templates. No scoping. | Multiple scoped files (.mdc with globs, CLAUDE.md + rules/). Sizing standards. Separate concerns. Versioned. | Config library distributed across projects. Token budget management. Ablation testing. Measured effectiveness (eval data). Structural loading strategies. |
| **Workflows** | Single-shot prompts. No verification. Agent self-grades. No lifecycle. | Defined skills/workflows. Some verification loop (tests after edits). Manual checkpoints. Saved reusable prompts. | Structural enforcement (hooks deny bad actions). Contract-first development. Eval regression suite. Measured skill effectiveness. Lifecycle statuses enforced. |
| **Multi-agent** | Single agent. Builder self-reviews. No role separation. | Role separation (planner/reviewer). Manual handoffs. Separate context per role. | Programmatic orchestration. Adversarial QA (evaluator challenges builder). Parallel evaluation. Auto-routing. Context isolation enforced. |
| **Interaction** | Vague one-liners. No structure. No context management. | Structured prompts (context/constraints/verification). Thread hygiene. Prompt templates. | Meta-prompts in subagent definitions. Context engineering (compaction, isolation, tool schemas). Prompt coaching rules. Measured interaction patterns. |

### 4.3. Scoring Rules

1. Every dimension score **MUST** cite ≥2 repo artifacts (file paths) as evidence
2. Every gap **MUST** reference a pending task, eval score, or explicit absence
3. **Advanced requires quantitative evidence** — aspirational Advanced without data scores Intermediate max
4. Baselines defined from Phase 2 data (GitHub scraping, community analysis), not stereotypes
5. Frontier cites external exemplars (named projects, papers, vendor guides)
6. **Red-team pass:** list 3 ways the repo is NOT advanced despite appearing sophisticated
7. One-paragraph honest positioning summary per dimension

## 5. Data Collection Plan (Phase 2)

### 5.1. GitHub Analysis

| Target | Method | Expected output |
|--------|--------|-----------------|
| `.cursorrules` prevalence | GitHub code search: `filename:.cursorrules` | Count, avg file size, common patterns |
| `.cursor/rules/` adoption | GitHub code search: `path:.cursor/rules/ extension:mdc` | Adoption of new format vs legacy |
| `CLAUDE.md` patterns | GitHub code search: `filename:CLAUDE.md` | Structure patterns, avg size, common sections |
| `CONVENTIONS.md` (Aider) | GitHub code search: `filename:CONVENTIONS.md` | Aider ecosystem size |
| `.cursor/hooks.json` | GitHub code search: `filename:hooks.json path:.cursor` | Hook adoption rate (expected: very low) |
| `.cursor/skills/` | GitHub code search: `path:.cursor/skills SKILL.md` | Skill adoption rate (expected: very low) |

### 5.2. Comparable Setups (deep-dive)

| Setup | What to analyze | Why |
|-------|----------------|-----|
| **Aider** (aider-ai/aider + aider-ai/conventions) | CONVENTIONS.md format, .aider.conf.yml, architect mode, repo map | Most mature open-source AI coding tool config. 2-layer model (runtime + coding guidelines). |
| **SWE-agent** (princeton-nlp/SWE-agent) | Agent-Computer Interface (ACI), scaffold design, tool definitions | Academic standard for coding agents. 2-agent model (localization + resolution). |
| **Claude Code** (code.claude.com) | CLAUDE.md, .claude/rules/, memory hierarchy, slash commands | Direct competitor to Cursor. 3-tier config (global/project/subdirectory). |
| **Cursor community** (PatrickJS/awesome-cursorrules, 39.8k stars) | Rule corpus, adoption patterns, common anti-patterns | Largest community dataset for Configuration dimension baseline. |
| **cursor-handbook** (girijashankarj/cursor-handbook) | 208 components, rule categorization, distribution model | Most ambitious comparable open-source rules library. |

### 5.3. Community Signal Mining

| Source | What to extract |
|--------|----------------|
| Reddit r/cursor | User pain points, common questions, rule-sharing behavior |
| Cursor forum / Discord | Advanced user patterns, hook adoption reports |
| blog posts (dev.to, thepromptshelf, openbooklet) | Best practice crystallization, anti-pattern catalogs |

## 6. Repo Inventory (§0 Baseline)

### 6.1. Configuration Layer

| Artifact | Count | Location | Notes |
|----------|-------|----------|-------|
| Rules (.mdc) | **16** | `library/cursor/rules/` | 796 total lines. 8 alwaysApply, 4 glob-scoped, 4 agent-requested |
| Rules standard | 1 | `docs/RULES_STANDARD.md` | Max ~200 lines/rule, ~2000 token budget for always-on |
| Claude rules (.md) | **23** | `library/claude/rules/` | Parallel port, more files (split differently) |
| References | **18 files** | `library/cursor/references/` | 6 architecture patterns, 4 design refs, 7 rubrics, 1 security |
| Sync system | 1 script | `sync-cursor.sh` (~500 lines) | Distributes library/ to all ~/redhat projects |

### 6.2. Workflows Layer

| Artifact | Count | Location | Notes |
|----------|-------|----------|-------|
| Skills (SKILL.md) | **14** | `library/cursor/skills/` | Adversarial-harness, 4 audits, code-review, commit, data-science, experiment, iac, info-arch, llm-skeptic, project-scaffolding, tech-writing |
| Skills standard | 1 | `docs/SKILLS_STANDARD.md` | Required sections: Proactive Triggers, Stop Conditions, Output Artifacts |
| Claude skills | **9** | `library/claude/skills/` | Subset (no audit skills, no llm-skeptic) |
| Hook scripts | **12** | `library/cursor/hooks/` | 1956 total lines. Includes hooks-lib.sh (shared utils) + validate-hooks.sh |
| Hook profiles | 2 | `library/cursor/hooks.{lean,full}.json` | Lean: 5 hooks (default), Full: 6 hooks (dogfooding) |
| Harness lifecycle | 5 statuses | `.harness/state.json` | pending → building → evaluating → verified → committed |
| Contract format | 1 | `.harness/contract.json` | Binary acceptance criteria, negotiation rounds, rubric refs |
| Eval scenarios | **27** standard + 1 long | `tests/eval/scenarios/` | Protocol, routing, contract, behavioral, adversarial categories |
| Eval pipeline | 6 Python files | `tests/eval/` | session_runner, session_judge (multi-tier), session_report, trajectory_checks, sandbox, capture_behavioral_baseline |

### 6.3. Multi-agent Layer

| Artifact | Count | Location | Notes |
|----------|-------|----------|-------|
| Subagent definitions | **2** | `library/cursor/agents/` | planner.md, evaluator.md |
| Roles | 3 | Defined in adversarial-harness SKILL.md | Planner (no code), Builder (main agent), Evaluator (adversarial QA) |
| Context isolation hooks | 2 | evaluator-guard.sh, chain-evaluator.sh | Evaluator can only write to .harness/; chain-evaluator routes by phase |
| Orchestration | **Manual** | `/planner` and `/evaluator` invocations | feat-13 (auto-orchestration) was cancelled — manual launch works |

### 6.4. Interaction Layer

| Artifact | Count | Location | Notes |
|----------|-------|----------|-------|
| Prompt coaching rule | 1 | `library/cursor/rules/prompt_coaching.mdc` | Agent-requested, coaches vague prompts |
| Critical thinking rule | 1 | `library/cursor/rules/critical_thinking.mdc` | Always-on, challenges user assumptions |
| Planning discipline rule | 1 | `library/cursor/rules/planning_discipline.mdc` | Always-on, structured tracking + thread hygiene |
| Agent behavior rule | 1 | `library/cursor/rules/agent_behavior.mdc` | Always-on, communication style + harness-aware opener |
| Session context hook | 1 | harness-context.sh | Injects harness state at session start |
| Breadcrumbs (audit trail) | 113 entries | `.harness/breadcrumbs.jsonl` | Append-only trace across sessions |

### 6.5. Verification & Measurement

| Artifact | Count | Notes |
|----------|-------|-------|
| Verified tasks | **47+** | Archived to archive.jsonl |
| Pending tasks | **7** | gap-14, gap-18, feat-14a, feat-16, chore-skill-scenarios, chore-archive-review, spike-research-agents |
| Hook tests | **52** | validate-hooks.sh |
| Behavioral judge tests | **44** | test_session_judge_behavioral.py |
| Trajectory tests | **33** | test_session_judge_trajectory.py |
| Validation checks | Multiple | tests/validate.py (rules/skills authoring) |

## 7. Preliminary Self-Assessment (honest, to be refined in Phase 7)

| Dimension | Likely level | Key evidence | Key gaps |
|-----------|-------------|--------------|----------|
| **Configuration** | Intermediate | 16 scoped rules, RULES_STANDARD, sync system, token budget awareness | No ablation testing (feat-16 pending), no measured effectiveness data, some rule overlap (progress_tracking + planning_discipline) |
| **Workflows** | Intermediate | 14 skills, contract-first lifecycle, structural hooks (contract-gate denies Write), 28 eval scenarios, 129 tests | Zero skill_activation eval coverage (chore-skill-scenarios pending), verify-harness trusts contract.verified without evaluator proof, session boundary 33% (gap-14). No quantitative skill/workflow effectiveness data — eval suite exists but hasn't produced published ablation results. |
| **Multi-agent** | Intermediate | 3-role model, context isolation hooks, evaluator-guard | Manual /planner /evaluator launches only, feat-13 cancelled, no parallel evaluation, no auto-routing |
| **Interaction** | Intermediate | Prompt coaching rule, critical thinking rule, breadcrumbs as session context, harness-context hook | No prompt versioning, no prompt A/B testing, no user interaction analytics |

**Preliminary one-liner:** rules-skills is Intermediate across all four dimensions. No dimension has quantitative evidence of effectiveness. Subject to revision after Phase 2 establishes empirical baselines — if the median GitHub user already uses scoped .mdc rules, our "Intermediate" may be the new normal (see §9.5).

## 8. Phase Dependencies

```
Phase 1 (this) ──→ Phase 2 (data collection)
                ──→ Phases 3-6 (dimension analyses, can reference §0 inventory)
All phases ──────→ Phase 7 (synthesis, fills ACAM matrix, scores scorecard)
```

## 9. Known Biases (self-audit, 2026-06-11)

This section documents biases identified via adversarial self-review BEFORE dimension analysis begins. Corrections are mandatory for Phases 2-7.

### 9.1. Confirmation bias — ~60% of Phase 1 repackages existing docs

The repo inventory, gap list, and honest assessment were already documented in `state.json`, `spike-eval-research.md`, and `HARNESS_ESSENCE.md`. Phase 1 mostly reformatted existing self-knowledge. Genuinely new contributions (~40%): ACAM framework, four-layer pyramid from literature, data collection plan, bibliography expansion beyond eval tooling.

**Correction:** Phases 3-6 must produce NEW analysis per dimension, not restate what `state.json` already says. Each phase must cite ≥3 external sources not referenced in any prior repo doc.

### 9.2. ACAM designed around what we already have

The "Advanced" criteria in Workflows ("structural enforcement, contract-first, eval regression suite") literally describe our harness. If we define the criteria AND evaluate against them, the framework is rigged.

**Correction:** Phase 7 must validate ACAM criteria against external vocabulary (Anthropic, OpenAI, SWE-bench papers) before scoring. If external sources don't independently arrive at the same criteria, the criteria must be revised.

### 9.3. Bibliography selection bias — missing challenging sources

Phase 1 bibliography is heavy on sources that validate structural enforcement. Missing: simplicity-first evidence, over-engineering warnings, evidence that simple setups produce equivalent outcomes, negative evidence on multi-agent approaches.

Specific gap: OpenAI GPT-5.5 guide [V3] says "Avoid ALWAYS, NEVER, must" — a direct challenge to our rule style — noted but not analyzed. Paper [A6] says "some top performers are single-agent with good scaffolding" — understated.

**Correction:** Phase 2 bibliography must include ≥2 sources arguing AGAINST complex agent configuration. Phase 3-6 must engage with counter-evidence, not just confirming sources.

### 9.4. Comparable setups favor us

Aider (simpler), awesome-cursorrules (Basic), Claude Code (no hooks) — all make rules-skills look more sophisticated by comparison. Missing: Devin (potentially more advanced), enterprise internal setups, GitHub Copilot Workspace, Windsurf Cascade.

**Correction:** Phase 2 must add Devin and ≥1 setup that may be MORE advanced than rules-skills. The comparable set must include at least one setup where rules-skills looks WORSE by comparison.

### 9.5. "Normie" baseline set too low

"Zero rules, copy-pasted .cursorrules" is the floor. A realistic 2026 normie: uses framework-specific .cursorrules from awesome-cursorrules (39.8k stars!), occasionally uses slash commands, runs tests manually. This normie is already near our "Intermediate" threshold — the gap between average and us is smaller than Phase 1 implies.

**Correction:** Phase 2 GitHub data must establish an empirical normie baseline. If the median GitHub user already has scoped .mdc files, "Intermediate" is the new normal, not an achievement.

### 9.6. Self-assessment hedging

"Intermediate" but "infrastructure for Advanced exists" is having it both ways.

**Correction:** Final self-assessment (Phase 7) must be Intermediate WITHOUT asterisks. Claiming credit for unused infrastructure is not allowed. "Built it" ≠ "proved it works."

## 10. Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Navel-gazing (scoring our own framework) | Phase 2 provides external baselines. Phase 7 red-team pass is mandatory. §9 bias corrections are binding. |
| GitHub scraping infeasible | Fallback: curated community repos (awesome-cursorrules, aider-ai/conventions) + blog/article data points |
| Over-engineering ACAM | 3 levels keeps it simple. If a cell has no observable artifact, it stays empty. |
| Research delays eval tooling | Research track is parallel; doesn't block feat-14a/feat-16. Phases are independent sessions. |
| Confirmation bias (§9.1-9.6) | Bias corrections are documented in methodology BEFORE analysis. Each phase must reference §9 and demonstrate compliance. |
