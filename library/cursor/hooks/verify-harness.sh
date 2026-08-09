#!/bin/bash
# Stop: anti-self-cert + post-commit ADVANCE + stale cleanup. Soft followup ≠ deny.

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
source "$SCRIPT_DIR/hooks-lib.sh"
hooks_init "verify-harness"

CONTRACT=".harness/contract.json"
STATE=".harness/state.json"
BREADCRUMBS=".harness/breadcrumbs.jsonl"

# Path 0: post-commit ADVANCE (verified + Commit: checkpoint → archive contract).
if [ -f "$CONTRACT" ] && [ -f "$BREADCRUMBS" ] && [ -f "$STATE" ]; then
  POST_COMMIT_ACTION=$(python3 -c "
import json, os
contract=json.load(open('$CONTRACT'))
if not contract.get('verified'):
    print('SKIP'); raise SystemExit
lines=[l.strip() for l in open('$BREADCRUMBS') if l.strip()]
recent=[]
for line in lines[-3:]:
    try: recent.append(json.loads(line))
    except Exception: pass
if not any(e.get('type')=='checkpoint' and 'Commit:' in e.get('msg','') for e in recent):
    print('SKIP'); raise SystemExit
task_id=contract.get('task_id', contract.get('feature',''))
state=json.load(open('$STATE'))
advanced=False
for t in state.get('tasks',[]):
    if t.get('id')==task_id and t.get('status') in ('verified','building','evaluating'):
        t['status']='committed'; advanced=True; break
if not advanced:
    print('SKIP'); raise SystemExit
open('$STATE','w').write(json.dumps(state, indent=2)+'\n')
os.remove('$CONTRACT')
harvest_type, harvest_rationale = 'none', ''
try:
    hr=json.load(open(f'.harness/.archive/evals/eval-{task_id}.json')).get('harvest_recommendation',{})
    harvest_type=hr.get('type','none') if hr.get('type') in ('skill','hook','none') else 'none'
    harvest_rationale=hr.get('rationale','')
except Exception: pass
pending=[t for t in state.get('tasks',[]) if t.get('status')=='pending']
next_task=pending[0]['id'] if pending else 'none'
print(f'ADVANCE|{task_id}|{next_task}|{harvest_type}|{harvest_rationale}')
" 2>/dev/null)

  if [ "$(echo "$POST_COMMIT_ACTION" | cut -d'|' -f1)" = "ADVANCE" ]; then
    COMMITTED_TASK=$(echo "$POST_COMMIT_ACTION" | cut -d'|' -f2)
    NEXT_TASK=$(echo "$POST_COMMIT_ACTION" | cut -d'|' -f3)
    HARVEST_TYPE=$(echo "$POST_COMMIT_ACTION" | cut -d'|' -f4)
    HARVEST_RATIONALE=$(echo "$POST_COMMIT_ACTION" | cut -d'|' -f5-)
    HARVEST_BLOCK=""
    if [ "$HARVEST_TYPE" = "skill" ] || [ "$HARVEST_TYPE" = "hook" ]; then
      HARVEST_BLOCK="\n\nHARVEST: reusable ${HARVEST_TYPE}. ${HARVEST_RATIONALE}"
    fi
    if [ "$NEXT_TASK" != "none" ]; then
      printf '%s\n' "{\"followup_message\": \"POST-COMMIT: Task \\\"$COMMITTED_TASK\\\" committed; contract archived. Next: $NEXT_TASK — write contract.json then /evaluator.${HARVEST_BLOCK}\"}"
    else
      printf '%s\n' "{\"followup_message\": \"POST-COMMIT: Task \\\"$COMMITTED_TASK\\\" committed; contract archived. All tasks complete.${HARVEST_BLOCK}\"}"
    fi
    exit 0
  fi
fi

# Path 1: contract present — scope + anti-self-cert + unverified soft pointer.
if [ -f "$CONTRACT" ]; then
  CONTRACT_ACTIVE=$(python3 -c "
import json, os
c=json.load(open('$CONTRACT'))
phase, task_id = c.get('phase',''), c.get('task_id','')
if phase in ('idle','committed') or not task_id: print('STALE'); raise SystemExit
if phase in ('negotiating','negotiated'): print('PRE_BUILD'); raise SystemExit
if os.path.exists('$STATE'):
    buildingish={t['id'] for t in json.load(open('$STATE')).get('tasks',[]) if t.get('status') in ('building','evaluating')}
    if not buildingish: print('NO_BUILD'); raise SystemExit
    if task_id not in buildingish: print('CROSS_THREAD'); raise SystemExit
print('ACTIVE')
" 2>/dev/null)

  case "$CONTRACT_ACTIVE" in
    STALE) rm -f "$CONTRACT"; echo '{}'; exit 0 ;;
    PRE_BUILD|NO_BUILD|CROSS_THREAD) echo '{}'; exit 0 ;;
  esac

  [ ! -f "$BREADCRUMBS" ] && {
    echo '{"followup_message":"HARNESS GATE: contract exists but breadcrumbs.jsonl missing — create it."}'
    exit 0
  }

  VERIFIED=$(python3 -c "
import json
try:
    print(str(json.load(open('$CONTRACT')).get('verified', False)))
except json.JSONDecodeError: print('PARSE_ERROR')
except Exception: print('False')
" 2>/dev/null)

  [ "$VERIFIED" = "PARSE_ERROR" ] && { echo '{}'; exit 0; }

  if [ "$VERIFIED" = "True" ]; then
    TASK_ID=$(python3 -c "import json; print(json.load(open('$CONTRACT')).get('task_id',''))" 2>/dev/null)
    EVAL_PASS=$(python3 -c "
import json
task_id='$TASK_ID'
try:
    for line in open('$BREADCRUMBS'):
        line=line.strip()
        if not line: continue
        try: b=json.loads(line)
        except Exception: continue
        if b.get('role')=='evaluator' and str(b.get('result','')).lower()=='pass' and (not task_id or b.get('feat','') in (task_id,'')):
            print('YES'); raise SystemExit
    print('NO')
except Exception: print('NO')
" 2>/dev/null)

    if [ "$EVAL_PASS" = "YES" ]; then
      python3 -c "
import json
tid='$TASK_ID'
try:
    s=json.load(open('$STATE'))
    for t in s.get('tasks',[]):
        if t.get('id')==tid and t.get('status')!='verified':
            t['status']='verified'; break
    open('$STATE','w').write(json.dumps(s, indent=2)+'\n')
except Exception: pass
" 2>/dev/null
      echo '{}'; exit 0
    fi
    FEATURE=$(python3 -c "import json; print(json.load(open('$CONTRACT')).get('feature','unknown'))" 2>/dev/null)
    cat <<EOF
{"followup_message":"HARNESS GATE: verified:true for \"$FEATURE\" but no evaluator pass breadcrumb. Launch /evaluator (role=evaluator, result=pass, feat=$TASK_ID)."}
EOF
    exit 0
  fi

  FEATURE=$(python3 -c "import json; print(json.load(open('$CONTRACT')).get('feature','unknown'))" 2>/dev/null)
  cat <<EOF
{"followup_message":"HARNESS GATE: contract for \"$FEATURE\" unverified. Launch /evaluator against .harness/contract.json."}
EOF
  exit 0
fi

# No contract → pass (contract-gate owns write deny).
echo '{}'
exit 0
