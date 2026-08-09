# Harvest Evaluation (post Mode 2)

After feature evaluation and before terminate, decide whether the completed task produced a reusable pattern. Add `harvest_recommendation` to the eval report JSON.

**Skip for trivial tasks:** If `task_id` starts with `chore-`, `spike-`, or `docs-`, set `type` to `none` and skip the signals below.

## Signals

**Type: skill** — set if ≥2 of:

- 3+ sequential, non-obvious steps another agent would need
- Domain knowledge unlikely to be inferred from code alone
- Agent consulted external references/docs/examples
- Pattern applies beyond this project (not tightly coupled to local paths)

**Type: hook** — set if ≥2 of:

- Check/gate that should fire without agent judgment
- Deterministic (same input → same output, no LLM reasoning)
- Fits a Cursor hook event (stop, preToolUse/Write, sessionStart, subagentStop)
- Project-agnostic (no hardcoded local paths)

**Type: none** — fewer than 2 signals for both, or an equivalent artifact already exists under `library/cursor/skills/` or `library/cursor/hooks/`.

```json
"harvest_recommendation": {
  "type": "skill | hook | none",
  "rationale": "One sentence: which signals matched and why this type was chosen (or why none)."
}
```

`verify-harness` may surface this after commit when advancing the next task.
