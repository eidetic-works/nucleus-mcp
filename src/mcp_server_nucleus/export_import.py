"""Nucleus Brain Export/Import — the sovereignty guarantee.

Users can extract their full brain data (``nucleus export``) and restore it
elsewhere (``nucleus import``). This is the data-portability primitive that
guarantees users are never locked in: their engrams, ledger, sessions, and
config are theirs to move.

Design constraints:
  - **Redaction by default.** Secrets (API keys, tokens, credentials) are
    excluded from exports unless ``--include-secrets`` is passed. The
    ``.brain/secrets/`` directory is always excluded.
  - **Manifest-first.** Every export includes a ``manifest.json`` with the
    schema version, tenant_id, file list, and redaction map. Import validates
    the manifest before touching anything.
  - **Non-destructive import.** Import into a non-empty brain requires
    ``--merge`` (default) or ``--replace`` (destructive, prompts). The
    default merge never overwrites existing files — it suffix-collides.
  - **Tenant-aware.** Export resolves the current tenant brain (via
    ``NUCLEUS_BRAIN_PATH`` or the tenant middleware path). Import targets a
    tenant brain the same way.
  - **Format.** Exports are ``.tar.gz`` archives — standard, inspectable,
    no proprietary format. Users can ``tar tzf`` to audit before importing.

Schema version: 1 (locked at first public release; bump on breaking changes).
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EXPORT_SCHEMA_VERSION = 1

# Directories / patterns that are ALWAYS excluded from export (even with
# --include-secrets). These are runtime-generated or infrastructure state
# that doesn't make sense to port.
_ALWAYS_EXCLUDED_DIRS = {
    "logs",           # runtime logs
    "instrumentation", # telemetry JSONL (regenerable)
    "__pycache__",
    ".cache",
}

# File patterns that are always excluded.
_ALWAYS_EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".log", ".lock"}

# Directories that contain secrets and are excluded unless --include-secrets.
_SECRET_DIRS = {"secrets"}

# Files that may contain secrets and are redacted by default.
_SECRET_FILE_PATTERNS = {
    "config/nucleus.yaml",   # may contain API keys
    "config/channels.json",  # channel tokens
}

# Maximum file size for a single file in export (100 MB safety valve).
_MAX_SINGLE_FILE_BYTES = 100 * 1024 * 1024


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

def export_brain(
    brain_path: Path,
    output_path: Path,
    *,
    include_secrets: bool = False,
    include_relay: bool = False,
    compression: str = "gz",
) -> Path:
    """Export a brain directory to a portable .tar.gz archive.

    Args:
        brain_path: Path to the .brain directory to export.
        output_path: Output file path (will be created/overwritten).
        include_secrets: If True, include secrets/ dir + secret-bearing config
            files. Default False — redact.
        include_relay: If True, include .brain/relay/ (cross-agent messages).
            Default False — relay is infrastructure state, not user memory.
        compression: "gz" for .tar.gz (default), "none" for .tar.

    Returns:
        The path to the created archive.

    Raises:
        FileNotFoundError: if brain_path doesn't exist.
        ValueError: if brain_path isn't a directory.
    """
    brain_path = Path(brain_path).resolve()
    if not brain_path.exists():
        raise FileNotFoundError(f"Brain path does not exist: {brain_path}")
    if not brain_path.is_dir():
        raise ValueError(f"Brain path is not a directory: {brain_path}")

    output_path = Path(output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Build the exclusion set
    excluded_dirs = set(_ALWAYS_EXCLUDED_DIRS)
    if not include_secrets:
        excluded_dirs.update(_SECRET_DIRS)
    if not include_relay:
        excluded_dirs.add("relay")

    # Collect files + build manifest
    files = []  # list of {relpath, size, sha256, redacted}
    redactions = []

    for root, dirs, filenames in os.walk(brain_path):
        rel_root = Path(root).relative_to(brain_path)
        # Filter dirs in-place (os.walk respects this)
        dirs[:] = [
            d for d in dirs
            if d not in excluded_dirs and d not in ("__pycache__",)
        ]
        for fname in filenames:
            fpath = Path(root) / fname
            relpath = str(rel_root / fname) if str(rel_root) != "." else fname

            # Skip always-excluded suffixes
            if fpath.suffix in _ALWAYS_EXCLUDED_SUFFIXES:
                continue

            # Size safety valve
            size = fpath.stat().st_size
            if size > _MAX_SINGLE_FILE_BYTES:
                continue

            sha = _sha256_file(fpath)
            redacted = False

            # Redact secret-bearing config files
            if not include_secrets:
                for pattern in _SECRET_FILE_PATTERNS:
                    if relpath == pattern or relpath.startswith(pattern):
                        redacted = True
                        redactions.append({
                            "path": relpath,
                            "reason": "secret-bearing config",
                        })
                        break

            files.append({
                "relpath": relpath,
                "size": size,
                "sha256": sha,
                "redacted": redacted,
            })

    # Resolve tenant_id from brain path structure
    tenant_id = _resolve_tenant_id_from_brain_path(brain_path)

    manifest = {
        "schema_version": EXPORT_SCHEMA_VERSION,
        "exported_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "tenant_id": tenant_id,
        "brain_path": str(brain_path),
        "file_count": len(files),
        "total_bytes": sum(f["size"] for f in files),
        "include_secrets": include_secrets,
        "include_relay": include_relay,
        "redactions": redactions,
        "files": files,
        "tool": "nucleus export",
        "version": _nucleus_version(),
    }

    # Write archive
    mode = "w:gz" if compression == "gz" else "w"
    suffix = ".tar.gz" if compression == "gz" else ".tar"

    # Ensure output has correct suffix
    if not str(output_path).endswith(suffix):
        output_path = output_path.with_suffix(suffix)

    with tarfile.open(output_path, mode) as tar:
        # Add manifest first
        manifest_bytes = json.dumps(manifest, indent=2).encode("utf-8")
        manifest_info = tarfile.TarInfo(name="manifest.json")
        manifest_info.size = len(manifest_bytes)
        from io import BytesIO
        tar.addfile(manifest_info, BytesIO(manifest_bytes))

        # Add brain files
        for f in files:
            relpath = f["relpath"]
            src = brain_path / relpath

            if f["redacted"]:
                # Write a redacted placeholder
                placeholder = (
                    f"[REDACTED by nucleus export — secret-bearing file]\n"
                    f"Original SHA-256: {f['sha256']}\n"
                    f"Re-export with --include-secrets to include contents.\n"
                ).encode("utf-8")
                info = tarfile.TarInfo(name=f"brain/{relpath}")
                info.size = len(placeholder)
                tar.addfile(info, BytesIO(placeholder))
            else:
                tar.add(str(src), arcname=f"brain/{relpath}", recursive=False)

    return output_path


# ---------------------------------------------------------------------------
# Import
# ---------------------------------------------------------------------------

def import_brain(
    archive_path: Path,
    target_brain: Path,
    *,
    merge: bool = True,
    replace: bool = False,
    dry_run: bool = False,
) -> dict:
    """Import a brain archive into a target brain directory.

    Args:
        archive_path: Path to the .tar.gz export archive.
        target_brain: Path to the .brain directory to import into.
        merge: If True (default), import without overwriting existing files.
            Collisions get a ``.imported-<timestamp>`` suffix.
        replace: If True, overwrite existing files. Destructive — requires
            explicit confirmation by the caller. Mutually exclusive with merge.
        dry_run: If True, validate the archive and report what would happen
            without writing anything.

    Returns:
        A dict with import results:
            {"imported": N, "skipped": N, "overwritten": N, "errors": [...],
             "manifest": {...}}

    Raises:
        FileNotFoundError: if archive doesn't exist.
        ValueError: if archive is invalid or manifest is missing/incompatible.
    """
    if merge and replace:
        raise ValueError("merge and replace are mutually exclusive")

    archive_path = Path(archive_path).resolve()
    if not archive_path.exists():
        raise FileNotFoundError(f"Archive does not exist: {archive_path}")

    target_brain = Path(target_brain).resolve()

    # Read + validate manifest
    manifest = _read_manifest_from_archive(archive_path)
    _validate_manifest(manifest)

    if dry_run:
        return {
            "imported": 0,
            "skipped": len(manifest["files"]),
            "overwritten": 0,
            "errors": [],
            "manifest": manifest,
            "dry_run": True,
            "target": str(target_brain),
        }

    # Extract to temp dir, then copy into target
    target_brain.mkdir(parents=True, exist_ok=True)

    result = {
        "imported": 0,
        "skipped": 0,
        "overwritten": 0,
        "errors": [],
        "manifest": manifest,
        "dry_run": False,
        "target": str(target_brain),
    }

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    with tempfile.TemporaryDirectory() as tmpdir:
        with tarfile.open(archive_path, "r:*") as tar:
            tar.extractall(path=tmpdir, filter="data")  # safe extraction

        extracted_brain = Path(tmpdir) / "brain"
        if not extracted_brain.exists():
            raise ValueError(
                "Archive is missing 'brain/' directory — not a valid nucleus export"
            )

        for f in manifest["files"]:
            relpath = f["relpath"]
            src = extracted_brain / relpath
            dst = target_brain / relpath

            if not src.exists():
                result["errors"].append(f"Missing in archive: {relpath}")
                continue

            # Skip redacted placeholders (they're not real data)
            if f.get("redacted"):
                result["skipped"] += 1
                continue

            # Verify SHA-256
            actual_sha = _sha256_file(src)
            if actual_sha != f["sha256"]:
                result["errors"].append(
                    f"SHA-256 mismatch for {relpath}: "
                    f"expected {f['sha256'][:16]}, got {actual_sha[:16]}"
                )
                continue

            dst.parent.mkdir(parents=True, exist_ok=True)

            if dst.exists() and not replace:
                if merge:
                    # Suffix-collide
                    dst = dst.with_name(
                        f"{dst.stem}.imported-{ts}{dst.suffix}"
                    )
                else:
                    result["skipped"] += 1
                    continue
            elif dst.exists() and replace:
                result["overwritten"] += 1

            shutil.copy2(str(src), str(dst))
            result["imported"] += 1

    return result


# ---------------------------------------------------------------------------
# Verify
# ---------------------------------------------------------------------------

def verify_export(archive_path: Path) -> dict:
    """Verify an export archive without importing it.

    Checks:
      - manifest.json present + valid schema
      - every file in manifest exists in archive
      - SHA-256 matches for every file

    Returns:
        {"valid": bool, "file_count": N, "verified": N, "mismatches": [...],
         "manifest": {...}}
    """
    archive_path = Path(archive_path).resolve()
    if not archive_path.exists():
        raise FileNotFoundError(f"Archive does not exist: {archive_path}")

    manifest = _read_manifest_from_archive(archive_path)
    _validate_manifest(manifest)

    result = {
        "valid": True,
        "file_count": len(manifest["files"]),
        "verified": 0,
        "mismatches": [],
        "missing": [],
        "manifest": manifest,
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        with tarfile.open(archive_path, "r:*") as tar:
            tar.extractall(path=tmpdir, filter="data")

        extracted_brain = Path(tmpdir) / "brain"
        for f in manifest["files"]:
            relpath = f["relpath"]
            src = extracted_brain / relpath
            if not src.exists():
                result["missing"].append(relpath)
                result["valid"] = False
                continue

            if f.get("redacted"):
                # Redacted placeholders can't be SHA-verified
                result["verified"] += 1
                continue

            actual_sha = _sha256_file(src)
            if actual_sha != f["sha256"]:
                result["mismatches"].append({
                    "path": relpath,
                    "expected": f["sha256"],
                    "actual": actual_sha,
                })
                result["valid"] = False
            else:
                result["verified"] += 1

    return result


# ---------------------------------------------------------------------------
# CLI handlers
# ---------------------------------------------------------------------------

def handle_export_command(args) -> int:
    """Handler for `nucleus export`."""
    from .runtime.common import get_brain_path

    try:
        brain = get_brain_path()
    except ValueError as e:
        print(f"Error: {e}")
        return 1

    output = Path(args.output) if args.output else None
    if output is None:
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        output = Path.cwd() / f"nucleus-brain-export-{ts}.tar.gz"

    print(f"Exporting brain: {brain}")
    print(f"Output:          {output}")
    print(f"Include secrets: {args.include_secrets}")
    print(f"Include relay:   {args.include_relay}")

    try:
        result_path = export_brain(
            brain_path=brain,
            output_path=output,
            include_secrets=args.include_secrets,
            include_relay=args.include_relay,
        )
    except Exception as e:
        print(f"Export failed: {e}")
        return 1

    size_mb = result_path.stat().st_size / (1024 * 1024)
    print(f"\nExport complete: {result_path} ({size_mb:.1f} MB)")
    print(f"Verify with: nucleus import --verify {result_path}")
    return 0


def handle_import_command(args) -> int:
    """Handler for `nucleus import`."""
    archive = Path(args.archive)
    if not archive.exists():
        print(f"Error: archive not found: {archive}")
        return 1

    # --verify mode: just verify, don't import
    if getattr(args, "verify", False):
        print(f"Verifying: {archive}")
        try:
            result = verify_export(archive)
        except Exception as e:
            print(f"Verify failed: {e}")
            return 1

        if result["valid"]:
            print(f"  VALID — {result['verified']}/{result['file_count']} files verified")
            if result["mismatches"]:
                print(f"  WARNING: {len(result['mismatches'])} SHA mismatches")
            return 0
        else:
            print(f"  INVALID — {len(result['mismatches'])} mismatches, {len(result['missing'])} missing")
            for m in result["mismatches"][:5]:
                print(f"    mismatch: {m['path']}")
            for m in result["missing"][:5]:
                print(f"    missing:  {m}")
            return 1

    # Resolve target brain
    if args.target:
        target = Path(args.target)
    else:
        from .runtime.common import get_brain_path
        try:
            target = get_brain_path()
        except ValueError as e:
            print(f"Error: {e}")
            return 1

    merge = not args.replace
    replace = args.replace

    if replace and not args.force:
        print("ERROR: --replace is destructive. Use --force to confirm.")
        return 1

    print(f"Importing:  {archive}")
    print(f"Target:     {target}")
    print(f"Mode:       {'replace' if replace else 'merge'}")
    if args.dry_run:
        print("Dry run:    yes (no files will be written)")

    try:
        result = import_brain(
            archive_path=archive,
            target_brain=target,
            merge=merge,
            replace=replace,
            dry_run=args.dry_run,
        )
    except Exception as e:
        print(f"Import failed: {e}")
        return 1

    print(f"\nImport complete:")
    print(f"  Imported:    {result['imported']}")
    print(f"  Skipped:     {result['skipped']}")
    print(f"  Overwritten: {result['overwritten']}")
    if result["errors"]:
        print(f"  Errors:      {len(result['errors'])}")
        for err in result["errors"][:10]:
            print(f"    {err}")
        return 1
    return 0


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _sha256_file(path: Path) -> str:
    """Compute SHA-256 of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _resolve_tenant_id_from_brain_path(brain_path: Path) -> Optional[str]:
    """Try to extract tenant_id from brain path structure.

    Brain paths follow: <NUCLEUS_BRAIN_ROOT>/<tenant_id>/.brain
    or are standalone .brain dirs (no tenant).
    """
    brain_path = Path(brain_path).resolve()
    if brain_path.name != ".brain":
        return None

    parent = brain_path.parent
    # Check if parent is under the tenants root
    brain_root = os.environ.get("NUCLEUS_BRAIN_ROOT")
    if brain_root:
        root = Path(brain_root).resolve()
        try:
            rel = parent.relative_to(root)
            return rel.name
        except ValueError:
            pass
    else:
        # Heuristic: ~/.nucleus/tenants/<id>/.brain
        tenants_dir = Path.home() / ".nucleus" / "tenants"
        try:
            rel = parent.relative_to(tenants_dir)
            return rel.name
        except ValueError:
            pass

    return None


def _read_manifest_from_archive(archive_path: Path) -> dict:
    """Read manifest.json from an export archive."""
    with tarfile.open(archive_path, "r:*") as tar:
        try:
            member = tar.getmember("manifest.json")
        except KeyError:
            raise ValueError(
                "Archive is missing manifest.json — not a valid nucleus export"
            )
        f = tar.extractfile(member)
        if f is None:
            raise ValueError("Could not read manifest.json from archive")
        return json.loads(f.read().decode("utf-8"))


def _validate_manifest(manifest: dict) -> None:
    """Validate manifest structure + schema version."""
    if "schema_version" not in manifest:
        raise ValueError("Manifest missing schema_version")
    if manifest["schema_version"] > EXPORT_SCHEMA_VERSION:
        raise ValueError(
            f"Manifest schema_version {manifest['schema_version']} is newer "
            f"than supported ({EXPORT_SCHEMA_VERSION}). Upgrade nucleus."
        )
    if "files" not in manifest or not isinstance(manifest["files"], list):
        raise ValueError("Manifest missing or invalid 'files' list")


def _nucleus_version() -> str:
    """Get the installed nucleus version."""
    try:
        from importlib.metadata import version
        return version("nucleus-mcp")
    except Exception:
        return "unknown"
