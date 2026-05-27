#!/bin/bash
# PreToolUse hook (Bash): prevents duplicate dev servers.
# If a dev server is already listening on a common port, blocks the command
# and tells the agent to reuse the existing one.
# Output: hookSpecificOutput with permissionDecision for PreToolUse

input=$(cat)

HOOK_LOG=".claude/hooks.log"

command=$(echo "$input" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('tool_input', {}).get('command', ''))
except Exception:
    print('')
" 2>/dev/null)

command_lower=$(echo "$command" | tr '[:upper:]' '[:lower:]')

is_server_cmd=false
for pattern in "npm start" "npm run dev" "npm run serve" "yarn dev" "yarn start" "pnpm dev" "pnpm start" "npx vite" "npx next" "vite" "next dev" "next start" "python -m http" "python3 -m http" "flask run" "uvicorn" "gunicorn" "cargo run" "go run"; do
  if echo "$command_lower" | grep -q "$pattern"; then
    is_server_cmd=true
    break
  fi
done

if [ "$is_server_cmd" = false ]; then
  exit 0
fi

echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] dedup-server: dev server command detected: $command" >> "$HOOK_LOG" 2>/dev/null

PORTS="3000 3001 3002 5173 5174 4200 8000 8080 8888"
FOUND_PORT=""
FOUND_PID=""

for port in $PORTS; do
  pid=$(lsof -ti :"$port" 2>/dev/null | head -1)
  if [ -n "$pid" ]; then
    FOUND_PORT="$port"
    FOUND_PID="$pid"
    break
  fi
done

if [ -n "$FOUND_PORT" ]; then
  echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] dedup-server: BLOCKED — server already on port $FOUND_PORT (pid $FOUND_PID)" >> "$HOOK_LOG" 2>/dev/null

  cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "Dev server already running on port $FOUND_PORT (pid $FOUND_PID). Use the existing server at http://localhost:$FOUND_PORT instead. If you need to restart it, kill pid $FOUND_PID first."
  }
}
EOF
  exit 0
fi

echo "[$(date -u +%Y-%m-%dT%H:%M:%S)] dedup-server: no existing server, allowing" >> "$HOOK_LOG" 2>/dev/null
exit 0
