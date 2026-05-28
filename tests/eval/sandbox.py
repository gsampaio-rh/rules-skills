"""Isolated workspace sandbox for eval captures.

The SDK agent needs a workspace with .cursor/rules/ and .cursor/skills/ loaded.
But if we point it at the real repo, it pollutes .harness/, src/, tests/, etc.

Solution: create a temporary git worktree for each capture run. The worktree
shares the git database (so the agent sees realistic repo structure) but has
its own working directory. After capture, we destroy the worktree.

Usage:
    with CaptureWorkspace() as ws:
        # ws.path is a Path to an isolated checkout
        # .cursor/rules/, .cursor/skills/, .cursor/hooks.json are present
        Agent.create(..., local=LocalAgentOptions(cwd=str(ws.path)))
"""

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent

CONTENT_DENYLIST = {".git", ".cursor", "node_modules", "__pycache__", ".venv", "venv", "dist", ".next"}
MAX_FILE_SIZE = 100_000  # 100KB per file
MAX_TOTAL_CAPTURE = 524_288  # 512KB total


class CaptureWorkspace:
    """Temporary git worktree for capture isolation.

    On enter: creates a worktree from HEAD with .cursor/ config copied in.
    On exit: removes the worktree completely.
    """

    def __init__(self, *, branch_suffix: str = "eval-sandbox"):
        self._tmpdir: tempfile.TemporaryDirectory | None = None
        self._branch_suffix = branch_suffix
        self.path: Path = Path()

    def __enter__(self) -> "CaptureWorkspace":
        self._tmpdir = tempfile.TemporaryDirectory(prefix="eval-sandbox-")
        worktree_dir = Path(self._tmpdir.name) / "workspace"

        subprocess.run(
            ["git", "worktree", "add", "--detach", str(worktree_dir), "HEAD"],
            cwd=REPO_ROOT,
            capture_output=True,
            check=True,
        )

        self.path = worktree_dir
        self._setup_cursor_config()
        self._setup_clean_harness()
        return self

    def __exit__(self, *exc):
        if self.path.exists():
            subprocess.run(
                ["git", "worktree", "remove", "--force", str(self.path)],
                cwd=REPO_ROOT,
                capture_output=True,
            )
        if self._tmpdir:
            self._tmpdir.cleanup()

    def _setup_cursor_config(self):
        """Copy library/cursor/ into the worktree's .cursor/ so rules/skills are active.

        Reads from library/cursor/ (source of truth), not .cursor/ (local copy).
        This means evals always test the latest edits without needing sync-local.
        """
        library_cursor = REPO_ROOT / "library" / "cursor"
        dst_cursor = self.path / ".cursor"

        if not library_cursor.exists():
            return

        dst_cursor.mkdir(exist_ok=True)

        for item in ("rules", "skills", "agents", "references",
                      "hooks", "hooks.json", "hooks.lean.json", "hooks.full.json"):
            src = library_cursor / item
            if not src.exists():
                # hooks.json lives at library/cursor/hooks.lean.json → .cursor/hooks.json
                if item == "hooks.json":
                    lean = library_cursor / "hooks.lean.json"
                    if lean.exists():
                        shutil.copy2(lean, dst_cursor / "hooks.json")
                continue
            dst = dst_cursor / item
            if src.is_dir():
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dst)

    def _setup_clean_harness(self):
        """Create a clean .harness/ so the agent sees a fresh project state."""
        harness_dir = self.path / ".harness"
        harness_dir.mkdir(exist_ok=True)

        state = {
            "project": "eval-sandbox",
            "created": "2026-01-01T00:00:00Z",
            "spec": "Sandbox workspace for eval captures",
            "features": [],
        }
        (harness_dir / "state.json").write_text(json.dumps(state, indent=2))
        (harness_dir / "breadcrumbs.jsonl").write_text("")

    def collect_artifacts(self, verify_commands: list[dict] | None = None) -> dict:
        """Collect git diff, changed file contents, harness state, and verify results.

        Must be called BEFORE __exit__ destroys the worktree.
        """
        artifacts: dict = {
            "files": [],
            "git_diff_stat": "",
            "git_diff": "",
            "file_contents": {},
            "capture_meta": {"files_captured": 0, "bytes_captured": 0, "truncated": False, "skipped_files": 0},
            "validations": [],
            "harness": {},
        }

        artifacts["files"] = self._collect_file_list()
        diff_stat, diff_patch, changed_paths = self._collect_git_diff()
        artifacts["git_diff_stat"] = diff_stat
        artifacts["git_diff"] = diff_patch
        artifacts["file_contents"] = self._collect_changed_contents(changed_paths)
        artifacts["capture_meta"] = self._capture_meta
        artifacts["harness"] = self._collect_harness()

        if verify_commands:
            artifacts["validations"] = self._run_verify_commands(verify_commands)

        return artifacts

    def _collect_file_list(self) -> list[str]:
        files = []
        for p in sorted(self.path.rglob("*")):
            if p.is_file() and not any(part in CONTENT_DENYLIST for part in p.parts):
                files.append(str(p.relative_to(self.path)))
        return files

    def _collect_git_diff(self) -> tuple[str, str, list[str]]:
        """Get git diff stat, patch, and list of changed file paths."""
        stat_result = subprocess.run(
            ["git", "diff", "HEAD", "--stat"],
            cwd=self.path, capture_output=True, text=True,
        )
        patch_result = subprocess.run(
            ["git", "diff", "HEAD"],
            cwd=self.path, capture_output=True, text=True,
        )
        names_result = subprocess.run(
            ["git", "diff", "HEAD", "--name-only"],
            cwd=self.path, capture_output=True, text=True,
        )
        untracked = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            cwd=self.path, capture_output=True, text=True,
        )

        changed = [
            f for f in names_result.stdout.strip().splitlines() if f
        ]
        new_files = [
            f for f in untracked.stdout.strip().splitlines() if f
        ]

        return stat_result.stdout, patch_result.stdout, changed + new_files

    def _collect_changed_contents(self, paths: list[str]) -> dict[str, str]:
        """Read content of changed/new files, respecting size caps."""
        self._capture_meta = {
            "files_captured": 0, "bytes_captured": 0,
            "truncated": False, "skipped_files": 0,
        }
        contents: dict[str, str] = {}
        total_bytes = 0

        for rel_path in paths:
            full = self.path / rel_path
            if not full.is_file():
                continue
            if any(part in CONTENT_DENYLIST for part in Path(rel_path).parts):
                continue

            try:
                size = full.stat().st_size
            except OSError:
                continue

            if size > MAX_FILE_SIZE:
                self._capture_meta["skipped_files"] += 1
                continue
            if total_bytes + size > MAX_TOTAL_CAPTURE:
                self._capture_meta["truncated"] = True
                self._capture_meta["skipped_files"] += 1
                continue

            try:
                text = full.read_text(errors="replace")
                contents[rel_path] = text
                total_bytes += len(text.encode())
                self._capture_meta["files_captured"] += 1
                self._capture_meta["bytes_captured"] = total_bytes
            except OSError:
                self._capture_meta["skipped_files"] += 1

        return contents

    def _collect_harness(self) -> dict:
        harness: dict = {}
        harness_dir = self.path / ".harness"

        for name in ("state.json", "contract.json", "breadcrumbs.jsonl"):
            path = harness_dir / name
            if not path.exists():
                continue
            try:
                if name.endswith(".jsonl"):
                    lines = []
                    for line in path.read_text().splitlines():
                        line = line.strip()
                        if line:
                            try:
                                lines.append(json.loads(line))
                            except json.JSONDecodeError:
                                lines.append({"_raw": line})
                    harness[name] = lines
                else:
                    harness[name] = json.loads(path.read_text())
            except (json.JSONDecodeError, OSError):
                harness[name] = {"_error": "failed to parse"}

        evals_dir = harness_dir / "evals"
        if evals_dir.exists():
            harness["evals"] = []
            for ep in sorted(evals_dir.glob("eval-*.json")):
                try:
                    harness["evals"].append(json.loads(ep.read_text()))
                except (json.JSONDecodeError, OSError):
                    continue

        return harness

    def _run_verify_commands(self, commands: list[dict]) -> list[dict]:
        results = []
        for cmd_spec in commands:
            command = cmd_spec.get("command", "")
            timeout_s = cmd_spec.get("timeout_s", 30)
            try:
                proc = subprocess.run(
                    command, shell=True,
                    cwd=self.path, capture_output=True, text=True,
                    timeout=timeout_s,
                )
                results.append({
                    "command": command,
                    "exit_code": proc.returncode,
                    "stdout": proc.stdout[:4000],
                    "stderr": proc.stderr[:2000],
                })
            except subprocess.TimeoutExpired:
                results.append({
                    "command": command,
                    "exit_code": -1,
                    "stdout": "",
                    "stderr": f"Timeout after {timeout_s}s",
                })
            except Exception as e:
                results.append({
                    "command": command,
                    "exit_code": -1,
                    "stdout": "",
                    "stderr": str(e),
                })
        return results
