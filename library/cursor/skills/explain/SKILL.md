---
name: explain
description: >-
  Produce the richest output format suitable for explaining a concept, system,
  or decision. Climbs a format ladder — controlled prose → diagram → HTML page
  → video outline — and defaults one level above plain text. Use when: explain,
  understand, break down, visualize, show me how, walk me through, what is,
  how does X work, explainer.
disable-model-invocation: false
---

# Explain

Pick the format that makes the concept *land*, not the format that is easiest to write.

## Format Ladder

| Level | Format | Best for |
|-------|--------|----------|
| 1 | **ASD-STE100 prose** | Definitions, facts, short procedures |
| 2 | **Diagram** (Mermaid) | Flows, relationships, hierarchies, state machines |
| 3 | **HTML page** (Canvas) | Multi-part concepts, interactivity, animations |
| 4 | **Video outline** | Deep intuition-building, "3b1b-style" walkthroughs |

**Default rule**: start at level 2 unless the topic is trivially simple (go 1) or the user explicitly asks for a richer format.

## How This Skill Works

### Mode 1: Auto-select format

Agent picks the best format based on topic type and produces the artifact immediately.

### Mode 2: User-directed format

User specifies a level or format explicitly ("give me an HTML page", "use a diagram", "STE100"). Agent produces that format without re-evaluating.

## Selection Protocol

1. Identify the *type* of concept:
   - Fact / definition → level 1
   - Process / flow / comparison → level 2
   - System with many moving parts, or user says "interactive" / "visual" → level 3
   - Conceptual intuition that requires narrative build-up → level 4

2. If uncertain between two levels, pick the higher one and note why.

3. Never silently downgrade. If a diagram would help but you're producing prose, say so.

## Level 1 — ASD-STE100 Prose

Use Simplified Technical English constraints:
- Max 20 words per sentence
- One instruction per sentence
- Active voice only
- Approved words only — no synonyms, no metaphors
- Technical nouns defined on first use

Softening is allowed: target "80% STE100" when full compliance would hurt clarity.

## Level 2 — Diagram

Use Mermaid inline. Choose sub-type:
- `flowchart LR` for processes and decisions
- `sequenceDiagram` for interactions / protocols
- `classDiagram` for structure / relationships
- `stateDiagram-v2` for state machines
- `erDiagram` for data models

Annotate edges and nodes. Prefer horizontal layout for wide flows.

## Level 3 — HTML Page

Read and follow the **canvas** skill before producing output:
`~/.cursor/skills-cursor/canvas/SKILL.md`

Target: self-contained HTML with embedded CSS and JS. Include:
- Visual hierarchy (sections, callouts)
- At least one interactive element (toggle, animation, hover detail)
- Color coding that maps to conceptual structure, not decoration

## Level 4 — Video Outline

Produce a narration script + visual direction document:

```
## Scene 1 — Hook (0:00–0:20)
Narration: "..."
Visual: [description of what appears on screen]

## Scene 2 — Core idea (0:20–1:30)
Narration: "..."
Visual: [animation / diagram / buildup]
...
```

Note which scenes benefit from animation (e.g. build-up of a graph) vs. static visuals.
Suggest a free TTS alternative if the user has no ElevenLabs key (e.g. `edge-tts`, `Kokoro`).

## Proactive Triggers

- User says: explain, understand, break down, walk me through, what is, how does X work, visualize, show me
- User asks for a summary or overview of a complex concept
- User pastes a dense block of text or code and asks "can you make this clearer?"
- User references a topic that has non-obvious relationships or flows (good candidate for level 2+)

## Stop Conditions

- Artifact is produced and the user signals understanding
- User says "that's enough" or "got it"
- User rejects the format and prefers plain text — downgrade and proceed
- Topic is out of scope or cannot be responsibly explained without domain data the agent lacks

## Output Artifacts

| Artifact | When |
|----------|------|
| ASD-STE100 prose block | Level 1 |
| Mermaid diagram (inline) | Level 2 |
| HTML file via Canvas skill | Level 3 |
| Scene-by-scene video outline (markdown) | Level 4 |

Always state the chosen level and reason in one sentence before the artifact.
Offer an upgrade path if a higher level would meaningfully improve comprehension.
