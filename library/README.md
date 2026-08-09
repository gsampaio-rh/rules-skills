# Distribution Library

Source-of-truth configurations for AI coding assistants. Canonical port: **Cursor** (`library/cursor/`).

## Cursor (`library/cursor/`)

Rules, skills, agents, hooks, and references.

### Automated install

```bash
./sync-cursor.sh              # syncs to all ~/redhat projects with .cursor/
./sync-cursor.sh --dry-run
```

### Manual install

```bash
cp -R library/cursor/rules/ /path/to/project/.cursor/rules/
cp -R library/cursor/hooks/ /path/to/project/.cursor/hooks/
cp -R library/cursor/references/ /path/to/project/.cursor/references/
cp library/cursor/hooks.json /path/to/project/.cursor/hooks.json
mkdir -p /path/to/project/.harness
```

Optional advisories: merge `hooks.optional.json` via `scripts/hooks-profile.sh optional`.

Agents and skills are synced globally to `~/.cursor/` by `sync-cursor.sh`.

## What goes where

| Source | Target | Scope |
|--------|--------|-------|
| `library/cursor/rules/` | `.cursor/rules/` | Per-project |
| `library/cursor/hooks/` | `.cursor/hooks/` | Per-project |
| `library/cursor/references/` | `.cursor/references/` | Per-project |
| `library/cursor/hooks.json` | `.cursor/hooks.json` | Per-project |
| `library/cursor/agents/` | `~/.cursor/agents/` | Global |
| `library/cursor/skills/` | `~/.cursor/skills/` | Global |
| (create empty) | `.harness/` | Per-project |

Other tools (Claude Code, Windsurf, Codex): regenerate adapters from this Cursor library as needed — no parallel port is maintained here.
