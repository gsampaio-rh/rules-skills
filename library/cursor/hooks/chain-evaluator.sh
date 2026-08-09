#!/bin/bash
# subagentStop: building→evaluating + .evaluator-active. Prose advisories → skill.

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
source "$SCRIPT_DIR/hooks-lib.sh"
hooks_init "chain-evaluator"

FLAG=".cursor/hooks/.evaluator-active"
CONTRACT=".harness/contract.json"

SUBAGENT_TYPE=$(echo "$HOOK_INPUT" | python3 -c "
import sys, json
try:
    d=json.load(sys.stdin); print(d.get('subagent_type') or d.get('subagentType') or '')
except Exception: print('')
" 2>/dev/null)

[ -f "$FLAG" ] && { hooks_log "chain-evaluator" "clearing evaluator-active flag"; rm -f "$FLAG"; }

if [ -n "$SUBAGENT_TYPE" ] && [ "$SUBAGENT_TYPE" != "planner" ] && [ "$SUBAGENT_TYPE" != "evaluator" ]; then
  hooks_log "chain-evaluator" "skip orchestration for subagent_type=$SUBAGENT_TYPE"
  echo '{}'; exit 0
fi

[ ! -f "$CONTRACT" ] && { hooks_log "chain-evaluator" "no contract, skipping"; echo '{}'; exit 0; }

RESULT=$(python3 << 'PY'
import json, os, sys, datetime
path, crumbs, flag = '.harness/contract.json', '.harness/breadcrumbs.jsonl', '.cursor/hooks/.evaluator-active'
try:
    contract = json.load(open(path))
except Exception:
    print(json.dumps({})); sys.exit(0)
if contract.get('phase') != 'building':
    print(json.dumps({})); sys.exit(0)
feat, tid = contract.get('feature', 'unknown feature'), contract.get('task_id', '')
try:
    contract['phase'] = 'evaluating'
    open(path, 'w').write(json.dumps(contract, indent=2, ensure_ascii=False) + '\n')
except Exception as e:
    print(json.dumps({'followup_message': f'MANUAL: Could not auto-advance contract phase ({e}). Set phase=evaluating, touch .cursor/hooks/.evaluator-active, launch /evaluator.'}))
    sys.exit(0)
try:
    os.makedirs(os.path.dirname(flag), exist_ok=True)
    open(flag, 'w').write('')
except Exception as e:
    print(json.dumps({'followup_message': f'MANUAL: Could not create evaluator-active flag ({e}). touch .cursor/hooks/.evaluator-active, then launch /evaluator.'}))
    sys.exit(0)
try:
    open(crumbs, 'a').write(json.dumps({
        'ts': datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
        'role': 'system', 'type': 'dispatch', 'feat': tid,
        'msg': 'chain-evaluator: auto-advanced to evaluating, evaluator-active flag set',
        'result': 'pass',
    }, ensure_ascii=False) + '\n')
except Exception:
    pass
print(json.dumps({'followup_message': f'Phase auto-advanced to evaluating. Evaluator-active flag set.\n\nBUILD COMPLETE for "{feat}". Launch /evaluator now.'}))
PY
)

[ -z "$RESULT" ] && { hooks_log "chain-evaluator" "python failed, passing"; echo '{}'; exit 0; }
hooks_log "chain-evaluator" "routed"
echo "$RESULT"
exit 0
