#!/bin/bash
# beforeSubmitPrompt hook: cold-start routing + glue/opt-out fast paths.
#
# Deterministic cases (no LLM needed):
#   1. Harness active (state.json or contract.json exists) → skip planner routing
#   2. Glue message (length < 10 AND word_count ≤ 2) → allow silently
#   3. User explicitly opts out ("skip harness") → allow silently
#   4. Cold start: no state.json + non-trivial prompt (> 10 chars) → set .routing-pending + planner advisory
#      (contract-gate then DENIES impl writes until state.json exists)

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
source "$SCRIPT_DIR/hooks-lib.sh"
hooks_init "harness-gate"
input="$HOOK_INPUT"

CONTRACT=".harness/contract.json"
STATE=".harness/state.json"

# Case 1: Harness already active — skip cold-start planner routing.
# P5: leftover contract.json must NOT inject HARNESS ROUTING on Q&A prompts.
harness_active=false
if [ -f "$CONTRACT" ] || [ -f "$STATE" ]; then
  echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] harness-gate: harness active, skipping planner routing" >> "$HOOK_LOG" 2>/dev/null
  harness_active=true
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
word_count=$(echo "$prompt" | wc -w | tr -d '[:space:]')

# Case 2: Glue messages — short conversational responses (< 10 chars AND ≤ 2 words).
# This heuristic keeps "ok", "yes", "got it", "proceed" silent while letting
# short imperative feature prompts like "refatora tudo" or "migra o banco" through.
if [ "$length" -lt 10 ] && [ "$word_count" -le 2 ]; then
  echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] harness-gate: glue message ($length chars, $word_count words), allowing" >> "$HOOK_LOG" 2>/dev/null
  echo '{}'
  exit 0
fi

# P6: count non-glue user turns for session handoff advisory (context-health).
hooks_session_stats_inc turns

prompt_lower=$(echo "$prompt" | tr '[:upper:]' '[:lower:]')

# Case 3: Explicit opt-out — clear cold-start marker so contract-gate unblocks.
if echo "$prompt_lower" | grep -q "skip harness"; then
  rm -f .harness/.routing-pending 2>/dev/null
  echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] harness-gate: user opted out, cleared routing-pending, allowing" >> "$HOOK_LOG" 2>/dev/null
  echo '{}'
  exit 0
fi

# Case 4: Cold start — no harness + non-trivial prompt → advise planner routing.
# Only fires when harness is NOT active; active-harness prompts fall through to Case 5.
# Threshold at 10 chars catches short multilingual feature prompts (e.g. "migra o banco").
if [ "$harness_active" = false ] && [ "$length" -gt 10 ]; then
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

# Skill discovery is host-owned (Cursor lists skills); not injected here.

# All other cases: allow silently
echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] harness-gate: allowing" >> "$HOOK_LOG" 2>/dev/null
echo '{}'
exit 0
