#!/bin/bash
# sessionStart hook: injects lean harness state (task + AC slice + last 3 crumbs).
# Calls context-package.py (co-located in this hooks directory) for the main
# context block, then appends session counter, SESSION BOUNDARY ADVISORY,
# and prune advisory.
#
# HARNESS_ROOT env var overrides the repo root (default: CWD). Used in tests.

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
source "$SCRIPT_DIR/hooks-lib.sh"
hooks_init "harness-context"

HARNESS_ROOT="${HARNESS_ROOT:-.}"
STATE="$HARNESS_ROOT/.harness/state.json"
CONTRACT="$HARNESS_ROOT/.harness/contract.json"
BREADCRUMBS="$HARNESS_ROOT/.harness/breadcrumbs.jsonl"
CONTEXT_PKG="$SCRIPT_DIR/context-package.py"

# Resolve Python interpreter: prefer python3, fall back to python.
PYTHON_BIN=""
if command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
fi

# Temp files for safe multiline content composition.
TMP_PKG=$(mktemp)
TMP_SUFFIX=$(mktemp)
trap 'rm -f "$TMP_PKG" "$TMP_SUFFIX"' EXIT

# Write session_start breadcrumb for session boundary tracking.
TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
mkdir -p "$HARNESS_ROOT/.harness" 2>/dev/null
echo "{\"ts\":\"$TS\",\"role\":\"system\",\"type\":\"session_start\",\"feat\":null,\"msg\":\"New chat session started\",\"result\":\"pass\"}" >> "$BREADCRUMBS" 2>/dev/null

# P6: reset session turn/write counters so prior-session stats cannot false-positive.
hooks_session_stats_reset

# ── Auto-maintenance on session start ─────────────────────────────────────────
# 1. Archive completed tasks from state.json
# 2. Truncate breadcrumbs.jsonl to rolling 30-line window
# 3. Compress state.json if bloated (>50 lines, 0 active tasks)
# 4. Truncate hooks.log to last 100 lines
ARCHIVE="$HARNESS_ROOT/.harness/.archive/archive.jsonl"
HOOK_LOG_FILE="$HARNESS_ROOT/.cursor/hooks.log"

if [ -n "$PYTHON_BIN" ] && [ -f "$STATE" ]; then
  "$PYTHON_BIN" - "$STATE" "$BREADCRUMBS" "$ARCHIVE" << 'MAINT_EOF' 2>/dev/null
import json, os, sys
from datetime import datetime, timezone

state_path, breadcrumbs_path, archive_path = sys.argv[1], sys.argv[2], sys.argv[3]
ts = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
os.makedirs(os.path.dirname(archive_path), exist_ok=True)

# --- 1. Auto-archive completed tasks ---
try:
    state = json.load(open(state_path))
    tasks = state.get('tasks', [])
    done_statuses = {'verified', 'committed', 'cancelled'}
    active = [t for t in tasks if t.get('status') not in done_statuses]
    archived = [t for t in tasks if t.get('status') in done_statuses]

    if archived:
        with open(archive_path, 'a') as af:
            for t in archived:
                entry = {'ts': ts, 'type': 'task_archived', 'task': t}
                af.write(json.dumps(entry) + '\n')
        state['tasks'] = active
        with open(state_path, 'w') as sf:
            json.dump(state, sf, indent=2)
            sf.write('\n')
except Exception:
    pass

# --- 2. Truncate breadcrumbs to last 30 lines ---
try:
    if os.path.isfile(breadcrumbs_path):
        lines = [l for l in open(breadcrumbs_path).readlines() if l.strip()]
        if len(lines) > 30:
            overflow = lines[:-30]
            with open(archive_path, 'a') as af:
                for line in overflow:
                    af.write(line if line.endswith('\n') else line + '\n')
            with open(breadcrumbs_path, 'w') as bf:
                bf.writelines(lines[-30:])
except Exception:
    pass

# --- 3. Compress state if bloated ---
try:
    state = json.load(open(state_path))
    tasks = state.get('tasks', [])
    active_tasks = [t for t in tasks if t.get('status') in ('pending', 'building', 'evaluating')]
    state_size = os.path.getsize(state_path)

    if len(active_tasks) == 0 and state_size > 2000:
        keep_keys = {'project', 'schema_version', 'vision', 'tasks'}
        compressed_fields = {k: v for k, v in state.items() if k not in keep_keys}
        if compressed_fields:
            with open(archive_path, 'a') as af:
                entry = {'ts': ts, 'type': 'state_compressed', 'fields': compressed_fields}
                af.write(json.dumps(entry) + '\n')
            slim = {k: state[k] for k in keep_keys if k in state}
            with open(state_path, 'w') as sf:
                json.dump(slim, sf, indent=2)
                sf.write('\n')
except Exception:
    pass
MAINT_EOF
fi

# Truncate hooks.log to last 100 lines
if [ -f "$HOOK_LOG_FILE" ] && [ "$(wc -l < "$HOOK_LOG_FILE" 2>/dev/null | tr -d ' ')" -gt 100 ]; then
  tail -100 "$HOOK_LOG_FILE" > "$HOOK_LOG_FILE.tmp" && mv "$HOOK_LOG_FILE.tmp" "$HOOK_LOG_FILE" 2>/dev/null
fi

# Cold-start: no harness files at all.
if [ ! -f "$STATE" ] && [ ! -f "$CONTRACT" ]; then
  echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] harness-context: no harness state, cold-start note" >> "$HOOK_LOG" 2>/dev/null
  echo '{"additional_context": "No harness active (.harness/state.json not found). If this task is non-trivial (3+ files, user-facing, architectural), launch /planner to create state.json before implementing."}'
  exit 0
fi

# ── Context package (markdown) → $TMP_PKG ────────────────────────────────────
if [ -n "$PYTHON_BIN" ] && [ -f "$CONTEXT_PKG" ]; then
  "$PYTHON_BIN" "$CONTEXT_PKG" --format markdown --root "$HARNESS_ROOT" > "$TMP_PKG" 2>/dev/null
fi

# Fallback when context-package.py is unavailable or produced empty output.
if [ ! -s "$TMP_PKG" ]; then
  {
    echo "## Current Task"
    echo "(context-package unavailable — reading state directly)"
    if [ -n "$PYTHON_BIN" ] && [ -f "$CONTRACT" ]; then
      "$PYTHON_BIN" -c "
import json
try:
    c = json.load(open('$CONTRACT'))
    print('## Acceptance Criteria')
    for ac in c.get('acceptance_criteria', []):
        print(f'- {ac}')
except Exception:
    pass
" 2>/dev/null
    fi
  } > "$TMP_PKG"
fi

# ── Session counter, advisories → $TMP_SUFFIX ────────────────────────────────
${PYTHON_BIN:-python3} - "$STATE" "$CONTRACT" "$BREADCRUMBS" > "$TMP_SUFFIX" 2>/dev/null << 'PYEOF'
import json, os, sys

state_path, contract_path, breadcrumbs_path = sys.argv[1], sys.argv[2], sys.argv[3]
parts = []

# Archive advisory and contract-without-state warning.
building = []
try:
    if os.path.isfile(state_path):
        state = json.load(open(state_path))
        tasks = state.get('tasks', [])
        sorted_tasks = sorted(tasks, key=lambda t: (t.get('priority', 99), tasks.index(t)))
        building = [t for t in sorted_tasks if t.get('status') == 'building']
        # Warn if >5 active tasks (auto-archive already ran; these are genuinely active)
        active = [t for t in tasks if t.get('status') in ('pending', 'building', 'evaluating')]
        if len(active) > 5:
            parts.append(f'TASK OVERLOAD: {len(active)} active tasks in state.json (max recommended: 5). Complete current work before adding more.')
    if not os.path.isfile(contract_path) and building:
        b = building[0]
        parts.append(f'CONTRACT REQUIRED: Task "{b.get("id","?")}" is building but no contract.json exists.')
        parts.append('Before ANY implementation code: write .harness/contract.json then launch /evaluator.')
except Exception:
    pass

# Session task counting (between last two session_start markers).
session_task_count = 0
try:
    if os.path.isfile(breadcrumbs_path):
        lines = open(breadcrumbs_path).readlines()
        parsed = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                parsed.append(json.loads(line))
            except Exception:
                parsed.append(None)
        markers = [i for i, e in enumerate(parsed) if e is not None and e.get('type') == 'session_start']
        if len(markers) >= 2:
            lo, hi = markers[-2] + 1, markers[-1]
            window = [e for e in parsed[lo:hi] if e is not None]
            feat_ids = set()
            for e in window:
                feat = e.get('feat')
                if (feat and e.get('role') == 'builder'
                        and e.get('type') == 'build'
                        and str(e.get('result', '')).lower() == 'pass'):
                    feat_ids.add(feat)
            session_task_count = len(feat_ids)
except Exception:
    pass

parts.append(f'Session tasks completed: {session_task_count}')
if session_task_count >= 3:
    parts.append(
        f'SESSION BOUNDARY ADVISORY: {session_task_count} tasks completed in the prior session window. '
        f'Checkpoint uncommitted work, append a handoff breadcrumb to .harness/breadcrumbs.jsonl '
        f'(Last: / Next:), and suggest a fresh thread before continuing.'
    )
print('\n'.join(parts))
PYEOF

# ── Prune advisory (>40 non-empty breadcrumb lines — shouldn't happen with auto-truncate)
PRUNE_NOTE=""
if [ -f "$BREADCRUMBS" ]; then
  BC_LINES=$(grep -c . "$BREADCRUMBS" 2>/dev/null || echo 0)
  if [ "$BC_LINES" -gt 40 ]; then
    PRUNE_NOTE="PRUNE WARNING: breadcrumbs.jsonl has ${BC_LINES} lines despite auto-truncation. Check if session maintenance failed."
  fi
fi

# ── Compose final JSON output ─────────────────────────────────────────────────
CONTEXT=$(${PYTHON_BIN:-python3} - "$TMP_PKG" "$TMP_SUFFIX" "$PRUNE_NOTE" << 'PYEOF'
import json, sys

pkg_path, suffix_path, prune_note = sys.argv[1], sys.argv[2], sys.argv[3]

pkg_md = open(pkg_path).read().strip() if __import__('os').path.isfile(pkg_path) else ''
suffix = open(suffix_path).read().strip() if __import__('os').path.isfile(suffix_path) else ''
prune = prune_note.strip()

parts = [p for p in [pkg_md, suffix, prune] if p]
additional_context = '\n\n'.join(parts)
print(json.dumps({'additional_context': additional_context}))
PYEOF
)

if [ -z "$CONTEXT" ]; then
  echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] harness-context: composition failed, empty context" >> "$HOOK_LOG" 2>/dev/null
  echo '{}'
  exit 0
fi

echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] harness-context: injected context" >> "$HOOK_LOG" 2>/dev/null
echo "$CONTEXT"
exit 0
