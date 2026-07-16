---
name: svg-edit
description: "Edit or create SVG files with a validate→preview→edit procedure that prevents XML entity-escape and well-formedness bugs. Use when: svg, edit svg, fix svg, svg encoding, xml entity, amp entity."
disable-model-invocation: false
---

# SVG Edit

You edit `.svg` files safely. Most SVG failures come from rewriting markup without validating XML or checking a render — especially raw `&` in text/attributes. Follow the procedure below; do not invent shortcuts.

**Scope boundary:** This skill applies only to `.svg` paths. Generic XML or HTML editing is out of scope (not HTML, not generic XML).

## Before Starting

1. Identify the target `.svg` path (new or existing).
2. Count prior Write/StrReplace ops on that path in this session without intervening render evidence (start at 0).
3. Read the current file if it exists; do not Write until Validate and Preview are complete (except the documented stub exception below).

## How This Skill Works

### Mode 1: Fix Existing SVG
Repair a broken or incorrect `.svg`. Run Validate → Preview → Edit. Cap writes at 2 without render evidence.

### Mode 2: Create New SVG
Author a new `.svg`. Same procedure. A trivial empty-root stub (`<svg xmlns="http://www.w3.org/2000/svg"></svg>` with no child elements and no attributes beyond `xmlns`) may skip Preview only; any non-trivial content still requires Validate → Preview before the first Write/StrReplace.

## Mandatory Procedure

Do **not** Write or StrReplace the target `.svg` path before Validate and Preview are complete (stub exception only as documented in Mode 2).

### Validate

1. Confirm the target path ends in `.svg`.
2. Check XML well-formedness: matching tags, single root, no truncated markup, parseable nesting.
3. Check entity escaping for `&`, `<`, and `>` — use `&amp;`, `&lt;`, `&gt;` in text and attribute values.
4. **Warning:** a raw/unescaped `&` in SVG text or attributes breaks the file. Never leave bare `&` (use `&amp;` or a complete named/numeric entity).
5. Reject invalid nesting or unclosed elements before any edit.

### Preview

Obtain **manual** render evidence only — no hook, script, or auto-render tooling.

Accepted forms that reset the 2-write counter (use at least one):

1. Read of screenshot/image tool output for that SVG
2. Browser snapshot or screenshot showing the rendered SVG
3. Explicit user message confirming visual OK

Document which evidence you used before continuing past the write cap.

### Edit

1. Prefer the smallest StrReplace that fixes the validated issue.
2. After each Write/StrReplace, re-Validate mentally (or re-parse) before another write.
3. Hard cap: max **2** Write or StrReplace operations per target SVG path without intervening render evidence.
4. A **third** Write/StrReplace on the same path without that evidence is **forbidden**.

## Proactive Triggers

- User asks to edit, fix, or create an SVG / `.svg` file
- Broken SVG from encoding (`&amp;`, raw `&`, truncated XML)
- Agent is about to rewrite an SVG without reading or rendering first
- Repeated SVG Write/StrReplace loops without a screenshot or browser check

## Output Artifacts

- Corrected or new `.svg` file at the agreed path
- Brief note of Validate findings (well-formedness + entity escapes)
- Which Preview evidence form was used (when evidence was obtained)

## Stop Conditions

- Stop after **2** Write/StrReplace ops on the same SVG path without render evidence; obtain evidence or user direction before continuing
- Stop if the path is not `.svg` — do not use this skill for HTML or generic XML
- Stop inventing auto-render hooks/scripts; preview stays manual
- Stop batching large rewrites when a small StrReplace would fix the validated defect
