# Distribution Library

Source-of-truth configurations for AI coding assistants. Not build output — these are authored here and distributed to target projects.

## Cursor (`library/cursor/`)

The full Cursor configuration: rules, skills, agents, hooks, and references.

### Automated install (recommended)

```bash
# From the rules-skills repo root:
./sync-cursor.sh              # syncs to all ~/redhat projects with .cursor/
./sync-cursor.sh --dry-run    # preview what would change
```

### Manual install

```bash
# Copy to a specific project:
cp -R library/cursor/rules/ /path/to/project/.cursor/rules/
cp -R library/cursor/hooks/ /path/to/project/.cursor/hooks/
cp -R library/cursor/references/ /path/to/project/.cursor/references/
cp .cursor/hooks.full.json /path/to/project/.cursor/hooks.json
mkdir -p /path/to/project/.harness/{evals,audits}
```

Agents and skills are synced globally to `~/.cursor/` (shared across all projects).

## Claude Code (`library/claude/`)

Parallel port of the Cursor config for Claude Code.

### Install

```bash
cp -R library/claude/ /path/to/project/.claude/
mkdir -p /path/to/project/.harness/{evals,audits}
```

## What goes where in target projects

| Source | Target | Scope |
|--------|--------|-------|
| `library/cursor/rules/` | `.cursor/rules/` | Per-project |
| `library/cursor/hooks/` | `.cursor/hooks/` | Per-project |
| `library/cursor/references/` | `.cursor/references/` | Per-project |
| `.cursor/hooks.full.json` | `.cursor/hooks.json` | Per-project |
| `library/cursor/agents/` | `~/.cursor/agents/` | Global |
| `library/cursor/skills/` | `~/.cursor/skills/` | Global |
| (create empty) | `.harness/` | Per-project |
