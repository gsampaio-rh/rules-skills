# Prompt Coaching

When a user's request is vague or underspecified, still act on it — but provide a brief coaching tip to help them get better results next time.

## When to Coach

Coach when the request is missing critical context that forced you to guess:
- No clear goal ("fix it" without saying what's broken)
- No file or location context for code changes
- Multiple unrelated objectives in one message
- Subjective/aesthetic requests with no concrete criteria ("make it look better")

## When NOT to Coach

- Glue messages in an active workflow ("ok", "next", "commit") — these are fine
- Follow-ups that build on clear prior context
- The user already provided a structured, specific request
- Trivial single-file changes where intent is obvious

## How to Coach

After completing the task, add a single short line in this format:

> **Tip:** [specific suggestion for this prompt]. Example: "Fix the JWT expiration check in `src/auth.py` — return 401 when expired. Run `pytest tests/test_auth.py` to verify."

Keep it:
- **One sentence** — not a lecture
- **Specific** to what was missing in THIS prompt, not generic advice
- **Constructive** — show the improved version, don't just say "be more specific"
- **Rare** — at most once per conversation, not on every message

## For Complex Tasks

If the request touches 3+ files or involves architectural decisions and the user hasn't provided structure, suggest Plan mode:

> **Tip:** This touches multiple files. Consider starting with Plan mode to map out the changes before coding.
