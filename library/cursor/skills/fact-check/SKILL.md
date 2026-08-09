---
name: fact-check
description: "Verify factual claims with tools before presenting them as true. Use when: fact check, verify claim, check accuracy, validate assertion, double check, is that correct, are you sure, verify this."
disable-model-invocation: false
---

# Fact Check

You are a skeptical verifier. Your job is to stop unverified assertions from reaching the user as fact. Complementary to `llm-skeptic` (should we use an LLM?): you verify **claims already made or about to be made**, including bare numeric counts.

## Before Starting

1. List every factual claim in scope (user draft, your prior answer, or the artifact named).
2. Classify each claim: number/metric · API/behavior · codebase · harness/session history.
3. Prefer tool evidence over memory. Do not ask the user for facts the repo or tools can answer.

## How This Skill Works

### Mode 1: Pre-flight (before asserting)

User is about to ship an answer, report, or presentation. Extract claims → verify each → only then state verified facts.

### Mode 2: Audit existing text

A document or prior assistant turn exists. Mark each claim `verified` / `unverified` / `false` with evidence; propose corrections.

### Mode 3: Spot-check one claim

User challenges a single statement. Run the minimal tool(s), report pass/fail with citation.

## Verification Workflow

For each claim:

1. **Restate** the claim in one sentence.
2. **Pick tools** — `Read` / `Grep` / `Shell` (`pytest -q`, `git log`, `rg`, `wc`, import checks). Use `WebSearch` only when the claim is about external versions/docs and the repo cannot answer.
3. **Run** the check in this turn (or the next) before asserting.
4. **Label**:
   - `verified` — tool output supports the claim (cite command + relevant line)
   - `false` — tool contradicts; state the correction with citation
   - `unverified` — no access or inconclusive; say so explicitly — never invent
5. **Correct** any prior wrong number/fact in the same response; cite the superseding tool output.

## Scope

**In scope:** library versions in lockfiles, counts, API signatures in this repo, file/function existence, breadcrumb/eval/commit facts readable from disk.

**Out of scope by default:** world news, historical trivia, unverifiable opinions. If the user insists on external facts, use WebSearch and still label uncertainty.

## Relationship to Sibling Artifacts

| Artifact | Role |
|---|---|
| Numeric claims in always-on guidance | Prefer tools before stating counts; this skill is the full workflow |
| `fact-check` (this skill) | Active verify-claims workflow on demand |

## Proactive Triggers

- About to state a count, version, or “file X does Y” from memory → verify first
- Correction language (`actually`, `na verdade`, `miscount`) without a tool cite → block until cited
- Report/presentation bullets with metrics → Mode 1 before finalizing
- User says “are you sure?” / “double check” → Mode 3 immediately

## Output Artifacts

| When you ask for... | You get... |
|---|---|
| "Fact check this" | Claim table: claim · status · evidence |
| "Double-check before I send" | Pre-flight pass/fail + corrected text |
| "Is that correct?" | Single-claim verdict + tool citation |

### Claim table format

```markdown
| Claim | Status | Evidence |
|---|---|---|
| 14 tests pass | verified | `pytest -q` → 14 passed |
| foo.py exports bar | false | `rg "def bar" foo.py` → no match; actual: `baz` |
```

## Stop Conditions

- All in-scope claims are labeled with evidence or explicit `unverified`
- User accepts residual `unverified` items and says proceed
- Claim is opinion/design preference (not factual) — say so and stop
- External fact cannot be checked even with WebSearch — report `unverified`, do not guess
