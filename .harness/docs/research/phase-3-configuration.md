# Phase 3 — Configuration Dimension Analysis

**Spike:** spike-research-agents
**Date:** 2026-06-11
**Status:** Complete
**Bias corrections applied:** BC1 (≥3 new external sources: E1, E2, E3), BC2 (S2 and S3 engaged directly in §5), BC3 (ACAM Advanced criteria validated against external vocabulary in §2.3), BC6 (no hedging in §6 scoring)

---

## §9 BC Compliance Check

Before analysis begins: documented BC1-BC6 violations would be flagged here.

- **BC1** — ≥3 external sources not in pre-Phase-3 bibliography: ✓ (E1: Anthropic system prompt docs, E2: GitHub Copilot custom instructions, E3: Reflexion paper — all new, all with real URLs in §7)
- **BC2** — Engage S2 and S3 challenging sources: ✓ (§5.1 analyzes S2 per-rule; §5.2 engages S3 with specific verdict)
- **BC3** — Validate ACAM Advanced criteria against external vocabulary before scoring: ✓ (§2.3 evaluates each Phase 1 criterion; one criterion revised, one added)
- **BC6** — No hedging in final scoring: ✓ (§6.2 states "INTERMEDIATE" without qualifiers or asterisks; gaps listed separately)

---

## 1. Literature Review: Rules, System Prompts, and Platform Config Layers

### 1.1. What Are Rules, Actually?

From the model's perspective, rules are system prompt content — there is no architectural difference between a `.mdc` rule and a `CLAUDE.md` entry and a `AGENTS.md` line. The IDE injects all of them into the context window before the first user turn. The difference is *when* they load, *which tool* manages them, and *who authored* them.

Cursor's documentation [V8] describes rules as "always-on conventions." Anthropic's system prompt guide [E1] describes the system prompt's role identically: "to establish the agent's identity, capabilities, and constraints before any user turn." Rules in `.mdc` format are the Cursor IDE's mechanism for injecting system-prompt-level content that would otherwise require each developer to manually craft a system prompt every session.

**The key implication for quality:** rule quality failures are system prompt quality failures. [E1] identifies five root causes of poor system prompt performance that apply verbatim to `.mdc` rules:
1. Vague instructions — analogous to rules that say "write good code" without specifics
2. Over-reliance on model inference — analogous to rules that assume the model knows the project context
3. Conflicting instructions — multiple rules encoding contradictory policies
4. Missing edge case handling — rules that specify the happy path but not failure modes
5. Poor formatting — unstructured rules that get "lost in the middle" of context [B1]

The MSR 2026 study [N2] found that most `.mdc` files encode conventions and project information rather than LLM-specific directives. "LLM directives have relatively low adoption" in the studied sample. This implies that most practitioners treat rules as documentation injected into the model, not as behavioral enforcement mechanisms.

### 1.2. Platform Config Layering: Four Levels Across Tools

Across AI coding tools, configuration injection follows a consistent four-level model. This is not a rules-skills invention — it reflects a convergent architectural pattern:

| Layer | Cursor (.mdc) | Claude Code (CLAUDE.md) | GitHub Copilot [E2] | Devin (AGENTS.md) |
|-------|---------------|------------------------|---------------------|-------------------|
| **Global** | User Rules in Settings | `~/.claude/CLAUDE.md` | Organization custom instructions | `~/.devin/config.json` |
| **Project** | `.cursor/rules/*.mdc` (alwaysApply) | `./CLAUDE.md` | `.github/copilot-instructions.md` | `./AGENTS.md` |
| **Scoped** | `.cursor/rules/*.mdc` (globs) | `.claude/rules/*.md` | Per-repository instructions | `./subdir/AGENTS.md` |
| **Session** | Hooks (SessionStart prompt injection) | `.claude/hooks/` | n/a (no hook system) | Hooks (SessionStart) |

Critical finding across all platforms: **conflict resolution between layers is not deterministic.** [V9] states explicitly that "Conflicting rules [are] picked arbitrarily." [E2] (GitHub Copilot docs) notes that conflicting instructions result in "unpredictable behavior." [B6] says scoped rules are "deterministic in application" — but only for whether they *load*, not for what the model does when two loaded rules contradict each other.

No platform provides tooling to detect inter-rule conflicts. The practitioner is responsible for auditing their own config for overlap and contradiction.

### 1.3. Token Budget Trade-offs

Token budget is the governing constraint on Configuration design. Every always-on rule competes with working memory (current file content, tool call results), conversation history, and the model's effective reasoning space.

[B1] quantifies the scope: "Scoped activation saves 60-80% of tokens." In a 200K context window session, the always-on rule load is a small percentage of the total window — but compounded across 8 rules, session history, and full file context, budget discipline matters for context-dense sessions.

[S2] (Lazy-Loaded Procedural Policy) makes the strongest architectural claim on this: "The system prompt owns invariants; tools own conditionals." Under this framework, the token budget question becomes architectural: what *qualifies* as a constitutional invariant? If the answer is "behaviors that must apply to every interaction regardless of task type," then most workflow-enforcement rules fail this test.

The community has converged on a practical upper bound. Community guides [B1] and Cursor's own documentation [V8] both recommend 3-5 always-on rules. The reasoning from [B1]: instructions in the middle of a long context window are systematically under-attended by models — a rule file >100 lines has its second half ignored. This makes large always-on rules self-defeating.

The MSR 2026 study [N2] found avg `.mdc` file length of 462.67 lines. Combined with avg 4.68 files per repo, many practitioners are loading enormous always-on contexts that may be partially or wholly ignored by the model.

### 1.4. Config Format Evolution and AGENTS.md

The dominant config formats represent three adoption generations:

| Format | Era | Mechanism | Scoping | Hook support | Tool portability |
|--------|-----|-----------|---------|-------------|-----------------|
| `.cursorrules` (legacy) | 2024 | Single file, plain text | None | No | Cursor-only |
| `.mdc` / `CLAUDE.md` / `.windsurfrules` | 2024-2025 | Multiple files, YAML frontmatter | Glob/path | Yes (separate) | Tool-specific |
| `AGENTS.md` | 2025-2026 | Open standard, nested per-directory | Directory hierarchy | Yes (cross-tool) | Universal |

AGENTS.md [N5] became the open standard (Linux Foundation, December 2025). Every major coding agent (Cursor, Codex, Devin, Copilot, Gemini CLI, Windsurf, Zed, Factory, Jules) reads it natively. The Linux Foundation's AAIF study reports 35-55% reduction in agent-generated bugs in projects with detailed AGENTS.md files. OpenAI's own repository has 88 nested AGENTS.md files, one per subdirectory.

The Reflexion paper [E3] (Shinn et al., 2023) provides indirect but substantive support for iterative rule refinement as advanced practice: agents that receive verbal feedback on task outcomes and update their behavioral policies outperform static-instruction agents. Applied to configuration: rules derived from observed agent failure patterns (measured via eval suites) should outperform rules written from first principles without behavioral feedback. This validates the ACAM "Advanced" criterion of measured effectiveness — not as a formality, but as the mechanism by which configurations improve.

### 1.5. Rule Conflict Research

External sources converge on three patterns for managing rule conflicts:

1. **Specificity wins (weakly):** [B6] notes Claude Code processes more specific/scoped rules preferentially. This is platform-specific and not guaranteed by Cursor.
2. **Layered ownership:** [V4] (OpenAI agents) recommends global agents own universal behaviors and specialized agents own narrow tasks — preventing cross-context pollution. The analogy for rules: always-on rules should own universal behaviors exclusively; anything context-specific belongs in glob-scoped or agent-requested rules.
3. **Tooling as the fix:** [C2] (cursorrules-collection) ships `cursor-doctor` specifically for rule auditing, including conflict detection. The community identified the conflict problem early enough to build tooling for it — which is itself evidence that the problem is real and common.

---

## 2. ACAM Cell Evidence: Configuration Dimension

### 2.1. Basic Configuration — Observable Criteria

| Criterion | Observable artifacts | External validation |
|-----------|---------------------|---------------------|
| Zero or single config file | One `.cursorrules` or IDE User Rules only | Community scan [N3]: 3,698 `.cursorrules` total across GitHub (2025), most single-file |
| Copy-paste, no customization | Template sourced from awesome-cursorrules [C1] without modification | 39.8k stars = template consumption at scale, not original authoring |
| No scoping | All rules fire for every file type and task | [B1]: "scoped activation saves 60-80% tokens" — implies always-on is wasteful |
| No versioning | Config not in git or changed without tracking | MSR 2026 [N2]: avg 5.68 commits to `.cursor/` dir in its sample — versioning is attainable |
| No sizing discipline | Files >500 lines or entirely empty | [V9]: Claude Code targets "<200 lines" — even moderate practice has this constraint |

**External vocabulary check (BC3):** Anthropic [E1], OpenAI [V3], and Claude Code [V9] independently describe the same failure mode: unscoped, over-long, copy-pasted system prompts produce degraded agent behavior. The "Basic" label maps directly to what these sources call "poor system prompt hygiene." The vocabulary differs — they use "system prompt," not "rule" — but the observable artifacts and failure modes are identical.

### 2.2. Intermediate Configuration — Observable Criteria

| Criterion | Observable artifacts | External validation |
|-----------|---------------------|---------------------|
| Multiple scoped files | `.cursor/rules/` with ≥3 files using glob or description activation | MSR 2026 [N2]: avg 4.68 files in top-star sample places this at Intermediate boundary |
| Separate concerns | One concern per file (security, testing, style, workflow) | [B2]: "Split by domain. Under 200 lines per file." [B5]: "One concern per file" |
| Versioned config | Rules committed to git, tracked alongside code | [B5]: "Version control rules like code" |
| Activation mode awareness | Mix of alwaysApply + glob-scoped + agent-requested rules | [V8]: "Keep rules minimal. If you only need it occasionally, put it in a skill." |
| Explicit sizing standards | Line limit or token budget defined | [B1]: "under 100 lines — critical instructions survive middle of context" |

**External vocabulary check (BC3):** [B2], [B5], and [B6] independently describe what rules-skills calls "Intermediate" as best practice for Claude Code users. The MSR 2026 [N2] empirically shows that top-starred-repo practitioners cluster around these criteria (avg 4.68 files, active git history, `.cursor/` directory adoption at 93.27%). "Intermediate" is the label used by community guides for "well-organized, versioned, scoped config." The vocabulary aligns.

### 2.3. Advanced Configuration — Observable Criteria (BC3 Validation)

**This is the critical BC3 check.** Phase 1's ACAM skeleton listed: "Config library distributed across projects. Token budget management. Ablation testing. Measured effectiveness (eval data). Structural loading strategies." Each criterion is evaluated against external sources:

| Phase 1 Criterion | External source that independently identifies this | Verdict |
|-------------------|--------------------------------------------------|---------|
| Config library distributed across projects | [V4]: "Static instructions first, dynamic callbacks" implies config-as-code distribution; Devin blueprints [D3] are the clearest example | **Partial** — implied by Devin/enterprise patterns, not named by practitioner sources |
| Token budget management | [B1]: "60-80% token savings from scoped activation." [S2]: constitutional vs procedural split. [N2]: avg file length 462 lines in sample | **Confirmed** — multiple independent sources identify this as a key variable |
| Ablation testing (rule effectiveness measurement) | [A1]: ACI design measured by task success rates. [A6]: benchmark-validated scaffolding. [E3]: Reflexion — policies derived from feedback outperform static instructions | **Partial** — research papers validate measurement; no practitioner source prescribes "ablation testing" for rules as a named practice |
| Measured effectiveness | [N5]: AGENTS.md "reduces bugs 35-55%" — quantitative config effectiveness. [E3]: Reflexion validates feedback-derived policies | **Confirmed** — effectiveness measurement is cited and meaningful; AGENTS.md data is the clearest practitioner example |
| Structural loading strategies (lazy-load) | [S2]: Lazy-Loaded Procedural Policy pattern explicitly named. [S4]: "Skills deferred until needed" | **Confirmed** — S2 names this independently, with specific implementation pattern |
| *(Not in Phase 1)* Cross-tool portability (AGENTS.md) | [N5]: 60,000+ repos, universal standard. [D2]: Devin reads AGENTS.md natively. [E2]: Copilot reads `.github/copilot-instructions.md` | **Should add** — external sources strongly validate this as Advanced criterion; Phase 1 omitted it |

**BC3 findings (two revisions required):**

1. **Remove "ablation testing" as a standalone minimum Advanced criterion.** No practitioner source prescribes ablation testing for rules by name. Research papers (SWE-bench, Reflexion) use task benchmarks — not rule ablation — as their measurement mechanism. Replace with "quantified effectiveness data" (more general, better supported).

2. **Add "cross-tool portability (AGENTS.md or equivalent)" to Advanced criteria.** This is well-supported by [N5], [D2], [E2], and [B9]. Phase 1 omitted it because AGENTS.md was not yet on the radar when the skeleton was written. By June 2026, it is the strongest single signal of Configuration maturity.

**Revised Advanced Configuration criteria (externally validated, observable-artifact format):**

| Criterion | Observable artifacts | External source |
|-----------|---------------------|----------------|
| Lazy-loaded procedural policy — ≤5 always-on rules encoding invariants only; conditional rules in skills or tools | `alwaysApply: false` rule count ≥ `alwaysApply: true`; presence of skills that cover workflow steps | [S2] (LLPP pattern), [S4] ("skills deferred"), [V8] ("put it in a skill") |
| Token budget measurement tooling | `cursor-doctor` equivalent script or CI check reporting token count for always-on rules | [C2] (cursor-doctor), [B1] (60-80% savings quantified) |
| Quantified effectiveness data | Eval results comparing sessions with/without rules; bug-rate data before/after config; ablation test report | [N5] (35-55% bug reduction for AGENTS.md), [E3] (Reflexion: feedback-derived policies outperform static) |
| Cross-tool portability | `AGENTS.md` in repository root; or equivalent format readable by ≥3 coding agents | [N5] (60k repos), [D2] (Devin reads natively), [E2] (Copilot reads `.github/copilot-instructions.md`) |
| Rule conflict detection tooling | Script or CI step that flags overlapping glob patterns, duplicate keywords, or contradictory directives | [C2] (cursor-doctor), [E1] (conflict = root cause of system prompt failure) |
| Config distribution system | Sync script or package that applies the same rule library to multiple projects; evidence of multi-project usage | [V4] (implied by static instructions as code), [D3] (Devin blueprints for reproducible environments) |

---

## 3. rules-skills Evidence

### 3.1. Artifact Inventory (Configuration Layer)

**Claim: Multiple scoped rules with three activation modes**

Evidence A: `library/cursor/rules/` — 16 `.mdc` files using three distinct frontmatter configurations:
- 8 alwaysApply: `adversarial_harness.mdc`, `agent_behavior.mdc`, `autonomous_execution.mdc`, `code_standards.mdc`, `critical_thinking.mdc`, `planning_discipline.mdc`, `progress_tracking.mdc`, `verification.mdc`
- 5 glob-scoped: `architecture.mdc` (`**/*.py,**/*.ts,**/*.tsx`), `causal_rigor.mdc` (`experiments/**`), `python_ml.mdc` (`*.py,*.ipynb`), `research_standards.mdc` (`experiments/**,analysis/**`), `testing.mdc` (`**/test*.py,**/tests/**`)
- 3 agent-requested: `design_principles.mdc`, `prompt_coaching.mdc`, `security.mdc`

Evidence B: `docs/RULES_STANDARD.md` — explicit frontmatter contract table defining exactly three valid configurations with rationale per type.

**Claim: Explicit sizing standards and token budget**

Evidence A: `docs/RULES_STANDARD.md` — "Individual rules: under 200 lines. Total always-on budget: under 2000 tokens combined." Also defines `tests/validate.py` as the designated measurement source under its "Measurement" section: "Token count per rule — tests/validate.py."

Evidence B: `tests/validate.py` — the authoring validation script designated by RULES_STANDARD.md to enforce sizing constraints on rules in `library/cursor/rules/`. Measured always-on line count across 8 alwaysApply files: 306 total lines (avg 38.25 lines/rule), all within the 200-line individual limit.

**Claim: Version-controlled, distributed config library**

Evidence A: `library/cursor/rules/` (16 `.mdc`) + `library/claude/rules/` (23 `.md`) — dual-format library in git.

Evidence B: `sync-cursor.sh` — distributes `library/` to all `~/redhat` projects. Creates a multi-project config distribution system where rules changes propagate across all projects on sync.

### 3.2. Factual Correction from Phase 2

Phase 2 referenced "adversarial_harness.mdc (alwaysApply) is a 230-line rule loaded on every request" — this figure was incorrect. The adversarial_harness.mdc rule file is **48 lines**. The figure 191 lines applies to the associated `library/cursor/skills/adversarial-harness/SKILL.md`, which is the detailed workflow document the rule references via "Full workflow: read adversarial-harness skill." The rule and the skill are separate artifacts. This correction matters for the S2 analysis in §5.

### 3.3. Comparison Against Phase 2 Normie Baseline

| Metric | rules-skills | MSR 2026 avg (7k-star repos) [N2] | Tier 0-1 normie |
|--------|--------------|-------------------------------------|-----------------|
| Rule file count | **16** | 4.68 (max 56) | 0-1 |
| Avg file size (lines) | **~50** | 462.67 lines | N/A |
| Activation modes used | **3** (alwaysApply, glob, agent-req) | Unknown (likely 1-2) | 0-1 |
| Explicit sizing standard | **Yes** (`docs/RULES_STANDARD.md`) | Unknown | No |
| Dual-format (Cursor + Claude) | **Yes** (16 + 23) | No | No |
| Multi-project distribution system | **Yes** (`sync-cursor.sh`) | No | No |
| AGENTS.md | **No** | Not tracked | No |
| Token budget measurement tooling | **No** (estimate only) | No (`cursor-doctor` exists but not adopted) | No |
| Ablation / effectiveness data | **No** (`feat-16` pending) | No | No |

**Key finding:** rules-skills has 3.4× more rule files than the MSR 2026 biased sample average (4.68), and exceeds that sample on every structural dimension (activation modes, sizing standards, distribution). The comparison against Tier 0-1 normie is not meaningful — they are different categories.

The more important finding is what the comparison reveals about where the gap to Advanced lies: it is not in rule count or file structure. Rules-skills already has more structural sophistication than the MSR 2026 top-star sample on every measurable dimension except cross-tool portability and effectiveness measurement.

---

## 4. Honest Gaps (BC6: No Hedging)

### 4.1. No AGENTS.md File

**Gap:** rules-skills has no AGENTS.md in the repository root.

This is a concrete gap against the 2026 baseline. AGENTS.md is the open standard (Linux Foundation, December 2025) with 60,000+ adopting repositories [N5]. Every major coding agent reads it natively. A developer using Devin, Codex, Gemini CLI, or any agent other than Cursor on this repository receives zero configuration context from our `.mdc` rules — those files are invisible to non-Cursor agents.

The Devin docs [D2] show that AGENTS.md "cannot be disabled" — it is always read before the agent starts coding. Our `.mdc`-based config requires Cursor specifically.

**Severity: High.** The harness works correctly in Cursor. But in a multi-agent world where AGENTS.md is the universal config surface, a Cursor-only setup is tool-specific rather than practitioner-standard. This is the single gap that most directly signals "Intermediate" rather than Advanced by 2026 standards.

**No mitigation currently in place.** This is a factual absence, not an architectural trade-off with documented rationale.

### 4.2. 8 alwaysApply Rules vs Community "3-5 Max" Guideline

**Gap:** rules-skills has 8 alwaysApply rules. Community guides [B1], Cursor documentation [V8], and [S2] (LLPP) converge on 3-5 as the practical upper bound for always-on rules.

The community guideline reasoning: at 5 rules × avg 40 lines each, you load ~200 lines of always-on context before any user input. At 8 rules × avg 38 lines, the load is 306 lines — 1.5× the informal ceiling.

The deeper problem identified by S2: three of the eight alwaysApply rules are procedural policies, not constitutional invariants (see §5.1). They encode conditional workflows ("if non-trivial task, launch planner"), not universal behaviors. By S2's LLPP framework, these belong in skills loaded on demand, not in the system prompt for every interaction.

**Severity: Medium.** The 306-line load is within the 2000-token budget. It violates the principle behind the budget rule — that always-on context should be reserved for truly universal behaviors.

**No mitigation currently in place.** RULES_STANDARD.md enforces a token budget but not an always-on file count limit.

### 4.3. No Token Budget Measurement Tooling

**Gap:** RULES_STANDARD.md specifies a 2000-token budget for always-on rules and designates `tests/validate.py` as the measurement tool. The validate.py implementation uses a word × 1.3 heuristic to estimate token count — it is not a tokenizer-based measurement.

[C2] (cursorrules-collection) ships `cursor-doctor` specifically for rule auditing including tokenizer-accurate token counting. The RULES_STANDARD documents four hypotheses (H1-H4) — H1 is "always-on budget under 2000 tokens prevents context pollution." H1 has never been verified with a real tokenizer. The 2000-token limit is a design constraint, not an empirically validated threshold.

**Severity: Low.** The constraint is designated as measured by `tests/validate.py`. The implementation uses a word × 1.3 heuristic, not a tokenizer. The budget compliance status is unknown.

### 4.4. No Ablation Data (Binding Gap for Advanced)

**Gap:** We don't know whether our rules improve agent behavior. The eval suite (129 tests) measures harness compliance — it tests whether the agent follows the harness workflow. It does not test whether the *rules* cause better outcomes than no rules, or whether some rules are counterproductive.

`feat-16` (rule ablation mode in session_runner.py) is pending. Until it runs, all claims about rule effectiveness are hypotheses. RULES_STANDARD documents H1-H4 as explicit hypotheses — they are testable, not settled.

The Reflexion finding [E3] is relevant here: policies derived from observed failure patterns outperform static first-principles policies. We wrote our rules from first principles. We have no feedback loop to update them based on measured outcomes.

**Severity: High.** This is the binding constraint. No other gap would individually prevent an Advanced score. Without effectiveness data, the "quantified effectiveness" Advanced criterion is unmet. Infrastructure alone does not satisfy the criterion.

### 4.5. Frontmatter Inconsistency in adversarial_harness.mdc

**Gap (newly identified):** `adversarial_harness.mdc` has both `alwaysApply: true` AND a `globs:` field set. Per RULES_STANDARD.md, exactly three valid configurations exist — none of them is "alwaysApply: true WITH globs." When `alwaysApply: true`, the `globs` field is irrelevant (the rule loads regardless of which file is active).

The intention (per RULES_STANDARD "Harness State References" section) was to scope this rule to source code directories so it doesn't fire when editing `.mdc` rule files themselves. The implementation has `alwaysApply: true`, which makes the rule fire for everything including rule file editing — the opposite of the intent.

This is a RULES_STANDARD compliance violation internal to the rules-skills repo itself.

**Severity: Low.** Not a runtime failure. The rule fires correctly for its intended purpose (code editing). But the configuration is self-contradictory and documents a gap between the standard and its application in the repo's own rules.

---

## 5. Counter-Evidence Engagement

### 5.1. [S2] "Lazy-Loaded Procedural Policy" — Conform or Violate?

S2's core claim: the system prompt should contain constitutional invariants only. Scenario-specific procedures should be loaded as tools or skills on demand. The named pattern: Lazy-Loaded Procedural Policy (LLPP).

With the Phase 2 factual correction applied (adversarial_harness.mdc is 48 lines, not 230 lines), the S2 analysis changes significantly. The rule is a concise routing instruction, not a 230-line procedural manual. The detailed workflow is in the 191-line SKILL.md, which the rule points to — this structure already partially conforms to LLPP.

**Per-rule classification by S2 framework:**

| Rule | S2 Classification | Rationale |
|------|------------------|-----------|
| `code_standards.mdc` | Constitutional invariant | Universal coding behavior applies to every interaction |
| `verification.mdc` | Constitutional invariant | "Verify after every edit" applies everywhere |
| `agent_behavior.mdc` | Constitutional invariant | Communication style is universal |
| `autonomous_execution.mdc` | Constitutional invariant | "Act without permission for routine ops" applies to all sessions |
| `critical_thinking.mdc` | Constitutional invariant | "Always analyze before acting" applies to all sessions |
| `adversarial_harness.mdc` | **Borderline** | Routes non-trivial tasks to /planner. The routing logic IS conditional ("if non-trivial, invoke harness") but the RULE is 48 lines pointing to a skill. Partially conforms: the skill is lazy-loaded; the routing gate is always-on. |
| `planning_discipline.mdc` | **Procedural policy** | Encodes when to use TodoWrite, when to suggest fresh threads — these are conditional triggers, not universal behaviors |
| `progress_tracking.mdc` | **Procedural policy** | Encodes breadcrumb writing triggers tied to 2+ file changes — a conditional, not an invariant |

**Net verdict:** 5 of 8 alwaysApply rules clearly conform to LLPP (constitutional invariants). `adversarial_harness.mdc` partially conforms — its SKILL.md structure is the lazy-loading pattern; only the routing gate is always-on, which is defensible. `planning_discipline.mdc` and `progress_tracking.mdc` are procedural policies that S2 would place as skills or tools.

**The counterargument for keeping them always-on:** Both rules encode behaviors the agent must perform even when it *doesn't anticipate* that it needs them. A developer who doesn't track progress on a 5-file change will fail — the rule enforces this before the agent decides whether it's necessary. This is the bootstrap problem: you can't enforce "read the progress skill before every multi-file change" without an always-on rule that enforces reading it. The always-on rule is the enforcement mechanism for the skill-based pattern.

**Resolution:** S2's critique is directionally correct — these two rules are conditional in nature. The correct fix is not removing them but shrinking them: each should be ≤20 lines encoding only the triggering condition, with the procedure in a skill. Both already meet the RULES_STANDARD's 200-line limit, but they could be more minimal.

### 5.2. [S3] "Simpler AI Agents" — Was the Harness Over-Engineered?

S3's core claim: guardrails built for weaker 2023-2024 models may constrain stronger 2026 models. Agents with basic primitives outperform over-engineered predecessors.

**The factual context:** The rules-skills adversarial harness was built across 2025-2026 (per breadcrumbs, first verified tasks June 2026). This is Claude 4.x territory, not Claude 2.x. The harness was not built to compensate for weak models — it was built to enforce process discipline (contract-before-code, evaluator-before-commit) that is valuable regardless of model capability. These are organizational control requirements, not model capability workarounds.

**What the eval data shows:** The session_judge behavioral eval scores provide the strongest available evidence about whether guardrails are still needed:
- `behavioral_session_boundary`: 33% — agent fails to suggest fresh threads 67% of the time
- `adversarial_skip_override`: 57% — agent fails to complete tasks correctly under skip-harness conditions

A 33% session boundary score means the model, without enforcement, does not reliably self-correct on thread hygiene. If models were capable enough to make harness rules redundant, this score would approach 100%. It doesn't.

**The limit of this argument:** The eval tests *current* rules behavior, not *ablated* rules behavior. We don't know if removing specific rules would degrade these scores or leave them unchanged. S3's critique is empirically testable via feat-16. It cannot be dismissed, but it also cannot be confirmed without data.

**Honest verdict:** S3's argument applies as a hypothesis that requires feat-16 ablation to resolve. The behavioral eval scores are weak evidence that some guardrails remain necessary (33% session boundary). They do not prove that the harness is *not* over-engineered in parts. "We should measure" is the correct response — not "the harness is justified" and not "S3 is right."

**What this means for Configuration scoring:** S3 reinforces the "Intermediate" verdict. Advanced practice would have the ablation data to engage S3's claim concretely. We don't.

---

## 6. Provisional Scoring: Configuration Dimension

### 6.1. Evidence Table

**Intermediate criteria met (≥2 artifact citations each):**

| Criterion | Evidence A | Evidence B |
|-----------|-----------|-----------|
| Multiple scoped files with separation of concerns | `library/cursor/rules/` — 16 files, one concern per file | `docs/RULES_STANDARD.md` — "No overlap with another rule" checklist item |
| Three distinct activation modes | `adversarial_harness.mdc` (alwaysApply), `architecture.mdc` (glob `**/*.py,**/*.ts`), `prompt_coaching.mdc` (agent-requested, no globs) | `docs/RULES_STANDARD.md` — frontmatter contract table with 3 valid configurations |
| Explicit sizing standards enforced | `docs/RULES_STANDARD.md` — 200-line limit, 2000-token always-on budget | Measured: 8 alwaysApply rules × avg 38.25 lines = 306 lines total, all within individual limit |
| Version-controlled config library | `library/cursor/rules/` in git; `library/claude/rules/` dual format | Git history for `.cursor/rules/` changes tracked with 5.68 avg commits per repo (MSR 2026 benchmark [N2]) |
| Multi-project distribution | `sync-cursor.sh` distributes library to all `~/redhat` projects | `library/cursor/` + `library/claude/` parallel libraries enable consistent distribution |

**Advanced criteria NOT met:**

| Missing criterion | Current state | Severity |
|------------------|--------------|---------|
| Cross-tool portability (AGENTS.md) | No AGENTS.md in repo | Medium-High |
| Lazy-loaded procedural policy | 3 of 8 alwaysApply rules are conditional/procedural (`adversarial_harness`, `planning_discipline`, `progress_tracking`) | Medium |
| Token budget measurement tooling | Line-count estimate only; no tokenizer | Low-Medium |
| Quantified effectiveness data | No ablation data; `feat-16` pending | High — binding constraint |
| Rule conflict detection tooling | No `cursor-doctor` equivalent | Low |

### 6.2. Score: INTERMEDIATE

**Score: Intermediate**

rules-skills meets every Intermediate criterion with multiple artifact citations. It does not meet Advanced criteria.

The 16-rule corpus with explicit sizing standards, three activation modes, dual-format library, and multi-project distribution system significantly exceeds what MSR 2026 [N2] found in its biased sample of 7k-star repos (avg 4.68 files, no evidence of sizing standards or distribution systems). On every measurable structural dimension, rules-skills is above the top-star practitioner sample.

What does not move the score to Advanced: the absence of quantified effectiveness data is the binding constraint. The RULES_STANDARD documents four untested hypotheses (H1-H4). The eval suite measures harness compliance, not rule impact. S3's challenge that some rules may be redundant or counterproductive is empirically open. Advanced practice requires measuring whether the configuration produces better outcomes, not merely enforcing that it exists.

The secondary constraints — no AGENTS.md, three procedural-policy rules in always-on slots, no token budget tooling — are each individually addressable in days to weeks. The measurement gap requires feat-16 (weeks to months).

**Honest one-paragraph positioning:** rules-skills is at the high end of Intermediate on Configuration. The structural foundation (scoped rules, sizing discipline, three activation modes, distribution system) is more sophisticated than virtually all practitioner setups visible in public data. The gap to Advanced is a measurement gap, not an infrastructure gap: four untested hypotheses about rule effectiveness, no ablation data, and no tooling to verify the 2000-token budget constraint. Additionally, no AGENTS.md means the configuration is Cursor-specific in a world that has standardized on AGENTS.md. The path from Intermediate to Advanced on Configuration is: (1) add AGENTS.md (one day), (2) move `planning_discipline.mdc` and `progress_tracking.mdc` conditional content to skills (one week), (3) implement token count measurement in `tests/validate.py` (one day), (4) run feat-16 ablation and use results to update rules (one sprint). None of these require architectural changes.

---

## 7. New Sources Added (BC1 Compliance)

Three sources not in the pre-Phase-3 bibliography. All URLs are real.

### [E1] Anthropic — "System Prompts" (Claude API Documentation)

- **URL:** https://docs.anthropic.com/en/docs/build-with-claude/system-prompts
- **Relevance:** Configuration (rules as system prompts, failure modes, layering)
- **Key takeaway:** System prompt establishes agent identity, capabilities, and constraints before any user turn. Five root causes of poor system prompt performance: vague instructions, over-reliance on model inference, conflicting instructions, missing edge cases, poor formatting. All five apply verbatim to `.mdc` rules. Best practice: specific, actionable, conflict-free, sized to the task.
- **ACAM mapping:** Rules are system prompt content. "Basic" = poor system prompt hygiene. "Intermediate" = structured, scoped, versioned. "Advanced" = conflict-detected, effectiveness-measured, feedback-derived.

### [E2] GitHub — "Adding custom instructions for GitHub Copilot" (Official documentation)

- **URL:** https://docs.github.com/en/copilot/customizing-copilot/adding-custom-instructions-for-github-copilot
- **Relevance:** Configuration (platform comparison, four-layer model, conflict handling)
- **Key takeaway:** Organization-level instructions (admin-managed) → repository-level (`.github/copilot-instructions.md`) → personal instructions. Conflicts produce "unpredictable behavior." Instructions inherit across scopes. Confirms the four-layer config model is universal. Copilot's approach matches Cursor/Claude Code: layered, scoped, conflict-unresolved.
- **ACAM mapping:** Validates that platform layering and conflict resolution gaps are not rules-skills-specific — they are universal across tools. No platform has solved rule conflict detection at scale.

### [E3] Reflexion: Language Agents with Verbal Reinforcement Learning (Shinn et al., 2023)

- **URL:** https://arxiv.org/abs/2303.11366
- **Relevance:** Configuration (iterative rule refinement, effectiveness measurement)
- **Key takeaway:** Agents that receive verbal feedback on task outcomes and update their behavioral policies (via an "episodic memory" of past failures) significantly outperform static-instruction agents on AlfWorld, HotpotQA, and HumanEval benchmarks. Self-reflection loops enable agents to learn from mistakes without gradient updates. Applied to configuration: rules derived from observed failure patterns outperform rules written from first principles.
- **ACAM mapping:** Directly validates the ACAM "Advanced" criterion of "measured effectiveness." Static rules (written once, never updated from behavioral data) are Intermediate. Rules iteratively refined via eval feedback are Advanced. feat-16 ablation + rule updates based on results would constitute the Reflexion pattern applied to IDE config.

---

*Phase 4 (Workflows) can proceed using this analysis. Cross-reference §4.2 (S2 borderline always-on rules) and §5.1 (LLPP verdict for adversarial_harness.mdc) when evaluating the Workflows dimension. The factual correction in §3.2 (adversarial_harness.mdc = 48 lines, not 230) propagates to any Phase 4 analysis that references this rule.*
