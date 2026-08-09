#!/bin/bash
# Stop hook: soft-block progress tracking when multi-file source work lacks a
# valid breadcrumb.
#
# Primary gate (PROGRESS BLOCKED):
#   source_writes >= 2 in .harness/.session-stats.json AND last breadcrumb is
#   missing or invalid (msg length < 20 OR result absent/empty) → followup
#   soft-block. Cursor stop hooks use followup_message (not permission deny).
#
# Exceptions (stdout {}):
#   - .harness/contract.json present (harness has its own enforcement)
#   - source_writes < 2 (single-write)
#   - source_writes == 0 / missing .session-stats.json (docs-only or fail-open)

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
source "$SCRIPT_DIR/hooks-lib.sh"
hooks_init "enforce-progress"

ROOT="${HARNESS_ROOT:-.}"
CONTRACT="$ROOT/.harness/contract.json"
STATS_FILE="$ROOT/.harness/.session-stats.json"
BREADCRUMBS="$ROOT/.harness/breadcrumbs.jsonl"

if [ -f "$CONTRACT" ]; then
  echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] enforce-progress: contract exists, skipping" >> "$HOOK_LOG" 2>/dev/null
  echo '{}'
  exit 0
fi

SOURCE_WRITES=$(python3 -c "
import json, os
path = '''$STATS_FILE'''
if not os.path.isfile(path):
    print(0)
    raise SystemExit
try:
    with open(path) as f:
        data = json.load(f)
    print(int(data.get('source_writes', 0) or 0))
except Exception:
    print(0)
" 2>/dev/null)

BREADCRUMB_VALID=$(python3 -c "
import json, os
path = '''$BREADCRUMBS'''
if not os.path.isfile(path):
    print('false')
    raise SystemExit
last = None
try:
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                last = json.loads(line)
except Exception:
    print('false')
    raise SystemExit
if not isinstance(last, dict):
    print('false')
    raise SystemExit
msg = last.get('msg')
if not isinstance(msg, str) or len(msg) < 20:
    print('false')
    raise SystemExit
result = last.get('result')
if not isinstance(result, str) or len(result) == 0:
    print('false')
    raise SystemExit
print('true')
" 2>/dev/null)

# Primary gate: ≥2 source Writes/StrReplaces without a valid breadcrumb
if [ "${SOURCE_WRITES:-0}" -ge 2 ] && [ "$BREADCRUMB_VALID" != "true" ]; then
  echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] enforce-progress: source_writes=$SOURCE_WRITES, invalid/missing breadcrumb — PROGRESS BLOCKED" >> "$HOOK_LOG" 2>/dev/null

  cat <<EOF
{
  "followup_message": "PROGRESS BLOCKED: session source_writes=$SOURCE_WRITES (>=2) but .harness/breadcrumbs.jsonl is missing or the last entry is invalid. Before ending your turn:\n1. Append a breadcrumb: {\"ts\":\"ISO-8601\",\"role\":\"builder\",\"type\":\"build\",\"feat\":null,\"msg\":\"<summary at least 20 chars>\",\"result\":\"pass\"}\n2. Requirements: msg length >= 20 AND result is a non-empty string\n3. If you haven't used TodoWrite for this multi-file task, create a todo list now\n\nDo NOT skip this — progress tracking is required for multi-file source changes."
}
EOF
  exit 0
fi

echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] enforce-progress: passed (source_writes=$SOURCE_WRITES valid=$BREADCRUMB_VALID)" >> "$HOOK_LOG" 2>/dev/null
echo '{}'
exit 0
