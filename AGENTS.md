# AGENTS.md — rules-skills

Distributable Cursor library: rules, skills, hooks, and a file-based adversarial harness
(`.harness/`). Canonical source: `library/cursor/`.

This file is **project memory** (portable, cross-tool). Session memory lives in `.harness/`
and is injected by `harness-context` on session start — do not confuse the two.

## Commands

```bash
make setup          # populate .cursor/ from library/cursor/ (+ seed AGENTS.md if missing)
make sync-local     # re-copy after editing the library
make validate       # structural checks (rules/skills/template)
make eval-fast      # validate + contract_lint + harness_lint (local, no API)
```

Consumer onboarding: `library/cursor/templates/AGENTS.md` → `scripts/adopt-agents-md.sh`
(missing-only) → `/agents-bootstrap` (fill Commands). Optional absence nudge:
`agents-md-nudge` via `scripts/hooks-profile.sh optional`.

## Harness (opt-in)

1. **Default is free** — no planner/contract required for everyday work.
2. **Opt in** with `use harness` / `with harness`, `/planner`, or skill `adversarial-harness`.
3. While harness is **active** (`pending`/`building`/`evaluating`), need `.harness/contract.json` (hooks deny ungated impl writes).
4. Do not self-certify — `/evaluator` verifies; only then `verified: true`.
5. Say `skip harness` to cancel an opt-in arm or leave active mode.

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

Default profile: [`library/cursor/hooks.json`](library/cursor/hooks.json) — harness-context, **harness-gate** (opt-in → `.routing-pending`), contract-gate, evaluator-guard, pre-commit, verify, enforce-progress, chain-evaluator.

Optional dogfood: [`library/cursor/hooks.optional.json`](library/cursor/hooks.optional.json) — `secret-read-guard`, `security-shell`, `dedup-server`, `agents-md-nudge` (sessionStart if no AGENTS.md).

> **Notes:** (1) `preToolUse` matchers use `Write|StrReplace` — `StrReplace` is not in Cursor's documented tool-type list; if contract-gate misses StrReplace operations, drop it and keep only `Write`. (2) Temporary harness markers (`.routing-pending`, `.evaluator-active`) are cleaned up by `session-cleanup.sh` on `sessionEnd`; manual cleanup: `rm -f .harness/.routing-pending .cursor/hooks/.evaluator-active`.

## Skills (active catalog)

`adversarial-harness`, `agents-bootstrap`, `fact-check`, `session-review`, `svg-edit`, `code-review`, `commit`, `llm-skeptic`, `prompt-coaching` — see `library/cursor/skills/`.

Archived extras live in `library/cursor/skills/_archive/` (source history only). `make sync-local` strips `_archive/` from `.cursor/skills/` after copying so archived skills never appear in the deployed agent catalog. If you install skills to `~/.cursor/skills/` manually, exclude `_archive/` yourself.

## Cross-tool

- **Cursor:** native — `make sync-local` → `.cursor/`.
- **Other agents:** copy a short AGENTS.md + skills; regenerate Claude/Windsurf adapters from Cursor as needed. No maintained parallel port in this repo.

## Eval (local opt-in)

Session eval / ablation need `CURSOR_API_KEY` and are local SDK runs — see [`docs/EVAL_GUIDE.md`](docs/EVAL_GUIDE.md). No GitHub Actions workflows ship with this repo today.
