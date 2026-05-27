#!/bin/bash
# Stop hook: enforces adversarial verification when a contract is active.
# If a contract exists but verified != true, the agent is forced to continue.
# No contract file = simple task = pass through silently.
# Output: decision "block" with reason for Stop event

input=$(cat)

HOOK_LOG=".claude/hooks.log"
echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] verify-harness: triggered" >> "$HOOK_LOG" 2>/dev/null

# Check stop_hook_active to prevent infinite loops
STOP_HOOK_ACTIVE=$(echo "$input" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(str(data.get('stop_hook_active', False)))
except Exception:
    print('False')
" 2>/dev/null)

if [ "$STOP_HOOK_ACTIVE" = "True" ]; then
  echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] verify-harness: stop_hook_active, skipping" >> "$HOOK_LOG" 2>/dev/null
  exit 0
fi

CONTRACT=".claude/harness/contract.json"
BREADCRUMBS=".claude/breadcrumbs.jsonl"

if [ ! -f "$CONTRACT" ]; then
  echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] verify-harness: no contract, skipping" >> "$HOOK_LOG" 2>/dev/null
  exit 0
fi

if [ ! -f "$BREADCRUMBS" ]; then
  cat <<EOF
{
  "decision": "block",
  "reason": "HARNESS WARNING: A contract exists but no breadcrumbs.jsonl was found. Create .claude/breadcrumbs.jsonl before continuing — the trace log is required for the adversarial harness workflow."
}
EOF
  exit 0
fi

VERIFIED=$(python3 -c "
import json
try:
    with open('$CONTRACT') as f:
        data = json.load(f)
    print(str(data.get('verified', False)))
except Exception:
    print('False')
" 2>/dev/null)

if [ "$VERIFIED" = "True" ]; then
  echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] verify-harness: contract verified, passing" >> "$HOOK_LOG" 2>/dev/null
  exit 0
fi

FEATURE=$(python3 -c "
import json
try:
    with open('$CONTRACT') as f:
        data = json.load(f)
    print(data.get('feature', 'unknown feature'))
except Exception:
    print('unknown feature')
" 2>/dev/null)

echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] verify-harness: BLOCKED — contract unverified for '$FEATURE'" >> "$HOOK_LOG" 2>/dev/null

cat <<EOF
{
  "decision": "block",
  "reason": "HARNESS GATE: A contract exists for \"$FEATURE\" but verification is incomplete. Launch an evaluator subagent to test the implementation against the contract at .claude/harness/contract.json. After the evaluator passes, set verified to true in the contract. Do not skip this step."
}
EOF
exit 0
