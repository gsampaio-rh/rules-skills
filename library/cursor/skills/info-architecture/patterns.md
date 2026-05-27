# Information Architecture Patterns

Concrete examples of documentation organization patterns. Use these as templates when structuring new documentation or restructuring existing docs.

---

## Pattern 1: Research Documentation

For projects that document a research investigation — exploring a problem space, comparing approaches, building toward an implementation.

### Directory Structure

```
content/docs/
  index.mdx              # Landing page: what this is, table of contents
  problem.mdx            # Explanation: why this matters
  concepts.mdx           # Reference: glossary of terms
  phenomena.mdx          # Reference + Explanation: emergent behaviors
  pipeline.mdx           # Reference: the process steps
  solution-map.mdx       # Reference: comparative table with readings
  deep-dive/             # Explanation: detailed analysis per approach
    index.mdx            # Overview + comparison table
    0-baseline.mdx       # Simplest approach
    1-analytical.mdx     # Next level
    2-statistical.mdx    # Next level
    3-calibrated.mdx     # Next level
    4-advanced.mdx       # Most sophisticated
  tools.mdx              # Reference: catalog of tools
  references.mdx         # Reference: bibliography
  mvp.mdx                # How-to + Explanation: what to build first
```

### Navigation Config

```json
{
  "title": "Docs",
  "pages": [
    "---Research---",
    "problem",
    "concepts",
    "phenomena",
    "pipeline",
    "solution-map",
    "...deep-dive",
    "tools",
    "references",
    "---Project---",
    "mvp"
  ]
}
```

### Why This Order

1. **problem** — establishes motivation; reader decides if this is relevant to them
2. **concepts** — vocabulary needed to understand everything that follows
3. **phenomena** — the specific behaviors that make the problem hard (builds on concepts)
4. **pipeline** — the process for addressing the problem (uses concepts and phenomena)
5. **solution-map** — landscape of all approaches (references pipeline steps)
6. **deep-dive/** — detailed analysis per approach (references everything above)
7. **tools** — concrete implementations (linked from deep dives)
8. **references** — bibliography (linked from everywhere)
9. **mvp** — the action plan (synthesizes everything above)

Each page builds on the previous ones. A reader going top-to-bottom accumulates context progressively.

---

## Pattern 2: Product Documentation

For projects documenting a product or library — getting started, guides, API reference.

### Directory Structure

```
docs/
  index.md                # Landing: what it does, quickstart link
  getting-started/
    index.md              # Tutorial: 5-minute setup
    installation.md       # How-to: install in different environments
    first-project.md      # Tutorial: build something real
  guides/
    index.md              # Overview of available guides
    authentication.md     # How-to: set up auth
    deployment.md         # How-to: deploy to production
    migration.md          # How-to: migrate from v1
  concepts/
    index.md              # Overview of key concepts
    architecture.md       # Explanation: how the system works
    data-model.md         # Explanation: how data flows
  reference/
    index.md              # Overview of API surface
    api.md                # Reference: REST API endpoints
    config.md             # Reference: configuration options
    cli.md                # Reference: CLI commands
  changelog.md            # Meta: version history
```

### Navigation Config

```json
{
  "pages": [
    "---Get Started---",
    "...getting-started",
    "---Guides---",
    "...guides",
    "---Understand---",
    "...concepts",
    "---Reference---",
    "...reference",
    "---Meta---",
    "changelog"
  ]
}
```

### Why This Order

Follows the reader's natural journey: try it → use it → understand it → look things up.

---

## Pattern 3: Sequential Deep Dive

For a series of pages that form a progression (approaches, phases, levels of complexity).

### Subdirectory Structure

```
deep-dive/
  index.mdx         # Overview + comparison table + difficulty map
  meta.json          # Explicit ordering
  0-baseline.mdx     # Simplest / starting point
  1-analytical.mdx   # Builds on 0
  2-statistical.mdx  # Builds on 1
  3-calibrated.mdx   # Builds on 2
  4-advanced.mdx     # Builds on 3
  5-research.mdx     # Frontier
```

### Index Page Template

```markdown
---
title: Deep Dive by Approach
description: Detailed analysis of each approach — tools, limitations, value, and pipeline coverage.
---

Detailed analysis of each approach from the [solution map](../solution-map).

## Approaches

- [0 — Baseline](./0-baseline)
- [1 — Analytical](./1-analytical)
- [2 — Statistical](./2-statistical)
- [3 — Calibrated](./3-calibrated)
- [4 — Advanced](./4-advanced)
- [5 — Research](./5-research)

---

## Comparison

| | 0 | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|---|
| **Engine** | ... | ... | ... | ... | ... | ... |
| **Maturity** | ... | ... | ... | ... | ... | ... |

---

## Difficulty Map

[Diagram showing progression from easy/ready to hard/research]
```

### Page Navigation Footer

Every page in the sequence includes a four-way navigation footer:

```markdown
---

**Previous:** [N-1 — Name](./prev) | **Next:** [N+1 — Name](./next) | **Index:** [Deep Dive](./) | **Map:** [Solution Map](../solution-map)
```

First page has no "Previous"; last page has no "Next".

### Meta Config

```json
{
  "title": "Deep Dive",
  "pages": [
    "0-baseline",
    "1-analytical",
    "2-statistical",
    "3-calibrated",
    "4-advanced",
    "5-research"
  ]
}
```

Explicit ordering in meta prevents alphabetical sorting from breaking the narrative sequence.

---

## Pattern 4: Cross-Link Map

Visualizing how pages connect to each other. Useful for audits and planning.

### Example Link Graph

```
problem ──→ concepts ──→ phenomena
  │              │            │
  │              ▼            ▼
  │         deep-dive/*    pipeline
  │              │            │
  │              ▼            ▼
  └──────→ solution-map ←────┘
                 │
                 ▼
              tools ──→ references
                 │
                 ▼
               mvp
```

### Rules for Graph Health

- **No orphans**: every page has at least one incoming link
- **No dead ends**: every page has at least one outgoing link (even if just navigation)
- **Bidirectional where possible**: if A links to B, B should ideally link back to A (or to A's parent)
- **Glossary is a hub**: the concepts/glossary page is the most linked-to page — terms defined there are referenced everywhere
- **Index pages are navigation nodes**: they link down to children and up/sideways to context

---

## Anti-Patterns

### Hub-and-Spoke Without Connections Between Spokes

```
         index
        / | | \
       A  B  C  D       ← A, B, C, D don't link to each other
```

Readers who land on A have no path to B except going back to the index. If A and B are related, link them directly.

### Flat Dump

```
docs/
  page1.md
  page2.md
  page3.md
  ...
  page27.md
```

No hierarchy, no grouping, no progression. The reader has no sense of where to start or what connects to what. Group into subdirectories when you have 8+ pages.

### Premature Nesting

```
docs/
  getting-started/
    overview/
      intro/
        page.md          ← 3 levels deep for one page
```

Don't nest until a directory has 3+ siblings. One page in a subdirectory is just friction.

### Navigation That Mirrors Code Structure

```
docs/
  src/
    components/
      button.md
    utils/
      helpers.md
    api/
      routes.md
```

This serves the developer who wrote the code, not the reader using the product. Reorganize by user intent.
