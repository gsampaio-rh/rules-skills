#!/bin/bash
# Stop: soft-followup when multi-file source work lacks a valid breadcrumb.
# Skips when contract.json exists (harness path owns tracking).

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
source "$SCRIPT_DIR/hooks-lib.sh"
hooks_init "enforce-progress"

ROOT="${HARNESS_ROOT:-.}"
[ -f "$ROOT/.harness/contract.json" ] && { echo '{}'; exit 0; }

SOURCE_WRITES=$(python3 -c "
import json, os
p='''$ROOT/.harness/.session-stats.json'''
print(0 if not os.path.isfile(p) else int(json.load(open(p)).get('source_writes',0) or 0))
" 2>/dev/null)

BREADCRUMB_VALID=$(python3 -c "
import json, os
p='''$ROOT/.harness/breadcrumbs.jsonl'''
if not os.path.isfile(p):
    print('false'); raise SystemExit
last=None
for line in open(p):
    if line.strip():
        try: last=json.loads(line)
        except Exception: print('false'); raise SystemExit
if not isinstance(last, dict):
    print('false'); raise SystemExit
msg, result = last.get('msg'), last.get('result')
ok = isinstance(msg,str) and len(msg)>=20 and isinstance(result,str) and len(result)>0
print('true' if ok else 'false')
" 2>/dev/null)

if [ "${SOURCE_WRITES:-0}" -ge 2 ] && [ "$BREADCRUMB_VALID" != "true" ]; then
  cat <<EOF
{"followup_message":"PROGRESS BLOCKED: source_writes=$SOURCE_WRITES (>=2) but last breadcrumb missing/invalid. Append {\"ts\":\"ISO\",\"role\":\"builder\",\"type\":\"build\",\"feat\":null,\"msg\":\"<≥20 chars>\",\"result\":\"pass\"}."}
EOF
  exit 0
fi
echo '{}'
exit 0
