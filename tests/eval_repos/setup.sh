#!/bin/bash
# Sync library/cursor/ into an eval repo under tests/eval_repos/<name>/.cursor/
# and git-init the repo so it can be opened as a standalone Cursor workspace.
#
# Usage:
#   ./tests/eval_repos/setup.sh eval-api-security           # sync + init
#   ./tests/eval_repos/setup.sh eval-api-security --reset    # wipe .harness/.cursor, resync clean

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "$SCRIPT_DIR/../.." && pwd)
LIBRARY_CURSOR="$REPO_ROOT/library/cursor"

NAME="${1:-}"
MODE="${2:-}"

if [ -z "$NAME" ]; then
  echo "Usage: $0 <eval-repo-name> [--reset]" >&2
  echo "Available: $(ls -1 "$SCRIPT_DIR" | grep '^eval-' | tr '\n' ' ')" >&2
  exit 1
fi

TARGET="$SCRIPT_DIR/$NAME"

if [ ! -d "$TARGET" ]; then
  echo "No such eval repo: $TARGET" >&2
  exit 1
fi

if [ "$MODE" = "--reset" ]; then
  echo "Resetting $NAME ..."
  rm -rf "$TARGET/.harness" "$TARGET/.cursor"
  if [ -d "$TARGET/.git" ]; then
    (cd "$TARGET" && git checkout -- . 2>/dev/null || true)
  fi
fi

if [ ! -d "$TARGET/.git" ]; then
  echo "git init: $NAME"
  (cd "$TARGET" && git init -q && git add -A && git commit -q -m "seed: $NAME eval repo")
fi

echo "Syncing library/cursor/ -> $NAME/.cursor/ ..."
mkdir -p "$TARGET/.cursor"
for dir in rules skills hooks agents references; do
  if [ -d "$LIBRARY_CURSOR/$dir" ]; then
    rm -rf "$TARGET/.cursor/$dir"
    cp -R "$LIBRARY_CURSOR/$dir" "$TARGET/.cursor/$dir"
  fi
done
cp "$LIBRARY_CURSOR/hooks.json" "$TARGET/.cursor/hooks.json"
mkdir -p "$TARGET/.harness"

echo "Done. Next steps:"
echo "  1. Open $TARGET as its own workspace in Cursor"
echo "  2. Paste the prompt from $NAME/PROMPT.md into a fresh chat"
echo "  3. After the session, run: (cd $TARGET && ./verify.sh)"
