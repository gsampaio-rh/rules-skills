#!/bin/bash
# preToolUse hook (matcher: Write): Blocks non-harness writes when the
# evaluator subagent is active. The evaluator must ONLY test and report —
# never modify implementation code.
#
# Flag lifecycle:
#   - Set by chain-evaluator.sh when evaluator is launched
#   - Cleared by chain-evaluator.sh on subagentStop
#   - Staleness: ignored if older than 30 minutes (crash recovery)

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
source "$SCRIPT_DIR/hooks-lib.sh"
hooks_init "evaluator-guard"

FLAG=".cursor/hooks/.evaluator-active"

# Fast exit: evaluator not active
if [ ! -f "$FLAG" ]; then
  echo '{}'
  exit 0
fi

# Staleness check: if flag is older than 30 minutes, it's stale (crash recovery)
AGE=$(hooks_file_age "$FLAG")

if [ "$AGE" -gt 1800 ]; then
  hooks_log "evaluator-guard" "stale flag ($AGE seconds old), removing"
  rm -f "$FLAG"
  echo '{}'
  exit 0
fi

# Extract target path using unified walk (fixes BUG-6: adds filePath, toolInput, tool_input)
target_path=$(hooks_extract_path "$HOOK_INPUT")

if [ -z "$target_path" ]; then
  echo '{}'
  exit 0
fi

# Evaluator is allowed to write ONLY to harness paths and breadcrumbs
if echo "$target_path" | grep -qE '\.harness/'; then
  hooks_log "evaluator-guard" "allowed harness write: $target_path"
  echo '{}'
  exit 0
fi

# Any other write is blocked
hooks_log "evaluator-guard" "DENIED impl write: $target_path"

cat <<EOF
{
  "permission": "deny",
  "agent_message": "EVALUATOR WRITE BLOCKED: You are in evaluator mode. You may ONLY write to:\n- .harness/contract.json\n- .harness/.archive/evals/*\n- .harness/breadcrumbs.jsonl\n\nYou must NOT modify implementation code. If you found issues:\n1. Document them in your eval report with specific fix_suggestion per criterion\n2. Set recommendation to 'fix_and_retest'\n3. The builder will implement the fixes\n\nBlocked file: $target_path"
}
EOF
exit 0
