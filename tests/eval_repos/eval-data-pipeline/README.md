# eval-data-pipeline

A fragile nightly sales ETL script with a deliberately vague, symptom-first
prompt. Used to validate that the harness pushes back on vagueness (via
the `prompt-coaching` skill), scopes the work into
a small task list via `/planner`, and that the evaluator checks for actual
robustness rather than "it ran once."

## Seeded Gaps (`src/pipeline.py`, `data/orders.csv`)

1. Hardcoded input/output paths — no CLI args, no config
2. No error handling — a single malformed row (`data/orders.csv` has one)
   crashes the whole run with an unhandled `ValueError`
3. `print()` instead of logging — no way to tell what happened after the fact
4. No tests at all
5. No handling for duplicate order IDs or missing regions

## Task Prompt

See `PROMPT.md`. It's intentionally vague ("make it production-ready") —
the point is to see whether the agent pushes back and scopes before writing
code, per the `prompt-coaching` skill.

## What "Good" Looks Like

- [ ] The agent does NOT immediately start rewriting code from a vague prompt
      — it asks a clarifying question or proposes a concrete scoped plan
- [ ] `/planner` (or equivalent direct scoping) breaks "production-ready"
      into discrete, testable tasks (e.g., error handling, logging, tests,
      config)
- [ ] The malformed row in `data/orders.csv` no longer crashes the pipeline
      — it's logged and skipped, or the run fails loudly with a clear message
      (either is acceptable; silent success on bad data is not)
- [ ] Structured logging replaces `print()`
- [ ] At least one automated test exists and passes
- [ ] Breadcrumbs reflect the multi-step nature of the work; contract is
      `verified: true` before the session ends

## Verify

```bash
./verify.sh
```
