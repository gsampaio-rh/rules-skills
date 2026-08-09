#!/bin/bash
# beforeSubmitPrompt: set/clear .routing-pending. Deny is contract-gate.

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
source "$SCRIPT_DIR/hooks-lib.sh"
hooks_init "harness-gate"

if [ -f ".harness/contract.json" ] || [ -f ".harness/state.json" ]; then echo '{}'; exit 0; fi

prompt=$(echo "$HOOK_INPUT" | python3 -c "
import sys, json
try:
    d=json.load(sys.stdin); print(d.get('prompt', d.get('content','')))
except Exception: print('')
" 2>/dev/null)
length=${#prompt}
word_count=$(echo "$prompt" | wc -w | tr -d '[:space:]')

# Glue: short conversational replies stay silent.
[ "$length" -lt 10 ] && [ "$word_count" -le 2 ] && { echo '{}'; exit 0; }

hooks_session_stats_inc turns
prompt_lower=$(echo "$prompt" | tr '[:upper:]' '[:lower:]')
if echo "$prompt_lower" | grep -q "skip harness"; then
  rm -f .harness/.routing-pending 2>/dev/null
  echo '{}'; exit 0
fi

# Cold start: arm contract-gate via .routing-pending.
if [ "$length" -gt 10 ]; then
  mkdir -p .harness
  date -u +%Y-%m-%dT%H:%M:%SZ > .harness/.routing-pending
  echo '{"followup_message":"HARNESS ROUTING: launch /planner (impl writes blocked until state.json). Or say skip harness."}'
  exit 0
fi
echo '{}'; exit 0
