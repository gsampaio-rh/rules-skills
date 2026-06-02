#!/bin/bash
# preToolUse hook (matcher: Write): Denies writes to product files in two cases:
#   1. Cold start: routing-pending marker exists but no state.json (planner not run)
#   2. Active harness: state.json exists but no contract.json (negotiation not done)
#
# Design:
#   - routing-pending + no state.json → block impl writes (cold-start enforcement)
#   - No state.json + no marker → allow (simple task, no harness)
#   - Contract exists → allow (negotiation done, builder working)
#   - State exists + no contract → allow ONLY .harness/ and .cursor/hooks/ writes

input=$(cat)

HOOK_LOG=".cursor/hooks.log"
echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] contract-gate: triggered" >> "$HOOK_LOG" 2>/dev/null

STATE=".harness/state.json"
CONTRACT=".harness/contract.json"

# Cold-start enforcement: routing-pending marker means harness-gate detected
# a non-trivial prompt but state.json hasn't been created yet (planner hasn't
# run). Block implementation writes until the agent creates state.json.
ROUTING_PENDING=".harness/.routing-pending"
if [ ! -f "$STATE" ] && [ -f "$ROUTING_PENDING" ]; then
  # Still need to extract the target path to decide allow/deny
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

  if [ -n "$target_path" ]; then
    if echo "$target_path" | grep -qE '\.harness/|\.cursor/hooks/'; then
      echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] contract-gate: cold-start, allowed harness path: $target_path" >> "$HOOK_LOG" 2>/dev/null
      echo '{}'
      exit 0
    fi
    echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] contract-gate: DENIED cold-start write to $target_path (routing-pending, no state.json)" >> "$HOOK_LOG" 2>/dev/null
    cat <<EOF
{
  "permission": "deny",
  "agent_message": "WRITE BLOCKED (cold start): A non-trivial task was detected but no .harness/state.json exists yet. You must launch the /planner subagent to create state.json before writing implementation code.\n\nTo proceed:\n1. Launch /planner to decompose the task into state.json\n2. After state.json is created, implementation writes will be allowed\n\nIf this is actually simple work, ask the user to say 'skip harness'.\n\nBlocked file: $target_path"
}
EOF
    exit 0
  fi
fi

# Fast exit: no harness active and no routing pending
if [ ! -f "$STATE" ]; then
  echo '{}'
  exit 0
fi

# Cleanup stale routing-pending marker now that state.json exists
[ -f "$ROUTING_PENDING" ] && rm -f "$ROUTING_PENDING" 2>/dev/null

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

# Check if gate should be skipped for spike/chore tasks (type-aware bypass)
GATE_RESULT=$(python3 -c "
import json
try:
    with open('$STATE') as f:
        data = json.load(f)
    tasks = data.get('tasks', [])
    sorted_tasks = sorted(tasks, key=lambda t: (t.get('priority', 99), tasks.index(t)))
    pending = [t for t in sorted_tasks if t.get('status') == 'pending']
    building = [t for t in sorted_tasks if t.get('status') == 'building']
    current = building[0] if building else (pending[0] if pending else None)
    if not current:
        print('SKIP|unknown')
    else:
        gatable = {'feature', 'bug', 'gap', 'fix'}
        has_gatable = any(
            t.get('type', 'feature') in gatable
            for t in tasks if t.get('status') in ('pending', 'building')
        )
        skip = (
            current.get('type', 'feature') not in gatable
            and current.get('status') == 'pending'
            and not has_gatable
        )
        name = current.get('name', current.get('id', 'unknown'))
        print(f'{'SKIP' if skip else 'GATE'}|{name}')
except Exception:
    print('GATE|unknown')
" 2>/dev/null)

GATE_ACTION=$(echo "$GATE_RESULT" | cut -d'|' -f1)
CURRENT_FEATURE=$(echo "$GATE_RESULT" | cut -d'|' -f2)

if [ "$GATE_ACTION" = "SKIP" ]; then
  echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] contract-gate: type-aware bypass (spike/chore), allowing" >> "$HOOK_LOG" 2>/dev/null
  echo '{}'
  exit 0
fi

echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] contract-gate: DENIED write to $target_path (no contract, feature: $CURRENT_FEATURE)" >> "$HOOK_LOG" 2>/dev/null

ESCAPED_PATH=$(echo "$target_path" | python3 -c "import sys,json; print(json.dumps(sys.stdin.read().strip()))" 2>/dev/null)

cat <<EOF
{
  "permission": "deny",
  "agent_message": "WRITE BLOCKED: The harness is active (state.json exists with feature \"$CURRENT_FEATURE\") but no contract.json was found. You must negotiate a contract before writing implementation code.\n\nTo proceed:\n1. Propose a contract for the current feature (write to .harness/contract.json)\n2. Launch the evaluator subagent for contract negotiation\n3. After negotiation completes, implementation writes will be allowed\n\nIf this is a simple fix unrelated to harness features, write a breadcrumb to .harness/breadcrumbs.jsonl explaining why you're skipping the contract, then the user can say 'skip harness' to proceed.\n\nBlocked file: $target_path"
}
EOF
exit 0
