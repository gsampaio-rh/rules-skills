#!/bin/bash
# subagentStop hook: automatically chains an evaluator subagent after
# a builder subagent finishes, if a contract is active and unverified.
#
# Flow:
# 1. Builder subagent finishes → contract.verified=false → followup: "launch evaluator"
# 2. Evaluator subagent finishes → contract.verified=true → pass through
# 3. No contract → pass through (simple task, no harness)

input=$(cat)

CONTRACT=".cursor/harness/contract.json"

if [ ! -f "$CONTRACT" ]; then
  echo '{}'
  exit 0
fi

RESULT=$(python3 -c "
import json

with open('$CONTRACT') as f:
    contract = json.load(f)

verified = contract.get('verified', False)
feature = contract.get('feature', 'unknown feature')

if verified:
    print(json.dumps({}))
else:
    msg = (
        f'The builder finished, but the contract for \"{feature}\" is not verified. '
        f'Launch the /evaluator subagent now to test this implementation against '
        f'the contract at .cursor/harness/contract.json. '
        f'The evaluator will grade each acceptance criterion with evidence and '
        f'update the contract when verification passes.'
    )
    print(json.dumps({'followup_message': msg}))
" 2>/dev/null)

if [ -z "$RESULT" ]; then
  echo '{}'
  exit 0
fi

echo "$RESULT"
exit 0
