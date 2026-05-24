#!/bin/bash
# sessionStart hook: injects current harness state into conversation context.
# Reads state.json, contract.json, and recent breadcrumbs to give the agent
# immediate awareness of where the harness is.

input=$(cat)

HOOK_LOG=".cursor/hooks.log"
echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] harness-context: triggered" >> "$HOOK_LOG" 2>/dev/null

STATE=".cursor/harness/state.json"
CONTRACT=".cursor/harness/contract.json"
BREADCRUMBS=".cursor/breadcrumbs.jsonl"

if [ ! -f "$STATE" ] && [ ! -f "$CONTRACT" ]; then
  echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] harness-context: no harness state, skipping" >> "$HOOK_LOG" 2>/dev/null
  echo '{}'
  exit 0
fi

CONTEXT=$(python3 -c "
import json, os

parts = []

state_path = '$STATE'
contract_path = '$CONTRACT'
breadcrumbs_path = '$BREADCRUMBS'

if os.path.isfile(state_path):
    try:
        with open(state_path) as f:
            state = json.load(f)
        project = state.get('project', 'unknown')
        features = state.get('features', [])
        total = len(features)
        done = sum(1 for f in features if f.get('status') in ('verified', 'committed'))
        pending = [f for f in features if f.get('status') == 'pending']
        building = [f for f in features if f.get('status') == 'building']

        parts.append(f'Harness active for \"{project}\": {done}/{total} features done.')

        if building:
            b = building[0]
            parts.append(f'Currently building: {b.get(\"id\", \"?\") } ({b.get(\"name\", \"unnamed\")}).')
        elif pending:
            p = pending[0]
            parts.append(f'Next pending: {p.get(\"id\", \"?\")} ({p.get(\"name\", \"unnamed\")}).')
    except Exception:
        parts.append('Harness state.json exists but could not be parsed.')

if os.path.isfile(contract_path):
    try:
        with open(contract_path) as f:
            contract = json.load(f)
        feat = contract.get('feature', 'unknown')
        phase = contract.get('phase', 'unknown')
        verified = contract.get('verified', False)
        parts.append(f'Contract for \"{feat}\": phase={phase}, verified={verified}.')
    except Exception:
        parts.append('Contract exists but could not be parsed.')

if os.path.isfile(breadcrumbs_path):
    try:
        with open(breadcrumbs_path) as f:
            lines = f.readlines()
        recent = lines[-3:] if len(lines) >= 3 else lines
        msgs = []
        for line in recent:
            try:
                entry = json.loads(line.strip())
                msgs.append(f'  [{entry.get(\"role\",\"?\")}] {entry.get(\"msg\",\"?\")}')
            except Exception:
                pass
        if msgs:
            parts.append('Recent breadcrumbs:')
            parts.extend(msgs)
    except Exception:
        pass

context = '\\n'.join(parts)
print(json.dumps({'additional_context': context}))
" 2>/dev/null)

if [ -z "$CONTEXT" ]; then
  echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] harness-context: python failed, skipping" >> "$HOOK_LOG" 2>/dev/null
  echo '{}'
  exit 0
fi

echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] harness-context: injected context" >> "$HOOK_LOG" 2>/dev/null
echo "$CONTEXT"
exit 0
