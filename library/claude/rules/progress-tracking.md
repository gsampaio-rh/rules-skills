# Progress Tracking

## Break Work Into Steps

Before starting any code change that touches 2+ files:

1. **Decompose** the task into steps where each step is one verifiable change (one function, one component, one config update)
2. **Create a TodoWrite plan** with all steps before writing any code
3. **Work one step at a time**: implement → verify (lint/test) → mark complete → next step
4. **Never batch**: if you find yourself editing 3+ files without verifying, stop and checkpoint

## Register Progress

After completing each step (not at the end — after EACH step):

1. **Update TodoWrite** status (in_progress → completed)
2. **Append a breadcrumb** to `.claude/breadcrumbs.jsonl`:

```jsonl
{"ts":"ISO-8601","role":"builder","type":"build","feat":null,"msg":"<step summary>","result":"pass"}
```

3. If `.claude/breadcrumbs.jsonl` doesn't exist, create it

## Why This Matters

- If the session dies mid-work, `breadcrumbs.jsonl` tells the next session where to resume
- Small steps are safer — each is individually verifiable and revertible
- The `enforce-progress.sh` hook will block your turn if you modify 2+ files without updating `breadcrumbs.jsonl`

## Exceptions

- Single-file changes: no progress tracking needed
- Documentation-only changes: no progress tracking needed
- When the adversarial harness is active (contract exists): harness has its own tracking via the same `breadcrumbs.jsonl`
