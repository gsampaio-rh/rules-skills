---
name: session-review
description: "Review the current agent session for harness health: guideline drift, missing breadcrumbs, SVG friction, numeric hallucinations, contract-gate false positives, and missing handoffs. Use when: review session, session review, analyze transcripts, como foi essa sessão, retrospectiva."
disable-model-invocation: false
---

# Session Review

You audit agent-session health against the six RCA failure patterns (P1–P6). Your goal is a structured report — not free prose — so the next thread starts with a clean handoff.

## Before Starting

1. Resolve the review root (repo cwd, or a fixture path the user names).
2. Prefer the deterministic checker when available:
   `python3 library/cursor/skills/session-review/review.py --root <root>`
3. If `.harness/` is absent, still evaluate transcript-only patterns (P1/P3/P4); mark P2/P5/P6 as `N/A` with evidence `no harness`.

## How This Skill Works

### Mode 1: Live session audit
Review the current chat + `.harness/` artifacts. Run the mandatory procedure, emit the canonical report, stop.

### Mode 2: Fixture / corpus audit
Point `--root` at a fixture directory or transcript corpus. Same procedure and same report headings. Use this for planted P2+P6 checks and CI.

## Mandatory Procedure

Follow this order — do not skip steps:

1. **Read breadcrumbs** — last 30 lines of `.harness/breadcrumbs.jsonl` (note if missing).
2. **Count turns** — turns since the latest `session_start` breadcrumb (or from `.harness/.session-stats.json`).
3. **Check P1–P6** — against breadcrumbs + transcript (prefer `rg` / `review.py`; do not dump the full transcript unless a pattern hits).
4. **Emit the canonical report** — sections below, in order, no free-form intro.
5. **Optional checkpoint** — append a `type:"checkpoint"` breadcrumb only if the user asks to persist, or a session-boundary advisory already fired.

### Pattern checks (P1–P6)

| ID | Check | Pass | Flag |
|---|---|---|---|
| P1 guidelines drift | Sticky format/tone rules | No sticky rules, or later turns still obey | Sticky rules early + contradictory output after turn ≥10 |
| P2 breadcrumbs | Progress trail | Multi-file source edits have msg≥20 + result | source_writes≥2 without valid breadcrumb |
| P3 SVG friction | SVG write loops | No `.svg` path, or ≤2 writes per SVG | Same SVG written ≥3 times without render evidence |
| P4 number/facts | Numeric claims | Claims verified by a tool same/next turn | Claim then correction language without tool cite |
| P5 gate misfire | Contract/harness gates | No false GATE, or legitimate building task | GATE while first turns are Q&A/explore |
| P6 handoff/rework | Session boundary | Checkpoint/handoff when turns≥5 and writes≥2 | Substantial session with no handoff |

## Canonical report (emit exactly)

Copy this structure. Headings must be byte-identical. Table cell content may vary.

### Session Review

**Session:** <transcript-id-prefix or "current">
**Turns since session_start:** <N>
**Breadcrumbs read:** <N>/30
**Harness task:** <id or "none"> | status=<pending|building|evaluating|done|n/a>

### Red Flags
| Pattern | Status | Evidence |
|---|---|---|
| P1 guidelines drift | PASS\|FLAG\|N/A | <1-line evidence or "—"> |
| P2 breadcrumbs | PASS\|FLAG\|N/A | <1-line> |
| P3 SVG friction | PASS\|FLAG\|N/A | <1-line> |
| P4 number/facts | PASS\|FLAG\|N/A | <1-line> |
| P5 gate misfire | PASS\|FLAG\|N/A | <1-line> |
| P6 handoff/rework | PASS\|FLAG\|N/A | <1-line> |

### Handoff
**Pending:** yes|no
**Suggested handoff block:**
```text
Continue working on <task-id>. Read .harness/breadcrumbs.jsonl and .harness/state.json.
Last: <one-line summary>. Next: <one-line next action>.
```

### Harness Recommendations
1. <action> — <why> — <skill|hook|rule|prompt>
(max 5; ordered by severity)

### Metrics (this session)
- source_files_touched: <N>
- breadcrumb_writes: <N>
- svg_path_writes: <N> (retries: <N>)
- gate_injections: <N>
- numeric_corrections: <N>

## Proactive Triggers

- User asks to review the session, retrospectiva, or analyze transcripts
- Context-health / session-boundary advisory already fired
- Suspected missing breadcrumbs after multi-file source edits
- Suspected numeric correction without tool citation
- Long session (turns≥5) with source writes and no checkpoint

## Output Artifacts

| When you ask for... | You get... |
|---|---|
| Live session review | Canonical Markdown report (headings above) |
| Fixture audit | Same report from `review.py --root <fixture>` |
| Persist handoff | Optional `.harness/` checkpoint breadcrumb only |

## Stop Conditions

- Stop after emitting the canonical report — do not add a closing essay
- Do not modify source files — session-review is read-only against the codebase
- Writes are limited to an optional `.harness/` checkpoint breadcrumb when the user asks or a session-boundary advisory is active
- Stop if asked to re-analyze the full RCA corpus offline — point to `review.py` / fixtures instead
