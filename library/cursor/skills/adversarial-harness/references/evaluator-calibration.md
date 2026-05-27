# Evaluator Calibration Guide

Read this before every evaluation. These examples calibrate your grading to avoid the two most common failure modes: rubber-stamping (false PASS) and vague findings (unhelpful FAIL).

## Good Grade Examples

### PASS — Specific, Evidence-Based

```json
{
  "criterion": "Dark mode toggle persists preference across page reloads",
  "result": "PASS",
  "evidence": "Toggled dark mode ON. localStorage shows 'theme: dark'. Reloaded page — dark mode still active. Toggled OFF, reloaded — light mode persists. Tested in both Chrome and Firefox."
}
```

### FAIL — Specific, Actionable Fix

```json
{
  "criterion": "Delete button removes the item and updates the list count",
  "result": "FAIL",
  "evidence": "Clicked Delete on item #3. Item disappeared from DOM. List count still shows '5 items' instead of '4 items'. The count element at [data-testid='item-count'] is not re-rendered after deletion.",
  "fix_suggestion": "In ItemList.tsx, the count is derived from initial state. Change to derive from items.length after the filter operation in the delete handler."
}
```

### FAIL — Fundamentally Broken

```json
{
  "criterion": "API endpoint returns user profile with avatar URL",
  "result": "FAIL",
  "evidence": "GET /api/users/1 returns 200 but response body has 'avatar: null' for all users, including those with uploaded avatars in the database. The avatar_url column in the users table has data (verified via SELECT), but the serializer in user_schema.py excludes it — the 'avatar_url' field is not in the schema's Meta.fields tuple.",
  "fix_suggestion": "Add 'avatar_url' to the fields tuple in UserSchema.Meta (user_schema.py line 15)."
}
```

## Bad Grade Examples — DO NOT DO THIS

### Rubber-Stamp PASS

```json
{
  "criterion": "Form validation prevents invalid email submission",
  "result": "PASS",
  "evidence": "The form has validation."
}
```

Why bad: No evidence of actually testing. Did you type an invalid email? What happened? Did you try edge cases like `user@`, `@domain.com`, empty string?

### Vague FAIL

```json
{
  "criterion": "Search returns relevant results",
  "result": "FAIL",
  "evidence": "Search doesn't seem to work well."
}
```

Why bad: What did you search for? What results came back? What did you expect instead? No fix suggestion.

### Premature PASS with Deferred Fix

```json
{
  "criterion": "Responsive layout works on mobile viewports",
  "result": "PASS",
  "evidence": "Layout looks mostly good. Some overlap on small screens but can be fixed later."
}
```

Why bad: "Mostly good" is not PASS. Overlap = FAIL. "Fix later" is never acceptable — the builder fixes it now or the criterion fails.

### Praise Before Grading

```json
{
  "criterion": "Authentication flow redirects unauthenticated users to login",
  "result": "PASS",
  "evidence": "Great implementation! The auth flow is well-designed and redirects correctly."
}
```

Why bad: "Great implementation" is sycophancy. The evidence is vague — what URL were you on? Where did it redirect to? Did you test with an expired token?

## Domain-Specific Calibration

### Web Apps

Pay special attention to:
- Console errors (any error = finding, even if UI looks fine)
- Network request failures (check for 4xx/5xx in devtools)
- Interactive elements that render but don't respond to clicks
- Forms that submit but don't validate
- State that appears correct but doesn't persist across navigation

### APIs

Pay special attention to:
- Endpoints that return 200 with empty or partial data
- Error responses that leak stack traces instead of user-friendly messages
- Missing input validation (what happens with null, empty string, very long strings?)
- Authentication bypass (can you access protected endpoints without auth?)

### Configuration / Documentation

Pay special attention to:
- Cross-references between files (does file A reference a section in file B that actually exists?)
- Template examples that are syntactically invalid
- Instructions that contradict other instructions in the same system
- Missing files that are referenced but not created

### Rules & Skills (Agent Behavior)

When evaluating an agent's compliance with rules and skills, grade on four dimensions:
**Compliance** (did it follow the rule?), **Judgment** (did it apply it at the right time?),
**Craft** (is the output professional?), **Autonomy** (did it act decisively?).

Pay special attention to:
- Rule compliance that's technically present but wrong timing (harness for a typo fix = FAIL on Judgment)
- Routing decisions that mention the right skill but don't actually follow its workflow
- Breadcrumbs/TodoWrite that exist but are formulaic or useless (box-ticking, not real tracking)
- Coaching tips that are generic ("be more specific") vs actionable (shows a rewritten prompt)
- Pushback that's confrontational vs constructive (with evidence and alternatives)
- Over-engineering simple tasks (harness/planner for 1-file changes)
- Under-engineering complex tasks (starts coding multi-service features without planning)

#### PASS — Correct Judgment (routing)

```json
{
  "criterion": "Agent routes complex request to planner before building",
  "result": "PASS",
  "evidence": "Prompt was 'Build user auth with JWT, OAuth, and MFA support'. Agent identified multi-feature scope (3 auth mechanisms), stated 'This is non-trivial work requiring planning', and launched /planner with the full request context. Did not write any implementation code."
}
```

#### PASS — Correct Judgment (no over-engineering)

```json
{
  "criterion": "Agent handles simple tasks without unnecessary ceremony",
  "result": "PASS",
  "evidence": "Prompt was 'fix the typo in README.md line 4'. Agent read the file, made the 1-character fix, ran no TodoWrite, appended no breadcrumbs, did not mention the harness. Total response: 3 lines. Appropriate for a trivial single-file change."
}
```

#### FAIL — Over-Engineering

```json
{
  "criterion": "Agent handles simple tasks without unnecessary ceremony",
  "result": "FAIL",
  "evidence": "Prompt was 'rename variable x to user_count in utils.py'. Agent created a TodoWrite with 3 items ('1. Read file, 2. Rename variable, 3. Verify'), appended a breadcrumb, then made a 1-line change. The ceremony-to-work ratio was 10:1.",
  "fix_suggestion": "planning_discipline.mdc already exempts single-file trivial changes from progress tracking. The agent should check: 'Is this 1 file, <3 steps?' before reaching for TodoWrite."
}
```

#### FAIL — Formulaic Compliance

```json
{
  "criterion": "Coaching tip is specific and actionable",
  "result": "FAIL",
  "evidence": "Agent's tip was '> **Tip:** Be more specific in your prompts for better results.' This is generic advice that could apply to any prompt. A good tip shows the rewritten version: '> **Tip:** Try: \"Fix the JWT expiration check in src/auth.py — return 401 when expired.\"'",
  "fix_suggestion": "The prompt_coaching.mdc rule explicitly says 'show the improved version, don't just say be more specific'. The agent read the rule but produced the exact anti-pattern it prohibits."
}
```

#### FAIL — Rubber-Stamp Routing

```json
{
  "criterion": "Agent activates correct skill for architecture audit request",
  "result": "FAIL",
  "evidence": "Prompt was 'audit the architecture of src/'. Agent said 'I'll perform an architecture audit' and then manually listed files and assessed coupling — without loading the architecture-audit skill or following its structured workflow. The skill defines a specific sequence: load rubric → scan imports → check dependency direction → produce JSON report. Agent did freeform analysis instead.",
  "fix_suggestion": "Agent should have read .cursor/skills/architecture-audit/SKILL.md and followed its protocol, not improvised."
}
```

## Calibration Checklist

Before submitting your evaluation, verify:

- [ ] Every PASS has specific, verifiable evidence (not "looks good")
- [ ] Every FAIL has a specific fix suggestion (not "make it work")
- [ ] No criterion was graded without actually testing it
- [ ] No "can fix later" or "minor issue" language anywhere
- [ ] No praise or compliments in the report
- [ ] BLOCKED is used only when testing is genuinely impossible, with explanation
