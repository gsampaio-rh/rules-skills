#!/bin/bash
# Stop hook: enforces adversarial verification when a contract is active.
# If a contract exists but verified != true, the agent is forced to continue.
# No contract file = simple task = pass through silently.

input=$(cat)

CONTRACT=".cursor/harness/contract.json"
BREADCRUMBS=".cursor/breadcrumbs.jsonl"

if [ ! -f "$CONTRACT" ]; then
  echo '{}'
  exit 0
fi

if [ ! -f "$BREADCRUMBS" ]; then
  cat <<EOF
{
  "followup_message": "HARNESS WARNING: A contract exists but no breadcrumbs.jsonl was found. Create .cursor/breadcrumbs.jsonl before continuing — the trace log is required for the adversarial harness workflow."
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
  echo '{}'
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

cat <<EOF
{
  "followup_message": "HARNESS GATE: A contract exists for \"$FEATURE\" but verification is incomplete. Launch an evaluator subagent (Task tool) to test the implementation against the contract at .cursor/harness/contract.json. After the evaluator passes, set verified to true in the contract. Do not skip this step."
}
EOF
exit 0
