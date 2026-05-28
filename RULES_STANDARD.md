# Rules Authoring Standard

Internal quality contract for every `.mdc` file in `library/cursor/rules/`. Not loaded by the agent.

## Frontmatter Contract

Every rule must use one of these valid configurations. No other combinations are allowed.

| Configuration | When to use | Example |
|---|---|---|
| `alwaysApply: true` | Universal rules that apply to every task | Coding standards, agent behavior, security |
| `globs: "<pattern>"` + `alwaysApply: false` | File-type-specific rules | Python patterns on `*.py`, test patterns on `**/test*.py` |
| `description: "<keywords>"` + `alwaysApply: false` (no globs) | Agent-intelligently-loaded rules | Design principles loaded when UI work is detected |

**Never** leave both `globs` and `alwaysApply` empty — the rule is effectively dead.

## Frontmatter Template

```markdown
---
description: One-line for intelligent matching. Include keywords the agent would search for.
globs: "*.py, tests/**/*.py"
alwaysApply: false
---
```

## Sizing

- Individual rules: **under 200 lines**
- Total always-on (`alwaysApply: true`) budget: **under 2000 tokens** combined
- If a rule exceeds 200 lines, split it or move procedural content to a skill

## Tone

- Direct, imperative, opinionated
- "Use X" not "Consider using X"
- State the WHY briefly after each point when it's not obvious
- Practitioner voice: write as someone who has done this 100 times

## Structure

```markdown
---
description: <keywords for matching>
globs: <file patterns>
alwaysApply: <true/false>
---

# Rule Title

## Section Name
- **Bold label**: Concise instruction
- **Another point**: With brief rationale when non-obvious
```

- Lead with the most impactful points
- Include both DO and DON'T examples where helpful (use checkmark/cross format)
- Group related instructions under clear section headings

## Content Guidelines

- No procedural workflows — those are skills
- No project-type-specific guidance — those are skills
- Reference files, don't copy their contents (prevents staleness)
- Don't duplicate what linters already enforce
- Each section must have at least one concrete, actionable instruction
- Point to `references/` for deep knowledge when appropriate (resolves to `library/cursor/references/` via symlink)

## Harness State References

Rules that reference harness state use `.harness/` (project root), not `.cursor/harness/`:
- `.harness/state.json` — feature list
- `.harness/contract.json` — active contract
- `.harness/breadcrumbs.jsonl` — decision trace

If a rule references harness state, scope it with `globs` targeting implementation code so it doesn't fire when editing the rule itself:

```yaml
globs: "src/**,app/**,lib/**,backend/**,frontend/**,services/**"
alwaysApply: false
```

## Design Rationale

Rules are **guides** (Fowler's taxonomy) — feedforward steering that shapes agent behavior before it acts, as opposed to sensors that provide feedback after. The design encodes these principles:

- **Progressive context management** — always-on rules consume the most valuable resource (context window). The 2000-token budget forces ruthless prioritization: only behaviors that must apply to every task earn always-on status. Everything else is scoped by globs or description keywords, loaded on demand.
- **Activation modes as a spectrum** — `alwaysApply` for universal behaviors, `globs` for file-type-specific patterns, `description` for agent-inferred relevance. This mirrors how a senior engineer applies different mental models depending on what file they're editing.
- **Opinionated over permissive** — "Use X" not "Consider using X." Models follow directive instructions more reliably than suggestions. Hedging produces hedged output.
- **Rules vs. skills boundary** — rules are passive constraints (always in context, no workflow), skills are active procedures (invoked, multi-step). If it has numbered steps, it's a skill. If it's a stance or constraint, it's a rule.

## Hypotheses

- **H1: Always-on budget under 2000 tokens prevents context pollution while covering critical behaviors.** Exceeding this threshold degrades task performance on unrelated work. Measurement: eval pass rates before/after budget enforcement.
- **H2: Scoped rules with keyword descriptions activate more reliably than glob-only rules.** Description-based matching lets the agent load rules for conceptual relevance (e.g., "design principles" when doing UI work), not just file type. Measurement: activation accuracy in eval pipeline.
- **H3: Practitioner voice produces more decisive agent behavior than neutral technical writing.** Direct, opinionated tone reduces agent hedging and "I could do X or Y" responses. Measurement: behavioral eval rubric scores for decisiveness.
- **H4: Referencing files instead of inlining content prevents staleness.** When rules point to `references/` rather than copying content, updates propagate automatically. Measurement: zero stale-content bugs after reference updates.

## Measurement

| Signal | Source | What it tells us |
|--------|--------|------------------|
| Token count per rule | `tests/validate.py` | Whether individual rules and always-on budget stay within limits |
| Always-on total tokens | `tests/validate.py` | Whether the combined budget is under 2000 |
| Behavioral eval pass rate | `tests/eval/` pipeline | Whether rules actually change agent behavior vs. baseline |
| Activation accuracy | Manual testing + eval | Whether the right rules fire for the right tasks |
| Rule overlap | `tests/validate.py` | Whether rules duplicate each other's content |

## Anti-Patterns

- Empty frontmatter fields (dead rule)
- Vague guidance ("write clean code") — be specific
- Rules over 200 lines without splitting
- Procedural steps disguised as rules
- Duplicating another rule's content
- Copying file contents instead of referencing them

## Quality Checklist

Before a rule is considered done:

- [ ] Valid frontmatter with correct activation mode
- [ ] Under 200 lines
- [ ] No overlap with another rule (check for duplication)
- [ ] At least one concrete, actionable instruction per section
- [ ] Tested: give agent an unrelated task, verify rule loads/doesn't load as expected
- [ ] Points to `references/` for deep content rather than inlining it
