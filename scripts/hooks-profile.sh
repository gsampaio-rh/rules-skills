#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
CURSOR_DIR="$REPO_ROOT/.cursor"
LIBRARY_DIR="$REPO_ROOT/library/cursor"

usage() {
    echo "Usage: $(basename "$0") <default|optional|status>"
    echo ""
    echo "Switch hook profiles:"
    echo "  default  — Core deny/inject hooks including harness-gate cold-start"
    echo "  optional — Core + secret-read-guard + security-shell + dedup-server + context-health"
    echo "  status   — Show current profile"
    exit 1
}

[[ $# -lt 1 ]] && usage

PROFILE="$1"
PROFILE_FILE="$CURSOR_DIR/.hooks-profile"
HOOKS_JSON="$CURSOR_DIR/hooks.json"

case "$PROFILE" in
    default)
        cp "$LIBRARY_DIR/hooks.json" "$HOOKS_JSON"
        echo "default" > "$PROFILE_FILE"
        echo "Switched to DEFAULT profile"
        echo "  Active: harness-context, harness-gate, contract-gate, evaluator-guard,"
        echo "          pre-commit-harness, verify-harness, enforce-progress, chain-evaluator"
        ;;
    optional)
        if ! command -v python3 >/dev/null 2>&1; then
            echo "python3 required to merge optional hooks" >&2
            exit 1
        fi
        python3 - "$LIBRARY_DIR/hooks.json" "$LIBRARY_DIR/hooks.optional.json" "$HOOKS_JSON" <<'PY'
import json, sys
base_path, opt_path, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
base = json.load(open(base_path))
opt = json.load(open(opt_path))
hooks = dict(base.get("hooks", {}))
for event, entries in opt.get("hooks", {}).items():
    hooks.setdefault(event, [])
    hooks[event] = list(hooks[event]) + list(entries)
base["hooks"] = hooks
json.dump(base, open(out_path, "w"), indent=2)
open(out_path, "a").write("\n")
PY
        echo "optional" > "$PROFILE_FILE"
        echo "Switched to OPTIONAL profile (default + secret-read-guard + security-shell + dedup + context-health)"
        ;;
    status)
        if [[ -f "$PROFILE_FILE" ]]; then
            current=$(cat "$PROFILE_FILE")
        else
            current="default (no .hooks-profile file)"
        fi
        if [[ -f "$HOOKS_JSON" ]]; then
            echo "Profile: $current"
            echo "hooks.json: present"
        else
            echo "Profile: not set (run 'make setup' first)"
        fi
        ;;
    lean|full)
        echo "Profiles 'lean' and 'full' were retired. Use: default | optional" >&2
        exit 1
        ;;
    *)
        usage
        ;;
esac
