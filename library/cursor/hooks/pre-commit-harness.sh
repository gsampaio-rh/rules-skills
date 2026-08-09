#!/bin/bash
# beforeShellExecution hook: fires on git commit commands.
#
# Enforcement:
#   1. BLOCKS the first commit attempt — forces the agent to get user approval
#   2. ALLOWS the second attempt (after agent creates .commit-approved flag)
#   3. Records a checkpoint breadcrumb with commit context
#   4. Injects post-commit guidance (harness state, doc changes, etc.)
#
# The commit gate uses a flag file (.cursor/hooks/.commit-approved) to break
# the deny loop: first attempt → deny + instruct, agent asks user, agent
# writes flag + retries → allow + delete flag.

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
source "$SCRIPT_DIR/hooks-lib.sh"
hooks_init "pre-commit"
input="$HOOK_INPUT"

BREADCRUMBS=".harness/breadcrumbs.jsonl"
CONTRACT=".harness/contract.json"
STATE=".harness/state.json"
COMMIT_GATE=".cursor/hooks/.commit-approved"

command=$(echo "$input" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('command', ''))
except Exception:
    print('')
" 2>/dev/null)

# Only act on actual git commit commands
if ! echo "$command" | grep -q "git commit"; then
  echo '{"permission":"allow"}'
  exit 0
fi

echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] pre-commit: git commit detected" >> "$HOOK_LOG" 2>/dev/null

# --- 0a. Block staged secret / dotenv filenames (prompt checklist is not enough) ---
STAGED_SECRETS=$(git diff --cached --name-only --diff-filter=ACM 2>/dev/null | grep -E '(^|/)\.env(\.|$)|(^|/)\.env$|\.pem$|credentials\.json$|id_rsa$|id_ed25519$|\.secret$' || true)
if [ -n "$STAGED_SECRETS" ]; then
  hooks_log "pre-commit" "DENIED — staged secret-like paths"
  ESCAPED_SECRETS=$(echo "$STAGED_SECRETS" | python3 -c "
import sys, json
files = sys.stdin.read().strip()
msg = 'COMMIT BLOCKED: staged files look like secrets/dotenv. Unstage them and use env vars or a vault.\n\nBlocked paths:\n' + files
print(json.dumps(msg))
" 2>/dev/null)
  printf '{"permission":"deny","agent_message":%s}\n' "$ESCAPED_SECRETS"
  exit 0
fi

# --- 0. Commit gate: require user approval ---

if [ -f "$COMMIT_GATE" ]; then
  # Check TTL: reject stale flags (>300s) to prevent auto-approval after crashes
  FLAG_AGE=$(hooks_file_age "$COMMIT_GATE")
  if [ "$FLAG_AGE" -gt 300 ]; then
    rm -f "$COMMIT_GATE" 2>/dev/null
    hooks_log "pre-commit" "DENIED — stale commit-approved flag (${FLAG_AGE}s > 300s TTL)"
    cat <<EOF
{
  "permission": "deny",
  "agent_message": "COMMIT BLOCKED: The .commit-approved flag is stale (${FLAG_AGE}s old, max 300s). This likely means a previous commit attempt failed or the session was interrupted. Please ask the user for approval again, then create a fresh .cursor/hooks/.commit-approved file and retry."
}
EOF
    exit 0
  fi
  # Agent already got user approval and set the flag — allow this attempt
  rm -f "$COMMIT_GATE" 2>/dev/null
  echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] pre-commit: commit-approved flag found, allowing" >> "$HOOK_LOG" 2>/dev/null
else
  # First attempt — DENY and force the agent to ask the user
  echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] pre-commit: DENIED — no commit-approved flag" >> "$HOOK_LOG" 2>/dev/null

  STAGED_PREVIEW=$(git diff --cached --name-only 2>/dev/null | head -10)
  if [ -z "$STAGED_PREVIEW" ]; then
    STAGED_PREVIEW=$(git status --porcelain 2>/dev/null | head -10)
  fi

  ESCAPED_MSG=$(echo "$STAGED_PREVIEW" | python3 -c "
import sys, json
files = sys.stdin.read().strip()
msg = 'COMMIT BLOCKED: You must get explicit user approval before committing. Show the user what will be committed and ask for their go-ahead. After they approve, write the flag file .cursor/hooks/.commit-approved (any content) and retry the commit command.\n\nFiles to be committed:\n' + files
print(json.dumps(msg))
" 2>/dev/null)

  printf '{"permission":"deny","agent_message":%s}\n' "$ESCAPED_MSG"
  exit 0
fi

# --- 1. Auto-record breadcrumb ---

TS=$(date -u +%Y-%m-%dT%H:%M:%S)

COMMIT_MSG=$(echo "$command" | python3 -c "
import sys, re
cmd = sys.stdin.read()

msg = ''

# 1. Heredoc
m = re.search(r\"<<['\\\"]?EOF['\\\"]?[)\\s]*\\\\n(.*?)\\\\nEOF\", cmd)
if not m:
    m = re.search(r\"<<['\\\"]?EOF['\\\"]?[)\\s]*\n(.*?)\nEOF\", cmd, re.DOTALL)
if m:
    msg = m.group(1).strip()

# 2. -m \"msg\" or -m 'msg'
if not msg:
    m = re.search(r'-m\s+\"((?:[^\"\\\\]|\\\\.)*)\"', cmd)
    if not m:
        m = re.search(r\"-m\s+'([^']*)'\", cmd)
    if m:
        msg = m.group(1).strip()

# 3. -m msg (unquoted)
if not msg:
    m = re.search(r'-m\s+([^\s\"'\\''][^\s]*)', cmd)
    if m:
        msg = m.group(1).strip()

print(msg[:120] if msg else '(message not extracted)')
" 2>/dev/null)

STAGED_FILES=$(git diff --cached --name-only 2>/dev/null | head -10)
STAGED_COUNT=$(git diff --cached --name-only 2>/dev/null | wc -l | tr -d ' ')

if [ "$STAGED_COUNT" = "0" ]; then
  STAGED_COUNT=$(git status --porcelain 2>/dev/null | grep -cE '^[MADRC ]' || echo "0")
  if [ "$STAGED_COUNT" = "0" ]; then
    STAGED_COUNT=$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')
  fi
fi

FEAT="null"
if [ -f "$CONTRACT" ]; then
  FEAT=$(python3 -c "
import json
try:
    with open('$CONTRACT') as f:
        data = json.load(f)
    fid = data.get('task_id', data.get('feature', ''))
    print(f'\"{fid}\"' if fid else 'null')
except Exception:
    print('null')
" 2>/dev/null)
fi

mkdir -p "$(dirname "$BREADCRUMBS")" 2>/dev/null

# Sanitize: strip newlines and excess whitespace from git outputs to prevent
# malformed JSON breadcrumbs like "(0\n0 files)".
STAGED_COUNT=$(echo "$STAGED_COUNT" | tr -d '\n\r' | tr -s ' ')
COMMIT_MSG=$(echo "$COMMIT_MSG" | tr '\n\r' ' ' | tr -s ' ')

python3 -c "
import json, sys
ts, feat_raw, msg, count = '$TS', '$FEAT', '''$COMMIT_MSG''', '''$STAGED_COUNT'''
msg = ' '.join(msg.split())
count = ''.join(c for c in count if c.isdigit()) or '0'
feat = None if feat_raw in ('null', '') else feat_raw.strip('\"')
entry = {'ts': ts, 'role': 'builder', 'type': 'checkpoint', 'feat': feat, 'msg': f'Commit: {msg} ({count} files)'}
print(json.dumps(entry, ensure_ascii=True))
" >> "$BREADCRUMBS" 2>/dev/null

echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] pre-commit: breadcrumb recorded" >> "$HOOK_LOG" 2>/dev/null

# --- 2. Build post-commit guidance ---

GUIDANCE=""

if [ -f "$CONTRACT" ]; then
  CONTRACT_STATE=$(python3 -c "
import json
try:
    with open('$CONTRACT') as f:
        data = json.load(f)
    feature = data.get('feature', 'unknown')
    verified = data.get('verified', False)
    phase = data.get('phase', 'unknown')
    print(f'{feature}|{verified}|{phase}')
except Exception:
    print('unknown|False|unknown')
" 2>/dev/null)

  FEATURE=$(echo "$CONTRACT_STATE" | cut -d'|' -f1)
  VERIFIED=$(echo "$CONTRACT_STATE" | cut -d'|' -f2)
  PHASE=$(echo "$CONTRACT_STATE" | cut -d'|' -f3)

  if [ "$VERIFIED" = "True" ]; then
    GUIDANCE="POST-COMMIT (harness active): Task \"$FEATURE\" is verified. After this commit: (1) Update .harness/state.json — set task status to 'committed'. (2) Pick the next pending task from state.json and start contract negotiation."
  else
    GUIDANCE="POST-COMMIT WARNING: Committing while contract for \"$FEATURE\" is unverified (phase=$PHASE). If this is a partial checkpoint, that's fine. But don't mark the task as done until the /evaluator passes."
  fi
elif [ -f "$STATE" ]; then
  GUIDANCE="POST-COMMIT (harness active): Commit recorded. Check .harness/state.json for the next pending task."
fi

HAS_API_CHANGES=""
if echo "$STAGED_FILES" | grep -qiE '(route|endpoint|api|schema|migration|model)'; then
  HAS_API_CHANGES="API/schema/model files changed — verify that related documentation (README, API docs, migration notes) is up to date."
fi

HAS_CONFIG_CHANGES=""
if echo "$STAGED_FILES" | grep -qiE '(config|\.env|settings|manifest|package\.json|pyproject)'; then
  HAS_CONFIG_CHANGES="Configuration files changed — verify that setup instructions or environment docs reflect these changes."
fi

# --- 3. Compose agent_message ---

PARTS=""
if [ -n "$GUIDANCE" ]; then
  PARTS="$GUIDANCE"
fi
if [ -n "$HAS_API_CHANGES" ]; then
  PARTS="$PARTS\n$HAS_API_CHANGES"
fi
if [ -n "$HAS_CONFIG_CHANGES" ]; then
  PARTS="$PARTS\n$HAS_CONFIG_CHANGES"
fi

if [ -z "$PARTS" ]; then
  echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] pre-commit: no guidance needed, allowing" >> "$HOOK_LOG" 2>/dev/null
  echo '{"permission":"allow"}'
  exit 0
fi

echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] pre-commit: injecting post-commit guidance" >> "$HOOK_LOG" 2>/dev/null

ESCAPED_PARTS=$(echo -e "$PARTS" | python3 -c "
import sys, json
text = sys.stdin.read().strip()
print(json.dumps(text))
" 2>/dev/null)

cat <<EOF
{
  "permission": "allow",
  "agent_message": $ESCAPED_PARTS
}
EOF
exit 0
