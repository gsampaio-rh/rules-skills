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
#  10. Missing handoff (P6): turns>=5 AND source_writes>=2 in .session-stats.json
#      with no type:checkpoint/handoff breadcrumb this session
#
# Severity:
#   1 signal  → WARNING: suggest new chat
#   2+ signals → CRITICAL: insist on new chat with handoff

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
source "$SCRIPT_DIR/hooks-lib.sh"
hooks_init "context-health"

BREADCRUMBS=".harness/breadcrumbs.jsonl"

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
from collections import defaultdict

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

# --- Signal 1: Session duration with tiered severity ---
# WARNING at 60min, STRONG at 120min, CRITICAL at 180min+
session_duration_min = 0
session_severity = None
try:
    first_ts = entries[0].get('ts', '')
    last_ts = entries[-1].get('ts', '')
    t_first = parse_ts(first_ts)
    t_last = parse_ts(last_ts)
    if t_first and t_last:
        session_duration_min = (t_last - t_first).total_seconds() / 60
        if session_duration_min >= 180:
            session_severity = 'CRITICAL'
            signals.append('session_duration_critical')
            details.append(f'Session running {int(session_duration_min)} min (CRITICAL: >3h). Write handoff and split NOW.')
        elif session_duration_min >= 120:
            session_severity = 'STRONG'
            signals.append('session_duration_strong')
            details.append(f'Session running {int(session_duration_min)} min (STRONG: >2h). Quality degrades. Split now.')
        elif session_duration_min > 60:
            session_severity = 'WARNING'
            signals.append('session_duration')
            details.append(f'Session running {int(session_duration_min)} min — consider splitting')
except Exception:
    pass

# --- Signal 2: Breadcrumb volume (this session only) ---
total = len(entries)
if total > 30:
    signals.append('breadcrumb_volume_critical')
    details.append(f'{total} breadcrumbs in this session — context critically saturated')
elif total > 20:
    signals.append('breadcrumb_volume')
    details.append(f'{total} breadcrumbs in this session — context is getting saturated')

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

# --- Signal 6: Incremental eval gap (2+ features built without evaluation) ---
built_feats_since_eval = []
for e in entries:
    if e.get('type') in ('evaluate', 'eval') and e.get('role') == 'evaluator':
        built_feats_since_eval = []
    elif (e.get('type') == 'build' and e.get('role') == 'builder'
          and e.get('feat') and str(e.get('result', '')).lower() == 'pass'):
        feat = e['feat']
        if feat not in built_feats_since_eval:
            built_feats_since_eval.append(feat)

if len(built_feats_since_eval) >= 2:
    signals.append('incremental_eval_gap')
    details.append(
        f'{len(built_feats_since_eval)} features built without intermediate evaluation: '
        + ', '.join(built_feats_since_eval) + '. Run /evaluator before starting next feature.'
    )

# --- Signal 7: Duplicate breadcrumbs (same feat+type within 15 min) ---
recent_keys = defaultdict(list)
for e in entries:
    key = (e.get('feat', ''), e.get('type', ''))
    ts_parsed = parse_ts(e.get('ts', ''))
    if ts_parsed:
        recent_keys[key].append(ts_parsed)

duplicate_count = 0
for key, timestamps in recent_keys.items():
    if len(timestamps) < 2:
        continue
    timestamps.sort()
    for i in range(1, len(timestamps)):
        if (timestamps[i] - timestamps[i-1]).total_seconds() < 900:
            duplicate_count += 1

if duplicate_count >= 2:
    signals.append('duplicate_breadcrumbs')
    details.append(f'{duplicate_count} near-duplicate breadcrumbs detected (same feat+type within 15 min)')

# --- Signal 8: Scope amnesia (feat:null builds = lost track of task) ---
null_builds = sum(1 for e in entries
    if e.get('type') == 'build' and e.get('role') == 'builder'
    and not e.get('feat'))
if null_builds >= 3:
    signals.append('scope_amnesia')
    details.append(f'{null_builds} builds with feat:null — agent lost track of which task it is working on')

# --- Signal 9: Decision churn (same feat replanned 3+ times) ---
plan_counts = defaultdict(int)
for e in entries:
    if e.get('type') == 'plan' and e.get('feat'):
        plan_counts[e['feat']] += 1

churning = {f: c for f, c in plan_counts.items() if c >= 3}
if churning:
    signals.append('decision_churn')
    for feat, count in churning.items():
        details.append(f'Feature {feat} replanned {count} times — going in circles')

# --- Signal 10: Missing handoff (P6 RCA) ---
# Requires .harness/.session-stats.json; absent file → do not fire (no false positives).
session_turns = 0
session_source_writes = 0
has_session_stats = False
try:
    with open('.harness/.session-stats.json') as sf:
        stats = json.load(sf)
    if isinstance(stats, dict):
        session_turns = int(stats.get('turns', 0) or 0)
        session_source_writes = int(stats.get('source_writes', 0) or 0)
        has_session_stats = True
except Exception:
    pass

has_handoff_breadcrumb = any(
    e.get('type') in ('checkpoint', 'handoff') for e in entries
)
if (
    has_session_stats
    and session_turns >= 5
    and session_source_writes >= 2
    and not has_handoff_breadcrumb
):
    signals.append('missing_handoff')
    details.append(
        f'Substantial session ({session_turns} turns, {session_source_writes} source writes) '
        'with no checkpoint/handoff breadcrumb — write a handoff before idle end'
    )

# --- Compose result ---
# Compute cognitive load score (0-10)
cognitive_load = min(10,
    2 * (1 if duplicate_count >= 2 else 0) +
    3 * (1 if null_builds >= 3 else 0) +
    3 * (1 if churning else 0) +
    1 * (1 if total > 20 else 0) +
    1 * (1 if session_duration_min > 60 else 0) +
    2 * (1 if 'missing_handoff' in signals else 0)
)

result = {
    'signals': len(signals),
    'signal_names': signals,
    'details': details,
    'session_breadcrumbs': total,
    'total_breadcrumbs': len(all_entries),
    'session_duration_hours': round(session_duration_min / 60, 1),
    'cognitive_load_score': cognitive_load,
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

result['session_turns'] = session_turns
result['session_source_writes'] = session_source_writes
result['has_session_stats'] = has_session_stats

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
active_str = active if active else '<task-id>'

last_summary = '<one-line summary>'
for line in reversed(recent or []):
    # recent lines look like: [role] msg (result)
    text = line.split('] ', 1)[-1] if '] ' in line else line
    text = text.rsplit(' (', 1)[0].strip() if text.endswith(')') and ' (' in text else text.strip()
    if text and text != '?':
        last_summary = text[:160]
        break

# P6: missing handoff gets a dedicated advisory with the canonical handoff block.
if 'missing_handoff' in names and signals == 1:
    lines = [
        'SESSION HANDOFF ADVISORY: Substantial session (turns>=5, source_writes>=2) with no checkpoint/handoff breadcrumb.',
        '',
        'Before idle end, write a type:checkpoint breadcrumb and give the user this handoff block:',
        '',
        f'Continue working on {active_str}. Read .harness/breadcrumbs.jsonl and .harness/state.json.',
        f'Last: {last_summary}. Next: <one-line next action>.',
    ]
    msg = '\\n'.join(lines)
    print(json.dumps({'followup_message': msg}))
    raise SystemExit(0)

# Severity escalation based on cognitive load score
has_critical_duration = 'session_duration_critical' in names
has_strong_duration = 'session_duration_strong' in names

load_score = data.get('cognitive_load_score', 0)

if has_critical_duration or load_score >= 7 or signals >= 4:
    severity = 'CONTEXT HEALTH CRITICAL'
    action = 'You MUST write a handoff breadcrumb and recommend the user start a fresh chat. Do NOT continue working on complex tasks in this session.'
elif has_strong_duration or load_score >= 5 or signals >= 2:
    severity = 'CONTEXT HEALTH STRONG WARNING'
    action = 'You should strongly recommend the user start a fresh chat. Session quality degrades significantly.'
else:
    severity = 'CONTEXT HEALTH WARNING'
    action = 'Consider suggesting the user start a fresh chat for better results.'

lines = [f'{severity}: {signals} fatigue signal(s) detected.']
lines.append('')
lines.append('Signals:')
for d in details:
    lines.append(f'  - {d}')
lines.append('')
lines.append(f'Action: {action}')
lines.append('')
lines.append('Before ending this session:')
lines.append('1. Write a handoff breadcrumb to .harness/breadcrumbs.jsonl summarizing current state and what to do next')
lines.append('2. Tell the user to start a new chat with a prompt like:')
if 'missing_handoff' in names:
    # Canonical P6 block only when the missing-handoff signal is present.
    lines.append(f'   Continue working on {active_str}. Read .harness/breadcrumbs.jsonl and .harness/state.json.')
    lines.append(f'   Last: {last_summary}. Next: <one-line next action>.')
elif active:
    lines.append(f'   \"Continue working on {active}. Read .harness/breadcrumbs.jsonl and .harness/ for context.\"')
else:
    lines.append('   \"Continue where I left off. Read .harness/breadcrumbs.jsonl for context.\"')
lines.append('3. Do NOT attempt complex multi-step work in this degraded session')

if 'missing_handoff' in names or has_critical_duration:
    lines.append('')
    lines.append('HANDOFF TEMPLATE (copy and adapt):')
    lines.append(f'{{\"ts\":\"...\",\"role\":\"builder\",\"type\":\"checkpoint\",\"feat\":\"{active_str}\",\"msg\":\"Handoff: <current state>. Next: <what to do>.\"}}')

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
