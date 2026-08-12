#!/usr/bin/env bash
# Fill ## Commands in TARGET/AGENTS.md from Makefile phony targets or package.json scripts.
# Does NOT create AGENTS.md (use scripts/adopt-agents-md.sh first).
# Does NOT invent overview/Directory structure/Tech stack sections.
# Usage: agents-bootstrap-fill.sh <TARGET_ROOT>
set -euo pipefail

TARGET_ROOT="${1:-}"
if [[ -z "$TARGET_ROOT" ]]; then
  echo "usage: $(basename "$0") <TARGET_ROOT>" >&2
  exit 2
fi

AGENTS="$TARGET_ROOT/AGENTS.md"
if [[ ! -f "$AGENTS" ]]; then
  echo "error: missing $AGENTS — run scripts/adopt-agents-md.sh first" >&2
  exit 1
fi

TMP="$(mktemp)"
trap 'rm -f "$TMP"' EXIT

python3 - "$TARGET_ROOT" "$AGENTS" "$TMP" <<'PY'
import json
import re
import sys
from pathlib import Path

root = Path(sys.argv[1])
agents_path = Path(sys.argv[2])
out_path = Path(sys.argv[3])

SKIP_PHONY = {"help", "all", "default", "clean"}

def makefile_commands(makefile: Path) -> list[str]:
    text = makefile.read_text()
    targets: list[str] = []
    for m in re.finditer(r"^\.PHONY:\s*(.+)$", text, re.M):
        for t in m.group(1).split():
            t = t.strip()
            if t and t not in SKIP_PHONY and t not in targets:
                targets.append(t)
    if not targets:
        for m in re.finditer(r"^([A-Za-z0-9][A-Za-z0-9_-]*):", text, re.M):
            t = m.group(1)
            if t not in SKIP_PHONY and t not in targets:
                targets.append(t)
    return [f"make {t}" for t in targets]

def package_commands(pkg: Path) -> list[str]:
    data = json.loads(pkg.read_text())
    scripts = data.get("scripts") or {}
    return [f"npm run {name}" for name in scripts.keys()]

cmds: list[str] = []
makefile = root / "Makefile"
pkg = root / "package.json"
if makefile.is_file():
    cmds = makefile_commands(makefile)
elif pkg.is_file():
    cmds = package_commands(pkg)
else:
    print("error: no Makefile or package.json in target", file=sys.stderr)
    sys.exit(1)

if not cmds:
    print("error: no commands discovered", file=sys.stderr)
    sys.exit(1)

text = agents_path.read_text()
# Replace fenced block immediately under ## Commands
pattern = re.compile(
    r"(## Commands\n\n)```bash\n.*?```",
    re.S,
)
block = "```bash\n" + "\n".join(cmds) + "\n```"
new_text, n = pattern.subn(r"\1" + block, text, count=1)
if n != 1:
    print("error: could not find ## Commands bash fence to replace", file=sys.stderr)
    sys.exit(1)

banned = ("Directory structure", "Tech stack", "## Overview", "## Harness")
for b in banned:
    if b in new_text and b not in text:
        print(f"error: refused to introduce banned section {b!r}", file=sys.stderr)
        sys.exit(1)

out_path.write_text(new_text)
PY

mv "$TMP" "$AGENTS"
