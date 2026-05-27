#!/bin/bash
# beforeSubmitPrompt hook: fast-path handler for obvious cases.
#
# This script handles 3 deterministic cases instantly (no LLM needed):
#   1. Harness already active (state.json or contract.json exists) → allow silently
#   2. Glue message (under 25 chars) → allow silently
#   3. User explicitly opts out ("skip harness") → allow silently
#
# All other cases pass through to the prompt hook (next in the chain)
# which uses LLM-as-judge to classify complexity.

input=$(cat)

HOOK_LOG=".cursor/hooks.log"
echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] harness-gate: triggered" >> "$HOOK_LOG" 2>/dev/null

CONTRACT=".harness/contract.json"
STATE=".harness/state.json"

# Case 1: Harness already active — no routing needed
if [ -f "$CONTRACT" ] || [ -f "$STATE" ]; then
  echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] harness-gate: harness active, allowing" >> "$HOOK_LOG" 2>/dev/null
  echo '{}'
  exit 0
fi

# Extract prompt text
prompt=$(echo "$input" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('prompt', data.get('content', '')))
except Exception:
    print('')
" 2>/dev/null)

length=${#prompt}

# Case 2: Glue messages pass through silently
if [ "$length" -lt 25 ]; then
  echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] harness-gate: glue message ($length chars), allowing" >> "$HOOK_LOG" 2>/dev/null
  echo '{}'
  exit 0
fi

prompt_lower=$(echo "$prompt" | tr '[:upper:]' '[:lower:]')

# Case 3: Explicit opt-out
if echo "$prompt_lower" | grep -q "skip harness"; then
  echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] harness-gate: user opted out, allowing" >> "$HOOK_LOG" 2>/dev/null
  echo '{}'
  exit 0
fi

# All other cases: pass through to the prompt hook (next in chain)
echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] harness-gate: passing to prompt hook for classification" >> "$HOOK_LOG" 2>/dev/null
echo '{}'
exit 0
