#!/bin/bash
# Stop hook: detects context rot, decision fatigue, and circular behavior.
# Forces the agent to recommend a fresh chat when the session is degraded.
#
# Session scoping: only analyzes breadcrumbs AFTER the last session_start marker
# (written by harness-context.sh on sessionStart). This prevents false positives
# when opening a fresh chat — breadcrumbs.jsonl is project-level, not session-level.
#
# Fatigue signals (scoped to current session):
#   1. Session too long (> 90 min since first breadcrumb this session)
#   2. Too many breadcrumbs (> 25 entries this session — context is saturated)
#   3. Consecutive failures (3+ fail results in a row — going in circles)
#   4. Multiple scrap-and-restart cycles (2+ scraps — approach exhaustion)
#   5. Same feature stuck (3+ eval failures on the same feature)
#
# Severity:
#   1 signal  → WARNING: suggest new chat
#   2+ signals → CRITICAL: insist on new chat with handoff

input=$(cat)

HOOK_LOG=".cursor/hooks.log"
echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] context-health: triggered" >> "$HOOK_LOG" 2>/dev/null

BREADCRUMBS=".cursor/breadcrumbs.jsonl"

if [ ! -f "$BREADCRUMBS" ]; then
  echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] context-health: no breadcrumbs, skipping" >> "$HOOK_LOG" 2>/dev/null
  echo '{}'
  exit 0
fi

LINES=$(wc -l < "$BREADCRUMBS" 2>/dev/null | tr -d ' ')
if [ "${LINES:-0}" -lt 5 ]; then
  echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] context-health: only $LINES breadcrumbs, too early to judge" >> "$HOOK_LOG" 2>/dev/null
  echo '{}'
  exit 0
fi

RESULT=$(python3 -c "
import json, sys
from datetime import datetime, timezone

breadcrumbs_path = '$BREADCRUMBS'

all_entries = []
with open(breadcrumbs_path) as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            all_entries.append(json.loads(line))
        except Exception:
            pass

# Scope to current session: find the last session_start marker.
# breadcrumbs.jsonl is project-level (persists across sessions).
# Without scoping, a fresh chat inherits fatigue signals from old sessions.
session_start_idx = 0
for i in range(len(all_entries) - 1, -1, -1):
    if all_entries[i].get('type') == 'session_start':
        session_start_idx = i + 1
        break

entries = all_entries[session_start_idx:]

if len(entries) < 5:
    print(json.dumps({'signals': 0}))
    sys.exit(0)

signals = []
details = []

def parse_ts(ts_str):
    for fmt in ('%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%dT%H:%M:%S%z', '%Y-%m-%dT%H:%M'):
        try:
            return datetime.strptime(ts_str, fmt)
        except ValueError:
            continue
    return None

# --- Signal 1: Session duration (time since session_start) ---
try:
    first_ts = entries[0].get('ts', '')
    last_ts = entries[-1].get('ts', '')
    t_first = parse_ts(first_ts)
    t_last = parse_ts(last_ts)
    if t_first and t_last:
        duration_min = (t_last - t_first).total_seconds() / 60
        if duration_min > 90:
            signals.append('session_duration')
            details.append(f'Session running for {int(duration_min)} minutes')
except Exception:
    pass

# --- Signal 2: Breadcrumb volume (this session only) ---
total = len(entries)
if total > 25:
    signals.append('breadcrumb_volume')
    details.append(f'{total} breadcrumbs in this session — context is likely saturated')

# --- Signal 3: Consecutive failures (this session) ---
recent = entries[-8:]
consecutive_fails = 0
max_consecutive = 0
for e in recent:
    if e.get('result') == 'fail':
        consecutive_fails += 1
        max_consecutive = max(max_consecutive, consecutive_fails)
    else:
        consecutive_fails = 0

if max_consecutive >= 3:
    signals.append('consecutive_failures')
    details.append(f'{max_consecutive} consecutive failures — going in circles')

# --- Signal 4: Scrap-and-restart count (this session) ---
scrap_count = sum(1 for e in entries if e.get('type') == 'scrap')
if scrap_count >= 2:
    signals.append('scrap_exhaustion')
    details.append(f'{scrap_count} scrap-and-restart cycles — approach exhaustion')

# --- Signal 5: Same feature stuck (this session) ---
eval_failures = {}
for e in entries:
    if e.get('type') == 'eval' and e.get('result') == 'fail':
        feat = e.get('feat', 'unknown')
        eval_failures[feat] = eval_failures.get(feat, 0) + 1

stuck_features = {f: c for f, c in eval_failures.items() if c >= 3}
if stuck_features:
    signals.append('feature_stuck')
    for feat, count in stuck_features.items():
        details.append(f'Feature \"{feat}\" failed evaluation {count} times')

# --- Compose result ---
result = {
    'signals': len(signals),
    'signal_names': signals,
    'details': details,
    'session_breadcrumbs': total,
    'total_breadcrumbs': len(all_entries),
}

if len(signals) >= 1:
    recent_msgs = []
    for e in entries[-5:]:
        role = e.get('role', '?')
        msg = e.get('msg', '?')
        result_str = e.get('result', '')
        line = f'[{role}] {msg}'
        if result_str:
            line += f' ({result_str})'
        recent_msgs.append(line)
    result['recent_context'] = recent_msgs

    active_feat = None
    for e in reversed(entries):
        if e.get('feat') and e.get('feat') != 'null':
            active_feat = e.get('feat')
            break
    result['active_feature'] = active_feat

print(json.dumps(result))
" 2>/dev/null)

if [ -z "$RESULT" ]; then
  echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] context-health: python failed, skipping" >> "$HOOK_LOG" 2>/dev/null
  echo '{}'
  exit 0
fi

SIGNAL_COUNT=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('signals',0))" 2>/dev/null)

if [ "${SIGNAL_COUNT:-0}" -eq 0 ]; then
  echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] context-health: healthy (0 signals)" >> "$HOOK_LOG" 2>/dev/null
  echo '{}'
  exit 0
fi

# Build the followup_message from the analysis
MESSAGE=$(echo "$RESULT" | python3 -c "
import sys, json

data = json.load(sys.stdin)
signals = data.get('signals', 0)
names = data.get('signal_names', [])
details = data.get('details', [])
recent = data.get('recent_context', [])
active = data.get('active_feature')

if signals == 1:
    severity = 'CONTEXT HEALTH WARNING'
    action = 'Consider suggesting the user start a fresh chat for better results.'
else:
    severity = 'CONTEXT HEALTH CRITICAL'
    action = 'You MUST recommend the user start a fresh chat. Do NOT continue working on complex tasks in this session.'

lines = [f'{severity}: {signals} fatigue signal(s) detected.']
lines.append('')
lines.append('Signals:')
for d in details:
    lines.append(f'  - {d}')
lines.append('')
lines.append(f'Action: {action}')
lines.append('')
lines.append('Before ending this session:')
lines.append('1. Write a handoff breadcrumb to .cursor/breadcrumbs.jsonl summarizing current state and what to do next')
lines.append('2. Tell the user to start a new chat with a prompt like:')

if active:
    lines.append(f'   \"Continue working on {active}. Read .cursor/breadcrumbs.jsonl and .cursor/harness/ for context.\"')
else:
    lines.append('   \"Continue where I left off. Read .cursor/breadcrumbs.jsonl for context.\"')

lines.append('3. Do NOT attempt complex multi-step work in this degraded session')

recent_str = '\\n'.join(f'  {r}' for r in recent)
if recent_str:
    lines.append('')
    lines.append('Recent activity:')
    lines.append(recent_str)

msg = '\\n'.join(lines)
print(json.dumps({'followup_message': msg}))
" 2>/dev/null)

if [ -z "$MESSAGE" ]; then
  echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] context-health: compose failed, skipping" >> "$HOOK_LOG" 2>/dev/null
  echo '{}'
  exit 0
fi

echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] context-health: $SIGNAL_COUNT signal(s) detected — ${SIGNAL_COUNT:+$(echo "$RESULT" | python3 -c "import sys,json; print(','.join(json.load(sys.stdin).get('signal_names',[])))" 2>/dev/null)}" >> "$HOOK_LOG" 2>/dev/null

echo "$MESSAGE"
exit 0
