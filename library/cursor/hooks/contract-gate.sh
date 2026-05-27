#!/bin/bash
# preToolUse hook (matcher: Write): Denies writes to implementation paths
# when state.json exists (harness active) but no contract.json has been negotiated.
#
# Design:
#   - No state.json → allow (simple task, no harness)
#   - Contract exists → allow (negotiation done)
#   - State exists + no contract → deny impl writes, allow harness/docs writes
#   - Staleness check: if state.json is older than 24h and no activity, warn but allow

input=$(cat)

HOOK_LOG=".cursor/hooks.log"
echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] contract-gate: triggered" >> "$HOOK_LOG" 2>/dev/null

STATE=".harness/state.json"
CONTRACT=".harness/contract.json"

# Fast exit: no harness active
if [ ! -f "$STATE" ]; then
  echo '{}'
  exit 0
fi

# Fast exit: contract exists (negotiation done)
if [ -f "$CONTRACT" ]; then
  echo '{}'
  exit 0
fi

# Extract the target file path from the tool input
target_path=$(echo "$input" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    # preToolUse Write input has the path in 'input.path' or 'path'
    inp = data.get('input', data)
    print(inp.get('path', inp.get('file_path', '')))
except Exception:
    print('')
" 2>/dev/null)

if [ -z "$target_path" ]; then
  echo '['"$(date -u +%Y-%m-%dT%H:%M:%S)"'] contract-gate: could not extract path, allowing' >> "$HOOK_LOG" 2>/dev/null
  echo '{}'
  exit 0
fi

# Always allow writes to harness, breadcrumbs, docs, config, and meta files
if echo "$target_path" | grep -qE '\.cursor/|breadcrumbs|\.md$|\.mdc$|\.json$|\.yaml$|\.yml$|\.toml$|__pycache__|\.gitignore|\.env|Makefile|hooks\.log'; then
  echo '['"$(date -u +%Y-%m-%dT%H:%M:%S)"'] contract-gate: allowed path (harness/docs/config): '"$target_path" >> "$HOOK_LOG" 2>/dev/null
  echo '{}'
  exit 0
fi

# State exists, no contract, target is implementation code → DENY
CURRENT_FEATURE=$(python3 -c "
import json
try:
    with open('$STATE') as f:
        data = json.load(f)
    for feat in data.get('features', []):
        if feat.get('status') in ('building', 'pending'):
            print(feat.get('name', feat.get('id', 'unknown')))
            break
    else:
        print('unknown')
except Exception:
    print('unknown')
" 2>/dev/null)

echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] contract-gate: DENIED write to $target_path (no contract, feature: $CURRENT_FEATURE)" >> "$HOOK_LOG" 2>/dev/null

ESCAPED_PATH=$(echo "$target_path" | python3 -c "import sys,json; print(json.dumps(sys.stdin.read().strip()))" 2>/dev/null)

cat <<EOF
{
  "permission": "deny",
  "agent_message": "WRITE BLOCKED: The harness is active (state.json exists with feature \"$CURRENT_FEATURE\") but no contract.json was found. You must negotiate a contract before writing implementation code.\n\nTo proceed:\n1. Propose a contract for the current feature (write to .harness/contract.json)\n2. Launch the evaluator subagent for contract negotiation\n3. After negotiation completes, implementation writes will be allowed\n\nIf this is a simple fix unrelated to harness features, write a breadcrumb to .harness/breadcrumbs.jsonl explaining why you're skipping the contract, then the user can say 'skip harness' to proceed.\n\nBlocked file: $target_path"
}
EOF
exit 0
