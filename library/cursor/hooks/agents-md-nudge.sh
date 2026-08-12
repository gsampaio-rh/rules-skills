#!/bin/bash
# Optional sessionStart: one-line nudge when AGENTS.md is missing.
# Soft hook — always exit 0; never create/modify AGENTS.md.

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# shellcheck source=hooks-lib.sh
source "$SCRIPT_DIR/hooks-lib.sh" 2>/dev/null || true
hooks_init "agents-md-nudge" 2>/dev/null || true

ROOT="${HARNESS_ROOT:-.}"
AGENTS="$ROOT/AGENTS.md"

if [ -f "$AGENTS" ]; then
  echo '{}'
  exit 0
fi

# Thin pointer only — adopt seeds the file; /agents-bootstrap fills commands.
python3 -c 'import json; print(json.dumps({"additional_context":"No AGENTS.md — run scripts/adopt-agents-md.sh then /agents-bootstrap."}))'
exit 0
