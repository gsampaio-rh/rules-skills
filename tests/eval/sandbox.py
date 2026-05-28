"""Isolated workspace sandbox for eval captures.

Creates a fresh temporary git repository for each eval run, copies in
.cursor/ config (rules, skills) so the agent sees them, and provides
artifact collection (git diff, file contents, verify commands).

The workspace is completely independent — no worktrees, no shared .git.
Destroyed on exit.

Usage:
    with CaptureWorkspace() as ws:
        # ws.path is a Path to an isolated git repo with .cursor/ loaded
        # Use with CursorClient.launch_bridge(workspace=str(ws.path))
        ...
        artifacts = ws.collect_artifacts(verify_commands)
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
    """Temporary isolated git repo for eval capture.

    On enter: creates temp dir, git init, copies .cursor/ config, writes seed files.
    On exit: deletes everything.
    """

    def __init__(self, *, prefix: str = "eval-sandbox-", seed_files: dict[str, str] | None = None):
        self._tmpdir: tempfile.TemporaryDirectory | None = None
        self._prefix = prefix
        self._seed_files = seed_files or {}
        self.path: Path = Path()
        self._capture_meta: dict = {}
        self._base_sha: str = ""

    def __enter__(self) -> "CaptureWorkspace":
        self._tmpdir = tempfile.TemporaryDirectory(prefix=self._prefix)
        self.path = Path(self._tmpdir.name)

        subprocess.run(
            ["git", "init"],
            cwd=self.path, capture_output=True, check=True,
        )
        subprocess.run(
            ["git", "commit", "--allow-empty", "-m", "eval-sandbox-init"],
            cwd=self.path, capture_output=True, check=True,
        )

        self._setup_cursor_config()
        self._write_seed_files()

        # Commit seed state so base_sha captures the clean starting point
        subprocess.run(
            ["git", "add", "-A"],
            cwd=self.path, capture_output=True, check=True,
        )
        subprocess.run(
            ["git", "commit", "--allow-empty", "-m", "seed"],
            cwd=self.path, capture_output=True, check=True,
        )
        self._base_sha = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=self.path, capture_output=True, text=True, check=True,
        ).stdout.strip()

        return self

    def __exit__(self, *exc):
        if self._tmpdir:
            self._tmpdir.cleanup()

    def _setup_cursor_config(self):
        """Copy library/cursor/ into .cursor/ so rules/skills are active."""
        library_cursor = REPO_ROOT / "library" / "cursor"
        dst_cursor = self.path / ".cursor"

        if not library_cursor.exists():
            return

        dst_cursor.mkdir(exist_ok=True)

        for item in ("rules", "skills", "agents", "references"):
            src = library_cursor / item
            if src.exists():
                shutil.copytree(src, dst_cursor / item, dirs_exist_ok=True)

    def _write_seed_files(self):
        """Write scenario seed files into the workspace."""
        for rel_path, content in self._seed_files.items():
            target = self.path / rel_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content)

    def collect_artifacts(self, verify_commands: list[dict] | None = None) -> dict:
        """Collect git diff, changed file contents, harness state, and verify results."""
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
        """Get all changes since sandbox init (handles both committed and uncommitted work)."""
        # Diff against the initial empty commit to capture everything the agent did
        base = self._base_sha
        stat_result = subprocess.run(
            ["git", "diff", base, "--stat"],
            cwd=self.path, capture_output=True, text=True,
        )
        patch_result = subprocess.run(
            ["git", "diff", base],
            cwd=self.path, capture_output=True, text=True,
        )
        names_result = subprocess.run(
            ["git", "diff", base, "--name-only"],
            cwd=self.path, capture_output=True, text=True,
        )
        # Also pick up uncommitted untracked files
        untracked = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            cwd=self.path, capture_output=True, text=True,
        )

        changed = [f for f in names_result.stdout.strip().splitlines() if f]
        new_files = [f for f in untracked.stdout.strip().splitlines() if f]

        return stat_result.stdout, patch_result.stdout, list(set(changed + new_files))

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
        if not harness_dir.exists():
            return harness

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
