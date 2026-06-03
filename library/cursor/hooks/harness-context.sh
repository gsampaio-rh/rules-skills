#!/bin/bash
# sessionStart hook: injects current harness state into conversation context.
# Reads state.json, contract.json, and recent breadcrumbs to give the agent
# immediate awareness of where the harness is.

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
source "$SCRIPT_DIR/hooks-lib.sh"
hooks_init "harness-context"

STATE=".harness/state.json"
CONTRACT=".harness/contract.json"
BREADCRUMBS=".harness/breadcrumbs.jsonl"

# Write a session_start marker so context-health.sh can scope its analysis
# to the current session only (breadcrumbs are project-level, not session-level).
TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
echo "{\"ts\":\"$TS\",\"role\":\"system\",\"type\":\"session_start\",\"feat\":null,\"msg\":\"New chat session started\",\"result\":\"pass\"}" >> "$BREADCRUMBS" 2>/dev/null

if [ ! -f "$STATE" ] && [ ! -f "$CONTRACT" ]; then
  echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] harness-context: no harness state, injecting cold-start note" >> "$HOOK_LOG" 2>/dev/null
  echo '{"additional_context": "No harness active (.harness/state.json not found). If this task is non-trivial (3+ files, user-facing, architectural), launch /planner to create state.json before implementing."}'
  exit 0
fi

CONTEXT=$(python3 -c "
import json, os

parts = []

state_path = '$STATE'
contract_path = '$CONTRACT'
breadcrumbs_path = '$BREADCRUMBS'

building = []

if os.path.isfile(state_path):
    try:
        with open(state_path) as f:
            state = json.load(f)
        project = state.get('project', 'unknown')
        tasks = state.get('tasks', [])
        total = len(tasks)
        archivable = [t for t in tasks if t.get('status') in ('verified', 'committed', 'cancelled')]
        done = len(archivable)
        sorted_tasks = sorted(tasks, key=lambda t: (t.get('priority', 99), tasks.index(t)))
        pending = [t for t in sorted_tasks if t.get('status') == 'pending']
        building = [t for t in sorted_tasks if t.get('status') == 'building']

        parts.append(f'Harness active for \"{project}\": {done}/{total} tasks done.')

        if len(archivable) >= 10:
            parts.append(f'ARCHIVE ADVISORY: {len(archivable)} completed/cancelled tasks in state.json. Run `python scripts/archive-tasks.py` (or --dry-run first) to move them to .harness/archive.jsonl and keep the backlog lean.')

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
elif building:
    b = building[0]
    parts.append(f'CONTRACT REQUIRED: Task \"{b.get(\"id\",\"?\")}\" is in building status but no contract.json exists. Before writing ANY implementation code, you MUST:')
    parts.append('1. Write .harness/contract.json with: feature, acceptance_criteria (binary-testable), edge_cases, verification_method')
    parts.append('2. Launch the evaluator subagent for contract negotiation')
    parts.append('3. Only after negotiation completes, proceed with implementation')
    parts.append('Skipping the contract violates the adversarial harness protocol.')

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
