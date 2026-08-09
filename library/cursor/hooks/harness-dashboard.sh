#!/bin/bash
# Optional soft hook: regenerate read-only Genius Bar session desk HTML.
# Side-effect only — always exit 0, print {} (no followup spam).

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
ROOT="${HARNESS_ROOT:-.}"

python3 "$SCRIPT_DIR/harness-dashboard.py" \
  --root "$ROOT" \
  --out "$ROOT/.harness/dashboard.html" \
  >/dev/null 2>&1 || true

echo '{}'
exit 0
