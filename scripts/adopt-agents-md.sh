#!/usr/bin/env bash
# Seed project-root AGENTS.md from the library template when missing.
# Always refresh TARGET/.cursor/templates/ from LIB_CURSOR/templates/.
# Usage: adopt-agents-md.sh <TARGET_ROOT> [LIB_CURSOR]
#   TARGET_ROOT — project root that should own AGENTS.md
#   LIB_CURSOR  — path to library/cursor (default: <repo>/library/cursor next to this script)
set -euo pipefail

TARGET_ROOT="${1:-}"
if [[ -z "$TARGET_ROOT" ]]; then
  echo "usage: $(basename "$0") <TARGET_ROOT> [LIB_CURSOR]" >&2
  exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_LIB="$(cd "$SCRIPT_DIR/../library/cursor" && pwd)"
LIB_CURSOR="$(cd "${2:-$DEFAULT_LIB}" && pwd)"
TEMPLATE="$LIB_CURSOR/templates/AGENTS.md"

if [[ ! -f "$TEMPLATE" ]]; then
  echo "error: template not found: $TEMPLATE" >&2
  exit 1
fi

mkdir -p "$TARGET_ROOT/.cursor/templates"
# Always refresh IDE-visible template copy (safe: not the project AGENTS.md).
cp "$TEMPLATE" "$TARGET_ROOT/.cursor/templates/AGENTS.md"

# Missing-only seed for portable project memory.
if [[ ! -f "$TARGET_ROOT/AGENTS.md" ]]; then
  cp "$TEMPLATE" "$TARGET_ROOT/AGENTS.md"
fi
