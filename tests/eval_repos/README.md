# Eval Repos — Real-Scenario Harness Validation

Standalone, IDE-openable starter codebases for dogfooding the simplified harness
(post `c9f57a4`) against realistic domain tasks — as opposed to the synthetic,
ephemeral scenarios in `tests/eval/scenarios/` which run headless through the
Cursor SDK bridge (no subagents, no skill auto-routing, no real IDE hooks UI).

## Why This Exists (vs. `tests/eval/scenarios/`)

| | `tests/eval/scenarios/*.yaml` | `tests/eval_repos/*` |
|---|---|---|
| Execution | `session_runner.py` → temp dir → SDK bridge | Human opens the folder in Cursor IDE |
| Subagents (`/planner`, `/evaluator`) | Not available (simulated internally) | Fully available |
| Skill auto-routing | Not available (IDE-only feature) | Fully available |
| Lifespan | Destroyed after each run | Persistent — reset between runs |
| Purpose | CI regression gate, fast, scriptable | Manual/periodic validation of real UX |

This fills the gap flagged in `docs/EVAL_GUIDE.md` under "Known Limitations →
Future improvements → IDE-mode testing": the SDK bridge cannot exercise
subagent launches or skill auto-activation, so those paths need a real IDE
session against a realistic repo.

## The Three Repos

| Repo | Domain | Stress-tests |
|---|---|---|
| `eval-api-security/` | REST API with staged security gaps | `security.mdc`, contract-gate on multi-file feature work |
| `eval-data-pipeline/` | Fragile ETL script needing hardening | `code_standards.mdc`, `testing.mdc`, planner scoping of a vague ask |
| `eval-infra-deploy/` | Kubernetes manifests missing deploy safety | `infra-deploy-checklist` skill, `iac-templates` skill auto-activation |

Each repo is intentionally small (a handful of files with realistic, seeded
gaps) so a session stays in the 5–15 minute range — long enough to exercise
planner → contract → build → evaluate, short enough to run repeatedly.

## Running a Scenario

1. **Sync harness config into the target repo:**

   ```bash
   ./tests/eval_repos/setup.sh eval-api-security
   ```

   This copies `library/cursor/` into `tests/eval_repos/eval-api-security/.cursor/`
   (mirroring `make sync-local`) and `git init`s the repo if needed. Safe to
   re-run — it fully resyncs `.cursor/` from the current `library/cursor/`.

2. **Open `tests/eval_repos/eval-api-security/` as its own workspace in Cursor**
   (not as a subfolder of `rules-skills` — the harness looks for `.harness/`
   and `.cursor/` relative to the workspace root).

3. **Paste the task prompt** from that repo's `PROMPT.md` into a fresh chat.

4. **Observe and record**, using the repo's `README.md` checklist:
   - Did `/planner` get invoked (or was it obviously skippable)?
   - Was a contract negotiated before implementation writes?
   - Did the relevant skill(s) auto-activate?
   - Did the evaluator run before `verified: true` was set?

5. **Run `./verify.sh`** inside the repo to check binary pass/fail criteria
   (harness artifacts + domain-specific fixes).

6. **Reset for the next run:**

   ```bash
   ./tests/eval_repos/setup.sh eval-api-security --reset
   ```

   Removes `.harness/` and `.cursor/` and re-syncs a clean `.cursor/`, leaving
   the seed source files untouched (source files are restored via `git
   checkout` if the repo is git-tracked).

## What NOT to Commit

`.harness/`, `.cursor/`, and `.git/` inside each eval repo are runtime
artifacts — generated locally by `setup.sh` (git-init'd so the repo is a
fully isolated workspace, matching how `tests/eval/sandbox.py` isolates
SDK-bridge runs). Only the seed source, `README.md`, `PROMPT.md`, and
`verify.sh` are tracked in the parent `rules-skills` repo.

Before committing anything to the parent repo, confirm no stray nested repo
or generated state is lying around:

```bash
find tests/eval_repos -maxdepth 2 \( -name ".git" -o -name ".cursor" -o -name ".harness" \)
```

If that prints anything, run `setup.sh <name> --reset` or manually `rm -rf`
the listed paths first — a nested `.git/` would otherwise be added to the
parent repo as a dangling gitlink.
