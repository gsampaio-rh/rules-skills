# Gap assessment

Judged on 2026-10-01 against `docs/agent-guidance-practice-brief.md`. Line counts below come from `wc -l` on that date.

## Boundary

### In scope

This assessment judges the current rules, skills, hooks, agents, and harness process in this repository against the practice brief. Each reading is keep, change, or undecided.

### Out of scope

A rewrite of the library, and any survey beyond the practice brief's source set. This assessment excludes library edits to rules, skills, hooks, or harness artifacts.

## Method

The practice brief headings Rules, Skills, Hooks, Clarify before acting, Token cost of long loops, and Tensions are the only standard used here. A reading is keep when the file already matches a named mechanism in that brief, change when it conflicts with one, and undecided when two brief sources disagree about whether the file is costly.

## Specificity

Two rules are `alwaysApply: true`: `library/cursor/rules/autonomous_execution.mdc` (27 lines) and `library/cursor/rules/agent_behavior.mdc` (16 lines). The other nine rule files are `alwaysApply: false`. `library/cursor/rules/python_ml.mdc` also sets globs for notebooks and experiments, so it attaches to matching files rather than every chat.

The verdict is change for `library/cursor/rules/agent_behavior.mdc` under the practice brief heading Rules, because "One file per edit chunk" is an always-on editing procedure of the kind that page says to leave out of rules that ride on every conversation.

The verdict is keep for `library/cursor/rules/python_ml.mdc` under the practice brief heading Rules, because `alwaysApply: false` plus globs matches the rules reference, where a rule is not inserted until a matching file is in context.

`library/cursor/skills/adversarial-harness/SKILL.md` is 206 lines, with another 352 lines under its references directory. That is specific, and it is the right layer for a rare workflow. The verdict on the invocation flag is keep under the practice brief heading Skills, because `disable-model-invocation: true` keeps that procedure out of chats that did not opt in.

## Clarify before acting

The verdict is change for `library/cursor/rules/autonomous_execution.mdc` under the practice brief heading Clarify before acting. The file is always on, and it says not to ask permission for routine operations. It does require a question before commit, push, and destructive actions. It does not require one when the goal or the scope is still ambiguous, so an underspecified task is treated like a lint command.

`library/cursor/skills/prompt-coaching/SKILL.md` does contain a clarify-before-acting mode, and a line that says to ask one focused question. The verdict is change under the practice brief heading Clarify before acting, because the default mode completes the work and then adds a coaching tip, and because `disable-model-invocation` is false while the don't-ask rule is always present. The question loses to the rule that is already in context.

The verdict is keep for `library/cursor/agents/planner.md` under the practice brief heading Clarify before acting. That agent writes a short plan and is told to stop, and not to build. That is one bounded checkpoint, closer to plan mode than to a long interview.

## Token cost

The verdict is change for `library/cursor/hooks/harness-context.sh` under the practice brief heading Token cost of long loops. The early exit that says to work freely runs only when both state and contract are missing. This repository commits `.harness/state.json`, so every session injects the context package, including sessions whose tasks are all verified or committed.

The verdict is change for `library/cursor/skills/adversarial-harness/SKILL.md` under the practice brief heading Token cost of long loops. Opt-in is right, and the body is still a four-role loop per task: planner, contract negotiation, build, and evaluator. The small-agent source in the brief caps a focused run at a short step count so the window does not fill with process. A docs spike pays that full loop.

The verdict is keep for `library/cursor/hooks.json` under the practice brief heading Hooks. `beforeSubmitPrompt` and `preToolUse` call scripts, and the write gate sets `failClosed`. That is a block at a named event, not another paragraph of always-on instructions. `library/cursor/skills/svg-edit/SKILL.md` is keep under the practice brief heading Skills: `paths` limits it to SVG files, so the procedure is not loaded for unrelated work.

The verdict is undecided for `library/cursor/rules/planning_discipline.mdc` under the practice brief heading Tensions. The file is `alwaysApply: false`. The Cursor rules reference says that flag keeps it out of unrelated chats. The Cursor Learn chapter says rule files are seen at the start of every conversation. The brief does not choose a winner, so this file's real token cost is undecided.

## Readings

- `library/cursor/rules/agent_behavior.mdc` — change — Rules
- `library/cursor/rules/python_ml.mdc` — keep — Rules
- `library/cursor/rules/autonomous_execution.mdc` — change — Clarify before acting
- `library/cursor/skills/prompt-coaching/SKILL.md` — change — Clarify before acting
- `library/cursor/agents/planner.md` — keep — Clarify before acting
- `library/cursor/hooks/harness-context.sh` — change — Token cost of long loops
- `library/cursor/skills/adversarial-harness/SKILL.md` — change — Token cost of long loops
- `library/cursor/hooks.json` — keep — Hooks
- `library/cursor/skills/svg-edit/SKILL.md` — keep — Skills
- `library/cursor/skills/adversarial-harness/SKILL.md` — keep — Skills
- `library/cursor/rules/planning_discipline.mdc` — undecided — Tensions
