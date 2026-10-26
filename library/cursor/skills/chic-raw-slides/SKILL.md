---
name: chic-raw-slides
description: "Apply or audit the Chic Raw minimalist slide design system — exact tokens (colors, type scale, weights 300/400/500 only, spacing), drop-in base CSS, and named layout patterns (bullet, side-by-side, three-col, steps, dense-table, card-grid, fill, data panels). Use when: slide deck, presentation style, Slidev, deck.md, design system for slides, chic raw, minimalist deck, slide typography, slide layout CSS."
disable-model-invocation: false
---

# Chic Raw — Minimalist Slide Style Guide

You are a practitioner applying **Chic Raw**: a raw-but-elegant notepad aesthetic (Apple Notes × Notion) for slide decks. White background, black text, color only for semantics, never bold — max weight is medium. This file is self-contained: it does not assume any existing theme package, component library, or repo layout. Apply the tokens/CSS directly, or port them into whatever templating system the deck uses (Slidev, reveal.js, plain HTML, Vue components).

## Design Tokens

```css
:root {
  --bg: #ffffff;
  --text: #1a1a1a;
  --text-secondary: #5f6368;
  --text-tertiary: #9aa0a6;
  --border: #e8eaed;
  --green: #008744;   /* positive / good */
  --red: #d62d20;     /* negative / bad */
  --blue: #0057e7;    /* neutral highlight */
  --yellow: #ffa700;  /* caution */
}
```

| Element | Weight | Size | Letter-spacing | Line-height | Color |
|---|---|---|---|---|---|
| H1 (title) | 500 | 32px | -0.03em | 1.2 | text |
| H2 (subtitle) | 400 | 22px | -0.02em | 1.3 | text |
| H3 (sub-section) | 400 | 18px | normal | 1.4 | text-secondary |
| Section label | 500 | 13px uppercase | 0.06em | — | semantic (green/red/blue/yellow) |
| Body / bullets | 300 | 18px | normal | 1.8 | text |
| Caption | 300 | 14px | normal | 1.6 | text-tertiary |
| Code | 400 | 14px | normal | 1.6 | text (JetBrains Mono) |

Fonts: **Inter** (sans, body/UI) + **JetBrains Mono** (code only). Weight law: **300 body, 400 code/table cells, 500 titles/labels/emphasis — 600/700/800 never, anywhere** (markdown, CSS, embedded SVG). Spacing is base-8: slide padding `56px 72px`, title→body gap `32px`, between sections `24px`, between list items `4px`.

## Base Styles (drop-in)

```css
.slide { background: var(--bg); color: var(--text); font-family: 'Inter', system-ui, sans-serif;
  font-weight: 300; font-size: 18px; line-height: 1.8; padding: 56px 72px; text-align: left; }
.slide h1 { font-weight: 500; font-size: 32px; letter-spacing: -0.03em; line-height: 1.2; margin-bottom: 32px; }
.slide h2 { font-weight: 400; font-size: 22px; letter-spacing: -0.02em; margin-bottom: 24px; }
.slide h3 { color: var(--text-secondary); font-weight: 400; font-size: 18px; margin-bottom: 16px; }
.slide strong { font-weight: 500; }                       /* emphasis = medium, never bold */
.slide em { color: var(--text-tertiary); font-style: normal; font-size: 14px; } /* italic = secondary note, no slant */
.slide ul, .slide ol { padding-left: 20px; margin: 8px 0; }
.slide li { margin-bottom: 4px; }
.slide li::marker { color: var(--text-tertiary); }
.slide table { width: 100%; border-collapse: collapse; font-size: 16px; font-weight: 300; margin: 16px 0; }
.slide th { color: var(--text-tertiary); font-weight: 500; font-size: 13px; text-transform: uppercase;
  letter-spacing: 0.06em; padding: 10px 12px; border-bottom: 1px solid var(--border); text-align: left; }
.slide td { padding: 10px 12px; border-bottom: 1px solid var(--border); }
.slide table tr:last-child td { border-bottom: none; }    /* bottom rule only — no grid lines, no zebra */
.slide code { font-family: 'JetBrains Mono', monospace; font-weight: 400; }
.slide blockquote { border-left: 2px solid var(--text-tertiary); padding: 4px 20px; margin: 16px 0; }

.label { font-weight: 500; font-size: 13px; text-transform: uppercase; letter-spacing: 0.06em; display: block; margin-bottom: 8px; }
.label-green { color: var(--green); } .label-red { color: var(--red); }
.label-blue { color: var(--blue); }  .label-yellow { color: var(--yellow); }
.caption { font-size: 14px; font-weight: 300; color: var(--text-tertiary); margin-top: 24px; }
```

Hard bans: no `box-shadow`, no `border` except the single bottom rule on tables/cards, no `background-image`/gradient, no centered text (content is always left-aligned), no color applied decoratively (only through `.label-*` or a semantic token).

## How This Skill Works

### Mode 1: Style a New Deck From Scratch
1. Drop the tokens + base CSS above into the deck's global stylesheet.
2. Wrap every slide's content in `.slide` (or the deck tool's equivalent root class).
3. Write content with plain markdown/HTML elements (`h1`, `p`, `ul`, `table`) — the base CSS already renders the house style; don't add per-slide inline styling.
4. Before shipping, scan for weight/shadow/gradient/centering violations (Proactive Triggers below).

### Mode 2: Add or Fix One Slide
1. Pick the content shape (list, comparison, sequence, table, 3+2 map, data panel) and match it to a pattern below.
2. Use the matching CSS classes/markup as-is; don't invent new container classes for a shape already covered.
3. One idea per slide — if a slide does two jobs, split it into two.

### Mode 3: Audit an Existing Deck
1. Grep CSS/inline styles for `font-weight: 600/700/800`, `box-shadow`, `border-radius` beyond 4px, `gradient`, `text-align: center`.
2. Check every color use traces to a token (`--green/--red/--blue/--yellow`) or `.label-*` — flag decorative color.
3. Check tables use bottom-rule only, uppercase tertiary headers — flag zebra stripes, vertical grid lines, boxed cells.
4. Report each violation with location + the token/class that replaces it.

## Layout Patterns

| Need | Pattern | Container | Key rule |
|---|---|---|---|
| One idea + short list | bullet | `.slide` default | no extra wrapper |
| Compare two sides | side-by-side | `.sb-cols` (2-col grid) | one side `muted`, one `accent` |
| Three symmetric axes | three-col | `.tc-cols` (3-col grid) | columns never mixed topics |
| Numbered sequence | steps | `ol` with `.steps` | strong = step verb only |
| Compact metrics w/ delta | dense-table | `.dt-table` | `.delta-up/-down/-neu` |
| 3+2 card map (5 cards) | card-grid | `.cg-grid` (6-col, 2-row) | cards 4 & 5 centered |
| Needs the whole viewport | fill | `.fill-body` (flex: 1) | caption stays outside fill |
| Content almost overflows | dense | add `.dense` modifier | tighten line-height, never shrink below base sizes |
| Bars / lines / shared-legend panels | data panel | chart component or SVG | max 4 series colors = the 4 tokens |

```css
.sb-cols { display: grid; grid-template-columns: 1fr 1fr; gap: 48px; }
.sb-label { font-size: 12px; font-weight: 500; letter-spacing: 0.08em; text-transform: uppercase; color: var(--text-tertiary); }
.sb-col.accent .sb-label { color: var(--green); }

.tc-cols { display: grid; grid-template-columns: repeat(3, 1fr); gap: 32px; }

.dt-table td:nth-child(n+2) { text-align: right; font-family: 'JetBrains Mono', monospace; font-variant-numeric: tabular-nums; }
.delta-up { color: var(--green); } .delta-down { color: var(--red); } .delta-neu { color: var(--text-tertiary); }

.cg-grid { display: grid; grid-template-columns: repeat(6, 1fr); grid-template-rows: repeat(2, 1fr); gap: 22px 26px; }
.cg-card { border: 1px solid color-mix(in srgb, var(--text) 18%, white); border-top: 2px solid var(--text); }
.cg-card:nth-of-type(4) { grid-column: 2 / 4; } .cg-card:nth-of-type(5) { grid-column: 4 / 6; } /* centers 4th+5th */

.fill-body { flex: 1 1 auto; min-height: 0; }
.dense { line-height: 1.45; padding-top: 28px; padding-bottom: 18px; }
```

**Data panels** (bar/line charts, beat diagrams, stage strips, row maps) follow the same law regardless of charting library: thin strokes, no gridlines, labels instead of a legend when ≤2 series, series colors drawn only from the 4 tokens, numbers in JetBrains Mono with tabular figures. Shape the data as `{ categories: string[], series: { key, label, color, data: number[] }[] }` and let the chart render with the base tokens — don't introduce a second palette for charts.

## Proactive Triggers

- `font-weight: 600/700/800` anywhere (CSS, inline style, embedded SVG) → flag, replace with 500.
- `box-shadow`, decorative `border`, or `gradient`/`background-image` → flag, remove.
- `text-align: center` on body content → flag; Chic Raw is always left-aligned.
- A color used without tracing to a token or `.label-*` → flag as decorative, map to the closest semantic token or drop it.
- Hand-rolled grid/flex container duplicating a pattern above with different class names → flag, consolidate to the shared class.
- A slide carrying two unrelated ideas (e.g. a comparison *and* a timeline) → flag, split into two slides.

## Output Artifacts

| Ask for… | You get… |
|---|---|
| "style this deck in Chic Raw" | Tokens + base CSS wired into the deck's stylesheet, slides re-rendered with `.slide` |
| "new slide for X" | Markup using the matching pattern class(es) from the table |
| "new chart/diagram" | Data shape (`categories`/`series`) + chart wired to the 4 semantic colors, no new palette |
| "audit this deck" | Violation list (location, rule broken, token/class fix) |

## Stop Conditions

- Content doesn't match any pattern above and isn't common enough to warrant a new shared class → propose the closest existing pattern or ask before inventing a new container.
- User explicitly wants a different visual system for this deck → stop applying Chic Raw and confirm scope.
- Underlying tool can't express `left-align everywhere` or `weight ≤ 500` (e.g. a locked template) → say so explicitly rather than silently diverging from the tokens.
