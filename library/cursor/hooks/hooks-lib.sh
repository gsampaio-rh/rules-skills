#!/bin/bash
# Shared library for Cursor hook scripts.
# Source via: SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
#             source "$SCRIPT_DIR/hooks-lib.sh"

# --- hooks_init hook_name ---
# Read stdin into $HOOK_INPUT, set HOOK_LOG, write trigger breadcrumb.
hooks_init() {
  local hook_name="${1:?hooks_init requires hook_name}"
  HOOK_INPUT=$(cat)
  HOOK_LOG=".cursor/hooks.log"
  hooks_log "$hook_name" "triggered"
}

# --- hooks_log hook_name message ---
# Append timestamped entry to $HOOK_LOG.
hooks_log() {
  local hook_name="${1:?hooks_log requires hook_name}"
  local message="${2:?hooks_log requires message}"
  local log="${HOOK_LOG:-.cursor/hooks.log}"
  echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] $hook_name: $message" >> "$log" 2>/dev/null
}

# --- hooks_extract_path [json_string] ---
# Extract target file path from tool input JSON.
# Reads from $1 if provided, otherwise from $HOOK_INPUT.
# Walks input/toolInput/tool_input for path/file_path/filePath.
# Prints path on stdout (empty if not found). Does NOT read stdin.
hooks_extract_path() {
  local json="${1:-$HOOK_INPUT}"
  echo "$json" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    path = ''
    for key in ('input', 'toolInput', 'tool_input'):
        nested = data.get(key)
        if isinstance(nested, dict):
            path = nested.get('path', nested.get('file_path', nested.get('filePath', '')))
            if path:
                break
    if not path:
        path = data.get('path', data.get('file_path', data.get('filePath', '')))
    print(path)
except Exception:
    print('')
" 2>/dev/null
}

# --- hooks_read_state state_path ---
# Parse state.json, return JSON with task metadata.
# Returns: {building_id, building_name, building_type, pending_id, pending_name,
#           pending_type, has_gatable, task_count, done_count}
# Callers apply their own GATE/SKIP logic using these fields.
hooks_read_state() {
  local state_path="${1:?hooks_read_state requires state_path}"
  python3 -c "
import json, sys
try:
    with open('$state_path') as f:
        data = json.load(f)
    tasks = data.get('tasks', [])
    sorted_tasks = sorted(tasks, key=lambda t: (t.get('priority', 99), tasks.index(t)))
    building = [t for t in sorted_tasks if t.get('status') == 'building']
    pending = [t for t in sorted_tasks if t.get('status') == 'pending']
    gatable = {'feature', 'bug', 'gap', 'fix'}
    has_gatable = any(
        t.get('type', 'feature') in gatable
        for t in tasks if t.get('status') in ('pending', 'building')
    )
    done = sum(1 for t in tasks if t.get('status') in ('verified', 'committed'))
    b = building[0] if building else {}
    p = pending[0] if pending else {}
    result = {
        'building_id': b.get('id', ''),
        'building_name': b.get('name', ''),
        'building_type': b.get('type', ''),
        'pending_id': p.get('id', ''),
        'pending_name': p.get('name', ''),
        'pending_type': p.get('type', ''),
        'has_gatable': has_gatable,
        'task_count': len(tasks),
        'done_count': done,
    }
    print(json.dumps(result))
except Exception:
    print(json.dumps({
        'building_id': '', 'building_name': '', 'building_type': '',
        'pending_id': '', 'pending_name': '', 'pending_type': '',
        'has_gatable': False, 'task_count': 0, 'done_count': 0,
    }))
" 2>/dev/null
}

# --- hooks_file_age file_path ---
# Cross-platform file age in seconds. Prints seconds since mtime.
hooks_file_age() {
  local file_path="${1:?hooks_file_age requires file_path}"
  local now mtime
  now=$(date +%s)
  mtime=$(stat -f %m "$file_path" 2>/dev/null || stat -c %Y "$file_path" 2>/dev/null || echo 0)
  echo $((now - mtime))
}

# --- hooks_skip_detected [breadcrumbs_path] ---
# Check last 5 breadcrumbs for "Skipped harness". Exit 0 = found, 1 = not found.
hooks_skip_detected() {
  local bc_path="${1:-.harness/breadcrumbs.jsonl}"
  [ -f "$bc_path" ] || return 1
  tail -5 "$bc_path" | grep -q "Skipped harness" 2>/dev/null
}

# --- hooks_git_total_count ---
# Count ALL changed + staged + untracked files (no filter).
# Used by enforce-progress.sh which counts every file.
hooks_git_total_count() {
  local changed staged untracked
  changed=$(git diff --name-only 2>/dev/null | wc -l | tr -d ' ')
  staged=$(git diff --cached --name-only 2>/dev/null | wc -l | tr -d ' ')
  untracked=$(git ls-files --others --exclude-standard 2>/dev/null | wc -l | tr -d ' ')
  echo $((changed + staged + untracked))
}

# --- hooks_git_impl_count ---
# Count implementation-only files (excludes .cursor/, breadcrumbs, .md, .json, .yaml).
# Used by verify-harness.sh Path 2 which only gates on impl changes.
hooks_git_impl_count() {
  local filter='\.cursor/|breadcrumbs|\.md$|\.json$|\.yaml$'
  local changed staged untracked
  changed=$(git diff --name-only 2>/dev/null | grep -vE "$filter" | wc -l | tr -d ' ')
  staged=$(git diff --cached --name-only 2>/dev/null | grep -vE "$filter" | wc -l | tr -d ' ')
  untracked=$(git ls-files --others --exclude-standard 2>/dev/null | grep -vE "$filter" | wc -l | tr -d ' ')
  echo $((changed + staged + untracked))
}

# --- Session stats (.harness/.session-stats.json) — P6 handoff counters ---
# Fields: turns (beforeSubmitPrompt), source_writes (Write/StrReplace to source paths).

hooks_session_stats_file() {
  echo "${HARNESS_ROOT:-.}/.harness/.session-stats.json"
}

# Reset turns/source_writes to 0 (called on sessionStart).
hooks_session_stats_reset() {
  local root="${HARNESS_ROOT:-.}"
  mkdir -p "$root/.harness" 2>/dev/null
  printf '%s\n' '{"turns":0,"source_writes":0}' > "$root/.harness/.session-stats.json"
}

# Increment a numeric field (turns|source_writes). Creates file if missing.
hooks_session_stats_inc() {
  local field="${1:?hooks_session_stats_inc requires field}"
  local root="${HARNESS_ROOT:-.}"
  local path="$root/.harness/.session-stats.json"
  mkdir -p "$root/.harness" 2>/dev/null
  python3 -c "
import json, os
path = '''$path'''
field = '''$field'''
data = {'turns': 0, 'source_writes': 0}
if os.path.isfile(path):
    try:
        with open(path) as f:
            loaded = json.load(f)
        if isinstance(loaded, dict):
            data['turns'] = int(loaded.get('turns', 0) or 0)
            data['source_writes'] = int(loaded.get('source_writes', 0) or 0)
    except Exception:
        pass
if field in ('turns', 'source_writes'):
    data[field] = int(data.get(field, 0) or 0) + 1
with open(path, 'w') as f:
    json.dump(data, f)
" 2>/dev/null
}

# Exit 0 if path is a source write target for P6 counting.
# Source: library/, src/, scripts/, .cursor/hooks/, tests/
# Excluded: docs/, .harness/
hooks_is_source_path() {
  local path="${1:-}"
  [ -n "$path" ] || return 1
  python3 -c "
import sys
path = sys.argv[1].replace('\\\\', '/').lstrip('./')
while path.startswith('/'):
    path = path[1:]
if path.startswith('docs/') or '/docs/' in path:
    sys.exit(1)
if path.startswith('.harness/') or '/.harness/' in path:
    sys.exit(1)
prefixes = ('library/', 'src/', 'scripts/', '.cursor/hooks/', 'tests/')
sys.exit(0 if any(path.startswith(p) for p in prefixes) else 1)
" "$path" 2>/dev/null
}

# Increment source_writes when path is a source target.
hooks_session_stats_maybe_inc_source_write() {
  local path="${1:-}"
  if hooks_is_source_path "$path"; then
    hooks_session_stats_inc source_writes
  fi
}
