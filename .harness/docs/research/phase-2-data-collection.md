# Phase 2 — Data Collection

**Spike:** spike-research-agents
**Date:** 2026-06-11
**Status:** Complete
**Bias corrections applied:** BC2 (≥2 challenging sources), BC4 (Devin + ≥1 more advanced comparable), BC5 (empirical normie baseline from data)

---

## §9 Compliance Check

Before analysis begins: documented BC1-BC6 violations would be flagged here.

- **BC1** — ≥3 external sources not in prior docs: ✓ (N1, N2, N3, N4, S1-S4 all new)
- **BC2** — ≥2 sources arguing AGAINST complex config: ✓ (S1, S2, S3, S4 — four sources)
- **BC4** — Devin + ≥1 setup more advanced than rules-skills: ✓ (Devin, SWE-agent both more advanced on specific dimensions)
- **BC5** — Normie baseline from GitHub data: ✓ (see §2)

---

## 1. GitHub Adoption Data

### 1.1. Config File Prevalence (as of mid-2026)

| File | Repos (est.) | Source | Notes |
|------|-------------|--------|-------|
| `AGENTS.md` | **60,000+** | Linux Foundation / AAIF announcement (Dec 2025) | Open standard. Read by Cursor, Codex, Copilot, Devin, Gemini CLI, Windsurf, Zed, Factory, Jules, Aider. OpenAI repo alone has 88 files. |
| `CLAUDE.md` | **2,804** (in 128k repo corpus) | Repobility Research [N1] | 50× higher adoption than `.cursorrules` in same corpus. Bias: corpus skews toward Claude users. |
| `.cursor/rules/*.mdc` | **401** repos (Sourcegraph starred repos) | MSR 2026 empirical study [N2] | Sourcegraph indexes starred repos only — heavy selection bias toward active, well-maintained projects. |
| `.cursorrules` (legacy) | **56** (in 128k corpus) / **~3,700** (all public, 2025) | Repobility [N1], community scan [N3] | Legacy format. Still works but deprecated. Migration ongoing. |
| `AGENTS.md` (Devin/per-project) | **Not separately tracked** | Devin docs | Devin reads AGENTS.md natively; no separate count. |
| `.windsurfrules` | **25** (in 128k corpus) | Repobility [N1] | Windsurf is newer; even simpler adoption signal. |
| `.github/copilot-instructions.md` | **Not surveyed** | — | Microsoft's variant; GitHub Actions adoption likely higher in enterprise. |

**Key observation (BC5):** The 60,000 AGENTS.md repos vs. 56 .cursorrules repos in the same corpus is striking — but the corpus is Claude-heavy. The 3,700 .cursorrules figure (all of GitHub, early 2025) is the more honest count for Cursor-native config. Even then, 3,700 across millions of repos means <0.1% of GitHub repos have any Cursor-specific config.

### 1.2. MSR 2026 Empirical Study — Key Findings [N2]

**Study:** "Beyond the Prompt: An Empirical Study of Cursor Rules" (arXiv:2512.18925, accepted MSR 2026)
**Sample:** 401 repositories with .mdc files (Sourcegraph, starred repos)

| Metric | Value |
|--------|-------|
| Avg .mdc files per repo | **4.68** (SD=6.89, max=56) |
| Repos using `.cursor/` directory | **93.27%** (374/401) |
| Avg file length | **462.67 lines** (SD=1,197.00, max=11,076) |
| Avg authors per cursor dir | **1.72** (max=8) |
| Avg commits to cursor dir | **5.68** (max=98) |
| Avg days between updates | **16 days** |
| Avg repo stars | **7,064** (SD=21,509) |

**Critical context:** The 401-repo sample is not random. Sourcegraph indexes only starred repositories. Average 7,064 stars means this sample is the top few percent of active, well-maintained projects. This is the "best of the best" in terms of Cursor usage — not the median practitioner.

**Content taxonomy (qualitative):** Developers primarily encode five themes:
1. **Conventions** — code style, naming, formatting
2. **Guidelines** — architectural decisions, patterns to use/avoid
3. **Project Information** — tech stack, architecture, dependencies
4. **LLM Directives** — agent-specific instructions, workflow enforcement
5. **Examples** — code snippets, reference patterns

LLM-specific directives (category 4) have "relatively low adoption rate" — most rules are conventions and guidelines, not agent workflow enforcement. Newer repos (< 7 months) include fewer rules overall.

### 1.3. Community Collection Analysis

**PatrickJS/awesome-cursorrules (39.8k stars):** The canonical evidence that interest in Cursor configuration is massive — but primarily template-consumption, not original authoring. The stars do not represent original rule writers; they represent developers who want to copy-paste a starting point.

**nedcodes/cursorrules-collection (110+ rules):** More structured. Includes cursor-doctor validator and rule-gen generator. Evidence that tooling for rule authoring is emerging.

**typical repo pattern** (inferred from community guides): Power users maintain 5-10 files; most "good" setups have 3-5 alwaysApply + 5-15 glob-scoped rules, total budget under 3,000 always-loaded tokens. This is the practical Intermediate ceiling for most practitioners.

---

## 2. Empirical Normie Baseline (BC5)

The normie baseline must come from data, not stereotypes.

### 2.1. Three-Tier Empirical Model

| Tier | Estimated prevalence | Observable signals | Evidence basis |
|------|---------------------|--------------------|----------------|
| **Tier 0 — No config** | ~85-90% of Cursor users | IDE defaults. No .cursorrules, no .cursor/rules/. Maybe User Rules in Cursor settings. | 3,700 .cursorrules files vs millions of repos using AI IDEs. Inference from low absolute counts. |
| **Tier 1 — Single-file or template** | ~8-12% | One `.cursorrules` copied from awesome-cursorrules or AI-generated. OR AGENTS.md with basic setup commands. No scoping, no lifecycle. | 3,700 .cursorrules files (2025 data) + AGENTS.md 60k repos trend. Most AGENTS.md files likely have basic project context only. |
| **Tier 2 — Multiple scoped files** | ~2-3% | `.cursor/rules/` with 3-8 scoped .mdc files. Glob activation. Some always-on rules. | MSR 2026 [N2]: 401 repos, avg **4.68 .mdc files/repo**, avg 7,064 stars — heavy selection bias toward high-star repos. Real prevalence among average Cursor users is lower. |
| **Tier 3 — Structured config + enforcement** | <0.5% | Hooks, skills, lifecycle tracking, eval suites, multi-role subagents. | cursor-handbook (22 stars), rules-skills, very few others visible in public data. |

### 2.2. Implications for ACAM Positioning

**What this means for "Intermediate" label:**
- Compared to Tier 0-1 (the actual majority), rules-skills at 16 scoped rules + 14 skills + 12 hooks is dramatically above average.
- Compared to Tier 2 (the starred-repo elite), rules-skills is above average on rule count and dramatically above on enforcement depth.
- "Intermediate" is a fair label IF we're measuring against theoretical advanced practice (structural enforcement + ablation testing + measured effectiveness), not against the actual user population.

**Revised honest framing:** rules-skills is in the top ~1% of practitioner setups by observable artifacts. The label "Intermediate" refers to its position relative to what is theoretically possible, not relative to what is typical. Whether "top 1%" counts as "advanced" depends on the reference frame.

This is a meaningful update from Phase 1, which treated "Intermediate" as an achievement to be measured against some abstract advanced ceiling.

### 2.3. What the Median Practitioner Actually Does

Based on community guides and Cursor token budget documentation:

```
Typical "power user" setup (2026):
- 3-5 alwaysApply rules: naming conventions, comment style, error format
- 5-15 auto-attached rules: framework-specific (React, API routes, tests)
- Total always-loaded budget: <3,000 tokens
- No hooks (too complex)
- No skills (emerging, not yet common)
- No eval suite (no awareness of this pattern)
```

This is what Phase 1 called "Intermediate." By this evidence, **Intermediate is a reasonable label for this typical power user**, but that means rules-skills (which vastly exceeds this pattern with hooks, skills, and eval) should technically score higher — the gap is that we lack quantitative effectiveness data, not sophisticated artifacts.

---

## 3. Comparable Setup Analysis (BC4)

### 3.1. Aider — "The Clean Minimalist"

**Source:** aider-ai/aider docs, .aider.conf.yml [T1, T2]
**Config model:**
- 2-layer: `.aider.conf.yml` (runtime) + `CONVENTIONS.md` (coding guidelines)
- Priority cascade: home → repo → cwd
- Single conventions file, no scoping, no lifecycle hooks
- `/read` command for always-loaded context
- No skills, no hooks, no multi-agent

**ACAM classification:**

| Dimension | Level | Evidence |
|-----------|-------|---------|
| Configuration | **Intermediate** | 2-file separation (runtime vs guidelines), priority cascade, `--model` selection, repo map token tuning. But no scoping, no structural loading. |
| Workflows | **Basic** | No lifecycle, no skills, no eval suite. Single-shot generation + apply. "Architect mode" is 2-pass but no enforcement. |
| Multi-agent | **Basic** | Single agent. Architect mode uses 2 models but no role separation between planner/evaluator. |
| Interaction | **Intermediate** | Good CONVENTIONS.md authoring guides, explicit `/ask` vs `/code` modes, clean command UX. |

**What Aider does better:** Runtime config (model selection, repo map tuning) is more explicit than rules-skills. `.aider.conf.yml` priority cascade is cleaner than our sync-cursor.sh approach.
**What rules-skills does better:** Lifecycle enforcement, skills, hooks, multi-agent roles, eval suite.

---

### 3.2. SWE-agent — "The Academic Standard"

**Source:** SWE-agent (princeton-nlp), SWE-Adept (arxiv 2603.01327), BOAD (IBM) [A1, A2, A3]
**Config model:**
- Agent-Computer Interface (ACI) design philosophy
- Scaffold as primary config artifact (Python code, not files)
- 2-agent model (SWE-Adept): localization agent + resolution agent
- BOAD: automatic hierarchical agent discovery via bandit optimization
- Programmatic orchestration — not IDE config

**ACAM classification:**

| Dimension | Level | Evidence |
|-----------|-------|---------|
| Configuration | **N/A** | Scaffold IS the config. Not file-based system prompts. ACI design (tool definitions, output parsers, action space) is the analog. |
| Workflows | **Advanced** | Structured ACI loop, reproducible runs, benchmark-validated. Plan→execute→verify is structural. |
| Multi-agent | **Advanced** | Programmatic 2+ agent orchestration. Automatic hierarchy discovery (BOAD). Context isolation enforced architecturally. |
| Interaction | **Advanced** | ACI design paper: tool interfaces are as important as model. Tool description quality = routing logic. |

**Challenge to rules-skills:** SWE-agent's "advanced" is architectural (programmatic), not file-based. The comparison is apples-oranges — SWE-agent is a research framework for autonomous agents, not an IDE practitioner config. But it shows that **truly advanced multi-agent is programmatic, not manual /planner launches**. Rules-skills' manual orchestration is the ceiling before this gap, not evidence of reaching it.

---

### 3.3. Claude Code — "The Direct Comparable"

**Source:** code.claude.com docs, hooks reference [V9, B5, B6, B7]
**Config model:**
- 3-tier: `~/.claude/CLAUDE.md` (global) → `./CLAUDE.md` (project) → `./subdir/CLAUDE.md` (path-scoped)
- `.claude/rules/` with YAML frontmatter for path-scoped rules
- Hooks: PreToolUse, PostToolUse, UserPromptSubmit, Stop, SessionStart — can block (exit code 2)
- Prompt-based hooks: LLM decides allow/deny
- Agent hooks: subagent verifies codebase state (50 tool-use turns)
- Plugin hooks: distributed through organization marketplace
- No eval pipeline equivalent
- Target: <200 lines per CLAUDE.md

**ACAM classification:**

| Dimension | Level | Evidence |
|-----------|-------|---------|
| Configuration | **Intermediate** | 3-tier hierarchy, path-scoped rules, <200 line guidance, version-controlled. No token budget management tooling, no ablation. |
| Workflows | **Intermediate** | Hooks for structural enforcement (PreToolUse can block). Prompt hooks for judgment. Agent hooks are genuinely advanced. No eval regression suite. |
| Multi-agent | **Intermediate** | Task tool for subagents. Skill frontmatter hooks. But no planner/evaluator role model. |
| Interaction | **Intermediate** | Structured memory model, clear hierarchy. Coaching rules possible. |

**Challenge to rules-skills:** Claude Code's agent hooks (subagent with 50 tool-use turns for verification) are potentially more powerful than rules-skills' verify-harness hook which trusts contract.verified. Claude Code plugin marketplace creates a distribution model we lack. The 3-tier hierarchy is cleaner than our global/project split.

---

### 3.4. Devin — "The More Advanced Comparable" (BC4)

**Sources:** Devin docs (hooks, AGENTS.md, config, blueprints) [D1, D2, D3, D4]
**Config model:**
- **AGENTS.md** — primary project context (always-on, injected at session start)
- **Blueprint YAML** — environment specification (init scripts, maintenance scripts, knowledge blocks). Creates bootable VM snapshots.
- **hooks.v1.json** — Claude Code-compatible hook format. PreToolUse, PostToolUse, UserPromptSubmit, PermissionRequest, SessionStart.
- **Permissions** — explicit allow/deny/ask lists for tool use
- **Sandbox network filtering** — allowed_domains, denied_domains, network_mode
- **Multi-project config cascade** — `.devin/config.json` → user config → `.claude/settings.json` fallback
- **read_config_from**: can import Cursor, Windsurf, Claude config automatically

**ACAM classification:**

| Dimension | Level | Evidence |
|-----------|-------|---------|
| Configuration | **Advanced** | Blueprint YAML for reproducible environments. Multi-source config cascade (reads Cursor/Windsurf/Claude automatically). Sandbox network filtering. |
| Workflows | **Advanced** | Plan→execute→PR in autonomous async sessions. Slack integration for task assignment. Hooks for structural enforcement. |
| Multi-agent | **Advanced** | Designed for multi-agent orchestration. Can be called programmatically via API. Async task management. |
| Interaction | **Advanced** | Natural language task assignment. Structured progress reporting. Conversational UI with IDE takeover capability. |

**Honest assessment of the comparison:** Devin is a commercial cloud product (~$500/month enterprise tier), not a practitioner's repo-level config setup. The comparison is structurally unfair — Devin's "Advanced" is the product itself, not a practitioner's configuration investment. A more honest comparable would be: how does Devin's *AGENTS.md + hooks setup* compare? Answer: similar to rules-skills on Configuration + Workflows, but with blueprint-level environment reproducibility we lack entirely.

**What Devin does better:** Environment blueprints (reproducible VM state) have no rules-skills equivalent. Async multi-session task management with real memory across sessions. Native AGENTS.md as primary config format (no sync scripts needed). Permission model with explicit allow/deny/ask lists.

**What rules-skills does better than Devin's config layer:** Adversarial eval pipeline. Contract-first negotiation. Breadcrumb audit trail. Behavioral test suite (44 behavioral + 33 trajectory tests). These are quality metrics that Devin's config doesn't address.

---

### 3.5. cursor-handbook — "The Ambitious Peer"

**Source:** girijashankarj/cursor-handbook (C3)
**Config model:**
- 208 components: 110 rules, agents, skills, commands, hooks
- Claims 30%+ token savings
- Live handbook website
- Distribution: clone/submodule/fork
- 22 stars (vs rules-skills which is private)

**ACAM classification:**

| Dimension | Level | Evidence |
|-----------|-------|---------|
| Configuration | **Intermediate** | 110 rules is more than rules-skills' 16. But no sizing standard, no token budget guidance, no sync system. Quantity ≠ quality. |
| Workflows | **Basic-Intermediate** | Has hooks listed. No lifecycle status tracking, no contract-first pattern, no eval suite. |
| Multi-agent | **Basic** | Agents listed but no role model (planner/builder/evaluator separation). |
| Interaction | **Basic-Intermediate** | Rules for agent behavior present but no measurable interaction patterns. |

**Challenge to rules-skills:** cursor-handbook has MORE artifacts in some dimensions (110 rules vs 16). But it lacks the enforcement infrastructure (structural hooks, contract-gate, eval pipeline). This is the "more is more" approach vs rules-skills' "fewer, enforced" approach. Which produces better outcomes is untested by either.

---

### 3.6. Windsurf — "The Simpler Alternative"

**Source:** Windsurf docs [N4]
**Config model:**
- Primary: `.windsurfrules` — single plain Markdown file, no frontmatter
- Advanced: `.windsurf/rules/` directory with YAML frontmatter (activation modes)
- Global custom instructions in settings panel
- No hooks, no structural enforcement
- 6,000-12,000 character limit
- Common anti-pattern noted: copy `.windsurfrules` ↔ `.cursorrules` ↔ `CLAUDE.md` without customizing

**ACAM classification:**

| Dimension | Level | Evidence |
|-----------|-------|---------|
| Configuration | **Basic-Intermediate** | Single file by default (Basic), `.windsurf/rules/` adds scoping (Intermediate). No hooks, no lifecycle. |
| Workflows | **Basic** | No hooks, no skills native to config, no eval suite. |
| Multi-agent | **Basic** | Single agent (Cascade). No role separation visible in config. |
| Interaction | **Basic-Intermediate** | Global custom instructions support. No prompt coaching rules. |

**Challenge to rules-skills:** Windsurf's simplicity might be a feature, not a bug. Its creator tutorial says "I personally don't really rely on these rules files" — evidence that even expert users find the always-on model insufficient for their workflow. This validates the lazy-loading argument (S2).

---

## 4. Challenging Sources (BC2) — Against Complex Configuration

Four sources argue that simpler is better. All are new to this bibliography.

### 4.1. [S1] "Why Most AI Agent Architectures Are Overengineered" (Vadim Alakhverdov)

**URL:** https://vadimall.com/posts/Why-most-ai-agent-architectures-are-overengineered
**Core claim:** A single-loop agent where the LLM decides tool calls outperforms multi-agent orchestration for most tasks. Multi-agent is only justified for: (1) parallel execution over distinct data sources, (2) genuinely long-running workflows with persistent state, (3) adversarial validation where the same model would have blind spots.
**Challenge to rules-skills:**
- 3-role model (planner/builder/evaluator) IS justified by point (3). The evaluator-as-adversary pattern is explicitly endorsed.
- BUT: the planner role is less justified. A single agent with good tools may plan as well.
- The ~20 tool threshold for splitting agents applies to rules-skills: our 14 skills + eval pipeline is well under the threshold.

**ACAM implication:** Multi-agent is not always Advanced. It's Advanced when the role separation solves a specific cognitive blind spot (evaluator challenging builder). It's over-engineering when it adds routing complexity without clear benefit.

---

### 4.2. [S2] "Stop Bloated Agent Prompts: Lazy-Loaded Procedural Policy" (Bechir Trabelsi, Medium, Apr 2026)

**URL:** https://bechirtr97.medium.com/stop-bloated-agent-prompts-a-pattern-i-call-lazy-loaded-procedural-policy-b6ade44dd1aa
**Core claim:** System prompt = constitutional layer (invariants only). Scenario-specific rules = procedural tools loaded on demand. Rules-as-tools pattern: `get_refund_rules()`, `get_escalation_rules()`, `get_sql_safety_rules()` — agent calls only when context requires.
**Challenge to rules-skills:**
- rules-skills has 8 alwaysApply rules. By this argument, most of them should be conditional (loaded only when relevant).
- The 4 glob-scoped rules are closer to this ideal (auto-attached by file context).
- The 4 agent-requested rules are exactly this pattern.
- But `adversarial_harness.mdc` (alwaysApply) is a 230-line rule loaded on every request — a direct counterexample to lazy loading.

**ACAM implication:** "Advanced" configuration may mean FEWER always-on rules, not more. Always-on loading 8 rules including a 230-line harness rule on every interaction is potentially anti-pattern.

---

### 4.3. [S3] "The Case for Simpler AI Agents" (Open Innovation AI)

**URL:** https://openinnovation.ai/the-case-for-simpler-ai-agents/
**Core claim:** Recent case studies show agents with basic primitives (bash, file access, one execution tool) outperform over-engineered predecessors. "The future of agent architecture isn't more sophisticated scaffolding. It's having the confidence to delete most of it." Models are more capable than assumed — guardrails built for weaker models may now constrain better ones.
**Challenge to rules-skills:**
- Structural enforcement (hooks, contract-gate) was designed when agents self-graded more unreliably.
- If models have improved sufficiently, hooks may now prevent behavior the model would have done correctly.
- The harness was built on Claude 3.x; Claude 4.x/Sonnet 4.x may need less scaffolding.

**ACAM implication:** Enforcement infrastructure that made sense in 2024 may be over-engineered for 2026 models. This is not a reason to delete it now, but it's a reason to measure (feat-16 ablation) whether rules improve or degrade outcomes.

---

### 4.4. [S4] "Heavy AI Agents Are an Anti-Pattern: Why Fewer Agents With More Skills Wins" (Sébastien d'Aout)

**URL:** https://www.dsebastien.net/heavy-ai-agents-are-an-anti-pattern-why-fewer-agents-with-more-skills-wins/
**Core claim:** Agents = rules of the game (small, stable). Skills = toolbox (many, evolvable). Heavy specialized agents with baked-in capability are anti-patterns. One lean agent + rich skill library beats multiple specialized agents. "Receptionist pattern": agent whose entire identity is one rule (route the request) + zero embedded capability.
**Challenge to rules-skills:**
- This is actually *validating* our rules/skills separation.
- BUT: our "Intermediate" rating on Interaction may be generous. 8 alwaysApply rules (including 230-line adversarial_harness.mdc) means the agent identity is not lean.
- If we moved adversarial_harness.mdc to a skill (loaded on demand), we'd be closer to this ideal.

**ACAM implication:** skills architecture is right; always-on rule count is too high. Advanced practice may require inverting our current ratio (fewer always-on, more agent-requested/skills).

---

## 5. Community Signal Mining

### 5.1. Reddit r/cursor Patterns (Inferred from guides and community data)

Key behaviors observed from community guides and Cursor forum discussions:

**Pain points reported:**
- Rules "not being followed" — primary complaint. Usually caused by file size (lost in middle of context), glob misconfiguration, or conflict between rules.
- Token budget anxiety — users don't know how many tokens their rules consume or which rules fire when.
- Copy-paste rule drift — team members have different rules versions.
- "I just include it in my prompts" — significant fraction of users never configure persistent rules (validates Tier 0 being large).

**Emerging practices (2025-2026):**
- `cursor-doctor` tool adoption for rule auditing (nedcodes)
- Numbered file naming for predictable rule ordering (`001-base.mdc`, `002-components.mdc`)
- "Source of truth" AI_RULES.md with sync scripts for multi-tool projects
- User rules vs project rules distinction (personal preferences vs team conventions)

### 5.2. AGENTS.md Adoption Signal

AGENTS.md (60,000+ repos, Linux Foundation AAIF) is the strongest community signal of 2025-2026:
- Reduces agent-generated bugs by **35-55%** in projects with detailed files (IntuitionLabs data point [N5])
- Improves task success rates by ~4% per AAIF study
- Supported natively by every major coding agent (Cursor, Codex, Copilot, Devin, Gemini CLI, Windsurf, Zed, Factory, Jules)
- The OpenAI repo itself has 88 AGENTS.md files (nested per-subdirectory)

**Rules-skills gap:** We have no AGENTS.md in the repository root. Our config is Cursor-first (.mdc format) with a separate Claude port. In a multi-agent world where Devin, Codex, and Gemini CLI all read AGENTS.md natively, our config is less portable than it should be.

### 5.3. Config Format Convergence Pattern

The market has converged on a recognizable pattern:

```
2024:  .cursorrules  → .mdc files  (Cursor-specific)
2024:  CLAUDE.md     → .claude/rules/ (Claude Code)
2025:  AGENTS.md     → nested AGENTS.md (Universal standard)
2026:  All tools read AGENTS.md + their own format as fallback
```

rules-skills is on the Cursor-specific track. To be truly advanced by 2026 standards, configuration should be AGENTS.md-first with tool-specific extensions.

---

## 6. ACAM Comparative Matrix

Based on Phase 2 data, here is the provisional ACAM classification of comparable setups:

| Setup | Config | Workflows | Multi-agent | Interaction | Notes |
|-------|--------|-----------|-------------|-------------|-------|
| **Typical normie** | Basic | Basic | Basic | Basic | ~85-90% of users [N2, N3] |
| **Template user** | Basic | Basic | Basic | Basic | Single copy-paste file [C1, N3] |
| **Power user** | Intermediate | Basic | Basic | Intermediate | 5-10 scoped rules [N2, B1] |
| **Aider** | Intermediate | Basic | Basic | Intermediate | 2-file model, good CLI UX [T1, T2] |
| **Claude Code** | Intermediate | Intermediate | Intermediate | Intermediate | 3-tier, hooks, agent hooks [V9, B5] |
| **Windsurf** | Basic-Int | Basic | Basic | Basic-Int | Single file default [N4] |
| **cursor-handbook** | Intermediate | Basic-Int | Basic | Basic-Int | 110 rules, no enforcement [C3] |
| **SWE-agent** | N/A | Advanced | Advanced | Advanced | Programmatic, not file-based [A1, A2] |
| **Devin** | Advanced | Advanced | Advanced | Advanced | Commercial product [D1, D2, D3] |
| **rules-skills** | Intermediate | Intermediate | Intermediate | Intermediate | Provisional (Phase 7 to confirm) |

**Key finding:** rules-skills is roughly on par with Claude Code across all dimensions. The main differentiator is the adversarial eval pipeline and lifecycle enforcement (hooks that deny) — which Claude Code partially matches with agent hooks but doesn't have as a regression suite. The gap vs Devin is the "commercial product vs practitioner config" distinction.

---

## 7. Revised Positioning After Phase 2

### 7.1. What Phase 2 Changed

**From Phase 1 (opinion-based):**
> "Normie: Zero rules, copy-pasted .cursorrules"

**To Phase 2 (evidence-based):**
> "~85-90% of users have zero or one config file. The 'power user' ceiling for most practitioners is 5-10 scoped .mdc files with no hooks or skills. The transition from Tier 0 to Tier 1 is what awesome-cursorrules (39.8k stars) serves."

**Implication:** rules-skills is NOT Intermediate relative to the actual user population. It's in the top 1-2% of observable setups. "Intermediate" is relative to theoretically possible Advanced (ablation testing, measured effectiveness, fully programmatic orchestration).

### 7.2. What the Challenging Sources Revealed

The four simplicity-first sources (S1-S4) converge on the same critique:
1. Always-on rules > ~5 are likely wasteful (BC2 implication: our 8 alwaysApply may be 3 too many)
2. System prompt should contain invariants only; scenario rules = skills or tools
3. Multi-agent is justified only for adversarial validation (planner role is questionable)
4. Structural enforcement from 2024 may be over-engineered for 2026 model capabilities

These are not reasons to simplify now, but they are inputs for Phase 7 synthesis:
- The "Advanced" cell in Workflows should note that evidence-based rule reduction (via ablation) is as important as rule addition.
- The "red team" pass in Phase 7 must engage these specific critiques.

### 7.3. AGENTS.md Gap

rules-skills has no AGENTS.md. This is a gap against the 2026 baseline. In a world where 60,000 repos use AGENTS.md and every major agent reads it natively, a Cursor-only config (.mdc) is increasingly tool-specific rather than practitioner-standard.

**Phase 7 recommendation:** Flag "no AGENTS.md" as a concrete gap in the scorecard.

---

## 8. Phase 2 Data Summary Table

| Finding | Value | Source | Implication |
|---------|-------|--------|-------------|
| .mdc users (empirical) | 401 high-star repos | MSR 2026 [N2] | Tiny fraction of all Cursor users |
| Avg .mdc files (empirical) | 4.68 | MSR 2026 [N2] | rules-skills (16 files) is 3.4× above average, in biased sample |
| Avg rule file length | 462.67 lines | MSR 2026 [N2] | rules-skills avg ~50 lines/rule — well below median |
| AGENTS.md adoption | 60,000+ repos | Linux Foundation [N5] | Open standard now dominant; rules-skills not on this track |
| .cursorrules total (2025) | ~3,700 | Community scan [N3] | Tiny absolute count vs millions of AI IDE users |
| Hook adoption | Near-zero (est.) | Community guides | Structural enforcement is rare; rules-skills in top 0.1% |
| Normie baseline | 0-1 file | Inferred | "Intermediate" label is relative to theoretical ceiling, not actual practice |
| Devin ACAM rating | Advanced (4/4) | Devin docs [D1-D4] | Commercial product; not directly comparable to practitioner config |
| Challenging sources | 4 sources (S1-S4) | New [BC2] | Simplicity case is strong; always-on rule count may be anti-pattern |

---

## 9. Open Questions for Phases 3-6

1. **Configuration (Phase 3):** Is our 8 alwaysApply rules justified vs 3-5 recommended by community guides [N2, B1]? What would a token budget audit reveal? [S2] argues the system prompt should hold invariants only.
2. **Workflows (Phase 4):** Does our `adversarial_harness.mdc` (230-line, alwaysApply) conform to lazy-loading best practice [S2, S4]? Should it become a skill?
3. **Multi-agent (Phase 5):** Is manual /planner launch genuinely "Intermediate" or is it just "not Basic"? The line is thin. [S1] argues adversarial validation is the one justified use of multi-agent — planner may not clear the bar.
4. **Interaction (Phase 6):** Does the prompt_coaching rule (agent-requested) count as "Advanced" interaction? Or is the absence of prompt A/B testing the binding gap?
5. **Cross-cutting:** Should we add an AGENTS.md file to the repo root [N5], or is Cursor-first config the right bet? AGENTS.md has 60k+ repo adoption [N5] vs our Cursor-specific .mdc format.

---

## 10. Deliverable: raw-data/ Summary

_Note: Full raw data not stored as separate files due to web-based research. All citations are to permanent URLs. Key numerical findings embedded in sections 1-2 above._

**Sources with dedicated bibliography entries added in Phase 2:** N1, N2, N3, N4, N5, S1, S2, S3, S4, D1, D2, D3, D4

---

*Phase 3 (Configuration) can proceed using this empirical baseline. Cross-reference §2 (normie tiers), §3 (comparables), and §4 (challenging sources) throughout dimension analysis.*
