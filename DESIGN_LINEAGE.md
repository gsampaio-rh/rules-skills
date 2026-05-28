# Design Lineage

The harness, rules, and skills in this project implement specific patterns from frontier AI research labs. Every design decision is traceable to a principle. This document maps concepts to their origins and to concrete artifacts in this repo.

## Primary Sources

### Anthropic — "Build Agents That Run for Hours"

Ash Prabaker and Andrew Wilson, AI Engineer Conference 2026. The primary inspiration for the adversarial harness workflow.

| Pattern | Origin | Repo Artifact |
|---------|--------|---------------|
| Generator-Evaluator (GAN-inspired) | Separate context windows for builder and evaluator prevent self-evaluation bias | `/evaluator` subagent in `.cursor/agents/evaluator.md` |
| Planner sets direction only | Granular planner details cascade errors over multi-hour horizons | `/planner` subagent in `.cursor/agents/planner.md`; `.harness/spec.md` stays at user-story level |
| Contract negotiation | Builder and evaluator agree on criteria before building — the key innovation over simple RALF loops | `.harness/contract.json`; Phase 1.5 in adversarial-harness SKILL |
| Self-evaluation is a trap | Tuning a standalone critic to be harsh is tractable; tuning a builder to be self-critical is not | Builder never judges its own work; evaluator is always a separate subagent |
| File system as durable state | JSON over markdown — models overwrite markdown more readily | `.harness/state.json`, `.harness/contract.json` (all JSON) |
| Breadcrumbs pattern | "You're basically just leaving breadcrumbs for another model to come and pick up" | `.harness/breadcrumbs.jsonl` — append-only JSONL trace |
| Scrap and restart | Models should discard hours of work if not hill-climbing against the rubric | `scrap_and_restart` recommendation in evaluator reports |
| Vague criteria → vague critiques | Granular, binary criteria produce actionable fixes (27 criteria for one app) | `acceptance_criteria` in contracts are binary testable assertions |
| Harness moves, doesn't shrink | Strip what's no longer load-bearing, add new components | Model-Adaptive Tuning table in `references/rubrics-and-tuning.md` |
| Read the traces | Primary debugging loop is reading what the agent did, finding where judgment diverged | Breadcrumbs + eval reports in `.harness/` |

### Anthropic — "Building Effective Agents"

Blog post and long-running agents series. Patterns for agent tool use and progressive complexity.

| Pattern | Repo Artifact |
|---------|---------------|
| Augmented LLM as building block | Rules and skills augment the base model with domain-specific guidance |
| Orchestrator-workers | Planner orchestrates; builder and evaluator are specialized workers |
| Evaluate-optimize loops | The build → evaluate → fix cycle in Phase 2-3 |

### OpenAI — Structured Tool Use & Eval-Driven Development

| Pattern | Repo Artifact |
|---------|---------------|
| Structured tool output for reliability | Contract JSON schema; eval report JSON schema |
| Progressive context management | Token budget enforcement in always-on rules; scoped rules loaded on demand |
| Eval-driven development | `tests/eval/` pipeline with `dataset.yaml`, `hybrid_judge.py`, `stats.py` |

### DeepMind — Planning & Self-Correction

| Pattern | Repo Artifact |
|---------|---------------|
| Planning decomposition | Planner breaks vague requests into feature-level specs |
| Reward hacking prevention | Evaluator is adversarial (separate from builder); rubric criteria are specific and binary |
| Agent self-correction through external feedback | Computational sensors (lints, tests) + inferential sensors (evaluator) provide correction signals |

### Fowler — Guides and Sensors Taxonomy (2026)

| Concept | Repo Artifact |
|---------|---------------|
| Guides (feedforward) | Planner spec, contract, rules files — steer the builder before it acts |
| Sensors (computational feedback) | Linters, type checkers, test suites — fast, deterministic quality gates |
| Sensors (inferential feedback) | Evaluator subagent — expensive, thorough adversarial testing |

## Design Principle

Every component of the harness encodes an assumption about what the model cannot do on its own. As models improve, re-examine assumptions. The model-adaptive tuning table in the adversarial harness skill tracks this explicitly.

## How to Use This Document

- **Extending the harness**: Before adding a new component, identify which assumption it encodes. If the model can already do it well, the component is not load-bearing.
- **Debugging agent behavior**: When an agent deviates from expected behavior, trace which pattern it violated and which artifact should have prevented it.
- **Onboarding**: Read this alongside the adversarial-harness SKILL.md to understand the "why" behind the "what".
