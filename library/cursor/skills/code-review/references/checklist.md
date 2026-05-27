# Code Review Checklist

Detailed per-category checklists for thorough reviews.

## Correctness
- [ ] Logic handles all branches (if/else, switch, match)
- [ ] Edge cases: empty collections, null/None, zero, negative numbers
- [ ] Off-by-one errors in loops and slicing
- [ ] Type mismatches (string vs int, float precision)
- [ ] Exception handling: specific exceptions caught, not bare `except:`
- [ ] Race conditions in concurrent/async code
- [ ] Resource cleanup (files, connections, locks)

## Security
- [ ] All user inputs validated at API boundary
- [ ] SQL queries parameterized (no string formatting)
- [ ] No secrets hardcoded (API keys, passwords, tokens)
- [ ] No PII in logs or error messages
- [ ] Authentication required on all protected endpoints
- [ ] Authorization checks for resource access
- [ ] CORS configured correctly
- [ ] Dependencies checked for known vulnerabilities

## Supply Chain
- [ ] Lockfile is committed and diff is reviewed for unexpected new dependencies
- [ ] No unfamiliar or typosquatted packages (e.g. `python3-dateutil` vs `python-dateutil`)
- [ ] Dependencies use exact versions, not open ranges (`^`, `~`, `*`, `>=`)
- [ ] CI uses frozen install (`npm ci`, `uv sync --frozen`, `pip install --require-hashes`)
- [ ] GitHub Actions pinned by commit SHA, not tag
- [ ] No unnecessary dependencies — functionality could be implemented directly
- [ ] Packages with install scripts (`preinstall`, `postinstall`) are justified and reviewed

## Performance
- [ ] No O(n²) where O(n) or O(n log n) is possible
- [ ] Database queries: no N+1, indexes on filtered/joined columns
- [ ] No blocking I/O in async context
- [ ] Large datasets: pagination, streaming, or chunking
- [ ] Caching for expensive computations or frequent queries
- [ ] No memory leaks (unbounded lists, retained references)

## Testing
- [ ] New functionality has corresponding tests
- [ ] Happy path AND error/edge cases tested
- [ ] Assertions test behavior, not implementation details
- [ ] Tests are deterministic (no flakiness from timing, ordering, random)
- [ ] External dependencies mocked (APIs, databases, file system)
- [ ] Test names describe the scenario being tested

## Architecture
- [ ] Single responsibility: each function/class does one thing
- [ ] Dependency direction respected (domain has no infrastructure imports)
- [ ] Interfaces used for external dependencies (injectable, testable)
- [ ] No business logic in controllers/handlers
- [ ] Changes don't break existing interfaces

## Data Science
- [ ] No data leakage (future info not used in features)
- [ ] Random seeds set for reproducibility
- [ ] Train/test split respects temporal ordering (if time-series)
- [ ] Baseline comparison included in evaluation
- [ ] Feature importance or SHAP analysis for non-trivial models
- [ ] Data quality checks (missing values, outliers, dtype validation)
- [ ] No hardcoded file paths (use config or pathlib)

## Code Quality
- [ ] Functions under 50 lines, files under 300 lines
- [ ] Meaningful variable/function names
- [ ] No dead code (commented-out blocks, unused imports)
- [ ] DRY: no copy-pasted logic
- [ ] Type hints on all function signatures (Python)
- [ ] Docstrings on public API functions/classes
