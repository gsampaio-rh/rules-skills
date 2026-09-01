# Archived skills

Moved out of the active catalog. `make sync-local` does **not** copy this directory to `.cursor/skills/` — only `library/cursor/skills/` keeps the history. This prevents archived SKILL.md files from leaking into the Cursor active catalog (Cursor scans all `SKILL.md` under `.cursor/skills/**` regardless of subdirectory name).

To restore a skill: move its directory back to `library/cursor/skills/`, then run `make sync-local`.

