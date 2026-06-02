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

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
source "$SCRIPT_DIR/hooks-lib.sh"
hooks_init "contract-gate"

STATE=".harness/state.json"
CONTRACT=".harness/contract.json"

# Cold-start enforcement: routing-pending marker means harness-gate detected
# a non-trivial prompt but state.json hasn't been created yet (planner hasn't
# run). Block implementation writes until the agent creates state.json.
ROUTING_PENDING=".harness/.routing-pending"
if [ ! -f "$STATE" ] && [ -f "$ROUTING_PENDING" ]; then
  target_path=$(hooks_extract_path "$HOOK_INPUT")

  if [ -n "$target_path" ]; then
    if echo "$target_path" | grep -qE '\.harness/|\.cursor/hooks/'; then
      hooks_log "contract-gate" "cold-start, allowed harness path: $target_path"
      echo '{}'
      exit 0
    fi
    hooks_log "contract-gate" "DENIED cold-start write to $target_path (routing-pending, no state.json)"
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
if hooks_skip_detected; then
  hooks_log "contract-gate" "skip breadcrumb found, allowing"
  echo '{}'
  exit 0
fi

# Extract the target file path from the tool input (single call — fixes BUG-2)
target_path=$(hooks_extract_path "$HOOK_INPUT")

if [ -z "$target_path" ]; then
  RAW_SNIPPET=$(echo "$HOOK_INPUT" | head -c 300)
  hooks_log "contract-gate" "could not extract path, allowing. raw(truncated): $RAW_SNIPPET"
  echo '{}'
  exit 0
fi

# No contract yet — only allow writes to harness state and hook transient files.
if echo "$target_path" | grep -qE '\.harness/|\.cursor/hooks/'; then
  hooks_log "contract-gate" "allowed path (harness/hook state): $target_path"
  echo '{}'
  exit 0
fi

# Check if gate should be skipped for spike/chore tasks (type-aware bypass)
STATE_DATA=$(hooks_read_state "$STATE")
GATE_RESULT=$(echo "$STATE_DATA" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    bid = data.get('building_id', '')
    btype = data.get('building_type', '')
    bname = data.get('building_name', '')
    pid = data.get('pending_id', '')
    ptype = data.get('pending_type', '')
    pname = data.get('pending_name', '')
    has_gatable = data.get('has_gatable', False)
    gatable = {'feature', 'bug', 'gap', 'fix'}

    if bid:
        current_type = btype
        current_name = bname or bid
    elif pid:
        current_type = ptype
        current_name = pname or pid
    else:
        print('SKIP|unknown')
        raise SystemExit(0)

    skip = (
        current_type not in gatable
        and (not bid or True)
        and not has_gatable
    )
    # contract-gate specific: also skip if current is pending + non-gatable
    if not bid and pid:
        skip = (
            current_type not in gatable
            and ptype not in gatable
            and not has_gatable
        )
    print(f\"{'SKIP' if skip else 'GATE'}|{current_name}\")
except Exception:
    print('GATE|unknown')
" 2>/dev/null)

GATE_ACTION=$(echo "$GATE_RESULT" | cut -d'|' -f1)
CURRENT_FEATURE=$(echo "$GATE_RESULT" | cut -d'|' -f2)

if [ "$GATE_ACTION" = "SKIP" ]; then
  hooks_log "contract-gate" "type-aware bypass (spike/chore), allowing"
  echo '{}'
  exit 0
fi

hooks_log "contract-gate" "DENIED write to $target_path (no contract, feature: $CURRENT_FEATURE)"

cat <<EOF
{
  "permission": "deny",
  "agent_message": "WRITE BLOCKED: The harness is active (state.json exists with feature \"$CURRENT_FEATURE\") but no contract.json was found. You must negotiate a contract before writing implementation code.\n\nTo proceed:\n1. Propose a contract for the current feature (write to .harness/contract.json)\n2. Launch the evaluator subagent for contract negotiation\n3. After negotiation completes, implementation writes will be allowed\n\nIf this is a simple fix unrelated to harness features, write a breadcrumb to .harness/breadcrumbs.jsonl explaining why you're skipping the contract, then the user can say 'skip harness' to proceed.\n\nBlocked file: $target_path"
}
EOF
exit 0
