---
name: architecture-audit
description: >-
  Audit a codebase for DDD, Clean Architecture, and Hexagonal patterns compliance.
  Use when: audit architecture, check DDD, architecture review, dependency direction,
  clean arch compliance, bounded contexts, hexagonal audit, layering violations.
disable-model-invocation: false
---

# Architecture Audit

Evaluate a codebase against DDD, Clean Architecture, and Hexagonal Architecture principles. Produces a structured report with pass/fail per criterion and actionable fix suggestions.

## How This Skill Works

### Mode 1: Full Audit
Comprehensive architecture audit of the specified scope. Maps layers, grades all criteria, produces full report.

### Mode 2: Harness Integration
Focused audit of files changed by a feature (invoked via contract rubrics). Checks new code follows existing patterns.

## Proactive Triggers

Activate this skill when the user says:
- "audit architecture", "check architecture", "architecture review"
- "DDD compliance", "check DDD", "domain-driven design audit"
- "clean architecture check", "dependency direction", "layering violations"
- "hexagonal audit", "ports and adapters check"
- "is this well-architected?"

## Before Starting

1. **Load the rubric**: Read `.cursor/references/rubrics/architecture.json`
2. **Determine scope**: What directories/modules to audit?
   - User specified a path → audit that path
   - No path specified → audit the entire `src/` or project root
3. **Check applicability**: Does this project have domain logic worth auditing?
   - If it's a simple script, CRUD app, or prototype with no domain layer, report "Not Applicable" with reasoning
   - If it's a project that SHOULD have architecture but doesn't, that's a finding (not a skip)

## Process

### Step 1: Map the Architecture

Before grading criteria, understand what exists:

1. Identify the top-level structure (directories, modules)
2. Determine if layers exist (domain, application, infrastructure, presentation)
3. Map the dependency graph between top-level modules
4. Identify entry points (API routes, CLI commands, event handlers)

Document your findings in a brief architecture map before grading.

### Step 2: Grade Each Criterion

For each criterion in the rubric:

1. **Test it** using the method described in `how_to_test`
2. **Grade it** as PASS, FAIL, or NOT_APPLICABLE
3. **Provide evidence**: specific file paths, line numbers, import statements
4. **Suggest fixes** for failures — concrete, actionable, not vague

### Step 3: Evidence Collection Methods

| evidence_type | How to collect |
|---|---|
| `file_grep` | Use Grep tool to search for specific import patterns |
| `file_location` | Use Glob tool to check where files live in the directory tree |
| `code_analysis` | Read source files and analyze structure, signatures, logic |
| `dependency_analysis` | Trace imports between modules, build dependency map |
| `naming_analysis` | Read class/function names and compare against domain terminology |
| `test_analysis` | Read test files to check what infrastructure they require |

### Step 4: Produce Report

Save to `.harness/audits/audit-architecture-{timestamp}.json`:

```json
{
  "domain": "architecture",
  "timestamp": "ISO-8601",
  "scope": ["src/"],
  "architecture_map": {
    "layers_detected": ["domain", "application", "infrastructure"],
    "entry_points": ["src/api/main.py"],
    "key_modules": ["orders", "payments", "users"]
  },
  "overall_score": "B",
  "summary": "1-2 sentence summary of findings",
  "criteria_results": [
    {
      "id": "criterion-id",
      "result": "PASS|FAIL|NOT_APPLICABLE",
      "severity": "high|medium|low",
      "evidence": "specific evidence with file paths and line numbers",
      "fix_suggestion": "concrete fix (only for FAIL)"
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
| F | Fundamental violations (no layer separation, business logic in controllers everywhere) |

## Output Artifacts

- Architecture map (layers, entry points, key modules)
- Audit report at `.harness/audits/audit-architecture-{timestamp}.json`
- Prioritized recommendations (3-5 most impactful improvements)

## Stop Conditions

- Report produced and saved → done
- Project is not applicable (simple script, no domain logic) → report NOT_APPLICABLE with reasoning → done
- Cannot access code (permissions, missing files) → report BLOCKED → done

## References

Load these for deeper context when grading:
- `.cursor/references/patterns/ddd.md`
- `.cursor/references/patterns/clean-architecture.md`
- `.cursor/references/patterns/hexagonal.md`

## Integration with Adversarial Harness

When invoked as part of the harness (contract contains `"rubrics": ["architecture"]`):
- Scope is limited to files changed by the feature
- Results are appended to the evaluator's report
- `rubric_mode` in contract determines if failures block (strict) or warn (warn)

## Anti-Patterns to Watch For

These are the most common architecture failures in practice:
1. **Fat controllers** — business logic in route handlers (most common)
2. **Anemic domain** — entities are data bags, all logic in services
3. **Framework coupling** — domain objects decorated with ORM/framework annotations
4. **God services** — one service class with 15+ methods spanning multiple concerns
5. **Shared database** — multiple bounded contexts reading/writing the same tables directly
