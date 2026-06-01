#!/bin/bash
# SessionStart hook: injects current harness state into conversation context.
# Reads state.json, contract.json, and recent breadcrumbs to give the agent
# immediate awareness of where the harness is.
# Output: hookSpecificOutput.additionalContext for SessionStart

input=$(cat)

HOOK_LOG=".claude/hooks.log"
echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] harness-context: triggered" >> "$HOOK_LOG" 2>/dev/null

STATE=".claude/harness/state.json"
CONTRACT=".claude/harness/contract.json"
BREADCRUMBS=".claude/breadcrumbs.jsonl"

# Write a session_start marker so hooks that read breadcrumbs can scope
# their analysis to the current session (breadcrumbs are project-level).
TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
echo "{\"ts\":\"$TS\",\"role\":\"system\",\"type\":\"session_start\",\"feat\":null,\"msg\":\"New chat session started\",\"result\":\"pass\"}" >> "$BREADCRUMBS" 2>/dev/null

if [ ! -f "$STATE" ] && [ ! -f "$CONTRACT" ]; then
  echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] harness-context: no harness state, skipping" >> "$HOOK_LOG" 2>/dev/null
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
        tasks = state.get('tasks', [])
        total = len(tasks)
        done = sum(1 for t in tasks if t.get('status') in ('verified', 'committed'))
        sorted_tasks = sorted(tasks, key=lambda t: (t.get('priority', 99), tasks.index(t)))
        pending = [t for t in sorted_tasks if t.get('status') == 'pending']
        building = [t for t in sorted_tasks if t.get('status') == 'building']

        parts.append(f'Harness active for \"{project}\": {done}/{total} tasks done.')

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
print(json.dumps({
    'hookSpecificOutput': {
        'hookEventName': 'SessionStart',
        'additionalContext': context
    }
}))
" 2>/dev/null)

if [ -z "$CONTEXT" ]; then
  echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] harness-context: python failed, skipping" >> "$HOOK_LOG" 2>/dev/null
  exit 0
fi

echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] harness-context: injected context" >> "$HOOK_LOG" 2>/dev/null
echo "$CONTEXT"
exit 0
