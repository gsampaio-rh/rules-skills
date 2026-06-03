# Doc D — Schema + Housekeeping

All items are conditional on Doc A/B/C decisions. No independent design choices here.

## Decision Table

### gap-20 — harness_level nested in post_hoc_rubric

| Field | Content |
|-------|---------|
| **Task ID** | gap-20 |
| **Depends on** | Doc B: `protocol_spike_bypasses_gate` survives (KEEP). Doc A: eval pipeline not killed. |
| **Verdict** | **implement** |
| **Implementation spec** | (1) Move `harness_level: light` from `post_hoc_rubric` to top-level in `tests/eval/scenarios/protocol-spike-bypasses-gate.yaml` (line 42→5) and `tests/eval/scenarios/behavioral-resume-mixed-tasks.yaml` (line 44→5). (2) Add nested fallback in `tests/eval/session_judge.py` `_get_harness_level()`: check `rubric.get("post_hoc_rubric", {}).get("harness_level")` as fallback. Note: `behavioral-resume-mixed-tasks` is being CUT in Doc B — fix only `protocol-spike-bypasses-gate.yaml`. |

### gap-21 — harness_metrics.py reads wrong fields

| Field | Content |
|-------|---------|
| **Task ID** | gap-21 |
| **Depends on** | Doc A: `harness_metrics.py` verdict = **KILL**. |
| **Verdict** | **cancel** |
| **Cancellation reason** | The file is being deleted (Doc A kill list item 3). Fixing a broken dashboard script that's about to be removed is waste. Remove file + Makefile targets + `.harness/metrics.json` during implementation. |

### gap-23 — Advisory vs structural enforcement architecture

| Field | Content |
|-------|---------|
| **Task ID** | gap-23 |
| **Depends on** | Doc A Part 2 (Enforcement Map) resolves this directly. |
| **Verdict** | **implement** (resolved by Doc A) |
| **Implementation spec** | Doc A's enforcement map IS the resolution. Concrete action: promote `pre-commit-harness.sh` to lean profile (Doc A verdict). No other enforcement changes — remaining advisory hooks (enforce-progress, context-health) classified as acceptable-advisory with justification. The architectural principle ("assume LLM non-compliance, enforce structurally") is documented in HARNESS_ESSENCE.md. |

### gap-24 — .commit-approved flag hygiene

| Field | Content |
|-------|---------|
| **Task ID** | gap-24 |
| **Depends on** | Doc A: pre-commit-harness.sh verdict = **promote-to-lean** (stays and gets strengthened). |
| **Verdict** | **implement** |
| **Implementation spec** | (1) Add `.commit-approved` to `.gitignore` (explicit, defense-in-depth). (2) In `library/cursor/hooks/pre-commit-harness.sh`: add TTL check using `hooks_file_age` — reject flag if older than 300 seconds (5 min covers human review + approval flow; agent writes flag → retries commit within seconds, but user may take time reviewing diff). (3) Add test to `validate-hooks.sh`: stale flag (>300s) treated as absent → deny. (4) Document TTL in HARNESS_ESSENCE.md under commit-gate description. |

### gap-25 — No dedup/grouping/archiving for tasks

| Field | Content |
|-------|---------|
| **Task ID** | gap-25 |
| **Depends on** | Doc A: HARNESS_STANDARD.md being replaced by HARNESS_ESSENCE.md. state.json currently 566 lines with 47 verified + 6 cancelled tasks. |
| **Verdict** | **implement** (partial — archiving + group documentation + simple dedup lint) |
| **Implementation spec** | (1) Document `group` field in HARNESS_ESSENCE.md (already in use on 8 tasks; just needs formal spec). (2) Create `scripts/archive-tasks.py`: move tasks with status `verified`/`cancelled` to `.harness/archive.jsonl` (one JSON object per line, preserving all fields + `archived_at` timestamp). Keep `tasks[]` as active backlog only. (3) Add to planner.md: "Before adding a task, scan existing pending tasks for overlapping scope." (4) Add `harness_lint.py` warning: tasks with identical `name` or >70% word overlap in name within same `group` — simple duplicate detection, not full semantic dedup. |

### chore-audit-2 — make setup creates .harness subdirs

| Field | Content |
|-------|---------|
| **Task ID** | chore-audit-2 |
| **Depends on** | Doc C: consumer setup includes `.harness/` directory creation. Eval pipeline is this-repo-only (Doc C "What you DON'T need" list). |
| **Verdict** | **implement** |
| **Implementation spec** | Add `@mkdir -p .harness/evals .harness/audits` to `Makefile` `setup` target (after `sync-local`). Consumer projects only need `mkdir -p .harness` (per Doc C step 4) — the evals/audits subdirs are for this repo's dogfooding. |

### spike-4 — Prevent agent from re-creating plans that already exist

| Field | Content |
|-------|---------|
| **Task ID** | spike-4 |
| **Depends on** | Doc A enforcement map: planner routing = advisory+structural pair (keep-as-is). Cold-start detection already handles "no state.json" case. |
| **Verdict** | **implement** (trivial rule addition) |
| **Implementation spec** | Add to `adversarial_harness.mdc` cold-start section: "**Existing state:** If `.harness/state.json` exists with pending tasks, do NOT launch `/planner`. Resume the workflow from the next pending task. Planner is only for cold-start (no state) or explicit user request." One paragraph, no new hooks. |

### HARNESS_STANDARD.md reconciliation

| Field | Content |
|-------|---------|
| **Task ID** | (part of spike-audit-1) |
| **Depends on** | Doc A: verdict = KILL (replace with HARNESS_ESSENCE.md ~80 lines). |
| **Verdict** | **implement** (kill old + create new) |
| **Implementation spec** | (1) Delete `docs/HARNESS_STANDARD.md`. (2) Create `docs/HARNESS_ESSENCE.md`: 5-problem statement, 3 core files (state.json, contract.json, breadcrumbs.jsonl), enforcement model summary (from Doc A), consumer quick-start reference (point to Doc C output), eval scope (from Doc B: 17 scenarios testing 5 problems). Target: 80 lines. (3) Update README.md link from HARNESS_STANDARD to HARNESS_ESSENCE. |

---

## Resolution Summary

| Task ID | Verdict | Reason |
|---------|---------|--------|
| gap-20 | implement | Eval pipeline survives; scenario survives Doc B |
| gap-21 | **cancel** | harness_metrics.py being killed (Doc A) |
| gap-23 | implement | Resolved by Doc A enforcement map + pre-commit promotion |
| gap-24 | implement | pre-commit stays and is promoted to lean |
| gap-25 | implement (partial) | Archiving + group doc; skip dedup lint |
| chore-audit-2 | implement | Makefile one-liner |
| spike-4 | implement | One paragraph in adversarial_harness.mdc |
| HARNESS_STANDARD | implement (kill+replace) | HARNESS_ESSENCE.md replaces it |
| spike-audit-1 | **this sprint** | Verified when all above complete + eval passes |
