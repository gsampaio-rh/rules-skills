# AGENTS.md — rules-skills

Distributable Cursor library: rules, skills, hooks, and a file-based adversarial harness
(`.harness/`). Canonical source: `library/cursor/`.

## Commands

```bash
make setup          # populate .cursor/ from library/cursor/
make sync-local     # re-copy after editing the library
make validate       # structural checks (rules/skills)
make eval-fast      # validate + contract_lint + harness_lint (local, no API)
```

## Harness (5 bullets)

1. Non-trivial work (3+ files, architectural, vague) → `/planner` before impl writes.
2. Build tasks need `.harness/contract.json` with binary criteria (hooks deny ungated writes).
3. Do not self-certify — `/evaluator` verifies; only then `verified: true`.
4. On session start, read `.harness/state.json` + last breadcrumbs (or trust harness-context inject).
5. User can say `skip harness` to opt out.

Procedure: skill `adversarial-harness`. Design: [`docs/HARNESS_ESSENCE.md`](docs/HARNESS_ESSENCE.md).

## Key artifacts

| File | Purpose |
|---|---|
| `.harness/state.json` | `schema_version: 2`, one-line `vision`, max 5 `tasks` (`id/name/type/status/scope`) |
| `.harness/contract.json` | Acceptance criteria + `phase` / `verified` |
| `.harness/breadcrumbs.jsonl` | Append-only audit (rolling ~30-line window) |
| `.harness/.archive/archive.jsonl` | Forensic overflow — never inject into prompts |

## Agents

| Persona | Invoke | Writes |
|---|---|---|
| Planner | `/planner` | `.harness/state.json` + breadcrumb |
| Builder | (default) | source |
| Evaluator | `/evaluator` | `.harness/` only (`evaluator-guard`) |

## Hooks

Default profile: [`library/cursor/hooks.json`](library/cursor/hooks.json) — harness-context, **harness-gate** (cold-start → `.routing-pending`), contract-gate, evaluator-guard, pre-commit, verify, enforce-progress, chain-evaluator.

Optional dogfood: [`library/cursor/hooks.optional.json`](library/cursor/hooks.optional.json) — `secret-read-guard` (failClosed Read deny on `.env`/keys), `security-shell` (failClosed deny curl|wget pipe-to-shell), `dedup-server`, `context-health`.

## Skills (active catalog)

`adversarial-harness`, `fact-check`, `session-review`, `svg-edit`, `code-review`, `commit`, `llm-skeptic`, `prompt-coaching` — see `library/cursor/skills/`. Archived extras: `library/cursor/skills/_archive/`.

## Cross-tool

- **Cursor:** native — `make sync-local` → `.cursor/`.
- **Other agents:** copy a short AGENTS.md + skills; regenerate Claude/Windsurf adapters from Cursor as needed. No maintained parallel port in this repo.

## Eval (local opt-in)

Session eval / ablation need `CURSOR_API_KEY` and are local SDK runs — see [`docs/EVAL_GUIDE.md`](docs/EVAL_GUIDE.md). No GitHub Actions workflows ship with this repo today.
