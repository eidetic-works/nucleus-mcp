"""Verification bundle and conflict-safe apply/dismiss helpers."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class ApplyConflict(Exception):
    """Raised when applying a workspace diff to the base would conflict or fail."""


class ApplyNotReady(Exception):
    """Raised when apply is requested for a run that is not reviewable."""


@dataclass
class ArtifactRef:
    """Reference to a persisted artifact."""

    sha256: str
    path: str
    size: int
    mimetype: str | None = None


@dataclass
class VerificationBundle:
    """Evidence bundle attached to a run at the review gate.

    Legacy fields ``output``, ``diff_sha256`` and ``diff_size`` are kept for
    backward compatibility and are populated from the artifact manifest.
    """

    status: str
    output: str  # deprecated: kept for backward compatibility
    diff_sha256: str = ""  # deprecated: kept for backward compatibility
    diff_size: int = 0  # deprecated: kept for backward compatibility
    is_clean: bool = False
    base_revision: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    patch: ArtifactRef | None = None
    test_report: ArtifactRef | None = None
    stdout_log: ArtifactRef | None = None
    stderr_log: ArtifactRef | None = None
    work_log: ArtifactRef | None = None

    target_head_at_review: str = ""
    route: dict[str, Any] = field(default_factory=dict)
    usage: dict[str, Any] = field(default_factory=dict)
    unknowns: list[str] = field(default_factory=list)

    verdict: str = "ok"
    warning: bool = False
    reason: str | None = None
    apply_eligible: bool = False  # True only when a real check passed and candidate is frozen

    @classmethod
    def with_artifact(
        cls,
        name: str,
        data: bytes,
        mimetype: str | None = None,
    ) -> ArtifactRef:
        """Persist ``data`` to ``.brain/artifacts/<sha256>.bin`` and return its ref.

        The ``name`` argument is a semantic label and is not used in the
        storage path; callers assign the returned ``ArtifactRef`` to the
        appropriate bundle field.
        """
        from mcp_server_nucleus.runtime.common import get_brain_path

        sha = hashlib.sha256(data).hexdigest()
        brain = Path(get_brain_path())
        path = brain / "artifacts" / f"{sha}.bin"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        rel = path.relative_to(brain)
        return ArtifactRef(
            sha256=sha,
            path=str(rel),
            size=len(data),
            mimetype=mimetype,
        )

    @classmethod
    def read_artifact(cls, ref: ArtifactRef) -> bytes | None:
        """Read an artifact back from disk, verifying its hash, or return ``None`` if missing."""
        from mcp_server_nucleus.runtime.common import get_brain_path

        brain = Path(get_brain_path())
        path = brain / ref.path
        if not path.is_file():
            return None
        data = path.read_bytes()
        # Verify content integrity if the ref carries a sha256.
        if ref.sha256:
            actual = hashlib.sha256(data).hexdigest()
            if actual != ref.sha256:
                raise ValueError(
                    f"artifact hash mismatch: expected {ref.sha256}, got {actual}"
                )
        return data

    def with_diff(self, diff: bytes) -> VerificationBundle:
        """Return a copy with the diff artifact attached and legacy fields set."""
        patch = self.with_artifact("diff", diff, mimetype="text/x-diff")
        return VerificationBundle(
            status=self.status,
            output=self.output,
            diff_sha256=patch.sha256,
            diff_size=patch.size,
            is_clean=not bool(diff),
            base_revision=self.base_revision,
            metadata=self.metadata,
            patch=patch,
            test_report=self.test_report,
            stdout_log=self.stdout_log,
            stderr_log=self.stderr_log,
            work_log=self.work_log,
            target_head_at_review=self.target_head_at_review,
            route=self.route,
            usage=self.usage,
            unknowns=self.unknowns,
            verdict=self.verdict,
            warning=self.warning,
            reason=self.reason,
            apply_eligible=self.apply_eligible,
        )
