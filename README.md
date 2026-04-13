# Cursor Rules & Skills

A curated set of AI coding assistant rules and skills for Cursor, built for data science, ML, full-stack development, and research workflows.

## What's Inside

### Rules (`.cursor/rules/`)

Passive, always-on constraints that shape how the AI agent writes code and communicates.

| Rule | Activation | What it does |
|---|---|---|
| `agent_behavior` | Always on | Communication style, change management, information handling |
| `autonomous_execution` | Always on | Act without asking permission, fix errors autonomously, pause on destructive ops |
| `code_standards` | Always on | Explicit > implicit, single responsibility, naming, DRY |
| `critical_thinking` | Always on | Analyze requests, challenge assumptions, improve vague prompts |
| `security` | Always on | Input validation, data protection, dependency scanning |
| `architecture` | `*.py, *.ts, *.tsx` | SOLID, dependency direction, pattern selection with trade-off reasoning |
| `python_ml` | `*.py, *.ipynb` | Type hints, pandas patterns, ML conventions, notebook standards |
| `testing` | `**/test*.py` | Pytest conventions, ML testing, contract testing |
| `research_standards` | `experiments/**` | Pre-registration, statistical rigor, honest reporting |
| `causal_rigor` | `experiments/**` | 5-test framework to avoid circular/obvious findings |
| `design_principles` | Intelligent load | Dieter Rams, BJ Fogg, Steve Jobs, Jony Ive — design philosophy |

### Skills (`.cursor/skills/`)

Active, task-driven workflows the agent loads when relevant.

| Skill | Trigger | What it does |
|---|---|---|
| `code-review` | Auto | Multi-category review with severity model and architecture opportunities |
| `commit` | Manual | Conventional commits with staging logic and pre-flight checks |
| `experiment-workflow` | Auto | 6-phase experiment lifecycle from design to findings report |
| `data-science-analysis` | Auto | Hypothesis generation, feature engineering, storytelling frameworks |
| `spec-driven-dev` | Auto | Write specs before coding — design, approve, then implement |
| `sprint-planning` | Manual | Agile project kickoff, sprint planning, review/retro |
| `project-scaffolding` | Manual | Multi-mode project structure (ML, full-stack, API, library) |
| `iac-templates` | Auto | Reuse, update, or create IaC templates from centralized repo |
| `sus-deep-dive` | Auto | Brazilian public health (SUS/DATASUS) investigation workflow |

### Shared References (`.cursor/references/`)

Deep knowledge loaded on demand by rules and skills.

- **`patterns/`** — Architecture patterns (clean architecture, DDD, hexagonal, event-driven, microservices, CQRS) with when-to-use, when-not-to-use, trade-offs, and evolution paths
- **`design/`** — Design thinking, UX research methods, data visualization principles, design systems

### Authoring Standards

Internal quality contracts at the repo root (not loaded by the agent):

- [`RULES_STANDARD.md`](RULES_STANDARD.md) — how to write `.mdc` rules
- [`SKILLS_STANDARD.md`](SKILLS_STANDARD.md) — how to write `SKILL.md` skills

## Project Structure

```
.cursor/
├── references/
│   ├── patterns/
│   │   ├── clean-architecture.md
│   │   ├── cqrs.md
│   │   ├── ddd.md
│   │   ├── event-driven.md
│   │   ├── hexagonal.md
│   │   └── microservices.md
│   └── design/
│       ├── design-thinking/
│       ├── ux-research/
│       ├── data-visualization/
│       └── design-systems/
├── rules/
│   ├── agent_behavior.mdc
│   ├── autonomous_execution.mdc
│   ├── architecture.mdc
│   ├── causal_rigor.mdc
│   ├── code_standards.mdc
│   ├── critical_thinking.mdc
│   ├── design_principles.mdc
│   ├── python_ml.mdc
│   ├── research_standards.mdc
│   ├── security.mdc
│   └── testing.mdc
└── skills/
    ├── code-review/
    ├── commit/
    ├── data-science-analysis/
    ├── experiment-workflow/
    ├── iac-templates/
    ├── project-scaffolding/
    ├── spec-driven-dev/
    ├── sprint-planning/
    └── sus-deep-dive/
```

## How It Works

**Rules** are loaded automatically based on their frontmatter:
- `alwaysApply: true` — active on every task
- `globs: "*.py"` — active when working on matching files
- `description: "keywords"` — loaded when the agent detects relevance

**Skills** are loaded when the user's request matches the skill's `description` keywords. Skills with `disable-model-invocation: true` must be explicitly invoked.

## Adding New Rules or Skills

Follow the conventions in `RULES_STANDARD.md` and `SKILLS_STANDARD.md`. Key principles:

- Rules are passive constraints (under 200 lines). Skills are procedural workflows (under 300 lines).
- Rules say "always do X". Skills say "when asked to do Y, follow these steps".
- Reference shared knowledge in `references/` instead of duplicating it.
- Every rule needs valid frontmatter. Every skill needs `name`, `description`, and `disable-model-invocation`.
