"""Isolated workspace backend for Renaissance runs."""
from __future__ import annotations

import fnmatch
import hashlib
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


class WorkspaceError(Exception):
    """Base exception for workspace operations."""


class WorkspaceEscape(WorkspaceError):
    """Raised when a requested path escapes the workspace target."""


class WorkspaceNotClean(WorkspaceError):
    """Raised when a workspace cannot be created because the target exists."""


class WorkspaceApplyError(WorkspaceError):
    """Raised when applying a patch to the base fails."""


@dataclass(frozen=True)
class Workspace:
    """A run's isolated work area."""

    run_id: str
    base_path: Path
    target_path: Path
    base_revision: str | None
    backend_name: str


class WorkspaceBackend(Protocol):
    """Pluggable workspace creation and lifecycle."""

    @property
    def name(self) -> str:
        ...

    def create(self, project_root: Path, run_id: str) -> Workspace:
        """Create an isolated workspace for a run."""
        ...

    def dispose(self, workspace: Workspace) -> None:
        """Remove the isolated workspace."""
        ...

    def resolve(self, workspace: Workspace, path: str) -> Path:
        """Resolve *path* inside the workspace target, raising if it escapes."""
        ...

    def diff(self, workspace: Workspace) -> bytes:
        """Return the difference between base and target as an artifact."""
        ...

    def apply(self, workspace: Workspace, patch: bytes) -> None:
        """Apply a captured patch to the base."""
        ...

    def is_clean(self, workspace: Workspace) -> bool:
        """Return True if the target matches the base byte-for-byte."""
        ...


def _assert_under_target(target: Path, candidate: Path) -> Path:
    target_resolved = target.resolve()
    candidate_resolved = candidate.resolve()
    if not candidate_resolved.is_relative_to(target_resolved):
        raise WorkspaceEscape(
            f"path {candidate_resolved!s} is outside workspace {target_resolved!s}"
        )
    return candidate_resolved


def _run_git(*args: str | Path, cwd: Path | None = None) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
        )
    except FileNotFoundError as exc:
        raise WorkspaceError("git is not installed or not on PATH") from exc
    except subprocess.CalledProcessError as exc:
        raise WorkspaceError(f"git failed: {exc.stderr or exc.stdout}") from exc
    return result.stdout


def _is_git_repo(path: Path) -> bool:
    return (path / ".git").is_dir() or (path / ".git").is_file()


def _git_base_revision(repo: Path) -> str:
    return _run_git("rev-parse", "HEAD", cwd=repo).strip()


def _link_venvs(project_root: Path, target: Path) -> None:
    """Symlink project venvs into the workspace so lanes can run tests.

    Worktrees don't carry gitignored dirs — a lane landing in a fresh
    workspace has no .venv and can't run pytest (observed: the mocks lane
    completed with no patch because 'the venv lacks pytest'). Symlink
    rather than copy (a venv is ~200MB+; symlinking shares the interpreter
    and site-packages — lanes share, not duplicate). Shallow scan only:
    project_root/.venv and project_root/*/.venv cover the layouts in use.
    """
    candidates = [project_root / ".venv"]
    try:
        candidates.extend(p / ".venv" for p in project_root.iterdir() if p.is_dir())
    except OSError:
        pass
    for venv in candidates:
        if not (venv / "bin" / "python").exists():
            continue
        rel = venv.relative_to(project_root)
        dst = target / rel
        if dst.exists() or dst.is_symlink():
            continue
        try:
            dst.symlink_to(venv)
        except OSError:
            pass


def _workspace_root() -> Path:
    env_root = os.environ.get("NUCLEUS_WORKSPACE_ROOT")
    if env_root:
        return Path(env_root)
    brain = os.environ.get("NUCLEUS_BRAIN_PATH")
    if brain:
        return Path(brain) / "runs" / "workspaces"
    return Path(tempfile.gettempdir()) / "nucleus-workspaces"


class GitWorkspaceBackend:
    """Uses a git worktree as the isolated target."""

    def __init__(self, workspace_root: Path | None = None) -> None:
        self._workspace_root = workspace_root

    @property
    def name(self) -> str:
        return "git"

    def _target_name(self, run_id: str) -> str:
        return f"nucleus-run-{run_id}"

    def create(self, project_root: Path, run_id: str) -> Workspace:
        if not _is_git_repo(project_root):
            raise WorkspaceError(f"project root {project_root} is not a git repository")
        base_revision = _git_base_revision(project_root)
        workspace_root = self._workspace_root or _workspace_root()
        target = workspace_root / self._target_name(run_id)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            raise WorkspaceNotClean(f"workspace target already exists: {target}")
        _run_git(
            "worktree",
            "add",
            "--detach",
            target,
            base_revision,
            cwd=project_root,
        )
        _link_venvs(project_root, target)
        return Workspace(
            run_id=run_id,
            base_path=project_root,
            target_path=target,
            base_revision=base_revision,
            backend_name=self.name,
        )

    def dispose(self, workspace: Workspace) -> None:
        if not workspace.target_path.exists():
            return
        try:
            _run_git("worktree", "remove", "--force", workspace.target_path)
        except WorkspaceError:
            shutil.rmtree(workspace.target_path, ignore_errors=True)

    def resolve(self, workspace: Workspace, path: str) -> Path:
        if Path(path).is_absolute():
            candidate = Path(path)
        else:
            candidate = workspace.target_path / path
        return _assert_under_target(workspace.target_path, candidate)

    def diff(self, workspace: Workspace) -> bytes:
        try:
            # Stage changes (including untracked) so the cached diff captures
            # the full worktree state against the base revision.
            subprocess.run(
                ["git", "add", "-A"],
                cwd=workspace.target_path,
                capture_output=True,
                check=True,
            )
            return subprocess.run(
                [
                    "git",
                    "diff",
                    "--cached",
                    "--binary",
                    "--no-color",
                    workspace.base_revision,
                ],
                cwd=workspace.target_path,
                capture_output=True,
                check=True,
            ).stdout
        except subprocess.CalledProcessError as exc:
            raise WorkspaceError(f"git diff failed: {exc.stderr.decode()}") from exc

    def apply(self, workspace: Workspace, patch: bytes) -> None:
        if not workspace.base_path.exists():
            raise WorkspaceApplyError("base path no longer exists")
        if self._has_uncommitted_changes(workspace.base_path):
            raise WorkspaceApplyError("base has uncommitted changes; apply blocked")
        try:
            subprocess.run(
                ["git", "apply", "--check"],
                input=patch,
                cwd=workspace.base_path,
                capture_output=True,
                check=True,
            )
            subprocess.run(
                ["git", "apply"],
                input=patch,
                cwd=workspace.base_path,
                capture_output=True,
                check=True,
            )
        except subprocess.CalledProcessError as exc:
            raise WorkspaceApplyError(f"patch rejected: {exc.stderr.decode()}") from exc

    def is_clean(self, workspace: Workspace) -> bool:
        return not self.diff(workspace)

    def _has_uncommitted_changes(self, repo: Path) -> bool:
        try:
            status = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=repo,
                capture_output=True,
                text=True,
                check=True,
            )
            return bool(status.stdout.strip())
        except subprocess.CalledProcessError as exc:
            raise WorkspaceError(f"git status failed: {exc.stderr}") from exc


class CopyWorkspaceBackend:
    """Copies the project root into a fresh directory."""

    # Directory names to ignore anywhere in the source tree.
    _IGNORE_DIRS: frozenset[str] = frozenset({
        ".git",
        ".next",
        "node_modules",
        "dist",
        "build",
        "coverage",
        ".venv",
        "venv",
        "env",
        "ENV",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".tox",
        ".nuxt",
        ".output",
        "out",
        ".svelte-kit",
        ".vercel",
        ".serverless",
        ".terraform",
        ".brain",
        ".claude",
        ".gstack",
        ".devin",
        ".research",
        ".cursor",
        ".aider",
        ".cache",
        ".turbo",
        ".parcel-cache",
        ".webpack",
        ".rollup.cache",
        ".tsup",
        ".nx",
        ".angular",
        ".nyc_output",
        ".vite",
    })

    # Names that are only ignored when they appear inside a content parent.
    _CONTENT_PARENT_DIRS: frozenset[str] = frozenset({
        "public",
        "content",
        "static",
        "assets",
    })

    _IGNORE_NAMES_IN_CONTENT: frozenset[str] = frozenset({
        "media",
        "models",
    })

    # File-name patterns to ignore anywhere.
    _IGNORE_PATTERNS: tuple[str, ...] = (
        "*.png",
        "*.jpg",
        "*.jpeg",
        "*.gif",
        "*.webp",
        "*.svg",
        "*.ico",
        "*.bmp",
        "*.tiff",
        "*.tif",
        "*.psd",
        "*.ai",
        "*.sketch",
        "*.mp3",
        "*.mp4",
        "*.mov",
        "*.avi",
        "*.mkv",
        "*.webm",
        "*.wav",
        "*.flac",
        "*.aac",
        "*.onnx",
        "*.data",
        "*.pkl",
        "*.pickle",
        "*.h5",
        "*.hdf5",
        "*.pb",
        "*.pt",
        "*.pth",
        "*.safetensors",
        "*.gguf",
        "*.bin",
        "*.npy",
        "*.npz",
        "*.parquet",
        "*.feather",
        "*.arrow",
        "*.db",
        "*.sqlite",
        "*.sqlite3",
        "*.xlsx",
        "*.xls",
        "*.pdf",
        "*.pptx",
        "*.ppt",
        "*.docx",
        "*.doc",
        "*.odt",
        "*.ods",
        "*.odp",
        "*.zip",
        "*.tar",
        "*.gz",
        "*.tgz",
        "*.bz2",
        "*.xz",
        "*.7z",
        "*.rar",
        "*.iso",
        "*.dmg",
        "*.log",
        "*.tmp",
        "*.temp",
        "*.swp",
        "*.swo",
        "*~",
        ".DS_Store",
        "Thumbs.db",
        "*.tsbuildinfo",
        ".eslintcache",
        ".prettiercache",
        ".stylelintcache",
        ".cache",
        ".turbo",
        ".parcel-cache",
        ".webpack",
        ".rollup.cache",
        ".tsup",
        ".nx",
        ".angular",
        ".nyc_output",
        ".vite",
        "*.map",
        "*.d.ts.map",
        "*.css.map",
        "*.js.map",
    )

    _MAX_FILE_SIZE: int = 1_048_576

    def __init__(self, workspace_root: Path | None = None) -> None:
        self._workspace_root = workspace_root

    @property
    def name(self) -> str:
        return "copy"

    def _target_name(self, run_id: str) -> str:
        return f"nucleus-copy-{run_id}"

    def _should_ignore(self, source: Path, path: Path) -> bool:
        """Return True if *path* under *source* should not be copied or hashed."""
        try:
            rel = path.relative_to(source)
        except ValueError:
            rel = path
        parts = rel.parts

        for i, part in enumerate(parts):
            if part in self._IGNORE_DIRS:
                return True
            if part in self._IGNORE_NAMES_IN_CONTENT and any(
                p in self._CONTENT_PARENT_DIRS for p in parts[:i]
            ):
                return True

        if path.is_file():
            try:
                size = path.stat().st_size
            except OSError:
                size = 0
            if size > self._MAX_FILE_SIZE:
                return True
            if any(fnmatch.fnmatch(parts[-1], pat) for pat in self._IGNORE_PATTERNS):
                return True

        return False

    def _copy_root(self, source: Path, target: Path) -> None:
        if target.exists():
            raise WorkspaceNotClean(f"target already exists: {target}")
        target.parent.mkdir(parents=True, exist_ok=True)

        def _ignore(src: str, names: list[str]) -> set[str]:
            current = Path(src)
            ignored: set[str] = set()
            for name in names:
                full = current / name
                if self._should_ignore(source, full):
                    ignored.add(name)
            return ignored

        shutil.copytree(
            source,
            target,
            symlinks=False,
            ignore_dangling_symlinks=True,
            ignore=_ignore,
        )

    def _hash_base(self, source: Path) -> str:
        hasher = hashlib.sha256()
        for path in sorted(source.rglob("*")):
            if path.is_file() and not path.is_symlink() and not self._should_ignore(source, path):
                hasher.update(path.read_bytes())
        return hasher.hexdigest()

    def create(self, project_root: Path, run_id: str) -> Workspace:
        if not project_root.is_dir():
            raise WorkspaceError(f"project root is not a directory: {project_root}")
        workspace_root = self._workspace_root or _workspace_root()
        target = workspace_root / self._target_name(run_id)
        target.parent.mkdir(parents=True, exist_ok=True)
        self._copy_root(project_root, target)
        return Workspace(
            run_id=run_id,
            base_path=project_root,
            target_path=target,
            base_revision=self._hash_base(project_root),
            backend_name=self.name,
        )

    def dispose(self, workspace: Workspace) -> None:
        if workspace.target_path.exists():
            shutil.rmtree(workspace.target_path, ignore_errors=True)

    def resolve(self, workspace: Workspace, path: str) -> Path:
        if Path(path).is_absolute():
            candidate = Path(path)
        else:
            candidate = workspace.target_path / path
        return _assert_under_target(workspace.target_path, candidate)

    def diff(self, workspace: Workspace) -> bytes:
        try:
            exclude_args: list[str] = []
            for name in sorted(self._IGNORE_DIRS | self._IGNORE_NAMES_IN_CONTENT):
                exclude_args.extend(["-x", name])
            for pat in self._IGNORE_PATTERNS:
                exclude_args.extend(["-x", pat])

            # Per-instance size guard: ignore any base file/symlink > _MAX_FILE_SIZE by basename.
            for path in workspace.base_path.rglob("*"):
                if not (path.is_file() or path.is_symlink()):
                    continue
                try:
                    size = path.stat().st_size
                except OSError:
                    size = 0
                if size > self._MAX_FILE_SIZE:
                    exclude_args.extend(["-x", path.name])

            return subprocess.run(
                ["diff", "-ru", *exclude_args, str(workspace.base_path), str(workspace.target_path)],
                capture_output=True,
                check=False,
            ).stdout
        except FileNotFoundError as exc:
            raise WorkspaceError("diff(1) is not available") from exc

    def apply(self, workspace: Workspace, patch: bytes) -> None:
        if not workspace.base_path.exists():
            raise WorkspaceApplyError("base path no longer exists")
        if patch.endswith(b"\n"):
            patch = patch.rstrip(b"\n") + b"\n"
        try:
            # Dry-run first so a conflict does not mutate the base.
            subprocess.run(
                ["patch", "-p1", "--dry-run", "-i", "-"],
                input=patch,
                cwd=workspace.base_path,
                capture_output=True,
                check=True,
            )
            subprocess.run(
                ["patch", "-p1", "-i", "-"],
                input=patch,
                cwd=workspace.base_path,
                capture_output=True,
                check=True,
            )
        except FileNotFoundError as exc:
            raise WorkspaceApplyError("patch(1) is not available") from exc
        except subprocess.CalledProcessError as exc:
            raise WorkspaceApplyError(f"patch rejected: {exc.stderr.decode()}") from exc

    def is_clean(self, workspace: Workspace) -> bool:
        return not self.diff(workspace)


class WorkspaceResolver:
    """Selects an appropriate backend for a project root."""

    def __init__(
        self,
        git_backend: GitWorkspaceBackend | None = None,
        workspace_root: Path | None = None,
    ) -> None:
        self.git = git_backend or GitWorkspaceBackend(workspace_root=workspace_root)
        self.copy = CopyWorkspaceBackend(workspace_root=workspace_root)

    def resolve_backend(self, project_root: Path) -> WorkspaceBackend:
        if _is_git_repo(project_root):
            return self.git
        return self.copy
