# Evaluator Rubrics & Model-Adaptive Tuning

## Evaluator Rubrics

Tune per domain. Vague criteria produce vague critiques. Granular criteria produce actionable fixes.

### Web App

| Criterion | Weight | How to Test |
|-----------|--------|-------------|
| Functionality | 40% | `browser_snapshot` after each action: roles, names, URL, control state |
| Error handling | 20% | Console clean; snapshot of error/status text |
| Responsiveness | 15% | Resize 320/768/1024; overflow via bounding box / `scrollWidth`, not screenshot |
| Accessibility | 15% | Snapshot roles/names; contrast via `getComputedStyle` |
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
  Use browser_snapshot to toggle theme, confirm roles/text persist, check URL.
  Screenshot only if the criterion is visual.

→ [evaluator reports PASS/FAIL with evidence]
```

## Optional rubric audit (no dedicated Mode 3 in the agent)

Audit skills are archived. When needed:

1. Load rubric JSON from `.cursor/references/rubrics/{domain}.json`
2. Grade each criterion PASS/FAIL/NOT_APPLICABLE/BLOCKED with evidence
3. Save report to `.harness/audits/audit-{domain}-{timestamp}.json`
4. If the active contract has `"rubrics": [...]`: after Mode 2, run rubric audit on changed files; `rubric_mode: warn` reports only, `strict` blocks verification on high-severity fails

```text
User: "Audit this project's architecture"

→ /evaluator Run rubric audit for architecture on src/. Load .cursor/references/rubrics/architecture.json
→ [grades each criterion with evidence]
→ [report at .harness/audits/audit-architecture-{timestamp}.json]
```

Available rubrics: `architecture`, `code-quality`, `organization`, `design-ui`, `llm-skeptic`, `cost-efficiency`.
