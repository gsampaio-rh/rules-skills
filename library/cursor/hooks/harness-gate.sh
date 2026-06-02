#!/bin/bash
# beforeSubmitPrompt hook: fast-path handler for obvious cases.
#
# Deterministic cases (no LLM needed):
#   1. Harness already active (state.json or contract.json exists) → allow silently
#   2. Glue message (under 25 chars) → allow silently
#   3. User explicitly opts out ("skip harness") → allow silently
#   4. Cold start: no state.json + non-trivial prompt → inject planner routing

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

# Case 4: Cold start — no harness + long prompt → advise planner routing
# and create marker so contract-gate can enforce the block on impl writes.
if [ "$length" -gt 100 ]; then
  SIMPLE_PATTERNS="review|audit|check|what|how|why|where|explain|debug|fix this|rename|add comment|update readme"
  if ! echo "$prompt_lower" | grep -qE "$SIMPLE_PATTERNS"; then
    echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] harness-gate: cold start routing ($length chars, non-trivial)" >> "$HOOK_LOG" 2>/dev/null
    mkdir -p .harness
    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > .harness/.routing-pending
    cat <<EOF
{
  "followup_message": "HARNESS ROUTING: No .harness/state.json found and this looks like non-trivial work. Before implementing, launch the /planner subagent to create state.json with tasks. Implementation writes are BLOCKED until state.json exists. If this is actually simple (1-2 files, no architecture), say 'skip harness' to proceed directly."
}
EOF
    exit 0
  fi
fi

# All other cases: allow
echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] harness-gate: allowing (short or simple prompt)" >> "$HOOK_LOG" 2>/dev/null
echo '{}'
exit 0
