# Page Patterns Reference

Concrete examples of each content pattern. Use these as templates when writing new pages.

---

## Glossary / Concept Reference

Each term is an H2 with a stable anchor. Definition first, then context, then cross-links.

```markdown
---
title: Core Concepts
description: Glossary of foundational terms — what each means, why it matters, and where it appears.
---

Glossary of foundational terms that underpin the [approaches](./approaches). Each concept includes what it is, why it matters, and where it enters the solution space.

---

## Concept Name

One-sentence definition that stands alone. This technique does X by Y. Used in [approach N](./deep-dive/n-approach) for Z purpose.

Extended context: when it matters, what problems it solves, how it connects to other concepts in this glossary. [Related concept](./concepts#related-concept) provides the complementary perspective.

## Another Concept

Definition. Connection to [the problem](./problem). Used as the basis of [approach M](./deep-dive/m-approach).

---

**Next:** [Emergent Phenomena](./phenomena) — the behaviors that motivate more sophisticated approaches.
```

**Key traits:**
- Opening paragraph sets scope and links to where concepts are used
- Each H2 = one term (enables `#anchor` deep linking)
- Cross-links woven into prose, not listed separately
- Navigation footer at the bottom

---

## Catalog / Registry

Consistent metadata table per entry, grouped by category.

```markdown
---
title: Tool Catalog
description: Tools organized by category — simulation, analytics, forecasting, observability.
---

Tools organized by category. Each entry includes: description, version, maintainer, method, and which [approach](./approaches) it supports. Versions captured as of [date].

---

## Category Name

### Tool Name

| Field | Detail |
|---|---|
| **Language** | Python |
| **Version** | 4.1.1 |
| **Maintained by** | Organization — context on who and why |
| **Method** | Statistical / ML / Analytical / None |
| **Approaches** | 0, 3, 4 |

Descriptive paragraph explaining what the tool does, its strengths, its limitations, and how it fits into the broader landscape. Not a marketing blurb — an honest assessment.

[official-site.org](https://example.org/) · [GitHub](https://github.com/example/tool)

### Another Tool

| Field | Detail |
|---|---|
| **Language** | Java |
| ... | ... |

Description paragraph.

---

## Another Category

### ...

---

**Next:** [References](./references) — papers, repositories, and documentation.
```

**Key traits:**
- Metadata table is identical in structure across all entries
- Paragraph after table adds judgment the table can't capture
- H2 = category, H3 = individual tool
- External links at bottom of each entry

---

## Deep Dive / Explanation

Structured analysis of a topic. Header block for quick scanning, detailed breakdown below.

```markdown
---
title: "Approach N — Descriptive Name"
description: One-sentence summary of what this approach IS and its key differentiator.
---

**Engine:** [Core technology](../concepts#tech) with specific configuration or calibration.

**Tools:**
- [Tool A](../tools#tool-a) — role in this approach
- [Tool B](../tools#tool-b) — role in this approach

**Key reference:** [Paper or project](../tools#ref) — why it matters (result metric).

**Limitation:** honest assessment of what doesn't work or where it breaks down.

**Value:** why this approach matters despite its limitations. What it enables that simpler approaches cannot.

## Pipeline Coverage

Covers **M of N** steps. [Context on what that means.]

**What it covers:**

| Step | What this approach does |
|---|---|
| 1 — Step Name | Specific action in this approach |
| 2 — Step Name | Specific action in this approach |

**What it skips (and why):**

| Step | Why it's skipped |
|---|---|
| N — Step Name | Reason this approach doesn't need or can't do this step |

**Key insight:** the conceptual leap from the previous approach to this one.

---

**Previous:** [N-1 — Name](./prev) | **Next:** [N+1 — Name](./next) | **Index:** [Overview](./) | **Map:** [Solution Map](../solution-map)
```

**Key traits:**
- Bold header block for scanning: engine, tools, reference, limitation, value
- Pipeline coverage table shows exactly what the approach does at each step
- Explicit comparison to adjacent approaches
- Four-way navigation footer (prev / next / index / map)

---

## Pattern / Phenomenon

Consistent structure for each pattern: what → mechanism → mitigation → references.

```markdown
---
title: Emergent Phenomena
description: Behaviors that only appear under stress — feedback loops, cascading failures, amplification.
---

Behaviors that only appear under stress and emerge from interaction between components. These are what make simple [approaches](./approaches) insufficient and motivate the more sophisticated ones.

---

## Pattern Name

**What it is:** one-sentence definition. Service X causes Y, which feeds back into Z.

**Mechanism:** step-by-step causal chain. Latency rises → clients retry → load increases → latency rises further → more retries. The effective traffic volume grows exponentially without backoff or budget.

**Mitigation:**
- Countermeasure A — how it breaks the feedback loop
- Countermeasure B — how it limits amplification
- Countermeasure C — how it isolates the blast radius

**References:** Author (Year, venue) — one-line summary. [Link](https://example.org)

---

## Another Pattern

**What it is:** ...

**Mechanism:** ...

**Mitigation:** ...

---

**Next:** [Pipeline](./pipeline) — the steps to build and validate a simulation.
```

**Key traits:**
- Every pattern has identical structure (what / mechanism / mitigation / references)
- Mechanism section is the most detailed — explains the causal chain
- Mitigations are concrete and actionable, not vague advice
- Horizontal rules between patterns for visual separation

---

## Process / Pipeline

Numbered steps with a diagram at the top. Each step answers a question.

```markdown
---
title: "Pipeline: From Topology to Diagnosis"
description: The N steps that any implementation must traverse.
---

The steps that any implementation must traverse. Simpler [approaches](./approaches) skip steps; complete ones traverse the full pipeline.

\`\`\`mermaid
graph LR
    S1["1. Step\nOne"] --> S2["2. Step\nTwo"]
    S2 --> S3["3. Step\nThree"]
    S3 --> S4["4. Step\nFour"]
    S4 -->|"feedback"| S2
\`\`\`

---

## 1. Step Name

**Question:** what does this step answer?

**Sources:**
- **Source A** — what it provides and how
- **Source B** — what it provides and how

**Output:** what this step produces for the next step. Be specific about the data structure or artifact.

---

## 2. Step Name

**Question:** ...

---

## Coverage by Approach

Not every approach traverses the full pipeline:

| Approach | Steps covered | Notes |
|---|---|---|
| 0 — Simple | 4, 5, 6 | Skips extraction and validation |
| 3 — Calibrated | 1–7 complete | First approach with full coverage |

---

**Next:** [Deep Dive](./deep-dive) — detailed analysis of each approach.
```

**Key traits:**
- Mermaid diagram at the top showing the full flow
- Each step is an H2 with a number prefix
- Consistent structure: question → sources → output
- Coverage table at the end showing which approaches use which steps

---

## Comparative / Decision Matrix

Table first, strategic readings after.

```markdown
---
title: Solution Map
description: Comparative table — all dimensions by approach, with strategic readings.
---

Complete table — all dimensions by approach. Each column is an approach, each row is a dimension of analysis.

| | **Option A** | **Option B** | **Option C** |
|---|---|---|---|
| **Input** | ... | ... | ... |
| **Engine** | ... | ... | ... |
| **Predicts X** | ... | ... | ... |
| **Predicts Y** | ... | ... | ... |
| **Maturity** | ... | ... | ... |
| **Effort** | ... | ... | ... |

---

## Reading 1: The Value Diagonal

[Narrative interpreting the table from this specific angle — e.g., how input complexity correlates with prediction power. Name the pattern the reader should see.]

## Reading 2: The Build-vs-Buy Frontier

[Another angle — e.g., where the boundary falls between existing tools and custom work. Different insight from the same data.]

## Reading 3: The Role of [Key Factor]

[A third lens — e.g., how a specific technology or method plays different roles across options.]

---

## Practical Decision

[Synthesis: given the readings, what should the reader actually do? Direct recommendation with reasoning.]
```

**Key traits:**
- Full comparison table up front for scanning
- Named "readings" that each extract a different insight from the same data
- Each reading has a thesis, not just description
- Ends with a practical decision section

---

## References / Bibliography

Organized by topic, consistent table format.

```markdown
---
title: References
description: Papers, repositories, and documentation organized by theme.
---

Papers, repositories, and documentation organized by theme. Links to original artifacts when available.

---

## Topic Area

| Reference | Year | Type | Description |
|---|---|---|---|
| Author et al. "Title" | 2024 | Paper (Venue) | One-line summary. [Link](https://example.org) |
| Tool Name | — | Code | One-line summary. [GitHub](https://github.com/example) |

---

## Another Topic

| Reference | Year | Type | Description |
|---|---|---|---|
| ... | ... | ... | ... |
```

**Key traits:**
- Grouped by topic, not by format (papers and code live together if they address the same topic)
- Consistent table columns: reference, year, type, description with link
- Description is one line — enough to decide whether to click
- Year column enables chronological scanning
