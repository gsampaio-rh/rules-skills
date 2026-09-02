#!/bin/bash
# session-cleanup.sh — sessionEnd hook
#
# Removes transient harness markers left from this session so a subsequent
# session does not start in a stale "active harness" or "evaluator active" state.
#
# Markers managed:
#   .harness/.routing-pending   — created by harness-gate.sh when user opts in
#   .cursor/hooks/.evaluator-active — created by chain-evaluator.sh
#
# TTL: markers live for the duration of one agent session. This hook clears them
# on sessionEnd. Manual cleanup: rm -f .harness/.routing-pending .cursor/hooks/.evaluator-active
#
# NOTE: sessionEnd does NOT fire in cloud agents — cloud agents have no editor-lifetime
# session boundary (ref: cursor.com/docs/hooks, cursor.com/help/ai-features/cloud-agents).
# For cloud runs, markers must be cleaned up manually or by a beforeShellExecution wrapper.

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
source "$SCRIPT_DIR/hooks-lib.sh"

hooks_init "session-cleanup"

# Remove routing-pending marker (harness opt-in state)
if [ -f ".harness/.routing-pending" ]; then
  rm -f ".harness/.routing-pending"
  hooks_log "session-cleanup" "removed .routing-pending"
fi

# Remove evaluator-active marker (chain-evaluator gating state)
if [ -f ".cursor/hooks/.evaluator-active" ]; then
  rm -f ".cursor/hooks/.evaluator-active"
  hooks_log "session-cleanup" "removed .evaluator-active"
fi

exit 0
