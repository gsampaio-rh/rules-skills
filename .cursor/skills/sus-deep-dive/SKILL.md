---
name: sus-deep-dive
description: "Investigate health conditions in SUS/DATASUS data. Use when: analyze SUS data, investigate disease, health condition analysis, SIH data, DATASUS, hospital admissions, epidemiology, public health Brazil, SUS investigation."
disable-model-invocation: false
---

# SUS Deep-Dive Investigation

You are an expert in Brazilian public health data analysis. Your goal is to investigate health conditions using SUS data (SIH, CNES, SIM, SINAN) with publication-grade rigor — producing insight that changes how people think about the problem.

For code tables and data reference, see `references/sus-data-reference.md`.

## Before Starting

Check for existing analysis: notebooks in `experiments/<condition>/`, prior FINDINGS.md, EXPERIMENT.md. Build on what exists.

## How This Skill Works

### Mode 1: New Investigation
No prior analysis. Start from ICD-10 code and data loading through full 7-step workflow.

### Mode 2: Deepen Existing Investigation
Analysis exists. Push past first-order findings, add ML modeling, policy simulation.

## Data Sources

All data lives in `data/` as parquet files downloaded from DATASUS via PySUS.

| System | Content | Folder | File pattern |
|---|---|---|---|
| SIH | Hospital admissions (AIH) | `data/sih/` | `RDSPYYMM.parquet` |
| CNES | Facility data, beds, equipment | `data/cnes/` | `STSPYYMM.parquet` |
| SIM | Death records | `data/sim/` | By year |
| SINAN | Disease notifications | `data/sinan/` | By disease code |
| SINASC | Birth records | `data/sinasc/` | By year |

### Loading Pattern

```python
import pandas as pd
from pathlib import Path

sih_dir = Path("data/sih")
files = sorted(sih_dir.glob("RDSP*.parquet"))
frames = []
for f in files:
    df = pd.read_parquet(f)
    available = [c for c in DESIRED_COLS if c in df.columns]
    frames.append(df[available])
sih = pd.concat(frames, ignore_index=True)
```

### Critical Gotchas

- **STRINGS, not integers**: `SEXO` is `"1"`/`"3"`, `CAR_INT` is `"01"`/`"02"`. `kidney["SEXO"] == 1` silently returns all False.
- **Date parsing**: `DT_INTER` is string `YYYYMMDD`. Use `pd.to_datetime(col, format="%Y%m%d", errors="coerce")`
- **Age encoding**: check `COD_IDADE` before using `IDADE`. `COD_IDADE=4` means years; 2=days, 3=months
- **Municipality codes**: 6-digit IBGE codes. São Paulo capital = 355030. When `MUNIC_RES != MUNIC_MOV`, patient migrated for treatment.
- **Column availability**: not all columns exist in every year. Always filter: `available = [c for c in desired if c in df.columns]`
- **Partitioned parquet**: files are directories, not single files. `pd.read_parquet()` handles both.
- **Large datasets**: SIH has millions of rows. Select only needed columns early.

## Investigation Workflow

### Step 1: Data Loading
- Load SIH parquets, filter by ICD-10 prefix (e.g., `DIAG_PRINC.str.startswith("N20")`)
- Parse dates, convert numeric columns, validate record counts
- Load relevant CNES data for facility characteristics
- Save filtered dataset to `outputs/` for downstream use

### Step 2: Exploratory Data Analysis
- Yearly admission trend (growth? decline? inflection point?)
- Seasonality (monthly distribution, seasonal patterns)
- Demographics (age groups, sex distribution, changes over time)
- Geography (top municipalities, urban vs interior, hotspot mapping)
- Sub-diagnosis breakdown (ICD-10 sub-codes within the condition)
- Severity indicators (average stay, cost, mortality over time)
- Save all plots to `outputs/plots/` and summary metrics to `outputs/metrics/`

### Step 3: Hypothesis Generation
After EDA, formulate hypotheses. Common patterns:
- **Procedure shift**: did a new procedure code appear and drive volume?
- **Access gap**: are patients migrating across cities for treatment?
- **Demographic shift**: is one sex/age group driving growth disproportionately?
- **Seasonal anomaly**: did a previously seasonal condition lose its pattern?
- **Cost anomaly**: is cost per admission rising faster than volume?

### Step 4: Hypothesis Testing
- Decompose trends by procedure code, facility type, admission type
- Compare migration rates between cities with/without specific procedures
- Statistical tests where appropriate (chi-square, t-tests, Mann-Whitney)
- Save test results to `outputs/metrics/hypothesis_tests.json`

### Step 5: ML Modeling
Build a patient-level model to understand drivers of the key outcome variable (usually `DIAS_PERM` for length of stay).

**Leakage prevention — DO NOT use as features:**
- `DIAS_PERM` derivatives (pct_gt7d, avg_stay) — these ARE the target
- `MORTE` — outcome, not predictor
- `MARCA_UTI` — outcome-adjacent
- `VAL_TOT` — directly correlated with stay length

**Temporal split**: train on earlier years, test on recent years. Never random split.

**SHAP analysis**: always compute and produce:
1. Feature importance bar chart
2. Beeswarm plot (per-patient impact)
3. Interaction dependence plots (top 3 pairs)

### Step 6: Policy Simulation
Use the trained model for counterfactual predictions:
- Identify hospitals with modifiable characteristics (high ER rate, low procedure adoption)
- Simulate interventions by modifying feature values in test data
- Quantify: bed-days saved, beds freed, cost saved (R$ 466/bed-day SUS average), deaths prevented

### Step 7: Executive Summary
- One-page summary plot with headline numbers
- Generate `outputs/FINDINGS.md` with methodology section
- Include data sources, split strategy, model specification

## Output Standards

### Plot Naming
`outputs/plots/NN_description.png` where NN = notebook number (01-06).

### Plot Style
```python
import seaborn as sns
sns.set_theme(style="whitegrid", palette="deep", font_scale=1.1)
# DPI: 150, bbox_inches="tight", no emojis (matplotlib can't render them)
```

### Experiment Folder Structure
```
experiments/<condition>/
  README.md
  EXPERIMENT.md
  notebooks/
    01_data_loading.ipynb
    02_exploratory.ipynb
    03_hypothesis_testing.ipynb
    04_ml_model.ipynb
    05_simulation.ipynb
    06_executive_summary.ipynb
  outputs/
    plots/
    metrics/
    FINDINGS.md
```

## Proactive Triggers

- **String vs integer comparison detected** → warn about SUS categorical encoding gotcha
- **Random train/test split on time-series data** → flag as data leakage risk
- **Outcome variable used as feature** → flag immediately
- **No baseline comparison** → model results are uninterpretable without baseline
- **No SHAP analysis for non-trivial model** → request it before interpreting results

## Output Artifacts

| When you ask for... | You get... |
|---|---|
| "Investigate [condition]" | Full 7-step workflow from data loading to executive summary |
| "Explore SIH data for [ICD code]" | EDA with trends, demographics, geography, and hypotheses |
| "Build a model for [outcome]" | LightGBM with temporal split, SHAP analysis, and leakage checks |
| "Simulate policy intervention" | Counterfactual predictions with quantified impact |

## Stop Conditions

- ICD-10 code yields too few records (<100) for meaningful analysis
- Data quality issues discovered that undermine conclusions (flag and quantify)
- Findings have policy implications requiring domain expert review
- Multiple plausible interpretations that data cannot distinguish
