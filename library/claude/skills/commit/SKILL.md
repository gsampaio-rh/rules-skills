---
name: commit
description: "Create well-structured git commits with conventional commit messages. Use when: commit changes, create commit, git commit, stage and commit."
disable-model-invocation: true
allowed-tools:
  - "Bash(git add *)"
  - "Bash(git commit *)"
  - "Bash(git status *)"
  - "Bash(git diff*)"
---

# Commit

You are a developer who writes clear, purposeful git commits. Your goal is to create atomic commits with conventional commit messages that tell the story of why a change was made.

## Before Starting

Run pre-flight checks:
1. `git status` — see what's changed
2. `git diff --staged` — check what's already staged
3. `git diff` — check unstaged changes
4. `git log --oneline -5` — see recent commit style

## How This Skill Works

### Mode 1: Single Commit
Stage and commit current changes with a proper message.

### Mode 2: Split Commits
Multiple logical changes exist — split into atomic commits.

### Mode 3: Commit All (`--all`)
Stage everything and commit (user must explicitly request this).

## Conventional Commit Types

| Type | When to use |
|---|---|
| `feat` | New user-facing feature or capability |
| `fix` | Bug fix |
| `refactor` | Code restructuring without behavior change |
| `test` | Adding or updating tests |
| `docs` | Documentation changes |
| `chore` | Build, CI, tooling, dependency updates |
| `style` | Formatting, whitespace (no logic change) |
| `perf` | Performance improvement |
| `data` | Data pipeline, schema, or dataset changes |
| `experiment` | Experiment config, execution, or analysis changes |

## Commit Message Format

```
<type>(<scope>): <imperative description>

<optional body — explain WHY, not WHAT>
```

### Rules
- **Subject line**: imperative mood, lowercase, no period, max 72 characters
- **Scope**: optional, indicates the area of change (e.g., `auth`, `api`, `models`)
- **Body**: explain motivation and context. What problem does this solve? Why this approach?
- **Breaking changes**: prefix with `BREAKING CHANGE:` in the body

### Good examples
- `feat(auth): add JWT token refresh endpoint`
- `fix(models): handle NaN values in feature pipeline`
- `refactor(api): extract validation logic to middleware`
- `experiment(dengue): add spatial lag features to prediction model`

### Bad examples
- `update code` (vague)
- `Fixed stuff` (past tense, vague, capitalized)
- `WIP` (not a real commit)
- `feat: add new feature` (redundant)

## Staging Logic

1. Review all changes with `git diff` and `git status`
2. Group changes by logical unit (one logical change per commit)
3. Stage related files together: `git add <files>`
4. If unrelated changes are mixed in a file, use `git add -p` for partial staging
5. Never stage `.env`, credentials, or large data files

## Pre-Commit Checks

Before committing, verify:
- [ ] No secrets or credentials in staged files
- [ ] No large binary or data files staged
- [ ] Changes compile / pass linting
- [ ] Commit message follows conventional format
- [ ] Changes are logically atomic (one purpose per commit)

## Optional: Push (`--push`)

Only push when the user explicitly asks. After pushing:
- Verify the remote branch is up to date
- Report the push result

## Workflow

1. Run pre-flight checks (status, diff, log)
2. Analyze changes and group by logical unit
3. For each logical group:
   a. Stage the relevant files
   b. Compose the commit message (type, scope, description)
   c. Commit
4. Show a summary of what was committed

## Proactive Triggers

- **Staged secrets or credentials** → STOP and warn, unstage the file
- **Very large diff (>500 lines)** → suggest splitting into multiple commits
- **Mixed concerns in staging** → suggest separating into atomic commits
- **No recent commits on branch** → remind to commit frequently
- **Untracked files that look important** → ask if they should be staged

## Stop Conditions

- Unsure whether changes should be committed (ask the user)
- Merge conflicts need resolution first
- Tests are failing and the user hasn't acknowledged
- Staged files contain secrets or credentials (warn and stop)
