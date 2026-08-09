#!/bin/bash
# beforeReadFile hook (optional): deny reading secret-bearing paths into agent context.
# Fail-closed when wired with failClosed: true in hooks.optional.json.

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
source "$SCRIPT_DIR/hooks-lib.sh"
hooks_init "secret-read-guard"

file_path=$(echo "$HOOK_INPUT" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('file_path') or data.get('filePath') or '')
except Exception:
    print('')
" 2>/dev/null)

if [ -z "$file_path" ]; then
  # No path → fail closed (optional profile sets failClosed; still deny when empty)
  hooks_log "secret-read-guard" "DENIED — missing file_path"
  cat <<EOF
{
  "permission": "deny",
  "agent_message": "READ BLOCKED: secret-read-guard could not determine file_path. Refusing read (fail-closed)."
}
EOF
  exit 0
fi

DENY=$(python3 -c "
import os, sys
path = sys.argv[1].replace('\\\\', '/')
base = os.path.basename(path)
# Allow common env templates (not live secrets)
allow_env = {'.env.example', '.env.sample', '.env.template', '.env.sample.local'}
if base in allow_env:
    print('allow')
    raise SystemExit
# Live dotenv / secret filenames
if base == '.env' or base.startswith('.env.'):
    print('deny')
    raise SystemExit
if base in ('credentials.json', 'id_rsa', 'id_ed25519', '.secret', 'secrets.yaml', 'secrets.yml'):
    print('deny')
    raise SystemExit
if base.endswith('.pem') or base.endswith('.key') or base.endswith('.p12') or base.endswith('.pfx'):
    print('deny')
    raise SystemExit
if base.endswith('.secret'):
    print('deny')
    raise SystemExit
print('allow')
" "$file_path" 2>/dev/null)

if [ "$DENY" = "deny" ]; then
  hooks_log "secret-read-guard" "DENIED read of secret path: $file_path"
  MSG=$(python3 -c "import json,sys; print(json.dumps('READ BLOCKED: Refusing to load secret-bearing path into context: %s. Use a vault / env injection; do not read live credentials into the agent.' % sys.argv[1]))" "$file_path")
  printf '{"permission":"deny","agent_message":%s}\n' "$MSG"
  exit 0
fi

hooks_log "secret-read-guard" "allowed: $file_path"
echo '{"permission":"allow"}'
exit 0
