#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
CURSOR_DIR="$REPO_ROOT/.cursor"
LIBRARY_DIR="$REPO_ROOT/library/cursor"

usage() {
    echo "Usage: $(basename "$0") <lean|full|status>"
    echo ""
    echo "Switch between hook profiles:"
    echo "  lean   — No harness enforcement (for rules/skills development)"
    echo "  full   — Full harness enforcement (for dogfooding / real projects)"
    echo "  status — Show current profile"
    exit 1
}

[[ $# -lt 1 ]] && usage

PROFILE="$1"
PROFILE_FILE="$CURSOR_DIR/.hooks-profile"
HOOKS_JSON="$CURSOR_DIR/hooks.json"

case "$PROFILE" in
    lean)
        cp "$LIBRARY_DIR/hooks.lean.json" "$HOOKS_JSON"
        echo "lean" > "$PROFILE_FILE"
        echo "Switched to LEAN profile (lightweight harness enforcement)"
        echo "  Active: harness-context, harness-gate, contract-gate, dedup-server, verify-harness, enforce-progress, context-health"
        echo "  Inactive: evaluator-guard, pre-commit-harness, chain-evaluator, LLM prompt hooks"
        ;;
    full)
        cp "$LIBRARY_DIR/hooks.full.json" "$HOOKS_JSON"
        echo "full" > "$PROFILE_FILE"
        echo "Switched to FULL profile (all harness enforcement active)"
        echo "  Active: ALL hooks — harness-context, harness-gate, evaluator-guard, contract-gate, dedup-server, pre-commit-harness, verify-harness, enforce-progress, context-health, chain-evaluator, LLM prompt hooks"
        echo "  Note: .harness/state.json must exist for enforcement to trigger"
        ;;
    status)
        if [[ -f "$PROFILE_FILE" ]]; then
            current=$(cat "$PROFILE_FILE")
        else
            current="lean (default — no .hooks-profile file)"
        fi
        if [[ -f "$HOOKS_JSON" ]]; then
            echo "Profile: $current"
            echo "hooks.json: present (copy)"
        else
            echo "Profile: not set (run 'make setup' first)"
        fi
        ;;
    *)
        usage
        ;;
esac
