# Cursor Rules & Skills

A curated library of AI coding assistant rules, skills, hooks, and an adversarial verification harness for **Cursor**. Canonical source: `library/cursor/`.

## Architecture

| Layer | Location | Purpose |
|-------|----------|---------|
| **Project state** | `.harness/` | Harness state — contracts, breadcrumbs |
| **IDE config** | `.cursor/` | Local copies from `library/cursor/` via `make setup` (gitignored) |
| **Product library** | `library/cursor/` | Distributable rules, skills, hooks, agents, references |

```
rules-skills/
├── .harness/                    # This project's harness state
├── .cursor/                     # IDE config (gitignored; from make setup)
├── docs/                        # Standards and guides
├── library/cursor/              # Canonical library
│   ├── rules/
│   ├── skills/
│   ├── agents/
│   ├── hooks/
│   ├── hooks.json               # Default hook profile
│   ├── hooks.optional.json      # Dogfood advisories
│   ├── templates/               # Consumer starters (e.g. AGENTS.md)
│   └── references/
├── scripts/
├── tests/eval/
└── sync-cursor.sh
```

## Quick Start

```bash
git clone <this-repo>
make setup                 # populate .cursor/ from library/cursor/
# Edit library/cursor/… then:
make validate && make sync-local
```

### Installing in another project

```bash
./sync-cursor.sh           # syncs to ~/redhat projects (seeds AGENTS.md if missing)
# Or manual:
cp -R library/cursor/rules/ /path/to/project/.cursor/rules/
cp -R library/cursor/hooks/ /path/to/project/.cursor/hooks/
cp -R library/cursor/references/ /path/to/project/.cursor/references/
cp library/cursor/hooks.json /path/to/project/.cursor/hooks.json
mkdir -p /path/to/project/.harness
# Seed project memory only when absent:
scripts/adopt-agents-md.sh /path/to/project library/cursor
# Optional: /agents-bootstrap to fill Commands from Makefile/package.json
```

## Hooks

**Default** (`library/cursor/hooks.json`): harness-context, harness-gate (cold-start), contract-gate, evaluator-guard, pre-commit-harness, verify-harness, enforce-progress, chain-evaluator.

**Optional** (`library/cursor/hooks.optional.json`): secret-read-guard, security-shell, dedup-server, agents-md-nudge — `scripts/hooks-profile.sh optional`.

```bash
make sync-local            # installs default hooks.json
```

## Harness Workflow

1. **Plan** — `/planner` → `.harness/state.json` (vision + tasks)
2. **Negotiate** — contract → `/evaluator`
3. **Build** — one task at a time
4. **Verify** — `/evaluator` with evidence
5. **Commit** — after PASS (commit gate requires approval flag)

Details: [`docs/HARNESS_ESSENCE.md`](docs/HARNESS_ESSENCE.md), skill `adversarial-harness`.

## Skills

**Active:** `adversarial-harness`, `agents-bootstrap`, `fact-check`, `session-review`, `svg-edit`, `code-review`, `commit`, `llm-skeptic`, `prompt-coaching`.

**Archived:** `library/cursor/skills/_archive/` (restore by moving a folder back up).

## Eval

```bash
make eval-fast              # validate + contract/harness lint (no API)
make eval-session           # needs CURSOR_API_KEY — local SDK only
```

No hosted CI for now — run `make eval-fast` locally. Session eval is opt-in (`CURSOR_API_KEY`). See [`docs/EVAL_GUIDE.md`](docs/EVAL_GUIDE.md).

## Sync

```bash
./sync-cursor.sh              # interactive
./sync-cursor.sh --dry-run
./sync-cursor.sh --yes
```

**Per-project** (`.cursor/`): rules, references, hooks + `hooks.json`  
**Global** (`~/.cursor/`): agents, skills

## Authoring Standards

- [`docs/RULES_STANDARD.md`](docs/RULES_STANDARD.md)
- [`docs/SKILLS_STANDARD.md`](docs/SKILLS_STANDARD.md)
- [`docs/HARNESS_ESSENCE.md`](docs/HARNESS_ESSENCE.md)
- [`AGENTS.md`](AGENTS.md) — short agent-facing guide
