# Development Workflow

## Document Hierarchy

Every project follows this documentation structure. Documents cross-reference each other via relative markdown links.

| Document | Purpose | Updated when |
|---|---|---|
| `docs/PRD.md` | Product requirements, goals, phases, target audience | Rarely — scope changes only |
| `docs/PLAN.md` | Sprint roadmap, pending work only | Sprint boundaries, new work added/removed |
| `docs/CHANGELOG.md` | Completed work by sprint, outcomes, decisions | Items completed — moved from PLAN.md |
| `docs/FUTURE_EXPLORATIONS.md` | Post-PoC themes, exploration backlog | New ideas surface that are out of current scope |
| `docs/adrs/NNN-slug.md` | Architecture decisions with context, trade-offs | Any non-trivial technical decision |
| `docs/ARCHITECTURE.md` | System overview, diagrams, component topology | ADRs change system topology |

## Lifecycle Rules

- **Starting new work?** Read `PLAN.md` to find the current sprint and pick a pending item.
- **Made an architecture decision?** Write an ADR in `docs/adrs/`, reference it in both `PLAN.md` and `CHANGELOG.md`.
- **Completed a sprint item?** Move it from `PLAN.md` to `CHANGELOG.md` with key outcomes.
- **Exploring something outside current sprint?** Add it to `FUTURE_EXPLORATIONS.md`, not `PLAN.md`.
- **Restructured components or topology?** Update `ARCHITECTURE.md`.
- **Don't duplicate** — each fact lives in one document and others link to it.

## ADR Conventions

- **Path:** `docs/adrs/NNN-lowercase-kebab-topic.md` (zero-padded to 3 digits)
- **Next number:** check existing files in `docs/adrs/`, increment the highest by 1
- **H1:** `# ADR-NNN: Short Descriptive Title`
- **Required sections:** Status, Date, Deciders, Context (with numbered options), Decision, Rationale, Trade-offs, Consequences

## Format Conventions

### PLAN.md
```
# Plan: <Project Name>

**Status:** Sprint N (in progress)
**Date:** YYYY-MM-DD
**Related:** [PRD](PRD.md) | [Architecture](ARCHITECTURE.md) | [ADRs](adrs/) | [Changelog](CHANGELOG.md) | [Future Explorations](FUTURE_EXPLORATIONS.md)
```
- ASCII progress bar per sprint
- Conventions line: `[ ]` = pending | `[!]` = blocked | **Gate** = required criterion
- Only pending/in-progress work lives here — completed items go to CHANGELOG.md

### CHANGELOG.md
```
# Changelog: <Project Name>

**Related:** [PLAN.md](PLAN.md) | [ADRs](adrs/) | [ARCHITECTURE.md](ARCHITECTURE.md)
```
- Sections by sprint: `## Sprint N — <Theme>`
- Each sprint has: **Date**, **PRD Phases**, **Status**, **Key Outcomes**, **Decisions** (table linking ADRs)

### FUTURE_EXPLORATIONS.md
```
# Future explorations
```
- Sections by sprint letter: `## Sprint A — <Topic>`
- Each exploration has: **Objetivo**, **Critérios de saída**, implementation notes when completed

### ADRs
```
# ADR-NNN: Title

**Status:** Accepted | Superseded by ADR-XXX
**Date:** YYYY-MM-DD
**Deciders:** <team or role>
```
- Context with numbered options considered
- Decision, Rationale, Trade-offs, Consequences
