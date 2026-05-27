---
paths:
  - "**/*.py"
  - "**/*.ipynb"
---

# Python & ML Patterns

## Type Safety
- **All function signatures**: type hints on every parameter and return type, including `-> None`
- **Strict typing**: use `mypy --strict` or `pyright` in CI
- **Pydantic models**: for data validation and serialization at boundaries
- **TypedDict**: for structured dictionaries (state, configs)
- **Avoid `Any`**: be specific. `dict[str, int]` not `dict`

## Docstrings
- **Google-style docstrings**: mandatory on all public functions, methods, and classes
- **Include**: purpose, Args, Returns, Raises, and usage example where helpful
- **Skip**: obvious one-liner private helpers

## Code Formatting & Linting
- **Ruff**: primary linter and formatter (replaces black, isort, flake8)
- **Import ordering**: stdlib → third-party → local, enforced by Ruff
- **Line length**: 88 characters (Ruff default)

## Error Handling
- **Specific exceptions**: create custom exception classes for domain errors
- **Error context**: include relevant context in exception messages
- **No bare `except:`**: always catch specific exception types
- **Graceful degradation**: handle failures without crashing, log with context
- **Retry logic**: exponential backoff for transient failures (API calls, network)

## Resource Management
- **Context managers**: use `with` for files, connections, locks
- **Connection pooling**: reuse database and HTTP connections
- **Cleanup**: always release resources in `finally` blocks

## Async/Await
- **Use async**: for I/O-bound operations (API calls, database queries)
- **Concurrent execution**: `asyncio.gather()` for independent parallel operations
- **Don't mix**: don't call blocking I/O from async context without `run_in_executor`

## Code Organization
- **Import order**: stdlib → third-party → local (enforced by Ruff)
- **Barrel exports**: use `__init__.py` for public API
- **Circular dependencies**: avoid; refactor shared types into a common module
- **Constants**: `UPPER_SNAKE_CASE`, grouped in a dedicated module or at file top

## Pandas Patterns
- **Vectorized operations**: prefer `.apply()` with vectorized functions over explicit loops
- **Selection**: use `.loc[]` for label-based, `.iloc[]` for position-based. Never chain `[][]`.
- **Method chaining**: use for readable transformations: `df.query(...).groupby(...).agg(...)`
- **Categorical dtypes**: use for low-cardinality string columns (saves memory, faster groupby)
- **Copy awareness**: use `.copy()` when modifying a slice to avoid `SettingWithCopyWarning`
- **Memory**: select only needed columns early; use `dtype` parameter in `read_csv`/`read_parquet`

## ML Conventions
- **Reproducibility**: set random seeds (`random_state=42`) in all stochastic operations
- **Experiment config**: use YAML for experiment parameters, commit alongside results
- **Temporal splits**: for time-series data, always split by time (train on past, test on future). Never random split.
- **Feature leakage**: never use target-derived or future-available features as predictors
- **Model versioning**: log model parameters, metrics, and artifacts (MLflow, W&B, or manual YAML)
- **SHAP analysis**: compute feature importance for any non-trivial model

## Notebook Conventions
- **Clear sections**: use markdown cells for section headers, numbered in execution order
- **Modular cells**: one logical operation per cell (load, transform, plot)
- **Explanatory markdown**: document WHY before showing HOW
- **Reproducible**: restart kernel and run all before committing. Cells must execute in order.
- **No hardcoded paths**: use `pathlib.Path` and relative paths from project root
- **Plot standards**: `sns.set_theme(style="whitegrid")`, DPI 150, `bbox_inches="tight"`, no emojis in matplotlib text
