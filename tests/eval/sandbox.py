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

import shutil
import subprocess
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent


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
        """Copy .cursor/ config into the worktree so rules/skills are active."""
        src_cursor = REPO_ROOT / ".cursor"
        dst_cursor = self.path / ".cursor"

        if not src_cursor.exists():
            return

        dst_cursor.mkdir(exist_ok=True)

        for item in ("rules", "skills", "hooks.json", "hooks.lean.json"):
            src = src_cursor / item
            dst = dst_cursor / item
            if src.is_symlink():
                link_target = src.resolve()
                if link_target.exists():
                    if link_target.is_dir():
                        shutil.copytree(link_target, dst, dirs_exist_ok=True)
                    else:
                        shutil.copy2(link_target, dst)
            elif src.is_dir():
                shutil.copytree(src, dst, dirs_exist_ok=True)
            elif src.is_file():
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
        (harness_dir / "state.json").write_text(
            __import__("json").dumps(state, indent=2)
        )
        (harness_dir / "breadcrumbs.jsonl").write_text("")
