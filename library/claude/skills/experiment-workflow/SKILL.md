---
name: experiment-workflow
description: "Run an experiment from design to report. Use when: set up experiment, run experiment, design experiment, experiment lifecycle, create EXPERIMENT.md, analyze results, write findings."
disable-model-invocation: false
---

# Experiment Workflow

You are an expert in rigorous experiment design and execution. Your goal is to guide experiments from hypothesis through analysis to publication-grade findings.

## Before Starting

Check for existing experiment files: `EXPERIMENT.md`, `PROJECT_CHECKLIST.md`, experiment YAML configs. Use existing context, only ask for what's missing.

## How This Skill Works

### Mode 1: Design a New Experiment
Starting fresh — no existing experiment documents.

### Mode 2: Execute an Existing Experiment
`EXPERIMENT.md` exists. Follow the lifecycle from current phase forward.

### Mode 3: Analyze Completed Experiment
Raw data exists. Run analysis and generate findings.

## Experiment Directory Structure

```
docs/experiments/<experiment_name>/
  EXPERIMENT.md          # Hypotheses, design, scoring, conditions
  PROJECT_CHECKLIST.md   # Phase-by-phase tracker
configs/<experiment_name>/
  experiment.yaml        # Declarative config: models, params, paths
output/<experiment_name>/
  trials.jsonl           # Raw trial data
  run.log                # Execution log
analysis/<experiment_name>/
  analyze.py             # Aggregation, metrics, plots
  plots/                 # Generated figures
  FINDINGS.md            # Technical findings report
```

## Lifecycle

### Phase 1: Design (before any code)
- Write `EXPERIMENT.md` using `${CLAUDE_SKILL_DIR}/templates/experiment.md`
- Hypotheses must be directional and falsifiable: "As X increases, Y decreases"
- Define metrics and how each maps to a hypothesis
- Define null baseline condition

### Phase 2: Implement
- Domain logic first (pure scoring, selection), infrastructure second, orchestration last
- Write tests at each layer before moving to the next
- Configuration in YAML, committed alongside code

### Phase 3: Validate
- Dry run (3 prompts, 2 conditions) before full execution
- Check that scores have variance across conditions
- Fix design issues BEFORE the full run

### Phase 4: Execute
- Run the full grid. Log everything.
- Do NOT stop early based on intermediate results
- Back up previous data before re-running

### Phase 5: Analyze
- Analysis script must be deterministic: same input → identical output
- Report per-condition aggregates with error bars
- Run per-factor breakdowns to find where effects concentrate
- Include at least one robustness check

### Phase 6: Report
- Write findings AFTER analysis is complete. Never write conclusions first.
- Every claim must reference a specific metric and confidence interval.
- Use `${CLAUDE_SKILL_DIR}/templates/findings.md` for structure.
- Include a "Limitations" section.

## Proactive Triggers

Surface these without being asked:
- **No baseline condition defined** → experiment cannot measure effect size
- **No pre-registered hypotheses** → risk of retrofitting conclusions to data
- **Metrics have zero variance** → experiment cannot test its hypothesis
- **Multiple variables changed** → confounded results, flag as limitation
- **Missing error bars in plots** → results cannot be interpreted

## Output Artifacts

| When you ask for... | You get... |
|---|---|
| "Design an experiment" | EXPERIMENT.md with hypotheses, conditions, metrics, and config YAML |
| "Run the experiment" | Execution with logging, dry-run validation first |
| "Analyze results" | Analysis script, plots with error bars, per-condition breakdown |
| "Write findings" | FINDINGS.md with claims tied to metrics and confidence intervals |

## Stop Conditions

- Hypotheses cannot be made falsifiable with available data
- Metrics do not map clearly to hypotheses
- Required data sources are unavailable
- Results contradict each other and need human interpretation
