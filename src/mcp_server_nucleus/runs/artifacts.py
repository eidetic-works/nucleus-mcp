from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path

from .store import ArtifactConflict, RunStore


class ArtifactIntegrityError(Exception):
    pass


class ArtifactStore:
    def __init__(self, root: str, run_store: RunStore) -> None:
        self._root = Path(root)
        self._root.mkdir(parents=True, exist_ok=True)
        self._run_store = run_store

    def _sha256(self, content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()

    def _content_path(self, sha256: str) -> Path:
        return self._root / sha256[:2] / sha256[2:4] / sha256

    def _relative_path(self, sha256: str) -> str:
        return f"{sha256[:2]}/{sha256[2:4]}/{sha256}"

    def _assert_under_root(self, path: Path) -> None:
        root_resolved = self._root.resolve()
        path_resolved = path.resolve()
        parent_resolved = path.parent.resolve()
        if not path_resolved.is_relative_to(root_resolved) or not parent_resolved.is_relative_to(
            root_resolved
        ):
            raise ArtifactIntegrityError("artifact path outside store root")

    def write_bytes(
        self,
        run_id: str,
        kind: str,
        content: bytes,
        mime_type: str,
        metadata: dict | None = None,
    ):
        sha256 = self._sha256(content)
        size = len(content)
        target = self._content_path(sha256)
        self._assert_under_root(target)

        target.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=target.parent)
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, target)
        except Exception:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise

        return self._run_store.record_artifact(
            run_id,
            kind,
            sha256,
            mime_type,
            size,
            metadata=metadata,
            path=self._relative_path(sha256),
        )

    def read_bytes(self, artifact_id: str) -> bytes:
        artifact = self._run_store.get_artifact(artifact_id)
        if artifact.path is None:
            raise ArtifactIntegrityError("artifact has no path")

        rel = Path(artifact.path)
        if ".." in rel.parts:
            raise ArtifactIntegrityError("path traversal detected")

        data_path = self._root / rel
        resolved = data_path.resolve()
        root_resolved = self._root.resolve()
        if not resolved.is_relative_to(root_resolved):
            raise ArtifactIntegrityError("path outside store root")

        try:
            data = data_path.read_bytes()
        except OSError as exc:
            raise ArtifactIntegrityError("artifact content missing or unreadable") from exc

        if len(data) != artifact.size:
            raise ArtifactIntegrityError("size mismatch")
        if hashlib.sha256(data).hexdigest() != artifact.sha256:
            raise ArtifactIntegrityError("hash mismatch")

        return data
