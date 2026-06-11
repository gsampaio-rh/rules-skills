# Annotated Bibliography

**Spike:** spike-research-agents
**Last updated:** 2026-06-11 (Phase 3 additions)
**Sources:** 60+ (Phase 2 added 13 sources: N1-N5, S1-S4, D1-D4; Phase 3 added 3 sources: E1-E3; Phase 4 added 3 sources: F1-F3; Phase 5 added 3 sources: G1-G3; Phase 6 added 3 sources: H1-H3)

Sources are organized by dimension relevance. A source may appear in multiple dimensions.

---

## Vendor Guides & Official Documentation

### [V1] Anthropic — "Building Effective Agents" (Blog post)
- **URL:** https://www.anthropic.com/research/building-effective-agents
- **Relevance:** Configuration, Workflows, Multi-agent
- **Key takeaway:** Start with simplest solution possible. Agentic systems trade latency/cost for task performance. Workflows for well-defined tasks, agents for flexibility. Three principles: simplicity, transparency (show planning steps), careful ACI design.
- **ACAM mapping:** Defines the "start simple" philosophy that separates normies (over-engineering) from advanced (right-sizing complexity).

### [V2] Anthropic — "Building Effective AI Agents: Architecture Patterns and Implementation Frameworks" (PDF, 30 pages)
- **URL:** https://resources.anthropic.com/hubfs/Building%20Effective%20AI%20Agents-%20Architecture%20Patterns%20and%20Implementation%20Frameworks.pdf
- **Relevance:** Multi-agent, Workflows
- **Key takeaway:** Sequential chains, parallelization, evaluator-optimizer loops as named patterns. Choose model for the job (capabilities vs speed vs cost). Modular design for evolving capabilities. Practice modular design.
- **ACAM mapping:** Evaluator-optimizer pattern directly maps to rules-skills planner/builder/evaluator model.

### [V3] OpenAI — "Prompt guidance" (API docs)
- **URL:** https://developers.openai.com/api/docs/guides/prompt-guidance
- **Relevance:** Interaction
- **Key takeaway:** Outcome-first prompts for GPT-5.5. Shorter prompts outperform process-heavy stacks. Avoid unnecessary ALWAYS/NEVER/must — reserve for true invariants. Use decision rules for judgment calls.
- **ACAM mapping:** Challenges rules-skills use of imperative rules (NEVER, MUST) — advanced practice may be lighter-touch.

### [V4] OpenAI — "Agent definitions" (API docs)
- **URL:** https://developers.openai.com/api/docs/guides/agents/define-agents
- **Relevance:** Multi-agent, Configuration
- **Key takeaway:** Define smallest agent that owns a clear task. Static instructions first, dynamic callbacks for runtime context. Keep handoff descriptions short and concrete.
- **ACAM mapping:** "Smallest agent" principle parallels rules-skills cancellation of feat-13 (over-orchestration).

### [V5] OpenAI Agents SDK Prompting Guide (SurePrompts)
- **URL:** https://sureprompts.com/blog/openai-agents-sdk-prompting-guide
- **Relevance:** Interaction, Multi-agent
- **Key takeaway:** Instructions field is the load-bearing prompt. Most failures trace to ambiguous instructions. Write as numbered protocol with explicit conditions. Debug via traces. Guardrails scope tightly.
- **ACAM mapping:** "Numbered protocol" aligns with rules-skills contract.json format. Tracing parallels breadcrumbs.jsonl.

### [V6] Cursor — "Hooks" (Official docs)
- **URL:** https://cursor.com/docs/hooks
- **Relevance:** Workflows, Configuration
- **Key takeaway:** Hooks fire at lifecycle events (sessionStart, preToolUse, stop, etc.). Types: command (side-effect-free), prompt (inject context), block (deny/allow). Cloud agents run command-based hooks from repo.
- **ACAM mapping:** Hooks are the structural enforcement layer. rules-skills uses 12 hooks; community adoption is near-zero.

### [V7] Cursor — "Skills" (Official docs)
- **URL:** https://cursor.com/docs/skills
- **Relevance:** Workflows
- **Key takeaway:** SKILL.md with YAML frontmatter. Auto-discovered from .cursor/skills/. Agent decides relevance by description. disable-model-invocation for explicit-only. /migrate-to-skills converts rules→skills.
- **ACAM mapping:** Skill format directly matches rules-skills library/cursor/skills/ structure.

### [V8] Cursor — "Customizing Agents" (Learn)
- **URL:** https://cursor.com/learn/customizing-agents
- **Relevance:** Configuration, Workflows
- **Key takeaway:** Rules = always-on conventions, Skills = specialized workflows. "Keep rules minimal and high quality. If you only need something occasionally, put it in a skill."
- **ACAM mapping:** Rules-skills follows this split but has 16 always-on rules — may exceed "minimal."

### [V9] Claude Code — "How Claude remembers your project" (Official docs)
- **URL:** https://code.claude.com/docs/en/memory.md
- **Relevance:** Configuration, Interaction
- **Key takeaway:** 3-tier hierarchy: global (~/.claude/CLAUDE.md) → project (./CLAUDE.md) → subdirectory. Target <200 lines. Path-scoped rules in .claude/rules/. Specific > verbose. Conflicting rules picked arbitrarily.
- **ACAM mapping:** Claude Code's config model is a direct comparable. rules-skills library/claude/ mirrors this.

---

## Community Resources & Collections

### [C1] PatrickJS/awesome-cursorrules (GitHub, 39.8k stars)
- **URL:** https://github.com/PatrickJS/awesome-cursorrules
- **Relevance:** Configuration (baseline data)
- **Key takeaway:** Canonical community collection. Promotes .mdc format. 90 contributors. Framework-specific rule templates. Stars indicate massive community interest in configuration.
- **ACAM mapping:** Primary baseline for "what normies do" — most users grab a template from here. 39.8k stars but most repos use 1 file.

### [C2] cursorrules-collection (nedcodes-ok, 110+ rules)
- **URL:** https://github.com/cursorrulespacks/cursorrules-collection
- **Relevance:** Configuration
- **Key takeaway:** 110+ tested .mdc and .cursorrules files. Includes cursor-doctor validator, rule-gen generator, rule-porter converter. Dual format support.
- **ACAM mapping:** More structured than awesome-cursorrules. Validator tool is Intermediate-level practice.

### [C3] cursor-handbook (girijashankarj, 208 components)
- **URL:** https://github.com/girijashankarj/cursor-handbook
- **Relevance:** Configuration, Workflows, Multi-agent
- **Key takeaway:** 110 rules, agents, skills, commands, hooks. Claims 30%+ token savings. Live handbook website. Distribution via clone/submodule/fork.
- **ACAM mapping:** Most ambitious comparable to rules-skills. Smaller community (22 stars vs 39.8k).

### [C4] best-of-Agent-Harnesses (RyanAlberts)
- **URL:** https://github.com/RyanAlberts/best-of-Agent-Harnesses
- **Relevance:** Workflows, Multi-agent
- **Key takeaway:** Curated comparison of agent harness projects. awesome-cursorrules at top (39.6k stars, "super simple content bundle"). Ranks by simplicity↔capability spectrum.
- **ACAM mapping:** Positions rules-skills-like projects on a complexity spectrum. Validates that harness complexity is a real market.

### [C5] Aider-AI/conventions (Community conventions for Aider)
- **URL:** https://github.com/aider-ai/conventions
- **Relevance:** Configuration
- **Key takeaway:** Community-contributed CONVENTIONS.md files. Each has README + CONVENTIONS.md. Aider's equivalent of awesome-cursorrules but smaller.
- **ACAM mapping:** Aider's configuration ecosystem is simpler (1 file) but well-documented.

---

## Blog Posts & Practitioner Guides

### [B1] "Cursor Rules That Actually Work" (OpenBooklet)
- **URL:** https://openbooklet.com/blog/cursor-rules-that-work
- **Relevance:** Configuration
- **Key takeaway:** .cursorrules deprecated → .cursor/rules/*.mdc. Keep each file <100 lines (critical instructions get lost in middle). Scoped activation saves 60-80% tokens. cursor.directory + awesome-cursorrules are primary sources.
- **ACAM mapping:** Defines "Intermediate" Configuration: multiple files, scoped, sized.

### [B2] "Cursor Rules Examples and Templates" (The Prompt Shelf)
- **URL:** https://thepromptshelf.dev/blog/cursor-rules-examples-templates-2026/
- **Relevance:** Configuration
- **Key takeaway:** .cursorrules for quick start, .cursor/rules/ for multi-layer projects. Split by domain. <200 lines per file. Reference external files for large context. Document the why.
- **ACAM mapping:** Matches rules-skills RULES_STANDARD.md recommendations exactly.

### [B3] "The Best Cursor Rules for Every Framework in 2026" (DEV Community)
- **URL:** https://dev.to/deadbyapril/the-best-cursor-rules-for-every-framework-in-2026-20-examples-29ag
- **Relevance:** Configuration
- **Key takeaway:** Users went from 30% to 80%+ AI suggestion acceptance with a single .cursorrules file. Framework-specific rules matter. "Mega Pack" commercial market exists.
- **ACAM mapping:** Shows Basic→Intermediate transition impact. Suggests most users are still at Basic.

### [B4] "Aider Rules & Config: Complete Setup Guide" (cursor-alternatives.com)
- **URL:** https://cursor-alternatives.com/blog/aider-rules/
- **Relevance:** Configuration (comparable)
- **Key takeaway:** Aider's 2-layer model: .aider.conf.yml (runtime) + CONVENTIONS.md (coding guidelines). 4-source priority cascade. `read:` key for always-loaded context. .aiderignore for scope control.
- **ACAM mapping:** Simpler but clean separation of concerns. No hooks, no skills, no multi-agent.

### [B5] "Claude Code Rules Directory" (claudefa.st)
- **URL:** https://claudefa.st/blog/guide/mechanics/rules-directory
- **Relevance:** Configuration
- **Key takeaway:** .claude/rules/ with path-scoped rules via YAML frontmatter. One concern per file. Version control rules like code. Audit CLAUDE.md and extract to rules/.
- **ACAM mapping:** Identical pattern to Cursor .mdc with globs. Claude Code's config maturation parallels Cursor's.

### [B6] "How Claude Code rules actually work" (Substack)
- **URL:** https://joseparreogarcia.substack.com/p/how-claude-code-rules-actually-work
- **Relevance:** Configuration, Interaction
- **Key takeaway:** Scoped rules are deterministic in application; CLAUDE.md is deterministic in expectation. Index in CLAUDE.md pointing to rules/. ML workflow example with experiments.md + production-ml.md scoping.
- **ACAM mapping:** "Deterministic in application" language maps directly to rules-skills "structural vs advisory" distinction.

### [B7] "CLAUDE.md Best Practices" (UX Planet)
- **URL:** https://uxplanet.org/claude-md-best-practices-1ef4f861ce7c
- **Relevance:** Configuration
- **Key takeaway:** 10 key sections for CLAUDE.md. Under 200 lines. Commands section is operational context. Part of project memory, not hard enforcement.
- **ACAM mapping:** "Not hard enforcement" — Claude Code lacks hooks for structural enforcement. Rules-skills fills this gap.

### [B8] "Context Engineering for AI Agents: 2026 Production Guide" (Lushbinary)
- **URL:** https://lushbinary.com/blog/context-engineering-ai-agents-production-guide/
- **Relevance:** Interaction
- **Key takeaway:** Context engineering > prompt engineering. Four strategies: write, select, compress, isolate. Bad context breaks agents more than weak models. Mid-tier model with good context > frontier model with sloppy window.
- **ACAM mapping:** rules-skills harness-context.sh hook is a form of context engineering (injects harness state at session start).

### [B9] "Context Engineering & Intent Specs: Implementation Guide" (Medium/Predict)
- **URL:** https://medium.com/predict/context-engineering-intent-specs-the-practitioners-implementation-guide-f92c6ff43d30
- **Relevance:** Interaction, Workflows
- **Key takeaway:** Four-layer pyramid: prompt → context → intent → specification engineering. AGENTS.md as industry standard (Linux Foundation, 2025). Living specs = specs agents update as they work.
- **ACAM mapping:** rules-skills state.json is a living spec. contract.json is specification engineering. Breadcrumbs are context engineering.

### [B10] "Top AI Agent Frameworks in 2026" (Towards AI)
- **URL:** https://pub.towardsai.net/top-ai-agent-frameworks-in-2026-a-production-ready-comparison-7ba5e39ad56d
- **Relevance:** Multi-agent
- **Key takeaway:** LangGraph = production standard (126k stars). CrewAI = fastest prototype. AutoGen 2.0 = enterprise async. Combination pattern: CrewAI for research → LangGraph for execution.
- **ACAM mapping:** rules-skills is not a framework — it's IDE-level config. But its evaluator-optimizer pattern mirrors framework concepts.

### [B11] "Agent Skills Explained" (Dev Genius)
- **URL:** https://blog.devgenius.io/agent-skills-explained-teaching-your-ai-assistant-new-tricks-c6ee66a632c4
- **Relevance:** Workflows, Configuration
- **Key takeaway:** 26 tools adopted standard format. .cursorrules has community momentum (awesome-cursorrules). Gradual migration to standards. Skills as cross-tool format emerging.
- **ACAM mapping:** Skills standardization is nascent. rules-skills adopted Cursor's format early.

---

## Academic & Research Papers

### [A1] SWE-bench / SWE-agent (Yang et al., 2024)
- **URL:** https://arxiv.org/abs/2310.06770 (SWE-bench), https://arxiv.org/abs/2405.15793 (SWE-agent)
- **Relevance:** Multi-agent, Workflows
- **Key takeaway:** Agent-Computer Interface (ACI) design is as important as model capability. SWE-agent achieves 12.5% → 19% with better interface. Scaffold architecture matters.
- **ACAM mapping:** ACI concept maps to rules-skills hooks (the interface between agent and environment).

### [A2] SWE-Adept: Two-Agent Framework (2026)
- **URL:** https://arxiv.org/html/2603.01327
- **Relevance:** Multi-agent
- **Key takeaway:** Localization agent + resolution agent. Agent-directed depth-first search for codebase navigation. Shared working memory with checkpoints. Git-based version control for branching/reverting.
- **ACAM mapping:** 2-agent model parallels planner/builder, but SWE-Adept agents are programmatic, not IDE subagents.

### [A3] BOAD: Hierarchical SWE Agents (IBM Research, ICLR 2026)
- **URL:** https://research.ibm.com/publications/boad-discovering-hierarchical-software-engineering-agents-via-bandit-optimization
- **Relevance:** Multi-agent
- **Key takeaway:** Automatic discovery of effective agent hierarchies via multi-armed bandit optimization. Monolithic designs force irrelevant context retention. Specialized sub-agents (localization, editing, validation) outperform single agents.
- **ACAM mapping:** Validates rules-skills role separation. But BOAD discovers roles automatically; rules-skills hardcodes 3 roles.

### [A4] SWE-Bench Pro: Long-Horizon Tasks (2025)
- **URL:** https://arxiv.org/pdf/2509.16941
- **Relevance:** Workflows
- **Key takeaway:** Long-horizon software tasks require multi-file editing, context management, iterative verification. Scaffold choice matters (SWE-agent vs Agentless).
- **ACAM mapping:** rules-skills harness is designed for exactly this: multi-file work with lifecycle tracking.

### [A5] Context Engineering (arxiv 2603.09619, 2026)
- **URL:** https://arxiv.org/pdf/2603.09619
- **Relevance:** Interaction
- **Key takeaway:** Formal treatment of context as agent's operating system. Five quality criteria. Four-layer hierarchy (prompt → context → intent → specification). No layer cancels the one below.
- **ACAM mapping:** Most theoretically grounded source. rules-skills operates at context + specification layers.

### [A6] Dissecting SWE-Bench Leaderboards (2026)
- **URL:** https://arxiv.org/html/2506.17208v2
- **Relevance:** Multi-agent, Workflows
- **Key takeaway:** 80 unique approaches across 178 submissions. Both agentic and non-agentic designs succeed. Claude 3.5 dominates as LLM. Three dimensions: repair workflow authoring, execution path autonomy, number of agents.
- **ACAM mapping:** Confirms multi-agent is not universally better. Some top performers are single-agent with good scaffolding.

---

## Comparable Tool Documentation

### [T1] Aider — Configuration docs
- **URL:** https://github.com/aider-ai/aider/blob/main/aider/website/docs/usage/conventions.md
- **Relevance:** Configuration
- **Key takeaway:** /read for loading conventions. Cached if prompt caching enabled. Example shows behavior change with/without CONVENTIONS.md.
- **ACAM mapping:** Aider's config is Basic-to-Intermediate: single conventions file, no scoping, no hooks, no skills.

### [T2] Aider — .aider.conf.yml
- **URL:** https://github.com/Aider-AI/aider/blob/main/aider/website/docs/config/aider_conf.md
- **Relevance:** Configuration
- **Key takeaway:** Full YAML config. Home → repo → cwd cascade. Model selection, repo map tokens, git settings, modes. Comprehensive but flat (no scoping, no lifecycle hooks).
- **ACAM mapping:** Aider's config is Intermediate on the runtime axis (priority cascade, repo map tuning) but Basic on enforcement (no hooks, no structural gates). Shows that config depth ≠ enforcement depth.

---

---

## Normie Baseline & Adoption Data (Phase 2)

### [N1] Repobility Research — "CLAUDE.md vs .cursorrules: The 50× Ratio"
- **URL:** https://repobility.com/blog/claudemd-vs-cursorrules-the-50-ratio/
- **Relevance:** Configuration (baseline data)
- **Key takeaway:** In a corpus of 128,000+ repos (Opus 4.7 training data bias toward Claude users): CLAUDE.md = 2,804 repos, AGENTS.md = 999, .cursorrules = 56, .windsurfrules = 25. Ratio CLAUDE.md:cursorrules = 50:1. Even combining all non-Claude AI configs = 107 repos.
- **ACAM mapping:** Quantifies the adoption gap. Cursor-specific config (.mdc) is a small fraction of the overall landscape. Bias noted: corpus skews toward Claude users.

### [N2] "Beyond the Prompt: An Empirical Study of Cursor Rules" (MSR 2026)
- **URL:** https://arxiv.org/html/2512.18925v2
- **Relevance:** Configuration (normie baseline), empirical data
- **Key takeaway:** 401 repositories with .mdc files (Sourcegraph starred repos). Avg 4.68 .mdc files/repo (max 56). 93.27% follow .cursor/ directory recommendation. Avg file: 462.67 lines. Avg repo stars: 7,064 — heavy selection bias toward active high-quality projects. LLM-specific directives have "relatively low adoption." Five content themes: Conventions, Guidelines, Project Information, LLM Directives, Examples.
- **ACAM mapping:** Primary empirical source for "what practitioners actually do." The 401-repo sample = top few percent by quality; real normie adoption is lower. rules-skills 16 files = 3.4× above this sample average.

### [N3] "I checked 3,689 .cursorrules files from public repositories" (Neura Market / r/cursor)
- **URL:** https://www.neura.market/directories/cursor/posts/reddit-1ieuwyi
- **Relevance:** Configuration (normie baseline)
- **Key takeaway:** Informal community scan (Feb 2025): 3,698 .cursorrules files across all GitHub. First one appeared April 2024. Most reused file: TypeScript template (21 repos). Longest: 254,439 chars (7,000 tokens). Top starred repos with .cursorrules: gpt-researcher (16k stars), Wox (25k stars).
- **ACAM mapping:** Absolute count of 3,698 across GitHub confirms .cursorrules is rare. Most are template copies. By 2026, this format is legacy.

### [N4] Windsurf — ".windsurfrules Configuration" (The Prompt Shelf, 2026)
- **URL:** https://thepromptshelf.dev/blog/windsurfrules-complete-guide-2026/
- **Relevance:** Configuration (comparable setup)
- **Key takeaway:** Primary config = `.windsurfrules` (single plain Markdown, no frontmatter). Advanced = `.windsurf/rules/` with YAML frontmatter and activation modes. 6,000-12,000 character limit. Common anti-pattern: copy file between .windsurfrules/.cursorrules/CLAUDE.md without customizing. Creator tutorial: "I personally don't rely on these rules files" — even expert users skip persistent config.
- **ACAM mapping:** Windsurf is Basic-Intermediate on Configuration. Single-file default is simpler than rules-skills. No hooks, no lifecycle. Expert behavior ("don't use rules files") is a signal for lazy-loading argument.

### [N5] Linux Foundation / AAIF — AGENTS.md Announcement
- **URL:** https://www.linuxfoundation.org/press/linux-foundation-announces-the-formation-of-the-agentic-ai-foundation
- **Relevance:** Configuration (standard), Interaction
- **Key takeaway:** AGENTS.md released by OpenAI Aug 2025, donated to Linux Foundation Dec 2025. 60,000+ open-source projects. Supported by Cursor, Codex, Copilot, Devin, Gemini CLI, Windsurf, Zed, Factory, Jules. Reduces agent-generated bugs 35-55% in projects with detailed files. Improves task success ~4%. OpenAI repo has 88 nested AGENTS.md files.
- **ACAM mapping:** AGENTS.md is the 2026 industry standard for Configuration. rules-skills has no AGENTS.md — a gap against the baseline. Not tool-specific (.mdc is Cursor-only); AGENTS.md is universal.

---

## Challenging Sources — Against Complex Configuration (BC2, Phase 2)

### [S1] Vadim Alakhverdov — "Why Most AI Agent Architectures Are Overengineered"
- **URL:** https://vadimall.com/posts/Why-most-ai-agent-architectures-are-overengineered
- **Relevance:** Multi-agent (challenge), Workflows (challenge)
- **Key takeaway:** Single-loop agent with good tools beats multi-agent orchestration for most tasks. Multi-agent justified ONLY for: parallel execution over distinct data, long-running workflows needing persistent state, adversarial validation (same model = blind spots). ~20 tool threshold: below that, split agents add routing complexity with no benefit.
- **ACAM mapping (challenge):** Evaluator-as-adversary is explicitly justified. Planner role is less justified. rules-skills 3-role model is ~50% justified by this analysis. Directly challenges "multi-agent = always Advanced."

### [S2] Bechir Trabelsi — "Stop Bloated Agent Prompts: Lazy-Loaded Procedural Policy" (Medium, Apr 2026)
- **URL:** https://bechirtr97.medium.com/stop-bloated-agent-prompts-a-pattern-i-call-lazy-loaded-procedural-policy-b6ade44dd1aa
- **Relevance:** Configuration (challenge), Workflows (challenge)
- **Key takeaway:** System prompt = constitutional layer (invariants only). Scenario-specific rules = procedural tools loaded on demand. Pattern: `get_refund_rules()`, `get_escalation_rules()` — agent calls when context requires. "The system prompt owns invariants; tools own conditionals." Lazy-Loaded Procedural Policy (LLPP) pattern.
- **ACAM mapping (challenge):** rules-skills' 8 alwaysApply rules — including 230-line adversarial_harness.mdc — is anti-pattern by LLPP standards. Advanced Configuration may mean FEWER always-on rules, not more. Our 4 agent-requested rules are the right approach; the 8 alwaysApply may be over-eager.

### [S3] Open Innovation AI — "The Case for Simpler AI Agents"
- **URL:** https://openinnovation.ai/the-case-for-simpler-ai-agents/
- **Relevance:** Workflows (challenge), Configuration (challenge)
- **Key takeaway:** Agents with basic primitives (bash, file access, one execution tool) outperform over-engineered predecessors in recent case studies. "Don't load every tool definition — let the agent search." "Don't pre-filter — let the model grep." "The future isn't more sophisticated scaffolding. It's having the confidence to delete most of it." Guardrails built for weak 2023 models may now constrain 2026 models.
- **ACAM mapping (challenge):** Structural enforcement was designed for less capable models. As model capability improves, the value of hooks (contract-gate, verify-harness) may decrease. feat-16 ablation is the right response — measure whether rules help or constrain.

### [S4] Sébastien d'Aout — "Heavy AI Agents Are an Anti-Pattern: Why Fewer Agents With More Skills Wins"
- **URL:** https://www.dsebastien.net/heavy-ai-agents-are-an-anti-pattern-why-fewer-agents-with-more-skills-wins/
- **Relevance:** Workflows (partial support), Configuration (challenge)
- **Key takeaway:** "Agents = rules of the game (small, stable). Skills = toolbox (many, evolvable)." Receptionist pattern: agent with one rule (route) and zero embedded capability. Many specialized agents = anti-pattern. One lean agent + rich skill library beats specialized agent roster. Skills deferred until needed = lazy loading.
- **ACAM mapping:** Partially validates rules/skills separation. Challenges: our agent identity is NOT lean (230-line always-on rule). Moving adversarial_harness.mdc to a skill would align with this principle. The 14 skills in library/ are the correct pattern; the 8 alwaysApply rules are the violation.

---

## Devin Comparable Documentation (BC4, Phase 2)

### [D1] Devin — Hooks Documentation
- **URL:** https://docs.devin.ai/cli/extensibility/hooks/overview
- **Relevance:** Workflows, Configuration (comparable)
- **Key takeaway:** Devin CLI hooks are Claude Code-compatible. Reads from `.devin/hooks.v1.json`, `.devin/config.json`, `.claude/settings.json` (fallback). Events: PreToolUse (can block via exit 2), PostToolUse, UserPromptSubmit, PermissionRequest, SessionStart, SessionEnd. regex matcher on tool_name. Also supports prompt hooks and agent hooks.
- **ACAM mapping:** Devin's hooks are structurally equivalent to Claude Code's — and more capable than Cursor's. PreToolUse blocking is the same structural enforcement pattern as rules-skills contract-gate. Key difference: Devin's hook format is open (cross-tool) while Cursor's is proprietary.

### [D2] Devin — AGENTS.md Documentation
- **URL:** https://docs.devin.ai/onboard-devin/agents-md
- **Relevance:** Configuration (comparable)
- **Key takeaway:** Devin reads AGENTS.md from project root before starting coding. Primary project context format. Also reads CLAUDE.md, .cursorrules, .windsurfrules via `read_config_from` config. AGENTS.md cannot be disabled; always-on. Example shows setup commands + code style + testing guidelines + project structure + development workflow.
- **ACAM mapping:** Devin's primary config is AGENTS.md (open standard). rules-skills' primary config is .mdc (Cursor-specific). Devin has broader tool compatibility by default.

### [D3] Devin — Configuration File Reference
- **URL:** https://docs.devin.ai/cli/reference/configuration/config-file
- **Relevance:** Configuration (comparable)
- **Key takeaway:** `.devin/config.json` with: permissions (allow/deny/ask lists), MCP servers, sandbox network filtering (allowed_domains, denied_domains, network_mode), `read_config_from` (Cursor/Windsurf/Claude fallback cascade). Blueprints (separate YAML) for environment snapshots.
- **ACAM mapping:** Devin has explicit permission model (allow/deny/ask) and network sandboxing — capabilities rules-skills lacks entirely. The blueprint system (reproducible VM snapshots) has no rules-skills equivalent.

### [D4] Devin — Lifecycle Hooks Events
- **URL:** https://docs.devin.ai/cli/extensibility/hooks/lifecycle-hooks
- **Relevance:** Workflows (comparable)
- **Key takeaway:** Events: PreToolUse, PostToolUse, PermissionRequest, UserPromptSubmit, PostCompaction, SessionStart, SessionEnd. Regex matcher on tool_name. Non-tool events: no tool_name, use empty matcher. Supports `mcp__servername__.*` pattern for MCP tools.
- **ACAM mapping:** More granular lifecycle hooks than Cursor (no PostCompaction or PermissionRequest in Cursor). rules-skills' 10 hooks cover 4 lifecycle events; Devin covers 7.

---

---

## Phase 3 Sources — Configuration Dimension

### [E1] Anthropic — "System Prompts" (Claude API Documentation)

- **URL:** https://docs.anthropic.com/en/docs/build-with-claude/system-prompts
- **Relevance:** Configuration (rules as system prompts, failure modes, layering)
- **Key takeaway:** System prompt establishes agent identity, capabilities, and constraints before any user turn. Five root causes of poor system prompt performance: vague instructions, over-reliance on model inference, conflicting instructions, missing edge cases, poor formatting. All apply verbatim to `.mdc` rules.
- **ACAM mapping:** Rules are system prompt content injected by the IDE. "Basic" = poor system prompt hygiene. "Advanced" = conflict-detected, effectiveness-measured, feedback-derived policies. Validates that rule quality analysis is system prompt quality analysis.

### [E2] GitHub — "Adding custom instructions for GitHub Copilot" (Official documentation)

- **URL:** https://docs.github.com/en/copilot/customizing-copilot/adding-custom-instructions-for-github-copilot
- **Relevance:** Configuration (platform comparison, four-layer config model, conflict handling)
- **Key takeaway:** Organization-level instructions → repository-level (`.github/copilot-instructions.md`) → personal instructions. Conflicts produce "unpredictable behavior." Instructions inherit across scopes. The four-layer config model is universal: no platform resolves inter-rule conflicts deterministically.
- **ACAM mapping:** Confirms that the layered config model and conflict resolution gaps are not Cursor-specific — they are universal across Cursor, Claude Code, Copilot, and Devin. Advanced Configuration requires tooling to detect conflicts; no platform currently provides this out-of-the-box.

### [E3] Reflexion: Language Agents with Verbal Reinforcement Learning (Shinn et al., 2023)

- **URL:** https://arxiv.org/abs/2303.11366
- **Relevance:** Configuration (iterative rule refinement, effectiveness measurement), Workflows (self-reflection loops)
- **Key takeaway:** Agents that receive verbal feedback on task outcomes and update behavioral policies via episodic memory outperform static-instruction agents on AlfWorld, HotpotQA, and HumanEval. Self-reflection loops enable agents to improve without gradient updates. Applied to config: rules iteratively refined via eval feedback outperform first-principles rules.
- **ACAM mapping:** Validates the ACAM "Advanced" Configuration criterion of "quantified effectiveness data." Static rules (written once, no feedback loop) are Intermediate. Rules updated iteratively from ablation results (feat-16 pattern) constitute the Reflexion approach applied to IDE config.

---

---

## Phase 4 Sources — Workflows Dimension

### [F1] ReAct: Synergizing Reasoning and Acting in Language Models (Yao et al., NeurIPS 2022 Workshop / ICLR 2023)

- **URL:** https://arxiv.org/abs/2210.03629
- **Relevance:** Workflows (agentic loop patterns, reasoning traces, plan-act-observe), Interaction
- **Key takeaway:** Interleaved Thought-Action-Observation cycles outperform pure reasoning (chain-of-thought) or pure acting on HotpotQA, AlfWorld, WebShop, and Fever tasks. Explicit reasoning traces make intermediate agent states observable, enabling diagnosis of failures and recovery from errors. The trace is the mechanism by which workflow failures become diagnosable. Without it, failures are opaque and unrecoverable.
- **ACAM mapping:** Validates "traced execution" as an Advanced Workflows criterion. breadcrumbs.jsonl is a human-authored reasoning trace at the session level (not per-turn). ReAct traces are more granular. Also validates the plan-act-observe structure as the canonical agentic loop against which rules-skills' plan-gate-contract-build-evaluate should be compared: the gate and contract steps are additions that add adversarial rigor at the cost of per-task latency.

### [F2] Inspect AI — Open-Source LLM Evaluation Framework (UK AI Safety Institute, 2024)

- **URL:** https://inspect.ai-safety-institute.org.uk/
- **Relevance:** Workflows (eval regression suites, structured eval architecture, CI integration)
- **Key takeaway:** Reference architecture for LLM/agent evaluation: Task (input + expected behavior), Solver (agent under test), Scorer (quality measurement function), Eval log (structured trace for regression). Eval suites should run as CI tasks producing structured logs comparable across runs. Used by the UK government for frontier model safety evaluation and by the research community for benchmark reproduction.
- **ACAM mapping:** Architecture is isomorphic to rules-skills' eval pipeline: scenarios (Tasks), session_runner (Solver), session_judge (Scorer), eval report (Eval log). Independently validates the pipeline architecture and confirms "eval regression suite" as correct ACAM Advanced vocabulary. Gap: rules-skills runs eval manually; Inspect AI targets automated CI integration as the defining Advanced characteristic.

### [F3] Berkeley Function Calling Leaderboard (BFCL) (Yan et al., 2024 — UC Berkeley / Gorilla Project)

- **URL:** https://gorilla.cs.berkeley.edu/leaderboard.html
- **Relevance:** Workflows (skill activation measurement, tool selection accuracy, description quality effects)
- **Key takeaway:** Benchmarks 150+ LLMs on 17 categories of function/tool calling (simple, multiple, parallel, nested, REST API, irrelevance detection). Accuracy ranges 30-95% based on model and scenario complexity. AST verification confirms argument correctness beyond function name selection. Critical finding: tool description quality directly drives routing accuracy — vague, overlapping, or keyword-sparse descriptions cause systematic misrouting across all models regardless of capability tier.
- **ACAM mapping:** Directly maps to IDE skill routing: SKILL.md `description` field is the function signature for skill selection. BFCL's description-quality finding means the 14 SKILL.md descriptions are a critical quality surface that has never been measured. The "zero skill_activation eval coverage" gap maps to a well-studied measurement problem with known methodology. chore-skill-scenarios should adopt BFCL-inspired structure: seed task, correct skill target, irrelevance detection, argument correctness check.

---

---

## Phase 5 Sources — Multi-agent Dimension

### [G1] AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation (Wu et al., Microsoft Research, 2023)

- **URL:** https://arxiv.org/abs/2308.08155
- **Relevance:** Multi-agent (orchestration, role separation, group chat, evaluator-optimizer pattern)
- **Key takeaway:** Agents are conversable entities with system prompts and conversation scope. GroupChatManager routes turns automatically — shared conversation history is the default, context isolation is opt-in. Multi-agent enables parallel tool execution and role specialization that single-agent cannot achieve. Includes teacher-student (evaluator-optimizer) and coding agent patterns.
- **ACAM mapping:** AutoGen's GroupChatManager is the canonical programmatic orchestration primitive — what feat-13 would have implemented. The shared-history default validates rules-skills' prompt-level isolation as a step above AutoGen's baseline. The evaluator-optimizer pattern in AutoGen is structurally equivalent to the builder/evaluator pair.

### [G2] OpenAI Swarm (GitHub Repository, OpenAI, 2024)

- **URL:** https://github.com/openai/swarm
- **Relevance:** Multi-agent (lightweight orchestration, handoff patterns, context isolation defaults)
- **Key takeaway:** Minimal framework intentionally labeled "educational, not production." Agents: instructions + tools + handoff functions. Handoffs transfer control to a new agent with a clean conversation history by default — context isolation is the default. Represents the simplicity end of the orchestration spectrum. Self-described reference implementation of multi-agent concepts, not a production recommendation.
- **ACAM mapping:** Swarm's clean-handoff default (fresh context per agent transition) is the contrast to rules-skills' prompt-level isolation. Advanced Multi-agent would implement explicit context packages (state.json + contract.json) rather than full history inheritance — Swarm shows this is achievable and lightweight. The educational framing supports S1's caution against over-engineering.

### [G3] "LLM Powered Autonomous Agents" (Lilian Weng, OpenAI Research, 2023)

- **URL:** https://lilianweng.github.io/posts/2023-06-23-agent/
- **Relevance:** Multi-agent (memory isolation, role separation, agent taxonomy), Interaction
- **Key takeaway:** Taxonomy of autonomous agent components: planning (CoT, reflection), memory (in-context, external, long-term), tools (execution), action spaces. Key multi-agent finding: "agents in a shared environment will inevitably read each other's outputs — the question is whether the reading is intentional (handoff) or accidental (shared memory/files)." Distinguishes task decomposition (subgoal) from role decomposition (specialization). 10k+ citations as of 2026 — most-cited agent architecture survey.
- **ACAM mapping:** Weng's intentional-vs.-accidental reading distinction maps to the evaluator context isolation gap: rules-skills evaluators intentionally read implementation outputs (correct) but may accidentally read builder reasoning history (unmeasured). The planning/memory/tools/action taxonomy maps to ACAM dimensions: Configuration = memory; Workflows = tools + planning; Multi-agent = role decomposition; Interaction = prompt engineering.

---

---

## Phase 6 Sources — Interaction Dimension

### [H1] "Context Engineering" (Andrej Karpathy, 2025)

- **URL:** https://karpathy.bearblog.dev/context-engineering/
- **Relevance:** Interaction (context engineering definition, right-information-at-right-time), Configuration
- **Key takeaway:** "Context engineering is the delicate art and science of filling the context window with just the right information at just the right time." Four strategies: write (create documents), select (retrieve relevant), compress (summarize), isolate (separate contexts). Reframes practitioner's job from prompt craft to information supply chain engineering. Most-cited practitioner crystallization of the academic context engineering paper [A5].
- **ACAM mapping:** Validates "structured context delivery" as an Advanced Interaction criterion. harness-context.sh implements write+select. Compress (compaction) and full isolate (context-window isolation, not just file-path restriction) are not implemented — two specific sub-gaps within the context engineering Advanced criterion.

### [H2] Simon Willison — AI Coding Assistants: Field Notes (Blog, 2025-2026)

- **URL:** https://simonwillison.net/tags/ai-coding-assistants/
- **Relevance:** Interaction (simplicity-first, structural constraints > templates), Configuration (challenge)
- **Key takeaway:** "The most durable improvements to AI coding workflows are structural constraints baked into the development environment — not prompt templates." "I've never found a mega .cursorrules file that improved my productivity." Advocates minimal rule sets, contextual prompting, and measuring outcomes before adding rules. Real-world experience across Cursor, Claude, and Aider.
- **ACAM mapping:** BC2 source challenging complex Interaction config. The Interaction-dimension version of S3's simpler-is-better argument. The 8 alwaysApply rules in rules-skills are Willison's target — each needs measurement evidence to justify its place. Validates that measuring rule effectiveness before adding more rules is Advanced practice, not gold-plating.

### [H3] LangSmith — LLM Evaluation and Observability Platform (LangChain, 2024-2026)

- **URL:** https://docs.smith.langchain.com/
- **Relevance:** Interaction (measured interaction patterns, prompt A/B testing, session metrics), Workflows
- **Key takeaway:** Production platform for LLM observability: prompt version tracking with A/B comparison, session traces (every tool call + response), quality scores over time, conversation efficiency (turns to completion), retrieval quality, latency. "Prompt playgrounds" for variant testing. Used by production teams to answer "did my prompt change improve outcomes?"
- **ACAM mapping:** Reference implementation of "Measured interaction patterns" Advanced Interaction criterion. rules-skills eval pipeline (session_runner + session_judge) is equivalent to LangSmith's evaluation layer — missing prompt versioning, A/B comparison, and real-session observability. Two specific extensions needed: (1) prompt variant parameterization in session_runner.py (analogous to --ablate-rule), (2) real-session telemetry alongside synthetic eval.

---

## To Add in Subsequent Phases

- [ ] AGENTS.md specification (Linux Foundation) deep-dive — Configuration (Phase 7 synthesis)
