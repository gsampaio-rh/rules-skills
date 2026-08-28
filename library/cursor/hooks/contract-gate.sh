#!/bin/bash
# preToolUse hook (matcher: Write): Denies writes to product files when harness is ACTIVE:
#   1. Opt-in cold start: routing-pending marker exists but no state.json
#   2. Active harness: pending|building|evaluating task and no contract.json
#
# Idle (free default): no state, or only committed/cancelled/verified tasks → allow.
# Contract exists → allow. .harness/ and .cursor/hooks/ always allowed when gating.

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
source "$SCRIPT_DIR/hooks-lib.sh"
hooks_init "contract-gate"

STATE=".harness/state.json"
CONTRACT=".harness/contract.json"

# P6: count Write/StrReplace to source paths for session handoff advisory.
# Runs before gate decisions so building sessions with a contract still increment.
_p6_target=$(hooks_extract_path "$HOOK_INPUT")
if [ -n "$_p6_target" ]; then
  hooks_session_stats_maybe_inc_source_write "$_p6_target"
fi

# Opt-in arm: routing-pending means harness-gate armed but state.json hasn't
# been created yet (planner hasn't run). Block implementation writes until
# state.json exists, user says "skip harness" (clears marker), a skip
# breadcrumb appears, or TTL expires.
ROUTING_PENDING=".harness/.routing-pending"
ROUTING_PENDING_TTL_SEC="${ROUTING_PENDING_TTL_SEC:-600}"
if [ ! -f "$STATE" ] && [ -f "$ROUTING_PENDING" ]; then
  target_path=$(hooks_extract_path "$HOOK_INPUT")

  if [ -n "$target_path" ]; then
    if echo "$target_path" | grep -qE '(^|/)\.harness/|(^|/)\.cursor/hooks/'; then
      hooks_log "contract-gate" "cold-start, allowed harness path: $target_path"
      echo '{}'
      exit 0
    fi

    # Opt-out breadcrumb (tail-5 "Skipped harness") — allow; marker may remain.
    if hooks_skip_detected; then
      hooks_log "contract-gate" "cold-start skip breadcrumb found, allowing: $target_path"
      echo '{}'
      exit 0
    fi

    # TTL: stale marker → remove and allow. Unreadable mtime → fail closed (deny).
    _rp_mtime=$(stat -f %m "$ROUTING_PENDING" 2>/dev/null || stat -c %Y "$ROUTING_PENDING" 2>/dev/null || true)
    if [ -z "$_rp_mtime" ] || [ "$_rp_mtime" = "0" ]; then
      hooks_log "contract-gate" "DENIED cold-start (unreadable routing-pending mtime): $target_path"
      cat <<EOF
{
  "permission": "deny",
  "agent_message": "WRITE BLOCKED (harness opt-in): .routing-pending is set but no .harness/state.json yet. Launch /planner to create state.json, or say skip harness to cancel.\n\nBlocked file: $target_path"
}
EOF
      exit 0
    fi
    _rp_now=$(date +%s)
    _rp_age=$((_rp_now - _rp_mtime))
    if [ "$_rp_age" -gt "$ROUTING_PENDING_TTL_SEC" ]; then
      rm -f "$ROUTING_PENDING" 2>/dev/null
      hooks_log "contract-gate" "cold-start routing-pending stale (${_rp_age}s > ${ROUTING_PENDING_TTL_SEC}s), cleared, allowing: $target_path"
      echo '{}'
      exit 0
    fi

    hooks_log "contract-gate" "DENIED cold-start write to $target_path (routing-pending age=${_rp_age}s, no state.json)"
    cat <<EOF
{
  "permission": "deny",
  "agent_message": "WRITE BLOCKED (harness opt-in): .routing-pending is set but no .harness/state.json yet. Launch /planner to create state.json, or say skip harness to cancel.\n\nBlocked file: $target_path"
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

# P5: docs-only / non-source writes → soft warn (never hard deny).
# Source paths (library/, src/, scripts/, tests/, …) still hard-gate below.
if ! hooks_is_source_path "$target_path"; then
  hooks_log "contract-gate" "P5 docs/non-source soft warn: $target_path"
  cat <<EOF
{
  "permission": "allow",
  "agent_message": "DOCS WRITE SOFT WARN: No contract.json exists, but this write targets documentation/non-source path \"$target_path\". Allowed without a hard CONTRACT gate. If you are starting implementation work, propose .harness/contract.json first."
}
EOF
  exit 0
fi

# P5: hard-deny source writes when a building, evaluating, OR pending task exists and
# there is no contract. Docs-only already soft-warned above.
# Idle = no pending/building/evaluating → allow (committed/cancelled/verified-only state).
STATE_DATA=$(hooks_read_state "$STATE")
GATE_RESULT=$(echo "$STATE_DATA" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    bid = data.get('building_id', '')
    bname = data.get('building_name', '')
    pid = data.get('pending_id', '')
    pname = data.get('pending_name', '')
    eid = data.get('evaluating_id', '')

    if bid:
        print(f'GATE|{bname or bid}')
    elif eid:
        print(f'GATE|{eid}')
    elif pid:
        print(f'GATE|{pname or pid}')
    else:
        print('SKIP|idle')
except Exception:
    print('GATE|unknown')
" 2>/dev/null)

GATE_ACTION=$(echo "$GATE_RESULT" | cut -d'|' -f1)
CURRENT_FEATURE=$(echo "$GATE_RESULT" | cut -d'|' -f2)

if [ "$GATE_ACTION" = "SKIP" ]; then
  hooks_log "contract-gate" "no building/pending task, allowing"
  echo '{}'
  exit 0
fi

hooks_log "contract-gate" "DENIED write to $target_path (no contract, feature: $CURRENT_FEATURE)"

# Auto-transition first pending task to 'building' status so the agent
# doesn't have to remember. This was forgotten 40% of the time in arena.
python3 -c "
import json
try:
    with open('.harness/state.json') as f:
        state = json.load(f)
    tasks = state.get('tasks', [])
    for t in tasks:
        if t.get('status') == 'pending':
            t['status'] = 'building'
            break
    with open('.harness/state.json', 'w') as f:
        json.dump(state, f, indent=2)
        f.write('\n')
except Exception:
    pass
" 2>/dev/null

cat <<EOF
{
  "permission": "deny",
  "agent_message": "WRITE BLOCKED: Harness is active (task \"$CURRENT_FEATURE\") but no contract.json was found. Propose .harness/contract.json and negotiate with /evaluator before implementation writes.\n\nTo leave harness mode, say skip harness or finish/cancel active tasks.\n\nBlocked file: $target_path"
}
EOF
exit 0
