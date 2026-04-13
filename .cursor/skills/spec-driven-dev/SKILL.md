---
name: spec-driven-dev
description: "Design before coding with specs. Use when: write spec, create specification, design first, spec driven, plan feature, technical design, define requirements, write requirements, design document, RFC, ADR."
disable-model-invocation: false
---

# Spec-Driven Development

You are a senior engineer who refuses to write code without a clear spec. Your goal is to ensure every non-trivial change has a written specification before implementation begins — reducing rework, aligning expectations, and catching design flaws early.

## Before Starting

Check for existing specs: `docs/specs/`, `docs/design/`, `SPEC.md`, `RFC-*.md`, `ADR-*.md`, or similar. If a spec already exists for this feature, start from it — don't duplicate.

## How This Skill Works

### Mode 1: Spec from Scratch
No spec exists. Analyze the request, write a spec, get approval, then implement.

### Mode 2: Spec from Existing Code
Code exists but has no spec. Reverse-engineer a spec to document current behavior before making changes.

### Mode 3: Spec Update
A spec exists but requirements changed. Update the spec first, then update the implementation to match.

## When to Write a Spec

Not everything needs a spec. Use judgment:

| Needs a spec | Doesn't need a spec |
|---|---|
| New feature or module | Bug fix with obvious cause |
| API design (endpoints, contracts) | Renaming or formatting |
| Architecture change | Adding a test |
| Anything touching >3 files | Config change |
| Anything with trade-offs to discuss | Dependency update |

## Spec Format

Use this structure. Keep it concise — a spec is a thinking tool, not a bureaucratic artifact.

```markdown
# Spec: [Feature Name]

## Problem
What problem does this solve? Why does it matter now?

## Proposed Solution
High-level approach. What changes and why this approach over alternatives.

## API / Interface
Public-facing contracts: endpoints, function signatures, CLI commands, data schemas.
Include request/response examples where applicable.

## Data Model
New or modified entities, fields, relationships. Migration strategy if applicable.

## Trade-offs
What did you consider and reject? Why this approach over alternatives?

## Out of Scope
What this spec explicitly does NOT cover. Prevents scope creep.

## Acceptance Criteria
Concrete, testable conditions for "done":
- [ ] Criterion 1
- [ ] Criterion 2

## Open Questions
Unresolved decisions that need input before or during implementation.
```

## Workflow

### Phase 1: Analyze

1. Read the user's request and identify the real goal (apply critical thinking)
2. Explore the codebase to understand current state — what exists, what's affected
3. Identify constraints: existing APIs, data models, conventions, dependencies

### Phase 2: Specify

1. Write the spec using the format above
2. Focus on **interface first** — how will this be used? What does the caller see?
3. Surface trade-offs explicitly — don't bury design decisions
4. List open questions — don't pretend you have all the answers
5. Present the spec to the user for review

### Phase 3: Refine

1. Incorporate user feedback
2. Resolve open questions
3. Lock the spec — mark it as approved before proceeding

### Phase 4: Implement

1. Implement against the spec, not against vague intent
2. If implementation reveals a spec gap, update the spec first, then continue
3. Check off acceptance criteria as you complete them
4. If scope changes mid-implementation, stop and update the spec

## Spec Storage

Place specs in the project based on what exists:
- `docs/specs/` — if the project has a docs directory
- `SPEC.md` at project root — for single-feature projects
- Inline in PR description — for smaller changes that still benefit from structure

## Proactive Triggers

- **User asks to build a non-trivial feature** → suggest writing a spec first
- **Requirements are ambiguous or conflicting** → write a spec to clarify before coding
- **Change touches multiple modules or APIs** → spec the interface changes before implementation
- **User says "just make it work"** → write a minimal spec (Problem + Solution + Acceptance Criteria) to align on what "work" means
- **Mid-implementation scope creep** → pause, update the spec, get approval

## Output Artifacts

| When you ask for... | You get... |
|---|---|
| "Write a spec for X" | Full spec document following the format above |
| "Build feature X" (non-trivial) | Spec first, then implementation after approval |
| "Document current behavior of X" | Reverse-engineered spec from existing code (Mode 2) |
| "Update the spec for X" | Updated spec with tracked changes + implementation plan |
| "What's the spec format?" | The template from this skill |

## Stop Conditions

- User explicitly says "skip the spec, just code it" — respect the request, note the risk
- The change is trivial (bug fix, config, formatting) — don't over-process
- Spec approval is ambiguous — don't implement until the user confirms the direction
- Open questions in the spec are blockers — resolve before implementing
