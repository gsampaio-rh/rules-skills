#!/bin/bash
# preToolUse hook (matcher: Write): Denies writes to product files
# when state.json exists (harness active) but no contract.json has been negotiated.
#
# Design:
#   - No state.json → allow (simple task, no harness)
#   - Contract exists → allow (negotiation done, builder working)
#   - State exists + no contract → allow ONLY .harness/ and .cursor/hooks/ writes
#     (builder must write a contract before touching anything else)

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

# Fast exit: recent skip breadcrumb (builder explicitly skipped harness)
BREADCRUMBS=".harness/breadcrumbs.jsonl"
if [ -f "$BREADCRUMBS" ]; then
  SKIP_FOUND=$(tail -5 "$BREADCRUMBS" | grep -c "Skipped harness" 2>/dev/null || echo "0")
  if [ "$SKIP_FOUND" -gt 0 ]; then
    echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] contract-gate: skip breadcrumb found, allowing" >> "$HOOK_LOG" 2>/dev/null
    echo '{}'
    exit 0
  fi
fi

# Extract the target file path from the tool input.
# The input schema varies by context: IDE sends {input: {path: ...}},
# SDK bridge may send {tool_name: ..., input: {path: ...}} or flat {path: ...}.
# We walk multiple known locations to handle all variants.
target_path=$(echo "$input" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    path = ''
    for key in ('input', 'toolInput', 'tool_input'):
        nested = data.get(key)
        if isinstance(nested, dict):
            path = nested.get('path', nested.get('file_path', nested.get('filePath', '')))
            if path:
                break
    if not path:
        path = data.get('path', data.get('file_path', data.get('filePath', '')))
    print(path)
except Exception:
    print('')
" 2>/dev/null)

if [ -z "$target_path" ]; then
  # Log truncated raw input for debugging path extraction failures
  RAW_SNIPPET=$(echo "$input" | head -c 300)
  echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] contract-gate: could not extract path, allowing. raw(truncated): $RAW_SNIPPET" >> "$HOOK_LOG" 2>/dev/null
  echo '{}'
  exit 0
fi

# No contract yet — only allow writes to harness state and hook transient files.
# Everything else (including .md, .mdc, .yaml product files) is blocked until
# a contract is negotiated. This prevents the builder from skipping negotiation
# in repos where the product IS markdown/YAML/JSON.
if echo "$target_path" | grep -qE '\.harness/|\.cursor/hooks/'; then
  echo '['"$(date -u +%Y-%m-%dT%H:%M:%S)"'] contract-gate: allowed path (harness/hook state): '"$target_path" >> "$HOOK_LOG" 2>/dev/null
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
