#!/bin/bash
# sessionStart: inject lean context-package + harness maintenance (no novel advisories).

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
source "$SCRIPT_DIR/hooks-lib.sh"
hooks_init "harness-context"

HARNESS_ROOT="${HARNESS_ROOT:-.}"
STATE="$HARNESS_ROOT/.harness/state.json"
CONTRACT="$HARNESS_ROOT/.harness/contract.json"
BREADCRUMBS="$HARNESS_ROOT/.harness/breadcrumbs.jsonl"
CONTEXT_PKG="$SCRIPT_DIR/context-package.py"
ARCHIVE="$HARNESS_ROOT/.harness/.archive/archive.jsonl"
HOOK_LOG_FILE="$HARNESS_ROOT/.cursor/hooks.log"

PYTHON_BIN=""
command -v python3 >/dev/null 2>&1 && PYTHON_BIN="python3"
[ -z "$PYTHON_BIN" ] && command -v python >/dev/null 2>&1 && PYTHON_BIN="python"

TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
mkdir -p "$HARNESS_ROOT/.harness" 2>/dev/null
echo "{\"ts\":\"$TS\",\"role\":\"system\",\"type\":\"session_start\",\"feat\":null,\"msg\":\"New chat session started\",\"result\":\"pass\"}" >> "$BREADCRUMBS" 2>/dev/null
hooks_session_stats_reset

# Auto-maintenance: archive done tasks, truncate breadcrumbs, compress bloated state.
if [ -n "$PYTHON_BIN" ] && [ -f "$STATE" ]; then
  "$PYTHON_BIN" - "$STATE" "$BREADCRUMBS" "$ARCHIVE" "$CONTRACT" << 'MAINT' 2>/dev/null
import json, os, sys
from datetime import datetime, timezone
state_path, breadcrumbs_path, archive_path, contract_path = sys.argv[1:5]
ts = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
os.makedirs(os.path.dirname(archive_path), exist_ok=True)
try:
    state = json.load(open(state_path))
    done = {'verified', 'committed', 'cancelled'}
    active = [t for t in state.get('tasks', []) if t.get('status') not in done]
    archived = [t for t in state.get('tasks', []) if t.get('status') in done]
    if archived:
        with open(archive_path, 'a') as af:
            for t in archived:
                af.write(json.dumps({'ts': ts, 'type': 'task_archived', 'task': t}) + '\n')
        state['tasks'] = active
        open(state_path, 'w').write(json.dumps(state, indent=2) + '\n')
except Exception:
    pass
try:
    if os.path.isfile(breadcrumbs_path):
        lines = [l for l in open(breadcrumbs_path) if l.strip()]
        if len(lines) > 30:
            evicted, retained = lines[:-30], lines[-30:]
            anchor_line = None
            try:
                st = json.load(open(state_path))
                active = [t for t in st.get('tasks', []) if t.get('status') in ('pending', 'building', 'evaluating')]
                if active:
                    task_id = active[0].get('id')
                    signal_types = {'evaluate', 'negotiate', 'build'}
                    for l in reversed(lines):
                        try:
                            e = json.loads(l)
                            if e.get('type') in signal_types and e.get('feat') == task_id:
                                if l in evicted:
                                    anchor_line = l if l.endswith('\n') else l + '\n'
                                break
                        except Exception:
                            pass
            except Exception:
                pass
            with open(archive_path, 'a') as af:
                af.writelines(l if l.endswith('\n') else l + '\n' for l in evicted)
                if anchor_line:
                    displaced = retained[0]
                    af.write(displaced if displaced.endswith('\n') else displaced + '\n')
                    retained = [anchor_line] + retained[1:]
            open(breadcrumbs_path, 'w').writelines(retained)
except Exception:
    pass
try:
    state = json.load(open(state_path))
    active_tasks = [t for t in state.get('tasks', []) if t.get('status') in ('pending', 'building', 'evaluating')]
    if len(active_tasks) == 0 and os.path.getsize(state_path) > 2000:
        keep = {'project', 'schema_version', 'vision', 'tasks'}
        extra = {k: v for k, v in state.items() if k not in keep}
        if extra:
            with open(archive_path, 'a') as af:
                af.write(json.dumps({'ts': ts, 'type': 'state_compressed', 'fields': extra}) + '\n')
            slim = {k: state[k] for k in keep if k in state}
            open(state_path, 'w').write(json.dumps(slim, indent=2) + '\n')
except Exception:
    pass
try:
    # Auto-archive orphan contract: verified=True with no active tasks means the
    # task was committed/cancelled and the contract is no longer needed.
    # Runs after task archival above so active_tasks reflects post-cleanup state.
    if os.path.isfile(contract_path):
        contract = json.load(open(contract_path))
        if contract.get('verified'):
            state = json.load(open(state_path))
            active_tasks = [t for t in state.get('tasks', []) if t.get('status') in ('pending', 'building', 'evaluating')]
            if not active_tasks:
                with open(archive_path, 'a') as af:
                    af.write(json.dumps({
                        'ts': ts, 'type': 'contract_archived',
                        'contract_task_id': contract.get('task_id'),
                        'phase': contract.get('phase'),
                    }) + '\n')
                os.remove(contract_path)
except Exception:
    pass
MAINT
fi

if [ -f "$HOOK_LOG_FILE" ] && [ "$(wc -l < "$HOOK_LOG_FILE" 2>/dev/null | tr -d ' ')" -gt 100 ]; then
  tail -100 "$HOOK_LOG_FILE" > "$HOOK_LOG_FILE.tmp" && mv "$HOOK_LOG_FILE.tmp" "$HOOK_LOG_FILE" 2>/dev/null
fi

# Idle harness state is just-in-time: with no pending/building/evaluating task,
# inject the one-line free-default message. An active task still prefetches the
# context package because the model will use the contract and criteria.
# The practice brief left pre-fetch vs just-in-time unresolved; this chooses
# just-in-time for the idle case only.
if [ -f "$STATE" ]; then
  ACTIVE_TASK=$(${PYTHON_BIN:-python3} -c "
import json
try:
    tasks = json.load(open('$STATE')).get('tasks', [])
except Exception:
    tasks = []
active = {'pending', 'building', 'evaluating'}
print('yes' if any(t.get('status') in active for t in tasks) else 'no')
" 2>/dev/null || echo no)
  if [ "$ACTIVE_TASK" != "yes" ]; then
    echo '{"additional_context":"No harness active. Work freely by default. Opt in with use harness / /planner when you want full planner→contract→gates."}'
    exit 0
  fi
fi

if [ ! -f "$STATE" ] && [ ! -f "$CONTRACT" ]; then
  echo '{"additional_context":"No harness active. Work freely by default. Opt in with use harness / /planner when you want full planner→contract→gates."}'
  exit 0
fi

TMP_PKG=$(mktemp)
trap 'rm -f "$TMP_PKG"' EXIT
if [ -n "$PYTHON_BIN" ] && [ -f "$CONTEXT_PKG" ]; then
  "$PYTHON_BIN" "$CONTEXT_PKG" --format markdown --root "$HARNESS_ROOT" > "$TMP_PKG" 2>/dev/null
fi
if [ ! -s "$TMP_PKG" ]; then
  echo "## Current Task"$'\n'"(context-package unavailable)" > "$TMP_PKG"
fi

${PYTHON_BIN:-python3} - "$TMP_PKG" << 'PY'
import json, sys
pkg = open(sys.argv[1]).read().strip()
print(json.dumps({'additional_context': pkg or '(empty)'}))
PY
exit 0
