#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
CURSOR_DIR="$REPO_ROOT/.cursor"

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
        rm -f "$HOOKS_JSON"
        ln -s hooks.lean.json "$HOOKS_JSON"
        echo "lean" > "$PROFILE_FILE"
        echo "Switched to LEAN profile (no harness enforcement)"
        echo "  Active: dedup-server, enforce-progress (Tier 1), context-health"
        echo "  Inactive: contract-gate, evaluator-guard, verify-harness, harness-gate, chain-evaluator, pre-commit-harness"
        ;;
    full)
        rm -f "$HOOKS_JSON"
        ln -s hooks.full.json "$HOOKS_JSON"
        echo "full" > "$PROFILE_FILE"
        echo "Switched to FULL profile (all harness enforcement active)"
        echo "  Active: ALL hooks including contract-gate, verify-harness, LLM prompt hooks"
        echo "  Note: .harness/state.json must exist for enforcement to trigger"
        ;;
    status)
        if [[ -f "$PROFILE_FILE" ]]; then
            current=$(cat "$PROFILE_FILE")
        else
            current="lean (default — no .hooks-profile file)"
        fi
        target=$(readlink "$HOOKS_JSON" 2>/dev/null || echo "not a symlink")
        echo "Profile: $current"
        echo "hooks.json → $target"
        ;;
    *)
        usage
        ;;
esac
