---
name: code-quality-audit
description: >-
  Audit code for SOLID principles, complexity, naming, DRY, coupling, and sizing.
  Use when: code quality audit, SOLID check, complexity review, code smell detection,
  coupling analysis, function sizing, quality gate, technical debt assessment.
---

# Code Quality Audit

Evaluate code against SOLID principles, complexity metrics, naming conventions, DRY compliance, and coupling/cohesion. Produces a structured report with pass/fail per criterion and prioritized fix suggestions.

## Proactive Triggers

Activate this skill when the user says:
- "audit code quality", "quality check", "code quality review"
- "SOLID check", "check SOLID principles"
- "complexity review", "too complex", "simplify this"
- "code smells", "technical debt", "tech debt assessment"
- "coupling analysis", "is this code clean?"

## Before Starting

1. **Load the rubric**: Read `.cursor/references/rubrics/code-quality.json`
2. **Determine scope**: What to audit?
   - User specified files/directories → audit those
   - "the whole project" → audit `src/` or main source directory
   - Recent changes → use `git diff` to scope
3. **Identify language**: Adjust criteria interpretation for Python, TypeScript, Go, etc.

## Process

### Step 1: Scan for Metrics

Collect quantitative data first (fast, objective):

1. **Function sizes**: count lines per function, flag >30, fail >50
2. **File sizes**: count lines per file, flag >200, fail >300
3. **Nesting depth**: check max indentation levels, fail >3
4. **Complexity**: count decision points per function (if/elif/for/while/and/or/except)
5. **Type coverage**: check for missing type hints on public functions

### Step 2: Analyze Patterns

Qualitative analysis (requires reading code):

1. **SOLID violations**: check each principle against the codebase
2. **DRY violations**: look for duplicated logic blocks
3. **Naming quality**: scan for unclear/inconsistent names
4. **Coupling**: trace import graphs, flag high fan-in/fan-out
5. **Error handling**: check try/except patterns

### Step 3: Grade Each Criterion

For each criterion in the rubric:

1. **Test it** using the described method
2. **Grade** as PASS, FAIL, or NOT_APPLICABLE
3. **Evidence**: specific file:line references, metrics, code snippets
4. **Fix suggestion**: concrete refactoring steps for failures

### Step 4: Produce Report

Save to `.harness/audits/audit-code-quality-{timestamp}.json`:

```json
{
  "domain": "code-quality",
  "timestamp": "ISO-8601",
  "scope": ["src/orders/", "src/payments/"],
  "language": "python",
  "metrics": {
    "total_functions": 42,
    "functions_over_30_lines": 3,
    "functions_over_50_lines": 1,
    "max_complexity": 8,
    "files_over_200_lines": 2,
    "type_coverage_percent": 78
  },
  "overall_score": "B",
  "summary": "1-2 sentence summary",
  "criteria_results": [
    {
      "id": "criterion-id",
      "result": "PASS|FAIL|NOT_APPLICABLE",
      "severity": "high|medium|low",
      "evidence": "specific evidence with file paths and line numbers",
      "fix_suggestion": "concrete refactoring steps (only for FAIL)"
    }
  ],
  "score_breakdown": {
    "high_pass": 0, "high_fail": 0,
    "medium_pass": 0, "medium_fail": 0,
    "low_pass": 0, "low_fail": 0
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
| F | Pervasive quality issues (no tests, god functions, no types, copy-paste everywhere) |

## Stop Conditions

- Report produced and saved → done
- Scope is empty (no source code found) → report with note → done
- Cannot determine language/framework → ask user for clarification

## Language-Specific Adjustments

### Python
- Check for type hints (PEP 484+)
- Bare `except:` is a high-severity fail
- Check for `# type: ignore` without justification

### TypeScript/JavaScript
- Check for `any` type usage
- Check for `eslint-disable` without justification
- Assess Promise handling (unhandled rejections)

### Go
- Check error handling (ignored error returns)
- Check for proper interface usage
- Assess package boundary discipline

## Integration with Adversarial Harness

When invoked as part of the harness (contract contains `"rubrics": ["code-quality"]`):
- Scope is limited to files changed by the feature
- Metric thresholds can be customized in the contract
- Results are appended to the evaluator's report

## Common Hotspots

These patterns are the highest-value fixes in most codebases:
1. **God functions** (>50 lines) — split into focused helpers
2. **Deep nesting** (4+ levels) — extract with early returns and guard clauses
3. **Duplicated validation** — extract shared validator
4. **Bare exception handlers** — catch specific exceptions, log context
5. **Missing types on public API** — add type hints to function signatures
