---
name: design-audit
description: >-
  Audit UI/UX for design system compliance, accessibility, visual hierarchy, and responsiveness.
  Use when: design audit, accessibility check, a11y review, UI review, design system compliance,
  visual hierarchy, responsiveness check, WCAG audit, design quality.
---

# Design Audit

Evaluate a user interface against design system compliance, accessibility standards (WCAG AA), visual hierarchy, responsiveness, and interaction quality. Produces a structured report with actionable findings.

## Proactive Triggers

Activate this skill when the user says:
- "audit design", "design review", "UI audit", "UX review"
- "accessibility check", "a11y audit", "WCAG compliance"
- "design system compliance", "check tokens", "visual consistency"
- "responsive check", "mobile test", "breakpoint test"
- "is this accessible?", "does this look good?"

## Before Starting

1. **Load the rubric**: Read `.cursor/references/rubrics/design-ui.json`
2. **Load design principles**: Read `.cursor/rules/design_principles.mdc` for philosophy context
3. **Load design system reference**: Read `.cursor/references/design/design-systems/design-systems.md` for token/component standards
4. **Determine scope**: What to audit?
   - User specified components/pages → audit those
   - "the whole app" → audit main pages and shared components
   - A specific PR → audit changed UI files
5. **Check applicability**: Does this project have a UI?
   - CLI tool, API-only, data pipeline → report NOT_APPLICABLE
   - Has React/Vue/Svelte/HTML → proceed

## Process

### Step 1: Identify the UI Surface

1. **Find component files**: Glob for `*.tsx`, `*.vue`, `*.svelte`, `*.html`
2. **Find style files**: Glob for `*.css`, `*.scss`, `*.module.css`, tailwind configs
3. **Find token/theme files**: Look for theme.ts, tokens.json, CSS custom properties, tailwind.config
4. **Identify pages/routes**: Find top-level page components

### Step 2: Static Analysis (Code-Level)

Check without running the app:

1. **Accessibility in code**:
   - aria-label on icon buttons
   - htmlFor on labels
   - alt text on images
   - Semantic HTML elements (nav, main, aside, article)
   - Role attributes on custom interactive elements
   - Focus management in modals/dialogs

2. **Design tokens usage**:
   - Raw hex/rgb colors outside theme files
   - Arbitrary spacing values (not on the scale)
   - Hardcoded font sizes outside the type scale
   - Inline styles overriding tokens

3. **Component API consistency**:
   - Prop naming conventions across similar components
   - Consistent size/variant/state patterns
   - Composability vs monolithic props

### Step 3: Visual/Runtime Analysis (Browser-Level)

If browser tools are available:

1. **Contrast check**: Evaluate text/background contrast ratios
2. **Keyboard navigation**: Tab through all interactive elements
3. **Responsive test**: Check at 320px, 768px, 1024px viewports
4. **Focus indicators**: Verify visible focus on tab
5. **Interaction states**: Hover, active, disabled appearances
6. **Loading states**: Trigger async actions, check for feedback

If browser tools are NOT available, note which criteria require runtime testing and mark them BLOCKED (not failed).

### Step 4: Grade Each Criterion

For each criterion in the rubric:

1. **Test it** using the appropriate method (static or runtime)
2. **Grade** as PASS, FAIL, BLOCKED, or NOT_APPLICABLE
3. **Evidence**: file paths, component names, screenshots (if browser available)
4. **Fix suggestion**: specific code changes, not vague "improve accessibility"

### Step 5: Produce Report

Save to `.cursor/harness/audits/audit-design-ui-{timestamp}.json`:

```json
{
  "domain": "design-ui",
  "timestamp": "ISO-8601",
  "scope": ["src/components/", "src/pages/"],
  "ui_surface": {
    "component_count": 24,
    "page_count": 6,
    "has_design_tokens": true,
    "css_framework": "tailwind",
    "component_library": "radix-ui"
  },
  "overall_score": "B",
  "summary": "1-2 sentence summary",
  "criteria_results": [
    {
      "id": "criterion-id",
      "result": "PASS|FAIL|BLOCKED|NOT_APPLICABLE",
      "severity": "high|medium|low",
      "evidence": "specific evidence with file paths, component names",
      "fix_suggestion": "concrete fix (only for FAIL)"
    }
  ],
  "score_breakdown": {
    "high_pass": 0, "high_fail": 0, "high_blocked": 0,
    "medium_pass": 0, "medium_fail": 0, "medium_blocked": 0,
    "low_pass": 0, "low_fail": 0, "low_blocked": 0
  },
  "top_recommendations": [
    "Prioritized list of 3-5 most impactful improvements"
  ]
}
```

### Score Mapping

| Score | Criteria |
|---|---|
| A | All high-severity pass, at most 1 medium fail |
| B | At most 1 high-severity fail |
| C | 2-3 high-severity fails |
| D | 4+ high-severity fails |
| F | No accessibility considerations, no design tokens, no responsive design |

BLOCKED criteria do not count against the score but are reported separately.

## Stop Conditions

- Report produced and saved → done
- Project has no UI (API-only, CLI, data pipeline) → report NOT_APPLICABLE → done
- Browser tools unavailable → complete static analysis, mark runtime criteria as BLOCKED → done
- Cannot identify UI framework → ask user for clarification

## References

Load these for deeper context:
- `.cursor/references/design/design-systems/design-systems.md` — tokens, component API
- `.cursor/references/design/design-thinking/design-thinking.md` — user-centered approach
- `.cursor/references/design/ux-research/ux-research.md` — research methods
- `.cursor/references/design/data-visualization/data-visualization.md` — chart/data UI

## Integration with Adversarial Harness

When invoked as part of the harness (contract contains `"rubrics": ["design-ui"]`):
- Scope is limited to UI components changed by the feature
- Runtime testing is expected (evaluator has browser access)
- Accessibility failures at high severity BLOCK verification in strict mode

## Critical Accessibility Failures

These MUST be caught — they represent legal/ethical compliance issues:
1. **No keyboard access** to interactive elements — users can't use the app without a mouse
2. **Missing form labels** — screen readers can't identify inputs
3. **Contrast below 3:1** — text is unreadable for low-vision users
4. **No focus indicators** — keyboard users can't see where they are
5. **Images without alt text** — screen readers skip important content
6. **Auto-playing media without controls** — users can't stop unwanted audio/video
