---
name: organization-audit
description: >-
  Audit codebase file structure, module boundaries, cohesion, and dependency flow.
  Use when: organization audit, file structure review, module boundaries check,
  circular dependencies, code organization, project structure, cohesion analysis.
disable-model-invocation: false
---

# Organization Audit

Evaluate a codebase's file structure, module boundaries, dependency flow, and cohesion. Produces a structured report identifying structural problems and recommending reorganization.

## How This Skill Works

### Mode 1: Full Audit
Comprehensive structure audit. Maps modules, traces dependencies, assesses cohesion, produces full report.

### Mode 2: Harness Integration
Focused audit of structural changes by a feature (invoked via contract rubrics). Checks new files follow conventions.

## Proactive Triggers

Activate this skill when the user says:
- "audit organization", "check file structure", "project structure review"
- "module boundaries", "circular dependencies", "dependency check"
- "code organization", "is this well organized?"
- "where should I put this?", "structure feels messy"
- "reorganize", "restructure suggestions"

## Before Starting

1. **Load the rubric**: Read `.cursor/references/rubrics/organization.json`
2. **Determine scope**: What to audit?
   - User specified a path → audit that subtree
   - No path specified → audit the entire project structure
3. **Check project size**: This skill is most valuable for projects with 5+ source files. For tiny projects, a brief note is sufficient.

## Process

### Step 1: Map the Structure

Build a mental model of the project:

1. **List top-level directories** — what does the structure communicate?
2. **Identify module boundaries** — where are the logical groupings?
3. **Trace entry points** — how does code flow from entry to implementation?
4. **Find shared code** — what's used across multiple modules?

### Step 2: Trace Dependencies

Map how modules depend on each other:

1. **Import graph**: for each top-level module, what does it import from other modules?
2. **Direction check**: do dependencies flow in one direction or are there cycles?
3. **Boundary violations**: are internal implementations imported directly from outside?
4. **Fan-in/fan-out**: which modules have the most importers/imports?

### Step 3: Assess Cohesion

For each module/directory:

1. **Internal cohesion**: are all files in this directory related to the same concept?
2. **Feature completeness**: can you understand a feature by reading one directory?
3. **Grab-bag detection**: are there utils/helpers/misc files accumulating unrelated code?

### Step 4: Grade Each Criterion

For each criterion in the rubric:

1. **Test it** using the described method
2. **Grade** as PASS, FAIL, or NOT_APPLICABLE
3. **Evidence**: specific directory paths, import chains, file lists
4. **Fix suggestion**: concrete reorganization steps

### Step 5: Produce Report

Save to `.harness/audits/audit-organization-{timestamp}.json`:

```json
{
  "domain": "organization",
  "timestamp": "ISO-8601",
  "scope": ["."],
  "structure_map": {
    "top_level_dirs": ["src/", "tests/", "config/"],
    "module_count": 8,
    "total_source_files": 45,
    "shared_modules": ["src/common/"],
    "entry_points": ["src/main.py", "src/cli.py"]
  },
  "dependency_graph": {
    "cycles_found": 1,
    "highest_fan_out": {"module": "src/api/", "imports_from": 6},
    "boundary_violations": 3
  },
  "overall_score": "B",
  "summary": "1-2 sentence summary",
  "criteria_results": [
    {
      "id": "criterion-id",
      "result": "PASS|FAIL|NOT_APPLICABLE",
      "severity": "high|medium|low",
      "evidence": "specific evidence",
      "fix_suggestion": "concrete reorganization steps (only for FAIL)"
    }
  ],
  "score_breakdown": {
    "high_pass": 0, "high_fail": 0,
    "medium_pass": 0, "medium_fail": 0,
    "low_pass": 0, "low_fail": 0
  },
  "top_recommendations": [
    "Prioritized list of 3-5 structural improvements"
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
| F | No discernible structure (everything in root, circular deps everywhere, no modules) |

## Output Artifacts

- Structure map (top-level dirs, modules, entry points)
- Dependency graph (cycles, fan-in/fan-out, boundary violations)
- Audit report at `.harness/audits/audit-organization-{timestamp}.json`
- Prioritized recommendations (3-5 structural improvements)

## Stop Conditions

- Report produced and saved → done
- Project has fewer than 5 source files → brief note, skip full audit → done
- Cannot determine project boundaries → ask user for clarification

## Visualization

When presenting results to the user, include:
- **Directory tree** showing the current structure
- **Dependency arrows** showing import direction between modules
- **Proposed tree** showing recommended restructuring (if score is C or below)

## Integration with Adversarial Harness

When invoked as part of the harness (contract contains `"rubrics": ["organization"]`):
- Focus on whether new files are placed correctly
- Check if new modules follow existing conventions
- Verify no new circular dependencies introduced

## Red Flags (Immediate Fails)

These structural issues cause daily friction:
1. **Circular dependencies** between top-level modules — breaks builds, causes import-time errors
2. **God directories** with 20+ files at one level — impossible to navigate
3. **Mixed conventions** — some modules by feature, some by layer, no consistency
4. **Deep nesting** without purpose — `src/app/modules/core/services/internal/helpers/utils.py`
5. **Scattered feature files** — one feature's code spread across 10+ unrelated directories
