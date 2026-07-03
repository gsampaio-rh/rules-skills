#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

echo "Cleaning harness state in $REPO_ROOT..."

rm -f "$REPO_ROOT/.harness/state.json"
rm -f "$REPO_ROOT/.harness/contract.json"
rm -f "$REPO_ROOT/.harness/breadcrumbs.jsonl"
rm -f "$REPO_ROOT/.harness/archive.jsonl"
rm -rf "$REPO_ROOT/.harness/evals/"
mkdir -p "$REPO_ROOT/.harness/evals"

rm -f "$REPO_ROOT/.cursor/hooks/.evaluator-active"
rm -f "$REPO_ROOT/.cursor/hooks/.commit-approved"
rm -f "$REPO_ROOT/.cursor/hooks.log"

echo "Done. Harness state reset to empty."
echo "  Removed: state.json, contract.json, breadcrumbs.jsonl, archive.jsonl, evals/*"
echo "  Removed: .evaluator-active, .commit-approved, hooks.log"
