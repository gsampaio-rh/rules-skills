# Doc A — Kill List + Enforcement Map

## Part 1: Kill List

### 1. `negotiations/` folder (mandatory JSON schema)

| Field | Content |
|-------|---------|
| **What it is** | Directory for structured negotiation round logs (builder proposals, evaluator challenges) |
| **Why it was built** | Provide an audit trail of contract negotiations separate from breadcrumbs |
| **Usage evidence** | 0 files ever created in `.harness/negotiations/`. 37 references across 6 files (SKILL.md, evaluator.md, harness_lint.py, HARNESS_STANDARD.md, evaluator-guard allow-list, state.json). Lint function is a no-op when dir missing. No hook creates or reads it. |
| **Verdict** | **KILL** |
| **Reasoning** | Spec without implementation. Breadcrumbs with `type: negotiate` capture the same signal (4 negotiate entries in this repo's history). The folder adds schema overhead, lint code, and SKILL.md instructions for an artifact no one produces. |
| **Replacement** | Breadcrumbs `type: negotiate` (already used). Remove lint function, SKILL.md references, evaluator.md instructions, HARNESS_STANDARD.md section. |

### 2. `hooks.full.json` profile

| Field | Content |
|-------|---------|
| **What it is** | Extended hook config with 11 hooks (lean has 7) + 2 LLM prompt classifiers |
| **Why it was built** | Maximum enforcement: evaluator isolation, commit gate, LLM routing, compliance checking |
| **Usage evidence** | 12 references across 8 files. `make setup` defaults to lean. `sync-cursor.sh` and README default to full (inconsistency). `validate-hooks.sh` tests all full-profile hooks. |
| **Verdict** | **SIMPLIFY** |
| **Reasoning** | Keep as opt-in for this repo's dogfooding. Remove LLM prompt hooks (item 5). Promote `pre-commit-harness.sh` to lean (item argued in enforcement map). Result: full = lean + evaluator-guard + chain-evaluator (2 extra hooks, not 4+2 LLM). |
| **Replacement** | Simplified full profile with only hooks that provide unique enforcement not in lean. |

### 3. `harness_metrics.py`

| Field | Content |
|-------|---------|
| **What it is** | Python script generating `.harness/metrics.json` dashboard (task progress, breadcrumb stats, eval pass rate) |
| **Why it was built** | Visualize harness effectiveness for the cancelled spike-2 UI dashboard |
| **Usage evidence** | 0 imports anywhere. 2 Makefile targets (`harness-metrics`, `harness-metrics-json`) not in `make validate` or `make eval`. Output is `.harness/metrics.json` which is broken (gap-21: reads wrong fields, wrong glob, shows 0% pass rate). Not used by any hook, lint, or eval. |
| **Verdict** | **KILL** |
| **Reasoning** | Built for a cancelled UI dashboard (spike-2). Has been broken since creation (gap-21). No consumer needs it — task progress is visible in state.json, breadcrumbs are greppable, eval results are in individual eval-*.json files. Complexity (241 LOC) without value. |
| **Replacement** | Nothing. `state.json` tasks + breadcrumbs + eval JSONs are the source of truth. If metrics are needed: `jq` one-liners or a future script built when there's actual demand. |

### 4. `docs/HARNESS_STANDARD.md`

| Field | Content |
|-------|---------|
| **What it is** | 347-line reference document specifying harness schemas, hooks, tiers, and anti-patterns |
| **Why it was built** | Single source of truth for harness structure and conventions |
| **Usage evidence** | 0 references in `library/`, `tests/`, or `.cursor/`. 12 references total: 10 in state.json (task descriptions), 2 in README. Not read by any hook, lint, or eval script. Documented schemas drift from live implementation (eval naming, contract phase, negotiations mandatory). |
| **Verdict** | **KILL** (replace with HARNESS_ESSENCE.md) |
| **Reasoning** | Drifts silently because nothing reads it programmatically. 347 lines is too long to maintain manually. Duplicates information in SKILL.md (which agents actually read) and harness_lint.py (which enforces schemas). Replace with a concise HARNESS_ESSENCE.md (~80 lines) that documents only what's enforced. |
| **Replacement** | `docs/HARNESS_ESSENCE.md` — concise doc answering the 5-problem model. SKILL.md remains the agent-facing reference. `harness_lint.py` remains the schema enforcer. |

### 5. LLM prompt hooks

| Field | Content |
|-------|---------|
| **What it is** | 2 `"type": "prompt"` hooks in hooks.full.json: beforeSubmitPrompt classifier (trivial vs non-trivial) and stop compliance checker |
| **Why it was built** | LLM-powered routing and verification beyond what shell heuristics can detect |
| **Usage evidence** | Full profile only. 0 automated tests (validate-hooks.sh tests shell hooks, not LLM prompts). No eval scenario coverage. No logs/breadcrumbs attributing behavior to them. Functionally redundant: beforeSubmitPrompt overlaps harness-gate.sh; stop overlaps verify-harness.sh + enforce-progress.sh + context-health.sh. |
| **Verdict** | **KILL** |
| **Reasoning** | Untested, unmeasured, redundant with shell hooks. Shell hooks are deterministic and testable; LLM prompts add latency, cost, and non-determinism for zero proven benefit. If the shell hooks are insufficient, the fix is strengthening them (more deny logic), not adding a probabilistic layer on top. |
| **Replacement** | Shell hooks already in lean profile cover the same workflow steps with structural/deterministic enforcement. |

### 6. `harness-gate.sh`

| Field | Content |
|-------|---------|
| **What it is** | beforeSubmitPrompt shell hook that detects cold-start (no state.json + long non-trivial prompt), creates `.routing-pending` marker, and injects advisory routing message |
| **Why it was built** | Enable contract-gate to structurally deny impl writes during cold-start without blocking the prompt itself |
| **Usage evidence** | In lean + full profiles. Tested in validate-hooks.sh (lines 211-249). Creates the `.routing-pending` that contract-gate reads. Protocol_fresh_repo_bootstrap scenario validates it. Part of the proven 94-95% routing effectiveness. |
| **Verdict** | **KEEP** |
| **Reasoning** | Not redundant — it's the detection half of the cold-start enforcement pair. contract-gate can only deny when `.routing-pending` exists; harness-gate is what creates that marker. Removing it breaks structural cold-start enforcement. Advisory message is a bonus; the marker is the essential output. |
| **Replacement** | N/A — keep as-is. |

### 7. Tier 2 eval / `dataset.yaml`

| Field | Content |
|-------|---------|
| **What it is** | Planned behavioral evaluation tier using dataset.yaml for prompt+expected-behavior pairs |
| **Why it was built** | HARNESS_STANDARD.md section 7.2 — designed as middle tier between lint (T1) and session judge (T3) |
| **Usage evidence** | `dataset.yaml` does not exist (0 files). 2 references to filename: HARNESS_STANDARD.md line 294, state.json gap-8. No runner, judge, or fixture. `make eval` runs T1 + T3 only. EVAL_GUIDE.md documents "Two-Tier" (T1 + T3). |
| **Verdict** | **KILL** |
| **Reasoning** | Already dead — never implemented. Only artifact is a stale doc section in HARNESS_STANDARD.md (which is itself being killed). Remove the 2 references during cleanup. |
| **Replacement** | Nothing — T1 (lint) + T3 (session judge) are the eval tiers. |

---

## Part 2: Enforcement Map

### 1. Route to planner (cold start)

| Field | Content |
|-------|---------|
| **Step name** | Route to planner when no harness exists and task is non-trivial |
| **Current mechanism** | `harness-gate.sh` (beforeSubmitPrompt, advisory) → creates `.routing-pending` → `contract-gate.sh` (preToolUse/Write, structural deny) |
| **Enforcement type** | Advisory detection + structural deny (paired) |
| **Effectiveness** | Routing scenarios: 94-95% after gap-13 fix. `routing_resume_existing` at 100%. Known bypass: prompts ≤100 chars or matching SIMPLE_PATTERNS skip detection. |
| **Verdict** | **keep-as-is** |
| **Reasoning** | The advisory+structural pair works: detection doesn't need to be perfect because contract-gate denies writes regardless once the marker exists. Short prompts bypassing detection are acceptable — they're likely simple tasks that don't need harness. 94%+ is sufficient. |

### 2. Contract before implementation

| Field | Content |
|-------|---------|
| **Step name** | Block implementation writes until contract.json exists |
| **Current mechanism** | `contract-gate.sh` (preToolUse/Write, structural deny) |
| **Enforcement type** | structural-deny |
| **Effectiveness** | 94-95% post-fix. Only bypass requiring attention: Write-only (StrReplace, shell redirects not gated). Known: spike/chore bypass is by design. |
| **Verdict** | **keep-as-is** |
| **Reasoning** | Core structural enforcement. Works. The Write-only limitation is a Cursor platform constraint (preToolUse only fires for registered tools), not a harness design flaw. Covering StrReplace would require a second preToolUse entry — acceptable future enhancement but not urgent given 94%+ scores. |

### 3. Verification before done

| Field | Content |
|-------|---------|
| **Step name** | Block turn completion until contract is verified or evaluator launched |
| **Current mechanism** | `verify-harness.sh` (stop, loop_limit: 3, soft-block) |
| **Enforcement type** | soft-block-stop |
| **Effectiveness** | Part of gap-13 fix band (94-95%). Loop limit of 3 means agent gets 3 reminders before enforcement exhausts. Agent can set `verified: true` without evaluator. |
| **Verdict** | **keep-as-is (with documented debt)** |
| **Reasoning** | Soft-block is appropriate here. Making verification a hard deny (block all tools) would deadlock the agent. The stop-loop gives 3 chances. **Known gap-23 debt:** agent can self-set `verified: true` without evaluator running — verify-harness only checks the JSON field, not breadcrumbs or eval-report existence. This is a structural bypass that remains unresolved. Fixing it requires verify-harness to also check for `type: eval, role: evaluator` breadcrumb or `.harness/evals/eval-*.json` existence — future enhancement, not this sprint. Document as accepted risk in HARNESS_ESSENCE.md. |

### 4. Progress breadcrumbs

| Field | Content |
|-------|---------|
| **Step name** | Remind agent to append breadcrumbs when making multi-file changes |
| **Current mechanism** | `enforce-progress.sh` (stop, loop_limit: 2, advisory stop-loop) |
| **Enforcement type** | advisory-inject (stop-loop with low limit) |
| **Effectiveness** | No dedicated scenario score. Triggers on ≥2 git-changed files + stale breadcrumbs (>180s). Lean profile disables Tier 2. Contract existence skips entirely. |
| **Verdict** | **acceptable-advisory** |
| **Reasoning** | Breadcrumbs are useful for session recovery but not critical for the 5-problem core. The hook is a gentle nudge, not enforcement. Agents that ignore it still produce working code — they just have less audit trail. Making this structural (deny writes without fresh breadcrumbs) would be over-engineering. The `progress_tracking.mdc` rule provides additional guidance. |

### 5. User commit approval

| Field | Content |
|-------|---------|
| **Step name** | Block git commit until user approval (via .commit-approved flag) |
| **Current mechanism** | `pre-commit-harness.sh` (beforeShellExecution/git commit, structural deny) — **full profile only** |
| **Enforcement type** | structural-deny |
| **Effectiveness** | Proven in validate-hooks.sh. But full-profile-only means lean users have no commit gate. gap-24: stale flag can auto-approve without user consent. |
| **Verdict** | **promote-to-lean** |
| **Reasoning** | Commits are irreversible (especially with push). The `autonomous_execution.mdc` rule says "NEVER run git commit without asking first" but that's advisory — agents ignore rules. This is exactly the gap-23 principle: a critical step relying on advisory instruction when a structural gate exists but isn't enabled. Promote to lean profile. Fix gap-24 (TTL) during implementation. |

### 6. Evaluator isolation

| Field | Content |
|-------|---------|
| **Step name** | Block evaluator from writing implementation code (only .harness/ allowed) |
| **Current mechanism** | `evaluator-guard.sh` (preToolUse/Write, structural deny) — **full profile only** |
| **Enforcement type** | structural-deny |
| **Effectiveness** | Tested in validate-hooks.sh. 30-min staleness auto-clear. Requires manual flag creation (`.evaluator-active`). |
| **Verdict** | **keep as full-only** |
| **Reasoning** | Evaluator isolation only matters during adversarial eval (Phase 3 of SKILL.md). Consumer projects doing quick single-agent work don't run /evaluator. Promoting to lean would add a hook that fires on every Write for a feature most users never activate. Keep in full for repos doing serious adversarial testing. |

### 7. Fresh thread suggestion

| Field | Content |
|-------|---------|
| **Step name** | Suggest fresh thread when session shows fatigue signals |
| **Current mechanism** | `context-health.sh` (stop, loop_limit: 1, advisory message) |
| **Enforcement type** | advisory-inject |
| **Effectiveness** | `behavioral_session_boundary` at 33% (was 70%, regressed). 5 signal types, 2 severity levels. loop_limit: 1 means exactly one reminder. |
| **Verdict** | **acceptable-advisory** |
| **Reasoning** | Making this structural (deny all tools after 90 min?) would be hostile UX. Session length is a soft quality signal, not a correctness requirement. The 33% score (gap-14) shows agents ignore the advice, but the consequence is degraded context quality, not broken artifacts. This is legitimately best-effort. Strengthening the `planning_discipline.mdc` rule may help; new infrastructure won't. |

---

## Simplicity Metrics (targets)

| Metric | Current | Target | Delta |
|--------|---------|--------|-------|
| Lean hook count | 7 | 8 (+pre-commit promotion) | +1 |
| Full hook count | 11 (7 shell + 2 LLM + 2 full-only shell) | 10 (8 lean + evaluator-guard + chain-evaluator, no LLM) | -1 |
| Eval scenarios | 41 | 12-20 (Doc B decides) | -21 to -29 |
| HARNESS_STANDARD.md LOC | 347 | 0 (replaced by HARNESS_ESSENCE.md ~80 LOC) | -267 |
| harness_metrics.py LOC | 241 | 0 (deleted) | -241 |
| negotiations/ lint code | ~40 LOC in harness_lint.py | 0 | -40 |
| Total killed LOC | — | ~588+ | — |

---

## Summary of Decisions

| Item | Verdict | Impact |
|------|---------|--------|
| negotiations/ | KILL | Remove folder spec, lint, docs, SKILL.md refs |
| hooks.full.json | SIMPLIFY | Remove LLM prompts; full = lean + evaluator-guard + chain-evaluator |
| harness_metrics.py | KILL | Delete file + Makefile targets + .harness/metrics.json |
| HARNESS_STANDARD.md | KILL (replace) | Delete 347-line doc; write ~80-line HARNESS_ESSENCE.md |
| LLM prompt hooks | KILL | Remove from hooks.full.json |
| harness-gate.sh | KEEP | No change |
| Tier 2 / dataset.yaml | KILL | Remove stale doc references |
| pre-commit to lean | PROMOTE | Move from full-only to lean profile |
