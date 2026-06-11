# Phase 7 — Scoping & Risk Mitigations (Pre-contract)

**Written:** 2026-06-11 (before Phase 6 — to lock Phase 7 requirements before context is lost)
**Status:** Draft — becomes contract.json after Phase 6 is verified

---

## Three Binding Risks → Contractual Acceptance Criteria

### Risk 1 — "Intermediate everywhere" reads flat

**Mitigation:** Phase 7 must produce a **two-axis scorecard**, not a single ACAM score.

- Axis 1: ACAM maturity level per dimension (Basic/Intermediate/Advanced)
- Axis 2: Population percentile per dimension (using Phase 2 Tier 0-3 empirical model)
- Both axes must appear in the same paragraph/table in `spike-research-agents.md` — neither cancels the other
- Required section: "What to steal first" — three ranked recommendations for practitioners at Tier 0-1 who want to move up one tier without building the full harness

**Draft AC:** `spike-research-agents.md` contains a table comparing ACAM score (Intermediate) AND population tier (Tier 3 / top ~0.5%) per dimension, with a "What to steal first" section of ≥3 ranked recommendations.

---

### Risk 2 — Red-team pass too gentle

**Mitigation:** Phase 7 must **attempt a genuine Basic case for at least one dimension**, then sustain or rebut it with evidence.

- Target dimension: Workflows (strongest Basic argument: 33% session boundary + zero skill_activation eval = no verified workflow behavior)
- The argument must be made in full: "if a workflow fires 33% of the time by its own eval, does a verified workflow exist?"
- Then rebutted (or sustained) with evidence from phases 3-5
- Complementary tool: "strip the harness" test — score the repo with hooks/contract/eval removed, keeping only rules + skills. What tier does it fall to? Name it explicitly.
- A red-team pass that finds only "Intermediate is justified" across all four dimensions without a serious Basic challenge fails the edge case

**Draft EC:** Phase 7 red-team section explicitly attempts AND rebuts (or sustains) a Basic case on ≥1 dimension. A verdict of "we tried Basic on Workflows and here is why it fails / holds" is required. A pass that skips the attempt fails EC.

---

### Risk 3 — Publication readiness

**Mitigation:** Phase 7 produces **three distinct deliverables** with explicit sizing constraints, each independently testable.

| Deliverable | Target size | Acceptance test |
|---|---|---|
| `acam-worksheet.md` | ≤60 lines | Evaluator scores a fictional Repo X using only the worksheet — must be completable in ≤30 min without reading any phase doc |
| `spike-research-agents.md` | 2,000-3,000 words | Self-contained — evaluator reads ONLY this file, no phase docs; can reconstruct all four ACAM scores and key findings |
| Blog series outline | 4 posts × 1 thesis + 3 evidence points | Each post has a stated thesis; the four posts together tell a complete story |

**Draft AC set:**
- AC-pub-1: `acam-worksheet.md` exists at ≤60 lines; evaluator applies it to a fictional repo and produces a score
- AC-pub-2: `spike-research-agents.md` is self-contained (1,500-3,000 words); evaluator reads only it and can answer: what is ACAM? what dimension scores what? what are the top gaps? what should a practitioner steal?
- AC-pub-3: Blog outline covers 4 posts with stated thesis per post and ≥3 evidence points per post sourced from the bibliography

---

## Phase 7 Deliverables (Full List)

1. `acam-worksheet.md` — 4×3 matrix + scoring questions (standalone, ≤60 lines)
2. `spike-research-agents.md` — master synthesis (self-contained, 2k-3k words)
3. `rules-skills-scorecard.json` — machine-readable: per-dimension score + evidence[] + gaps[] + frontier_comparison
4. Blog series outline — 4-post outline with thesis + evidence points
5. ACAM matrix — filled 4×3 with externally-validated criteria (from BC3 revisions across phases 3-5)
6. Red-team pass — Basic case attempt + verdict on ≥1 dimension

---

## What Phase 6 Needs to Deliver for Phase 7

- Interaction dimension ACAM score (fills the last empty cell)
- New sources H1-H3 for bibliography (Karpathy, Simon Willison, LangSmith or equivalent)
- Cross-reference: how does the 33% session boundary failure look from the Interaction angle vs. the Workflows angle?
- How does `critical_thinking.mdc` and `prompt_coaching.mdc` relate to the four-layer pyramid (prompt → context → intent → specification engineering)?
- Honest gap: no prompt effectiveness data — this is the Interaction-dimension binding constraint, mirroring ablation data as the Configuration constraint

---

## Revised ACAM Advanced Criteria (from BC3 revisions — to fill Phase 7 matrix)

### Configuration (Phase 3 BC3)
Removed: "ablation testing" as standalone criterion → replaced with "quantified effectiveness data"
Added: "cross-tool portability (AGENTS.md)"

### Workflows (Phase 4 BC3)
Renamed: "contract-first development" → "acceptance-criteria-gated implementation"
Added: "traced execution with append-only audit log"

### Multi-agent (Phase 5 BC3)
Removed: "parallel evaluation" from required Advanced
Added: "trust boundary enforcement (evaluator cannot write source)"

### Interaction (Phase 6 BC3)
*TBD — to be filled by Phase 6 analysis*
