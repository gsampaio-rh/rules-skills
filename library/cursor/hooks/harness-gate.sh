#!/bin/bash
# beforeSubmitPrompt: opt-in arm of .routing-pending. Deny is contract-gate.
# Default is free (silent {}). Arm only on explicit harness opt-in phrases.
#
# Marker TTL: .harness/.routing-pending lives for the duration of one agent session.
# It is created here when the user opts in and removed by session-cleanup.sh (sessionEnd).
# Manual cleanup: rm -f .harness/.routing-pending

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

# Opt-out / clear: always harmless.
if echo "$prompt_lower" | grep -q "skip harness"; then
  rm -f .harness/.routing-pending 2>/dev/null
  echo '{}'
  exit 0
fi

# Opt-in only: arm contract-gate via .routing-pending.
# Phrases: use harness | with harness | /planner | adversarial-harness (case-insensitive).
if echo "$prompt_lower" | grep -Eq 'use harness|with harness|/planner|adversarial-harness'; then
  mkdir -p .harness
  date -u +%Y-%m-%dT%H:%M:%SZ > .harness/.routing-pending
  echo '{"followup_message":"HARNESS OPT-IN: launch /planner (impl writes blocked until state.json). Say skip harness to cancel."}'
  exit 0
fi

# Free default — no auto-arm on long prompts.
echo '{}'
exit 0
