#!/bin/bash
# SubagentStop hook: gates transitions between harness phases using the
# contract's "phase" field.
#
# Routing:
#   No state.json or contract.json → pass through (simple subagent)
#   state.json exists, no contract  → PLAN GATE (planner just finished)
#   phase=negotiating/negotiated    → negotiation done, builder should build
#   phase=building                  → builder's subagent done, launch evaluator
#   phase=evaluating + unverified   → evaluator done but failed, re-launch
#   phase=evaluating + verified     → pass through
#
# Output: decision "block" with reason for SubagentStop event

input=$(cat)

HOOK_LOG=".claude/hooks.log"
echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] subagent-gate: triggered" >> "$HOOK_LOG" 2>/dev/null

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
  echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] subagent-gate: stop_hook_active, skipping" >> "$HOOK_LOG" 2>/dev/null
  exit 0
fi

CONTRACT=".claude/harness/contract.json"
STATE=".claude/harness/state.json"

# Scenario 1: planner just finished — state.json exists but no contract yet
if [ -f "$STATE" ] && [ ! -f "$CONTRACT" ]; then
  NOW=$(date +%s)
  MTIME=$(stat -f %m "$STATE" 2>/dev/null || stat -c %Y "$STATE" 2>/dev/null || echo 0)
  AGE=$((NOW - MTIME))

  if [ "$AGE" -lt 300 ]; then
    echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] subagent-gate: planner finished — spec confirmation required" >> "$HOOK_LOG" 2>/dev/null

    FEATURE_COUNT=$(python3 -c "
import json
try:
    with open('$STATE') as f:
        data = json.load(f)
    print(len(data.get('features', [])))
except Exception:
    print('?')
" 2>/dev/null)

    cat <<EOF
{
  "decision": "block",
  "reason": "PLAN GATE: The planner produced state.json with $FEATURE_COUNT features. Before starting development:\n1. Read .claude/harness/state.json and present vision, direction, and feature list to the user\n2. Ask the user to confirm the plan before proceeding\n3. Do NOT start contract negotiation or building until the user confirms\n\nThis ensures the user agrees with the direction before any code is written."
}
EOF
    exit 0
  fi
fi

# No contract → no harness state, pass through
if [ ! -f "$CONTRACT" ]; then
  echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] subagent-gate: no harness state, skipping" >> "$HOOK_LOG" 2>/dev/null
  exit 0
fi

# Read phase and verified from contract
RESULT=$(python3 -c "
import json

with open('$CONTRACT') as f:
    contract = json.load(f)

phase = contract.get('phase', 'unknown')
verified = contract.get('verified', False)
feature = contract.get('feature', 'unknown feature')

if phase in ('negotiating', 'negotiated'):
    msg = (
        f'CONTRACT NEGOTIATED: The evaluator has reviewed the contract for \"{feature}\". '
        f'Negotiation is complete. Now:\n'
        f'1. Set phase to \"building\" in .claude/harness/contract.json\n'
        f'2. Update state.json to set the feature status to \"building\"\n'
        f'3. Begin implementation against the contract'
    )
    print(json.dumps({'decision': 'block', 'reason': msg}))
elif phase == 'building':
    msg = (
        f'BUILD COMPLETE: A subagent finished while building \"{feature}\". '
        f'Now set phase to \"evaluating\" in .claude/harness/contract.json '
        f'and launch the /evaluator subagent to test the implementation.'
    )
    print(json.dumps({'decision': 'block', 'reason': msg}))
elif phase == 'evaluating':
    if verified:
        print('{}')
    else:
        msg = (
            f'EVAL INCOMPLETE: The evaluator tested \"{feature}\" but verification failed. '
            f'Read the eval report at .claude/harness/evals/, fix the issues, '
            f'then re-launch /evaluator to re-test.'
        )
        print(json.dumps({'decision': 'block', 'reason': msg}))
else:
    print('{}')
" 2>/dev/null)

if [ -z "$RESULT" ]; then
  echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] subagent-gate: python failed, passing" >> "$HOOK_LOG" 2>/dev/null
  exit 0
fi

# Log the routing decision
PHASE=$(python3 -c "
import json
try:
    with open('$CONTRACT') as f:
        print(json.load(f).get('phase', '?'))
except:
    print('?')
" 2>/dev/null)
echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] subagent-gate: phase=$PHASE, routed" >> "$HOOK_LOG" 2>/dev/null

echo "$RESULT"
exit 0
