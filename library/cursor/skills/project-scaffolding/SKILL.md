---
name: project-scaffolding
description: "Scaffold a new project structure. Use when: start new project, create project structure, set up repo, initialize project, project layout, folder structure."
disable-model-invocation: true
---

# Project Scaffolding

You are an experienced software architect. Your goal is to set up a project structure that is clean, scalable, and appropriate for the problem — not over-engineered, not under-structured.

For architectural pattern deep-dives, see `.cursor/references/patterns/`.

## Before Starting

Check what already exists: `README.md`, `pyproject.toml`, `package.json`, existing source files. If the project has an existing structure, adapt rather than replace.

## How This Skill Works

### Mode 1: ML / Data Science Project
Notebooks, experiments, data pipelines, model training.

### Mode 2: Full-Stack Application
Backend API + frontend UI, shared types, monorepo.

### Mode 3: API Service
Backend-only service with domain logic, infrastructure, and API layer.

### Mode 4: Python Library / Package
Publishable package with src layout, docs, CI/CD.

## Architecture Selection

Don't prescribe an architecture blindly. Reason about fit:

- **Data pipeline / ML project**: simple modular layout is better than forcing DDD. Separate data, features, models, and visualization. Notebooks at the top level.
- **API service with complex domain**: hexagonal or clean architecture gives testability at the cost of boilerplate. Worth it when business logic is the competitive advantage.
- **Simple CRUD API**: layered architecture (routes → services → repositories) is sufficient. Don't add ports/adapters for a TODO app.
- **Library / package**: src layout with clear public API. Focus on documentation and test coverage.

## Common Conventions (All Modes)

### File Naming
- **Python modules**: `snake_case.py`
- **Classes**: `PascalCase`
- **Functions/Variables**: `snake_case` (Python) or `camelCase` (TypeScript)
- **Constants**: `UPPER_SNAKE_CASE`

### Module Sizing
- **Files**: max 300 lines (ideally under 200)
- **Functions**: max 50 lines (ideally under 20)
- **Classes**: max 500 lines (ideally under 200)

## Mode 1: ML / Data Science

```
project_root/
├── data/                # Raw and processed data (gitignored)
│   ├── raw/             # Original, immutable data
│   └── processed/       # Cleaned, transformed data
├── notebooks/           # Jupyter notebooks (numbered: 01_, 02_)
├── src/                 # Python source code
│   ├── data/            # Data loading and processing
│   ├── features/        # Feature engineering
│   ├── models/          # Model definitions and training
│   └── visualization/   # Plotting utilities
├── experiments/         # Experiment configs and results
├── tests/               # Test suite
├── outputs/             # Generated outputs (plots, metrics, reports)
├── configs/             # Configuration files (YAML)
├── pyproject.toml       # Dependencies and project metadata
└── README.md
```

### Dependency Rules
- `src/data/` → no dependencies on models or features
- `src/features/` → can import from `src/data/`
- `src/models/` → can import from `src/features/` and `src/data/`
- Notebooks import from `src/`, never the reverse

## Mode 2: Full-Stack Application

```
project_root/
├── backend/
│   ├── src/
│   │   ├── domain/          # Core business logic (no external deps)
│   │   ├── application/     # Use cases, workflows
│   │   ├── infrastructure/  # External deps (DB, APIs, queues)
│   │   └── api/             # API layer (REST/GraphQL)
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── components/      # UI components
│   │   ├── pages/           # Page components
│   │   ├── services/        # API client services
│   │   └── store/           # State management
│   └── tests/
├── shared/                  # Shared types and schemas
└── docs/
```

### Dependency Rules
- `domain/` → no imports from application, infrastructure, or api
- `application/` → domain only
- `infrastructure/` → domain + application (implements interfaces)
- `shared/` → no dependencies on backend or frontend

## Mode 3: API Service

```
project_root/
├── src/
│   ├── domain/          # Core business logic, entities, value objects
│   ├── application/     # Use cases, DTOs, service interfaces
│   ├── infrastructure/  # Database, external APIs, messaging
│   └── api/             # HTTP handlers, middleware, routing
├── tests/
├── configs/
└── pyproject.toml
```

### Dependency Rules
Same as backend in Mode 2. Domain has zero external dependencies.

## Mode 4: Python Library / Package

```
project_root/
├── src/
│   └── package_name/    # Source code
│       ├── __init__.py  # Public API exports
│       ├── core.py      # Core functionality
│       └── utils.py     # Internal utilities
├── tests/
├── docs/
├── pyproject.toml       # Build config, dependencies, metadata
├── README.md
├── CHANGELOG.md
└── LICENSE
```

## Security Scaffolding

Every new project should include these supply chain protections from day zero:

- **`.gitignore`**: include `.env`, `data/`, credentials, and OS artifacts
- **Lockfiles**: commit `package-lock.json`, `uv.lock`, or `poetry.lock` — never `*`-ignore them
- **CI frozen installs**: use `npm ci` / `uv sync --frozen` / `pip install --require-hashes` in pipelines
- **GitHub Actions by SHA**: pin actions to commit hash, not tag (tags can be hijacked)
- **Dependency audit in CI**: add `npm audit` / `pip-audit` as a pipeline step

## Proactive Triggers

- **No `.gitignore`** → risk of committing data, secrets, or build artifacts
- **No test directory** → testing will be an afterthought
- **Flat structure with >10 files** → time to organize into modules
- **Business logic in API layer** → suggest moving to domain/application
- **Data files in git** → suggest `.gitignore` + DVC or cloud storage
- **No lockfile committed** → supply chain risk, add and commit lockfile
- **Open dependency ranges** (`^`, `>=`, `*`) → pin exact versions

## Output Artifacts

| When you ask for... | You get... |
|---|---|
| "Scaffold an ML project" | Full directory structure, pyproject.toml, .gitignore, README |
| "Scaffold an API service" | Layered structure with domain/application/infrastructure, tests |
| "Scaffold a full-stack app" | Backend + frontend monorepo with shared types |
| "Scaffold a Python package" | src layout with build config, docs, CI templates |

## Stop Conditions

- Requirements are unclear and the right mode can't be determined
- Existing project has a mature structure that shouldn't be disrupted
- Team has strong opinions about structure that conflict with these modes (defer to team)
