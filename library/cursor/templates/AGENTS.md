# AGENTS.md

Portable project memory for coding agents. Keep this short: build/test commands,
non-obvious constraints, and pointers — not a README rewrite.

## Commands

```bash
# Replace with this project's real gates
make test
make lint
```

## Security considerations

- Canonical library edits live under `library/` (or your project's agreed source tree) — do not edit generated IDE copies as the source of truth.
- Do not invent secrets, commit `.env`, or run destructive git history rewrites without explicit user approval.
- Prefer existing project scripts over ad-hoc one-off shell.

## See also

- Human docs: `README.md`
- Deeper agent workflow (if present): project skills / `.cursor/skills/`
- UI checks: rule `ui_verification` (snapshot-first YAML; Playwright only if the user asks)
- Session task state (if present): `.harness/state.json` — not a substitute for this file
