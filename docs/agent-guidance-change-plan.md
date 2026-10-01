# Change plan

Decisions for the library edits. The practice brief and the gap assessment stay as the research record. This file matches what that cycle implements.

## Boundary

### In scope

Edits to the always-on rules, `prompt-coaching`, idle harness context, the evaluator's `spike-`/`docs-` contract bar, and a short same-session section in the harness skill.

### Out of scope

This plan excludes flipping `alwaysApply` on `library/cursor/rules/planning_discipline.mdc`. It excludes a token measurement. It excludes deleting skills and publishing a catalog. It excludes commits until asked.

## Do not change

- do not change `library/cursor/hooks.json`. The `failClosed` write gates stay.
- do not change `library/cursor/rules/planning_discipline.mdc`. It stays `alwaysApply: false`. The two Cursor pages still disagree on whether that flag saves tokens.
- do not change `library/cursor/agents/planner.md`. It still stops after a short plan and does not build.
- do not change `library/cursor/rules/python_ml.mdc`. Globs and `alwaysApply: false` stay.
- do not change `library/cursor/skills/svg-edit/SKILL.md`. The `paths` limit to SVG files stays.
- do not change `disable-model-invocation: true` on `library/cursor/skills/adversarial-harness/SKILL.md`. The procedure stays opt-in.

## Change

- `library/cursor/rules/agent_behavior.mdc` — Remove "One file per edit chunk". "No unnecessary confirmations" means do not repeat a confirmation the user already gave this session, and that line does not cancel the one required question.
- `library/cursor/rules/autonomous_execution.mdc` — This rule owns the one question. Act when the message names an outcome and a target (a file, a command, or the next step already named). Ask once, with one proposed interpretation, when there is no outcome ("fix it", "make it better") or no boundary ("refactor everything", "improve performance"). If the user picks another step, name the indicated step in one sentence and do what they asked. Commit, push, and destructive actions still wait for an explicit yes.
- `library/cursor/skills/prompt-coaching/SKILL.md` — Remove act-then-tip. If the always-on rule already asked this turn, this skill does not ask again and does not append a tip. Mode 3 decomposition is a deliverable structure, not a second round.
- `library/cursor/hooks/harness-context.sh` — When no task is `pending`, `building`, or `evaluating`, inject the one-line free-default message. An active task still prefetches the context package because the model will use the contract and criteria. This chooses just-in-time for the idle case. The practice brief did not pick a winner between pre-fetch and just-in-time; the choice is only for idle sessions.
- `library/cursor/agents/evaluator.md` — `spike-` and `docs-` still skip a runtime behavioral criterion. They do not pass on headings and `test -f` alone. At least one criterion must name a source line and fail if the deliverable contradicts it. `chore-` stays file-interrogation only.
- `library/cursor/skills/adversarial-harness/SKILL.md` — Same-session re-check is the negotiated contract. A design audit of an artifact this session wrote belongs in a new thread, with the artifact and the sources and without the author's suspected findings. If the user insists, the off-path alert applies and the prompt still omits that list. These tasks do not skip the evaluator.

## Sequence

The edits land in this order. This document records the decisions; the library files hold the behavior.

1. Edit `library/cursor/rules/agent_behavior.mdc` and `library/cursor/rules/autonomous_execution.mdc` together, so the question has one owner and the old confirmation line does not cancel it.
2. Edit `library/cursor/skills/prompt-coaching/SKILL.md` so it cannot ask a second time or add a tip.
3. Edit `library/cursor/hooks/harness-context.sh` and cover idle versus `building` with a hook test.
4. Edit `library/cursor/agents/evaluator.md` and `library/cursor/skills/adversarial-harness/SKILL.md`. `spike-` and `docs-` tasks still go through negotiation and grading. They do not skip a separate evaluator subagent.

## Reconciliation

An ambiguous goal gets that one question before any edit, while an already-specified command does not. The question proposes one interpretation and waits. The question is not followed by a coaching tip or a second round. `library/cursor/rules/autonomous_execution.mdc` is the only owner. `library/cursor/skills/prompt-coaching/SKILL.md` does not ask again after that rule has asked.
