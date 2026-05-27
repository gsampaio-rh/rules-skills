#!/bin/bash
# preToolUse hook (matcher: Write): Blocks non-harness writes when the
# evaluator subagent is active. The evaluator must ONLY test and report —
# never modify implementation code.
#
# Flag lifecycle:
#   - Set by chain-evaluator.sh when evaluator is launched
#   - Cleared by chain-evaluator.sh on subagentStop
#   - Staleness: ignored if older than 30 minutes (crash recovery)

input=$(cat)

HOOK_LOG=".cursor/hooks.log"
FLAG=".cursor/hooks/.evaluator-active"

# Fast exit: evaluator not active
if [ ! -f "$FLAG" ]; then
  echo '{}'
  exit 0
fi

# Staleness check: if flag is older than 30 minutes, it's stale (crash recovery)
NOW=$(date +%s)
MTIME=$(stat -f %m "$FLAG" 2>/dev/null || stat -c %Y "$FLAG" 2>/dev/null || echo 0)
AGE=$((NOW - MTIME))

if [ "$AGE" -gt 1800 ]; then
  echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] evaluator-guard: stale flag ($AGE seconds old), removing" >> "$HOOK_LOG" 2>/dev/null
  rm -f "$FLAG"
  echo '{}'
  exit 0
fi

# Extract target path
target_path=$(echo "$input" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    inp = data.get('input', data)
    print(inp.get('path', inp.get('file_path', '')))
except Exception:
    print('')
" 2>/dev/null)

if [ -z "$target_path" ]; then
  echo '{}'
  exit 0
fi

# Evaluator is allowed to write ONLY to harness paths and breadcrumbs
if echo "$target_path" | grep -qE '\.harness/'; then
  echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] evaluator-guard: allowed harness write: $target_path" >> "$HOOK_LOG" 2>/dev/null
  echo '{}'
  exit 0
fi

# Any other write is blocked
echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] evaluator-guard: DENIED impl write: $target_path" >> "$HOOK_LOG" 2>/dev/null

cat <<EOF
{
  "permission": "deny",
  "agent_message": "EVALUATOR WRITE BLOCKED: You are in evaluator mode. You may ONLY write to:\n- .harness/contract.json\n- .harness/evals/*\n- .harness/breadcrumbs.jsonl\n\nYou must NOT modify implementation code. If you found issues:\n1. Document them in your eval report with specific fix_suggestion per criterion\n2. Set recommendation to 'fix_and_retest'\n3. The builder will implement the fixes\n\nBlocked file: $target_path"
}
EOF
exit 0
