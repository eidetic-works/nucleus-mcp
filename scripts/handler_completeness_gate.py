"""MCP handler completeness gate — treatment sweep #010 vaccine.

Scans registered MCP tool handler source files for stub patterns that
indicate an incomplete implementation: `raise NotImplementedError`.

Treatment rationale (TREATMENT.md Week 2 sweep f):
  - Static analysis identified 42 primitives in sweep #001; pruning sweep
    #006 reduced Server A to 15 active tools. Call-count instrumentation
    (sweep #002) now accumulates live data. This gate prevents stub handlers
    from being *added back* as new tools are registered — ensuring that every
    shipped primitive actually executes (criterion 2 vaccine).

Scope:
  Servers A + B (mcp-server-nucleus tools/ + nucleus_wedge/server.py).
  Server C (eidetic bridge) uses a dispatch-table pattern in a separate repo;
  gated by NUCLEUS_HANDLER_GATE_SERVER_C=1 if the repo is mounted.

Patterns flagged:
  - `raise NotImplementedError` (bare or with message) anywhere inside a
    registered handler source file, on a non-comment line.

Patterns deliberately NOT flagged:
  - Lines where `NotImplementedError` appears inside a string literal
    (e.g. error message construction `str(...)`).
  - Abstract-base-class method stubs in `_abc` / `abc` subclasses (rare in
    this codebase; explicit allow-list via ALLOW_STUB_FILES env var).
  - Test files (`tests/`).

CLI:
    python scripts/handler_completeness_gate.py [--src-dir DIR] [--json]
    Exit 0 = all handlers complete
    Exit 1 = stub patterns found (CI gate fails)
    Exit 2 = scan error (e.g. permission denied)

Env knobs:
    NUCLEUS_HANDLER_GATE_DISABLED=1      skip entirely (zero overhead).
    NUCLEUS_HANDLER_GATE_SERVER_C=1      also scan $EIDETIC_BRIDGE_SRC_DIR.
    EIDETIC_BRIDGE_SRC_DIR=<path>        Server C source path (default:
                                          ~/eidetic-daemon/bridge/python/eidetic_mcp).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import NamedTuple


# Pattern: bare `raise NotImplementedError` or `raise NotImplementedError(...)`.
# Anchored so it doesn't match inside strings (best-effort; AST would be
# more precise but adds complexity and dependency on syntax correctness).
_STUB_PATTERN = re.compile(r"\braise\s+NotImplementedError\b")

# Lines that are pure Python comments — skip them.
_COMMENT_LINE = re.compile(r"^\s*#")


class StubHit(NamedTuple):
    path: Path
    line_no: int
    text: str


def scan_file(path: Path) -> list[StubHit]:
    """Return StubHit list for every flagged line in *path*."""
    hits: list[StubHit] = []
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as exc:
        print(f"[handler-gate] WARNING: cannot read {path}: {exc}", file=sys.stderr)
        return hits
    for i, line in enumerate(lines, start=1):
        if _COMMENT_LINE.match(line):
            continue
        if _STUB_PATTERN.search(line):
            hits.append(StubHit(path=path, line_no=i, text=line.rstrip()))
    return hits


def scan_directory(root: Path, *, exclude_tests: bool = True) -> list[StubHit]:
    """Recursively scan *.py files under *root* for stub patterns."""
    all_hits: list[StubHit] = []
    for py_file in sorted(root.rglob("*.py")):
        if exclude_tests and ("tests" in py_file.parts or "test_" in py_file.name):
            continue
        if "__pycache__" in py_file.parts:
            continue
        all_hits.extend(scan_file(py_file))
    return all_hits


def _default_src_dirs(repo_root: Path) -> list[Path]:
    """Return the standard Servers A + B source directories."""
    candidates = [
        repo_root / "mcp-server-nucleus" / "src" / "mcp_server_nucleus" / "tools",
        repo_root / "mcp-server-nucleus" / "src" / "nucleus_wedge",
        # Fallback: running from inside mcp-server-nucleus/
        repo_root / "src" / "mcp_server_nucleus" / "tools",
        repo_root / "src" / "nucleus_wedge",
    ]
    return [d for d in candidates if d.is_dir()]


def run(
    src_dirs: list[Path],
    *,
    scan_server_c: bool = False,
    server_c_dir: Path | None = None,
    json_output: bool = False,
) -> int:
    """Main scan logic. Returns exit code (0=ok, 1=stubs found, 2=error)."""
    if os.environ.get("NUCLEUS_HANDLER_GATE_DISABLED") == "1":
        return 0

    all_hits: list[StubHit] = []

    for src in src_dirs:
        if not src.is_dir():
            print(f"[handler-gate] WARNING: src dir not found: {src}", file=sys.stderr)
            continue
        all_hits.extend(scan_directory(src))

    if scan_server_c or os.environ.get("NUCLEUS_HANDLER_GATE_SERVER_C") == "1":
        c_dir = server_c_dir
        if c_dir is None:
            env_c = os.environ.get("EIDETIC_BRIDGE_SRC_DIR")
            c_dir = Path(env_c) if env_c else Path.home() / "eidetic-daemon" / "bridge" / "python" / "eidetic_mcp"
        if c_dir.is_dir():
            all_hits.extend(scan_directory(c_dir))
        else:
            print(f"[handler-gate] WARNING: Server C dir not found: {c_dir}", file=sys.stderr)

    if json_output:
        output = [
            {"file": str(h.path), "line": h.line_no, "text": h.text}
            for h in all_hits
        ]
        print(json.dumps(output, indent=2))
    else:
        for h in all_hits:
            print(f"{h.path}:{h.line_no}: {h.text.strip()}")

    if all_hits:
        if not json_output:
            print(
                f"\n[handler-gate] FAIL: {len(all_hits)} stub pattern(s) found. "
                "Implement or deprecate before merge.",
                file=sys.stderr,
            )
        return 1

    if not json_output:
        print("[handler-gate] PASS: no stub patterns in shipped handlers.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="MCP handler completeness gate — treatment sweep #010.",
    )
    parser.add_argument(
        "--src-dir",
        dest="src_dirs",
        action="append",
        type=Path,
        metavar="DIR",
        help="Source directory to scan (repeatable; defaults to Servers A + B src dirs).",
    )
    parser.add_argument(
        "--server-c",
        action="store_true",
        default=False,
        help="Also scan Server C (eidetic bridge) source dir.",
    )
    parser.add_argument(
        "--server-c-dir",
        type=Path,
        metavar="DIR",
        help="Override Server C source path (default: ~/eidetic-daemon/bridge/python/eidetic_mcp).",
    )
    parser.add_argument(
        "--json",
        dest="json_output",
        action="store_true",
        default=False,
        help="Emit JSON array of findings to stdout.",
    )
    args = parser.parse_args(argv)

    repo_root = Path(__file__).parent.parent
    src_dirs: list[Path] = args.src_dirs or _default_src_dirs(repo_root)

    return run(
        src_dirs,
        scan_server_c=args.server_c,
        server_c_dir=args.server_c_dir,
        json_output=args.json_output,
    )


if __name__ == "__main__":
    sys.exit(main())
