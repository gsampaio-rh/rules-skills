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

input=$(cat)

HOOK_LOG=".cursor/hooks.log"
echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] pre-commit: triggered" >> "$HOOK_LOG" 2>/dev/null

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

# --- 0. Commit gate: require user approval ---

if [ -f "$COMMIT_GATE" ]; then
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

  ESCAPED_PREVIEW=$(echo "$STAGED_PREVIEW" | python3 -c "
import sys, json
text = sys.stdin.read().strip()
print(json.dumps(text))
" 2>/dev/null)

  cat <<EOF
{
  "permission": "deny",
  "agent_message": "COMMIT BLOCKED: You must get explicit user approval before committing. Show the user what will be committed and ask for their go-ahead. After they approve, write the flag file .cursor/hooks/.commit-approved (any content) and retry the commit command.\n\nFiles to be committed:\n$(echo "$STAGED_PREVIEW" | head -10)"
}
EOF
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
    fid = data.get('feature_id', data.get('feature', ''))
    print(f'\"{fid}\"' if fid else 'null')
except Exception:
    print('null')
" 2>/dev/null)
fi

mkdir -p "$(dirname "$BREADCRUMBS")" 2>/dev/null
echo "{\"ts\":\"$TS\",\"role\":\"builder\",\"type\":\"checkpoint\",\"feat\":$FEAT,\"msg\":\"Commit: $COMMIT_MSG ($STAGED_COUNT files)\"}" >> "$BREADCRUMBS" 2>/dev/null

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
    GUIDANCE="POST-COMMIT (harness active): Feature \"$FEATURE\" is verified. After this commit: (1) Update .harness/state.json — set feature status to 'committed'. (2) Pick the next pending feature from state.json and start contract negotiation."
  else
    GUIDANCE="POST-COMMIT WARNING: Committing while contract for \"$FEATURE\" is unverified (phase=$PHASE). If this is a partial checkpoint, that's fine. But don't mark the feature as done until the /evaluator passes."
  fi
elif [ -f "$STATE" ]; then
  GUIDANCE="POST-COMMIT (harness active): Commit recorded. Check .harness/state.json for the next pending feature."
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
