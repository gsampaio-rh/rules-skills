# Spec: Rules-Skills Standards Compliance

## Vision

The rules-skills project is a distributable library of Cursor rules, skills, hooks, and an adversarial verification harness. It must **dogfood its own authoring standards**: every rule, skill, and validation gate should pass before the library is considered trustworthy. Today the repo violates its own contracts (token budget, skill structure, stale examples) and treats `.cursor/` as version-controlled IDE state when it should be a local, reproducible symlink layout sourced from `library/cursor/`.

This initiative brings the project into full compliance, fixes hygiene drift from prior eval sessions, and documents the intellectual lineage of the harness so contributors understand *why* the patterns exist—not just *what* they do.

**Audience:** maintainers of rules-skills, consumers who clone the repo for development, and teams syncing config via `sync-cursor.sh`.

## Technical Direction

- **`library/cursor/`** remains the single source of truth for all distributable Cursor config (rules, skills, hooks, agents, references, hook profiles).
- **`.cursor/`** becomes a local-only IDE directory (gitignored), created on demand via a `make setup` (or equivalent) target that symlinks into `library/cursor/` and selects a hook profile.
- **Validation** (`make validate`) must pass with zero errors; the always-on token budget constant must match `RULES_STANDARD.md` (2,000 tokens).
- **Eval artifacts** (`dataset.yaml`, calibration corpus) must use examples that exist in the repo or are clearly synthetic—no references to deleted `src/` sample code.
- **Design lineage** is captured in project documentation (not loaded by agents), mapping harness concepts to their research/workshop origins.

Constraints inherited from the codebase:
- Hook profiles (`hooks.lean.json`, `hooks.full.json`) currently live only under `.cursor/`; they must relocate to `library/cursor/` without breaking `sync-cursor.sh`, `scripts/hooks-profile.sh`, or eval sandbox setup.
- `tests/validate.py` reads via `.cursor/` symlinks today; setup must ensure that path exists before validation runs.
- Parallel `library/claude/` port exists; stale-reference fixes in rules should consider whether the Claude mirror needs the same hygiene (scope decision left to builder).

## Features

### Feature 1: Local `.cursor/` Setup and Git Hygiene

**User stories:**
- As a **new contributor**, I want to clone the repo and run one command so my local `.cursor/` symlinks and hook profile are ready without committing IDE state.
- As a **maintainer**, I want `.cursor/` gitignored so hook logs, evaluator flags, and local profile choices never enter version control.
- As a **consumer running `sync-cursor.sh`**, I want hook profile JSON sourced from `library/cursor/` so distribution does not depend on a gitignored path.

**Scope notes:** Includes relocating `hooks.full.json` and `hooks.lean.json` to `library/cursor/`, updating `sync-cursor.sh` and related scripts/docs, adding `make setup`, and adjusting `.gitignore`. Does **not** include rewriting hook script logic or changing which hooks fire in each profile.

### Feature 2: Always-On Rules Token Budget

**User stories:**
- As an **agent user**, I want the combined always-on rule payload under 2,000 tokens so context budget is preserved for the actual task.
- As a **maintainer**, I want `make validate` to enforce the same 2,000-token limit documented in `RULES_STANDARD.md`, not a stale 2,500 constant.

**Scope notes:** Trim or restructure the nine `alwaysApply: true` rules—`security.mdc` and `code_standards.mdc` are the largest offenders. Content moved out of always-on rules should land in scoped rules, skills, or `references/` per the standards (procedural detail belongs in skills). Includes updating the validation constant. Does **not** change which rules are always-on vs intelligently-loaded—that is a separate product decision.

### Feature 3: Skill Authoring Compliance

**User stories:**
- As a **maintainer**, I want every skill in `library/cursor/skills/` to pass `SKILLS_STANDARD.md` validation so the library is internally consistent.
- As an **agent invoking `/adversarial-harness`**, I want that skill under 300 lines with required sections (Proactive Triggers, Stop Conditions, Output Artifacts) and explicit modes so behavior is predictable.
- As a **user running audit skills**, I want architecture/code-quality/design/organization audit skills to declare `disable-model-invocation` and multi-mode entry points where the standard requires them.

**Scope notes:** Nine skills lack "Output Artifacts"; `adversarial-harness` exceeds the line limit and lacks multiple required sections/modes; four audit skills lack proper frontmatter and mode headings. Heavy content should move to `references/` rather than bloating `SKILL.md`. Does **not** include rewriting skill workflows beyond what standards compliance requires.

### Feature 4: Stale Reference Cleanup

**User stories:**
- As a **maintainer running evals**, I want `dataset.yaml` and rule examples to reference code that exists (or neutral placeholders), not deleted `src/auth.py` artifacts from eval pollution.
- As a **reader of README**, I want accurate counts and descriptions (13 skills, not 14).
- As an **agent following `prompt_coaching`**, I want coaching examples that reflect the current repo layout.

**Scope notes:** Fix known stale refs in `prompt_coaching.mdc`, `dataset.yaml`, and `README.md`. Audit related eval calibration files and `library/claude/` mirrors for the same deleted-path examples where they would confuse contributors or judges. Does **not** redesign the eval dataset—only replace invalid references.

### Feature 5: Harness Design Lineage Documentation

**User stories:**
- As a **new contributor**, I want to understand which harness patterns (generator-evaluator, contract negotiation, breadcrumbs, scrap-and-restart) come from which sources so I can extend the system thoughtfully.
- As a **team adopting the harness**, I want a single doc that credits Anthropic's "Build Agents That Run for Hours" workshop patterns plus relevant OpenAI and DeepMind practices, mapped to concrete artifacts in this repo (hooks, `.harness/`, subagents).

**Scope notes:** New documentation describing design lineage and mapping concepts → repo artifacts. Should be discoverable from README. Does **not** require external links to break if workshops move—describe patterns by name and intent. Does **not** change harness behavior.

## Design Direction

- **Onboarding:** README Quick Start leads with `make setup` before "edit rules in `library/cursor/`".
- **Source-of-truth clarity:** Diagrams and tables consistently show `library/cursor/` → local `.cursor/` symlink flow; no implication that `.cursor/` is tracked.
- **Self-certification:** `make validate` passing is the definition of "standards compliant" for this initiative.
- **Documentation tone:** Practitioner voice—explain trade-offs and lineage without academic overhead; link from README to the lineage doc.

## Open Questions

- Should `.cursor/` be **removed from git history** in this initiative, or only gitignored going forward (existing tracked symlinks untracked via `git rm --cached`)?
- Should `tests/validate.py` read directly from `library/cursor/` instead of `.cursor/` symlinks, reducing setup dependency for CI?
- How aggressively should eval calibration files (`tests/eval/calibration/*.md`) be scrubbed of `src/auth.py` references—only broken paths, or all historical examples for consistency?
- Should `library/claude/rules/prompt-coaching.md` receive the same example fix as the Cursor rule in the same feature or a follow-up?
- Where should design lineage live: `docs/DESIGN_LINEAGE.md`, `library/README.md` section, or README appendix?

## Trade-offs

| Decision | Alternative considered | Reasoning |
|----------|------------------------|-----------|
| Gitignore entire `.cursor/` | Keep symlinks tracked, gitignore only transient files | Matches how consumer projects treat IDE config; `library/cursor/` is the distributable artifact |
| Trim always-on rules in place | Demote bulky rules to `alwaysApply: false` | Keeps universal guidance available but risks agents not loading security/code standards on non-matching globs |
| Move adversarial-harness overflow to `references/` | Split into multiple skills | Preserves one entry point (`/adversarial-harness`) while meeting line limits |
| Fix stale refs narrowly (3 known files) | Full-repo grep and purge all `src/` mentions | Narrow fix ships faster; broad audit may be warranted but expands eval/calibration scope |
| Design lineage as standalone doc | Embed only in README | Standalone doc scales; README gets a short pointer |
