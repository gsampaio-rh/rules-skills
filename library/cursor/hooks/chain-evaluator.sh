#!/bin/bash
# subagentStop hook: programmatic state-transition orchestration.
#
# Phase transitions handled automatically (not just advisory):
#   phase=building → writes phase=evaluating to contract.json in-place,
#                    creates .evaluator-active flag, appends dispatch breadcrumb,
#                    returns imperative followup_message with /evaluator invocation.
#
# Advisory-only (Cursor hook API cannot auto-invoke subagents):
#   phase=negotiating/negotiated → imperative message to start building
#   phase=evaluating + unverified → EVAL FAIL retry message
#   phase=evaluating + verified   → pass through {}
#   state.json exists, no contract → PLAN GATE user confirmation required
#
# Final /evaluator invocation remains manual — hook injects prescribed text.

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
source "$SCRIPT_DIR/hooks-lib.sh"
hooks_init "chain-evaluator"

EVALUATOR_FLAG=".cursor/hooks/.evaluator-active"
CONTRACT=".harness/contract.json"
STATE=".harness/state.json"
BREADCRUMBS=".harness/breadcrumbs.jsonl"

# Clear evaluator flag on any subagent completion
if [ -f "$EVALUATOR_FLAG" ]; then
    hooks_log "chain-evaluator" "clearing evaluator-active flag"
    rm -f "$EVALUATOR_FLAG"
fi

# ─── Scenario 1: planner just finished ─────────────────────────────────────
if [ -f "$STATE" ] && [ ! -f "$CONTRACT" ]; then
    AGE=$(hooks_file_age "$STATE")

    if [ "$AGE" -lt 300 ]; then
        hooks_log "chain-evaluator" "planner finished — plan gate"

        TASK_COUNT=$(python3 -c "
import json
try:
    with open('$STATE') as f:
        data = json.load(f)
    print(len(data.get('tasks', [])))
except Exception:
    print('?')
" 2>/dev/null)

        cat <<EOF
{
  "followup_message": "PLAN GATE: The planner produced state.json with $TASK_COUNT tasks. Before starting development:\n1. Read .harness/state.json and present vision, direction, and task list to the user\n2. Ask the user to confirm the plan before proceeding\n3. Do NOT start contract negotiation or building until the user confirms"
}
EOF
        exit 0
    fi
fi

# No contract → no harness state
if [ ! -f "$CONTRACT" ]; then
    hooks_log "chain-evaluator" "no harness state, skipping"
    echo '{}'
    exit 0
fi

# ─── Read contract fields ────────────────────────────────────────────────────
RESULT=$(python3 << 'PYEOF'
import json, os, sys

contract_path = '.harness/contract.json'
breadcrumbs_path = '.harness/breadcrumbs.jsonl'
evaluator_flag = '.cursor/hooks/.evaluator-active'

try:
    with open(contract_path) as f:
        contract = json.load(f)
except Exception as e:
    print(json.dumps({}))
    sys.exit(0)

phase = contract.get('phase', 'unknown')
verified = contract.get('verified', False)
feature = contract.get('feature', 'unknown feature')
task_id = contract.get('task_id', '')

# ─── phase=building: AUTO-ADVANCE STATE ────────────────────────────────────
if phase == 'building':
    # 1. Advance phase to evaluating in contract.json
    patch_ok = False
    try:
        contract['phase'] = 'evaluating'
        contract_text = json.dumps(contract, indent=2, ensure_ascii=False) + '\n'
        with open(contract_path, 'w') as f:
            f.write(contract_text)
        patch_ok = True
    except Exception as e:
        # AC5 fallback: write error
        msg = (
            f'MANUAL: Could not auto-advance contract phase ({e}). '
            f'Manually: set phase=evaluating in .harness/contract.json, '
            f'touch .cursor/hooks/.evaluator-active, then launch /evaluator.'
        )
        print(json.dumps({'followup_message': msg}))
        sys.exit(0)

    # 2. Create .evaluator-active flag (EC2: mkdir if needed)
    flag_dir = os.path.dirname(evaluator_flag)
    try:
        os.makedirs(flag_dir, exist_ok=True)
        with open(evaluator_flag, 'w') as f:
            f.write('')
    except Exception as flag_err:
        # AC5/EC2: flag creation failed → MANUAL fallback (same as write-error path)
        msg = (
            f'MANUAL: Could not create evaluator-active flag ({flag_err}). '
            f'Manually: touch .cursor/hooks/.evaluator-active, then launch /evaluator.'
        )
        print(json.dumps({'followup_message': msg}))
        sys.exit(0)

    # 3. Append dispatch breadcrumb
    import datetime
    ts = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    crumb = {
        'ts': ts,
        'role': 'system',
        'type': 'dispatch',
        'feat': task_id,
        'msg': 'chain-evaluator: auto-advanced to evaluating, evaluator-active flag set',
        'result': 'pass',
    }
    try:
        with open(breadcrumbs_path, 'a') as f:
            f.write(json.dumps(crumb, ensure_ascii=False) + '\n')
    except Exception:
        pass  # EC3: breadcrumbs.jsonl may not exist; non-fatal

    # 4. Return imperative followup_message
    msg = (
        f'Phase auto-advanced to evaluating. Evaluator-active flag set.\n\n'
        f'BUILD COMPLETE for "{feature}".\n\n'
        f'Launch /evaluator now: invoke the /evaluator subagent to verify the implementation '
        f'against the acceptance criteria in .harness/contract.json.\n\n'
        f'The evaluator will test your implementation adversarially and return PASS or FAIL.'
    )
    print(json.dumps({'followup_message': msg}))
    sys.exit(0)

# ─── phase=negotiating/negotiated ─────────────────────────────────────────
if phase in ('negotiating', 'negotiated'):
    msg = (
        f'Contract negotiation complete for "{feature}". '
        f'Set phase to building in .harness/contract.json and start implementation now. '
        f'Steps: (1) update .harness/contract.json phase to "building", '
        f'(2) update state.json task status to "building", '
        f'(3) begin implementation against the acceptance criteria.'
    )
    print(json.dumps({'followup_message': msg}))
    sys.exit(0)

# ─── phase=evaluating ─────────────────────────────────────────────────────
if phase == 'evaluating':
    if verified:
        print(json.dumps({}))
    else:
        msg = (
            f'EVAL FAIL — fix and retry for "{feature}". '
            f'Read the eval report at .harness/.archive/evals/, fix all failing acceptance criteria, '
            f'then launch /evaluator again. '
            f'Max 2 retests per harness rule — if both fail, re-negotiate the contract.'
        )
        print(json.dumps({'followup_message': msg}))
    sys.exit(0)

# ─── other phases (verified, committed) ───────────────────────────────────
print(json.dumps({}))
PYEOF
)

EXIT_CODE=$?

if [ -z "$RESULT" ] || [ "$EXIT_CODE" -ne 0 ]; then
    hooks_log "chain-evaluator" "python failed (exit=$EXIT_CODE), passing"
    echo '{}'
    exit 0
fi

PHASE=$(python3 -c "
import json
try:
    with open('$CONTRACT') as f:
        print(json.load(f).get('phase', '?'))
except:
    print('?')
" 2>/dev/null)
hooks_log "chain-evaluator" "phase=$PHASE, routed"

echo "$RESULT"
exit 0
