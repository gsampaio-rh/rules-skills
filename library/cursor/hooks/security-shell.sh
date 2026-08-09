#!/bin/bash
# beforeShellExecution hook (optional): deny classic download-and-execute patterns
# (curl|wget|… piped to sh/bash, process substitution). Narrow matcher in hooks.optional.json.
# Fail-closed when wired with failClosed: true.

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
source "$SCRIPT_DIR/hooks-lib.sh"
hooks_init "security-shell"

command=$(echo "$HOOK_INPUT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('command', ''))
except Exception:
    print('')
" 2>/dev/null)

if [ -z "$command" ]; then
  hooks_log "security-shell" "DENIED — missing command"
  cat <<EOF
{
  "permission": "deny",
  "agent_message": "SHELL BLOCKED: security-shell could not parse command (fail-closed)."
}
EOF
  exit 0
fi

BLOCK=$(python3 -c "
import re, sys
cmd = sys.argv[1]
patterns = [
    r'(curl|wget|fetch)[^|;]*\|\s*(sudo\s+)?(ba)?sh\b',
    r'(ba)?sh\s+<\(\s*(curl|wget|fetch)',
    r'wget\s+[^\n]*-O-\s*\|\s*(sudo\s+)?(ba)?sh\b',
    r'curl\s+[^\n]*\|\s*(sudo\s+)?python[0-9.]*\b',
    r'\|\s*(sudo\s+)?(ba)?sh\s+-s\b',
]
for p in patterns:
    if re.search(p, cmd, re.I):
        print('deny')
        raise SystemExit
print('allow')
" "$command" 2>/dev/null)

if [ "$BLOCK" = "deny" ]; then
  hooks_log "security-shell" "DENIED download-exec: $command"
  MSG=$(python3 -c "import json,sys; print(json.dumps('SHELL BLOCKED: download-and-execute pattern denied (%s). Fetch to a file, inspect it, then run explicitly — do not pipe remote scripts into a shell.' % sys.argv[1][:240]))" "$command")
  printf '{"permission":"deny","user_message":"Blocked download-and-execute shell pattern.","agent_message":%s}\n' "$MSG"
  exit 0
fi

hooks_log "security-shell" "allowed: $command"
echo '{"permission":"allow"}'
exit 0
