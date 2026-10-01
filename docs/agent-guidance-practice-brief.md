# How agents should be guided

Retrieved 2026-10-01. This spike records what a tight set of sources actually says. It does not grade this repository.

## Boundary

### In scope

This brief compares Cursor official guidance with a bounded set of repos, articles, and talks: the Cursor rules, skills, and hooks references; the Cursor Learn chapter on customizing agents; the humanlayer/12-factor-agents repository (the written form of that project's conference talk, not the video); the anthropics/skills repository; Anthropic's context-engineering essay; and Claude Code's best-practices page.

### Out of scope

Excluded class: a survey of every agent framework, social-media threads, and slide decks that never name a mechanism. This spike also excludes library edits to rules, skills, hooks, or harness artifacts.

## Sources

- https://cursor.com/docs/rules — retrieval 2026-10-01 — verified
- https://cursor.com/docs/skills — retrieval 2026-10-01 — verified
- https://cursor.com/docs/hooks — retrieval 2026-10-01 — verified
- https://cursor.com/learn/customizing-agents — retrieval 2026-10-01 — verified
- https://github.com/humanlayer/12-factor-agents — retrieval 2026-10-01 — verified
- https://github.com/anthropics/skills — retrieval 2026-10-01 — verified
- https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents — retrieval 2026-10-01 — verified
- https://code.claude.com/docs/en/best-practices — retrieval 2026-10-01 — verified
- https://github.com/humanlayer/12-factor-agents/blob/main/content/factor-07-contact-humans-with-tools.md — retrieval 2026-10-01 — verified
- https://github.com/humanlayer/12-factor-agents/blob/main/content/factor-10-small-focused-agents.md — retrieval 2026-10-01 — verified
- https://github.com/humanlayer/12-factor-agents/blob/main/content/appendix-13-pre-fetch.md — retrieval 2026-10-01 — verified

## Rules

Cursor's rules reference keeps a project rule in a file whose frontmatter decides inclusion, and it tells authors to stay under 500 lines, to skip rare edge cases, and to point at files instead of pasting them.

`alwaysApply`

[Cursor rules](https://cursor.com/docs/rules)

The Learn chapter describes rules as short conventions the agent should always know, and it says too many of them spend context and can confuse the agent, so occasional guidance belongs in a skill.

`.cursor/rules/`

[Customizing agents](https://cursor.com/learn/customizing-agents)

Claude Code loads project instructions on every session, so each line should stay only if deleting it would cause a mistake, and sometimes-relevant workflows should be skills instead.

`/init`

[Claude Code best practices](https://code.claude.com/docs/en/best-practices)

## Skills

Cursor discovers a skill from a folder, shows the agent the description, and loads the body only when the skill is relevant or explicitly invoked.

`disable-model-invocation`

[Cursor skills](https://cursor.com/docs/skills)

The same reference says to keep the main file focused and to put long material in a references directory, because those files are read only when needed.

`paths`

The public skills repository uses the same package shape: one folder, one instruction file, and frontmatter limited to a name plus a description, with the body loaded dynamically for a specialized task.

`SKILL.md`

[anthropics/skills](https://github.com/anthropics/skills)

## Hooks

Cursor hooks are scripts declared in a project file. They run at named points in the agent loop and may observe, block, or change behavior, which is a harder gate than text added to the prompt.

`beforeSubmitPrompt`

[Cursor hooks](https://cursor.com/docs/hooks)

One event runs before a prompt is submitted, another runs when the context window is compacted, and another fires for every tool. A rule cannot refuse a shell command; these events can.

`preCompact`

## Clarify before acting

The 12-factor guide models a human question as a tool result, not as free-text chatter. The loop saves state, notifies a person, and returns, so the model does not keep spending turns while it guesses.

`request_human_input`

[Factor 7](https://github.com/humanlayer/12-factor-agents/blob/main/content/factor-07-contact-humans-with-tools.md)

Claude Code's best-practices page separates exploration from edits. Plan mode reads and answers without writing, and the page says to skip that step when the change is small enough to describe in one sentence.

`claude --permission-mode plan`

[Claude Code best practices](https://code.claude.com/docs/en/best-practices)

Cursor's skill template includes an instruction to use the ask-questions tool when requirements are still unclear, so clarification is a step inside a workflow rather than a permanent chat style.

`SKILL.md`

[Cursor skills](https://cursor.com/docs/skills)

## Token cost of long loops

Anthropic describes context rot: as the window grows, recall gets worse, so the useful move is the smallest set of high-signal tokens, then a summary pass, notes, or a subagent that returns a short summary.

`compaction`

[Effective context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)

The Learn chapter states the cost split directly. Rules occupy context on every conversation. A skill spends its full text only when it is invoked.

`SKILL.md`

[Customizing agents](https://cursor.com/learn/customizing-agents)

The small-agent factor caps a focused agent at a handful of steps so the window does not become the place where the model gets lost.

`factor-10-small-focused-agents.md`

[Factor 10](https://github.com/humanlayer/12-factor-agents/blob/main/content/factor-10-small-focused-agents.md)

Claude Code's best-practices page says the window fills with every message, file read, and command output, and that performance drops as it fills, which is why always-on instructions have to stay short.

`/context`

[Claude Code best practices](https://code.claude.com/docs/en/best-practices)

## Tensions

[Cursor Learn](https://cursor.com/learn/customizing-agents) says rules stored in `.cursor/rules/` are seen at the start of every conversation.

[Cursor rules](https://cursor.com/docs/rules) says a rule is always included only when `alwaysApply` is true, and a rule with that flag false and no description or globs is included only when someone `@`-mentions it.

[12-factor appendix](https://github.com/humanlayer/12-factor-agents/blob/main/content/appendix-13-pre-fetch.md) says that if you already know which tool the model will call, call it deterministically and put the result in the prompt instead of spending a round trip.

[Context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) says to keep lightweight identifiers and load data with tools at runtime rather than pre-processing all relevant data up front.

This spike does not choose a winner.
