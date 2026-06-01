# Evaluator Rubrics & Model-Adaptive Tuning

## Evaluator Rubrics

Tune per domain. Vague criteria produce vague critiques. Granular criteria produce actionable fixes.

### Web App

| Criterion | Weight | How to Test |
|-----------|--------|-------------|
| Functionality | 40% | All interactive elements work per contract |
| Error handling | 20% | Console clean, graceful degradation |
| Responsiveness | 15% | Mobile, tablet, desktop breakpoints |
| Accessibility | 15% | Keyboard nav, ARIA, contrast |
| Performance | 10% | No layout shifts, fast load |

### API / Backend

| Criterion | Weight | How to Test |
|-----------|--------|-------------|
| Correctness | 40% | Endpoints return expected responses |
| Error handling | 25% | Invalid inputs → proper error codes |
| Edge cases | 20% | Boundary values, empty, concurrent |
| Security | 15% | Auth enforced, input validated |

### Data / ML

| Criterion | Weight | How to Test |
|-----------|--------|-------------|
| Correctness | 35% | Output matches expected distributions |
| Reproducibility | 25% | Fixed seed → same results |
| Edge cases | 20% | Empty, NaN, extreme, single-row |
| Performance | 20% | Within time/memory budget |

## Model-Adaptive Tuning

Every harness component encodes an assumption about what the model can't do on its own. As models improve, re-examine assumptions:

- **Context resets**: Opus 4.6+ handles long contexts well. Use continuous sessions with compaction. Older models may need fresh context windows per feature.
- **Sprint decomposition**: Stronger models hold multi-hour builds coherently. Weaker models need explicit one-feature-at-a-time gating.
- **Evaluator frequency**: For strong models, evaluate at the end of a full build. For weaker models, evaluate after each feature.
- **Contract negotiation depth**: If the model consistently produces strong criteria on its own, reduce negotiation rounds.

The harness doesn't shrink as models improve — it moves. Strip what's no longer load-bearing, add new components for new capabilities.

## Invocation Examples

Full harness for a new feature:

```text
User: "Add dark mode support to the dashboard"

→ /planner Add dark mode support to the dashboard. The app uses React + Tailwind.
  Check the current theme setup in src/styles/ and component structure.

→ [planner produces state.json, user confirms]

→ [builder proposes contract for feat-1]

→ /evaluator Review the proposed contract — negotiation mode

→ [evaluator pushes back, builder revises, agreement reached]

→ [builder implements the feature, runs computational sensors]

→ /evaluator Test the dark mode implementation against the contract.
  Use browser tools to toggle theme, verify all components, check persistence.

→ [evaluator reports PASS/FAIL with evidence]
```

Standalone rubric audit (no feature build):

```text
User: "Audit this project's architecture"

→ [skill architecture-audit activates]
→ [loads rubric from .cursor/references/rubrics/architecture.json]
→ [scans codebase: file structure, imports, dependency direction, naming]
→ [launches /evaluator in rubric audit mode]
→ /evaluator Run rubric audit for architecture on src/. Load .cursor/references/rubrics/architecture.json
→ [evaluator grades each criterion PASS/FAIL with evidence]
→ [produces report at .harness/audits/audit-architecture-{timestamp}.json]
```

Feature build with rubric integration:

```text
User: "Add payment processing"

→ [harness flow: plan → negotiate → build → evaluate]
→ [contract includes: "rubrics": ["architecture", "code-quality"], "rubric_mode": "strict"]
→ [evaluator does Mode 2 (feature eval) — PASS]
→ [evaluator does Mode 3 (rubric audit) on changed files]
→ [rubric finds: new PaymentService violates dependency direction — imports from infrastructure]
→ [rubric_mode is strict → feature BLOCKED until architecture fix applied]
```
