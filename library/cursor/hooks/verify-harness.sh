#!/bin/bash
# Stop hook: enforces adversarial verification when a harness is active.
#
# Two enforcement paths:
#   1. Contract exists + verified != true → force evaluator launch
#   2. State.json has building feature + impl files changed + no contract/eval → force workflow
#
# No state.json and no contract = simple task = pass through silently.

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
source "$SCRIPT_DIR/hooks-lib.sh"
hooks_init "verify-harness"

CONTRACT=".harness/contract.json"
STATE=".harness/state.json"
BREADCRUMBS=".harness/breadcrumbs.jsonl"

# ─── Path 1: Contract exists but unverified ───────────────────────────────────

if [ -f "$CONTRACT" ]; then
  if [ ! -f "$BREADCRUMBS" ]; then
    cat <<EOF
{
  "followup_message": "HARNESS WARNING: A contract exists but no breadcrumbs.jsonl was found. Create .harness/breadcrumbs.jsonl before continuing — the trace log is required for the adversarial harness workflow."
}
EOF
    exit 0
  fi

  # BUG-7 fix: validate JSON before reading verified field
  VERIFIED=$(python3 -c "
import json
try:
    with open('$CONTRACT') as f:
        data = json.load(f)
    print(str(data.get('verified', False)))
except (json.JSONDecodeError, ValueError):
    print('PARSE_ERROR')
except Exception:
    print('False')
" 2>/dev/null)

  if [ "$VERIFIED" = "PARSE_ERROR" ]; then
    hooks_log "verify-harness" "contract JSON malformed, skipping"
    echo '{}'
    exit 0
  fi

  if [ "$VERIFIED" = "True" ]; then
    # Require at least one breadcrumb with role=evaluator AND result=pass for this task.
    # Prevents builder from self-certifying by directly setting verified:true.
    TASK_ID=$(python3 -c "
import json
try:
    with open('$CONTRACT') as f:
        data = json.load(f)
    print(data.get('task_id', ''))
except Exception:
    print('')
" 2>/dev/null)

    EVAL_PASS=$(python3 -c "
import json
task_id = '$TASK_ID'
try:
    lines = []
    with open('$BREADCRUMBS') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    lines.append(json.loads(line))
                except Exception:
                    pass
    # Accept evaluator entry with result=pass; feat match is optional (legacy compat)
    for b in lines:
        if (b.get('role') == 'evaluator'
                and str(b.get('result', '')).lower() == 'pass'
                and (not task_id or b.get('feat', '') == task_id or b.get('feat', '') == '')):
            print('YES')
            exit()
    print('NO')
except Exception:
    print('NO')
" 2>/dev/null)

    if [ "$EVAL_PASS" = "YES" ]; then
      hooks_log "verify-harness" "contract verified + evaluator PASS breadcrumb found, passing"
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

    hooks_log "verify-harness" "BLOCKED — contract verified:true but no evaluator PASS breadcrumb for task '$TASK_ID'"

    cat <<EOF
{
  "followup_message": "HARNESS GATE: contract.json has verified:true for \"$FEATURE\" but no evaluator PASS breadcrumb was found in breadcrumbs.jsonl.\n\nSelf-certification is not allowed. You must:\n1. Launch an evaluator subagent (Task tool) to test against .harness/contract.json\n2. Evaluator must append a breadcrumb: {\"role\":\"evaluator\",\"result\":\"pass\",\"feat\":\"$TASK_ID\",...}\n\nIf the evaluator already ran but the breadcrumb is missing, append it manually with the correct schema."
}
EOF
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

  hooks_log "verify-harness" "BLOCKED — contract unverified for '$FEATURE'"

  cat <<EOF
{
  "followup_message": "HARNESS GATE: A contract exists for \"$FEATURE\" but verification is incomplete. You must:\n1. Create the evaluator flag: touch .cursor/hooks/.evaluator-active\n2. Launch an evaluator subagent (Task tool) to test the implementation against .harness/contract.json\n3. After the evaluator passes, set verified to true in the contract\n\nDo not skip this step — the harness requires adversarial verification before completion."
}
EOF
  exit 0
fi

# ─── Path 2: State.json exists but no contract — check if work was done ───────

if [ ! -f "$STATE" ]; then
  hooks_log "verify-harness" "no harness state, skipping"
  echo '{}'
  exit 0
fi

# Check if state.json has a task in "building" status (with type-aware bypass)
STATE_DATA=$(hooks_read_state "$STATE")
BUILDING_RESULT=$(echo "$STATE_DATA" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    bid = data.get('building_id', '')
    btype = data.get('building_type', '')
    bname = data.get('building_name', '')
    has_gatable = data.get('has_gatable', False)

    if not bid:
        print('NONE|')
    else:
        gatable = {'feature', 'bug', 'gap', 'fix'}
        skip = (btype not in gatable and not has_gatable)
        print(f\"{'SKIP' if skip else 'GATE'}|{bname or bid}\")
except Exception:
    print('NONE|')
" 2>/dev/null)

BUILDING_ACTION=$(echo "$BUILDING_RESULT" | cut -d'|' -f1)
BUILDING_FEATURE=$(echo "$BUILDING_RESULT" | cut -d'|' -f2)

if [ "$BUILDING_ACTION" = "NONE" ]; then
  hooks_log "verify-harness" "no building task, passing"
  echo '{}'
  exit 0
fi

if [ "$BUILDING_ACTION" = "SKIP" ]; then
  hooks_log "verify-harness" "type-aware bypass (spike/chore), passing"
  echo '{}'
  exit 0
fi

# Check if a recent "Skipped harness" breadcrumb exists
if hooks_skip_detected "$BREADCRUMBS"; then
  hooks_log "verify-harness" "skip breadcrumb found, passing"
  echo '{}'
  exit 0
fi

# A feature is marked as building — check if implementation files were modified
TOTAL_IMPL=$(hooks_git_impl_count)

if [ "$TOTAL_IMPL" -lt 1 ]; then
  hooks_log "verify-harness" "building feature but no impl changes, passing"
  echo '{}'
  exit 0
fi

# Implementation files changed while a feature is building — enforce workflow
hooks_log "verify-harness" "BLOCKED — $TOTAL_IMPL impl files changed, feature '$BUILDING_FEATURE' building, no contract"

cat <<EOF
{
  "followup_message": "HARNESS ENFORCEMENT: Feature \"$BUILDING_FEATURE\" is in 'building' status and $TOTAL_IMPL implementation file(s) were modified, but no contract exists. The adversarial harness requires:\n\n1. Propose a contract for this feature (write .harness/contract.json with acceptance_criteria, edge_cases, verification_method)\n2. Launch the evaluator subagent for contract negotiation\n3. After negotiation, implement against the agreed contract\n4. Launch the evaluator again for verification\n\nIf you've already completed the work and need to skip the harness, write a breadcrumb explaining why: {\"ts\":\"...\",\"role\":\"builder\",\"type\":\"decision\",\"msg\":\"Skipped harness: <reason>\"}"
}
EOF
exit 0
