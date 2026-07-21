"""Cross-repo census — immutable-snapshot outside-PRODUCTION share (PRINCIPAL G1 crit 4).

Authority: docs/PRINCIPAL.md:47-49,75-85,149 (G1 criterion 4).
Immutable source: docs/PRINCIPAL.md@principal-v3.

The gated metric is ONE definition (PRINCIPAL.md:81)::

    outside_share = |units satisfying (b)∧(c)∧(d) ∧ (a)=outside|
                    / |all units satisfying (b)∧(c)∧(d)|

evaluated as a PURE FUNCTION of an immutable committed evidence snapshot
(raw gh-API + checks conclusions + relay-envelope hashes); an audit rerun
over the same snapshot is bit-identical.

A "unit" is a repo (an outside-PRODUCTION unit for the measurement window).
The four predicates (PRINCIPAL.md:75-80), each machine-read from the
snapshot (no human judgment):

  (a) outside vs substrate — the PARTITION label (versioned, hash-committed
      classification), NOT a qualifying conjunct.
  (b) On the spine — nucleus-initialized, has a ``.brain``.
  (c) Causally substrate-attributed (cross-vendor) — there exists an
      increment bound to ≥K cross-vendor relay envelopes by a STRUCTURED
      CAUSAL EDGE: ≥1 of the K envelopes carries an ``artifact_refs`` entry
      naming that increment's commit SHA / PR URL; the K envelopes span
      ≥2 genuine vendor surfaces (dedup per crit-3) under an anti-dominance
      guard (no single vendor surface supplies > X% of the K); AND the
      ≥2-vendor span is satisfied by envelopes BOUND to this increment
      (the ≥2 surfaces appear among envelopes sharing the referencing
      envelope's thread/conversation, OR ≥2 of the K carry this increment's
      ``artifact_refs`` across ≥2 surfaces). Co-occurrence alone — on either
      the edge or the breadth axis — does NOT qualify.
      **(v3 anchor precondition)** pre-anchor envelopes (forgeable
      ``from``/attribution — ``from_verified`` absent or False) are
      NON-QUALIFYING. The ``artifact_ref`` must be VENDOR-DERIVED
      (``artifact_ref_source == "vendor_derived"``); caller-input
      artifact_refs (``"caller_input"``) do NOT qualify — closes the
      causation gap PRINCIPAL.md:77 indicts.
  (d) Verifiable non-trivial build-output — the increment's own CI
      concludes ``success`` (enumerated; ``neutral/skipped/cancelled/
      failure/timed_out/action_required/stale`` = not-pass, FAIL-CLOSED)
      OR a committed clean-env build/resolve/import recipe exits 0; AND
      non-trivial by a coded predicate — touches ≥L non-generated source
      lines across ≥M files, OR adds/changes ≥1 test, OR is provably
      exercised by the (c) coordination.

Pass = BOTH (PRINCIPAL.md:83):
  (i) ``outside_share ≥ frozen_baseline + Δ`` with a minimum-denominator
      guard — if the qualifying denominator < D_min the share is
      INCONCLUSIVE → NOT-PASS (fail-closed);
  (ii) an absolute floor — ≥ F distinct outside-PRODUCTION units.

**(v3 anchor precondition)** the snapshot may be captured (baseline OR
measurement) ONLY after relay-sender AND engram-insert are merged and
flag-ON on every surface feeding the snapshot; pre-anchor envelopes are
non-qualifying; baseline and measurement windows MUST run under the SAME
anchor-flag regime, else NOT-PASS.

This module is the census — a pure reader of a snapshot directory. The
snapshot itself is captured by ``capture_snapshot`` (also here) which
freezes the live evidence (relay envelopes, repo registry, increment CI
conclusions, classification) into a committed, hash-stamped directory.
The census NEVER calls live git/gh — those calls happen at capture time,
so an audit rerun over the same snapshot is bit-identical.

Rerunnable from a clean checkout::

    # Capture a snapshot (live evidence → committed dir):
    python3 -m mcp_server_nucleus.runtime.cross_repo_census capture \\
        --brain-path .brain --out .brain/audits/cross_repo_census/snap_<date>

    # Run the census over a snapshot (pure function, bit-identical rerun):
    python3 -m mcp_server_nucleus.runtime.cross_repo_census census \\
        --snapshot .brain/audits/cross_repo_census/snap_<date> --json

Exit code 0 always (measurement instrument, not a gate). The JSON report
is the load-bearing artifact; commit it under
``.brain/audits/cross_repo_census/`` for tamper-evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

# Reuse the existing vendor-surface classifier (capture_census is the G1
# workstream-0 instrument; its classification table is the canonical map).
# Reuse the anchor-verified + timestamp helpers from seam_query (crit-3).
# Wiring existing modules rather than duplicating the tables/predicates.
from .capture_census import _classify_vendor_surface, _iter_relay_files
from .seam_query import _is_anchor_verified, _parse_created_at

# ── Schema / versioning ───────────────────────────────────────────────────────
INSTRUMENT = "cross_repo_census"
INSTRUMENT_VERSION = 1
SNAPSHOT_SCHEMA_VERSION = 1
PRINCIPAL_AUTHORITY = "docs/PRINCIPAL.md:47-49,75-85,149 (G1 criterion 4)"
PRINCIPAL_SOURCE_TAG = "principal-v3"

# ── CI conclusion enumeration (PRINCIPAL.md:78) ───────────────────────────────
# Only ``success`` is a pass. Every other state — including the GitHub
# ``neutral``/``skipped``/``cancelled``/``action_required``/``stale`` long
# tail — is NOT-PASS, fail-closed. This is the (d) build-output gate.
_CI_PASS = frozenset({"success"})
_CI_NOT_PASS = frozenset({
    "neutral", "skipped", "cancelled", "failure", "timed_out",
    "action_required", "stale", "pending", "null", "", None,
})

# ── artifact_ref provenance (PRINCIPAL.md:77 v3) ──────────────────────────────
# ``vendor_derived`` = the capture instrument stamped the ref from the
#   vendor worktree's git-reported SHA (the dispatch/relay tool schema
#   does NOT accept artifact_ref as caller input on the anchored path).
# ``caller_input`` = a caller typed the ref — NON-QUALIFYING under v3.
# ``absent`` = no artifact_ref on the envelope — non-qualifying for (c).
ARTIFACT_REF_VENDOR_DERIVED = "vendor_derived"
ARTIFACT_REF_CALLER_INPUT = "caller_input"
ARTIFACT_REF_ABSENT = "absent"


def _ci_passes(conclusion: Any) -> bool:
    """(d) build-output CI gate. Only ``success`` passes; fail-closed otherwise."""
    if isinstance(conclusion, str):
        c = conclusion.strip().lower()
    else:
        c = conclusion
    return c in _CI_PASS


def _is_vendor_derived_artifact_ref(envelope: Dict[str, Any]) -> bool:
    """v3 anchor precondition: the artifact_ref must be vendor-derived.

    The envelope carries ``artifact_ref_source`` (stamped by the capture
    instrument at snapshot time, derived from the dispatch tool's
    code-shape — NOT caller input). ``vendor_derived`` qualifies;
    ``caller_input`` and ``absent`` do NOT.
    """
    src = envelope.get("artifact_ref_source")
    return src == ARTIFACT_REF_VENDOR_DERIVED


def _envelope_artifact_refs(envelope: Dict[str, Any]) -> List[str]:
    """Extract the artifact_refs list from an envelope.

    The relay ``body`` is a JSON *string* carrying ``artifact_refs`` (see
    ``relay/core.py`` STRICT gate and ``vendor_dispatch._capture``). Tolerate
    both string-body and pre-parsed dict-body snapshots.
    """
    body = envelope.get("body")
    if isinstance(body, str):
        try:
            body = json.loads(body)
        except (ValueError, TypeError):
            return []
    if not isinstance(body, dict):
        return []
    refs = body.get("artifact_refs")
    if not isinstance(refs, list):
        return []
    return [str(r) for r in refs if isinstance(r, (str, int)) and str(r).strip()]


# ── Snapshot capture (live evidence → immutable committed dir) ────────────────
def _hash_json(obj: Any) -> str:
    """Stable SHA-256 of a JSON-serializable object (sorted keys, no whitespace)."""
    return "sha256:" + hashlib.sha256(
        json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


def _hash_file_tree(root: Path) -> str:
    """Stable SHA-256 over a directory tree (file names + contents, sorted)."""
    h = hashlib.sha256()
    files = sorted(p for p in root.rglob("*") if p.is_file())
    for p in files:
        rel = p.relative_to(root).as_posix()
        h.update(rel.encode("utf-8"))
        h.update(b"\0")
        try:
            h.update(p.read_bytes())
        except Exception:
            h.update(b"<unreadable>")
        h.update(b"\0")
    return "sha256:" + h.hexdigest()


def _read_classification(brain_path: Path) -> Dict[str, Any]:
    """Read or synthesize the substrate/outside classification.

    The classification is a versioned, hash-committed partition label set
    (PRINCIPAL.md:79, G0 item (3)). If a committed classification exists
    under ``.brain/audits/cross_repo_census/classification.json`` it is
    used verbatim; otherwise an empty classification is returned (the
    census will report 0 units — fail-closed, not a free pass).
    """
    cls_path = brain_path / "audits" / "cross_repo_census" / "classification.json"
    if cls_path.is_file():
        try:
            return json.loads(cls_path.read_text(encoding="utf-8"))
        except Exception:
            return {"repos": {}, "taxonomy_version": 0}
    return {"repos": {}, "taxonomy_version": 0}


def _detect_spine_repos(brain_path: Path) -> Dict[str, Dict[str, Any]]:
    """Detect repos on the spine (nucleus-initialized, have a ``.brain``).

    Walks the parent of ``brain_path`` for sibling dirs containing a
    ``.brain/`` subdir. Each is a candidate spine repo. The partition
    label (outside vs substrate) comes from the committed classification;
    a repo absent from the classification is reported as
    ``partition: "unclassified"`` and does NOT qualify (fail-closed).
    """
    repos: Dict[str, Dict[str, Any]] = {}
    parent = brain_path.parent
    if not parent.is_dir():
        return repos
    for d in sorted(parent.iterdir()):
        if not d.is_dir():
            continue
        if d.name.startswith("."):
            continue
        sub_brain = d / ".brain"
        if sub_brain.is_dir():
            repos[d.name] = {
                "repo_id": d.name,
                "path": str(d),
                "spine": True,
                "has_brain": True,
            }
    # The nucleus repo itself (the one whose .brain we're in) is on the spine
    # too — it is the substrate repo by default.
    if brain_path.parent.is_dir():
        nucleus_repo = brain_path.parent.name
        repos.setdefault(nucleus_repo, {
            "repo_id": nucleus_repo,
            "path": str(brain_path.parent),
            "spine": True,
            "has_brain": True,
        })
    return repos


def capture_snapshot(
    brain_path: Path,
    *,
    out_dir: Path,
    repo_increments: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    anchor_regime: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Freeze the live evidence into an immutable, hash-stamped snapshot dir.

    The snapshot contains:
      - ``snapshot_manifest.json`` — schema version, capture UTC, anchor
        regime (relay_sender_anchor / engram_anchor flags), classification
        hash, snapshot content hash, principal tag.
      - ``classification.json`` — versioned substrate/outside partition
        labels (copied from the committed classification).
      - ``relay/`` — relay envelope files frozen from ``.brain/relay``.
      - ``increments.jsonl`` — per-increment evidence (commit SHA, PR URL,
        CI conclusion, files touched, test changes, artifact_ref_source).
      - ``repos.json`` — spine repo registry with partition labels.

    ``repo_increments`` is the per-repo increment evidence dict. In a live
    capture this is gathered via ``gh`` API + checks conclusions; for tests
    it is supplied directly so the census is a pure function of the
    snapshot (no live network in the census read path).

    The snapshot content hash binds the WHOLE snapshot — any post-capture
    mutation (relabel, commit-churn, repo-mint) changes the hash and is
    detectable on rerun.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    relay_out = out_dir / "relay"
    relay_out.mkdir(exist_ok=True)

    # 1. Freeze relay envelopes.
    relay_root = brain_path / "relay"
    relay_count = 0
    if relay_root.is_dir():
        for bucket, f in _iter_relay_files(relay_root):
            bdir = relay_out / bucket
            bdir.mkdir(exist_ok=True)
            dest = bdir / f.name
            dest.write_bytes(f.read_bytes())
            relay_count += 1

    # 2. Classification (versioned, hash-committed partition labels).
    classification = _read_classification(brain_path)
    (out_dir / "classification.json").write_text(
        json.dumps(classification, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    classification_hash = _hash_json(classification)

    # 3. Spine repo registry + partition labels.
    spine_repos = _detect_spine_repos(brain_path)
    cls_repos = classification.get("repos", {}) if isinstance(classification, dict) else {}
    repos_registry: Dict[str, Any] = {}
    for repo_id, info in spine_repos.items():
        label = cls_repos.get(repo_id, {})
        partition = label.get("partition", "unclassified") if isinstance(label, dict) else "unclassified"
        repos_registry[repo_id] = {
            "repo_id": repo_id,
            "path": info["path"],
            "spine": True,
            "has_brain": True,
            "partition": partition,
        }
    (out_dir / "repos.json").write_text(
        json.dumps(repos_registry, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )

    # 4. Per-increment evidence.
    increments = repo_increments or {}
    inc_lines: List[str] = []
    for repo_id, incs in increments.items():
        for inc in incs:
            line = dict(inc)
            line.setdefault("repo_id", repo_id)
            inc_lines.append(json.dumps(line, sort_keys=True, default=str))
    (out_dir / "increments.jsonl").write_text(
        "\n".join(inc_lines) + ("\n" if inc_lines else ""),
        encoding="utf-8",
    )

    # 5. Anchor regime (v3 precondition: relay_sender + engram anchor flags
    #    must be ON; baseline + measurement must share the same regime).
    #    v3 also requires artifact_ref_vendor_derived (the dispatch tool schema
    #    MUST NOT accept artifact-ref as caller input).
    regime = {
        "relay_sender_anchor": bool(anchor_regime and anchor_regime.get("relay_sender_anchor")),
        "engram_anchor": bool(anchor_regime and anchor_regime.get("engram_anchor")),
        "artifact_ref_vendor_derived": bool(anchor_regime and anchor_regime.get("artifact_ref_vendor_derived")),
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
    }

    # 6. Snapshot content hash (binds relay + classification + repos + increments).
    content_hash = _hash_file_tree(out_dir)

    manifest = {
        "instrument": INSTRUMENT,
        "snapshot_schema_version": SNAPSHOT_SCHEMA_VERSION,
        "captured_at_utc": regime["captured_at_utc"],
        "principal_authority": PRINCIPAL_AUTHORITY,
        "principal_source_tag": PRINCIPAL_SOURCE_TAG,
        "anchor_regime": regime,
        "classification_hash": classification_hash,
        "snapshot_content_hash": content_hash,
        "relay_envelope_count": relay_count,
        "repo_count": len(repos_registry),
        "increment_count": len(inc_lines),
    }
    (out_dir / "snapshot_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    return manifest


# ── Census: pure function of a snapshot dir ───────────────────────────────────
@dataclass
class IncrementEvidence:
    """One increment's evidence row from ``increments.jsonl``."""
    repo_id: str
    commit_sha: str
    pr_url: str = ""
    ci_conclusion: str = ""
    files_touched: List[Dict[str, Any]] = field(default_factory=list)
    has_test_changes: bool = False
    artifact_ref_source: str = ARTIFACT_REF_ABSENT
    raw: Dict[str, Any] = field(default_factory=dict)


def _load_snapshot(snapshot_dir: Path) -> Dict[str, Any]:
    """Load a snapshot dir into in-memory structures (the census read path)."""
    snapshot_dir = Path(snapshot_dir)
    manifest_path = snapshot_dir / "snapshot_manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"snapshot manifest not found: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    classification = json.loads((snapshot_dir / "classification.json").read_text(encoding="utf-8"))
    repos_registry = json.loads((snapshot_dir / "repos.json").read_text(encoding="utf-8"))

    increments: List[IncrementEvidence] = []
    inc_path = snapshot_dir / "increments.jsonl"
    if inc_path.is_file():
        for line in inc_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except (ValueError, TypeError):
                continue
            increments.append(IncrementEvidence(
                repo_id=str(d.get("repo_id", "")),
                commit_sha=str(d.get("commit_sha", "")),
                pr_url=str(d.get("pr_url", "")),
                ci_conclusion=str(d.get("ci_conclusion", "")),
                files_touched=list(d.get("files_touched", []) or []),
                has_test_changes=bool(d.get("has_test_changes", False)),
                artifact_ref_source=str(d.get("artifact_ref_source", ARTIFACT_REF_ABSENT)),
                raw=d,
            ))

    # Load relay envelopes into memory (id → envelope + bucket + refs + surface).
    relay_root = snapshot_dir / "relay"
    envelopes: List[Dict[str, Any]] = []
    if relay_root.is_dir():
        for bucket, f in _iter_relay_files(relay_root):
            try:
                msg = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                continue
            refs = _envelope_artifact_refs(msg)
            surface = _classify_vendor_surface(bucket, msg)
            envelopes.append({
                "id": msg.get("id"),
                "bucket": bucket,
                "msg": msg,
                "refs": refs,
                "surface": surface,
                "from_verified": _is_anchor_verified(msg),
                "in_reply_to": msg.get("in_reply_to"),
                "created_at": _parse_created_at(msg.get("created_at")),
                "artifact_ref_source": msg.get("artifact_ref_source", ARTIFACT_REF_ABSENT),
            })

    return {
        "manifest": manifest,
        "classification": classification,
        "repos": repos_registry,
        "increments": increments,
        "envelopes": envelopes,
    }


def _non_generated_lines(files_touched: List[Dict[str, Any]]) -> Tuple[int, int]:
    """(d) non-triviality: count non-generated source lines + distinct files.

    A file is ``generated`` iff its ``generated`` flag is true (snapshot
    captures this from the increment's diff — vendored/auto-generated
    files are marked). Returns (non_gen_lines, non_gen_files).
    """
    non_gen_lines = 0
    non_gen_files: Set[str] = set()
    for f in files_touched:
        if not isinstance(f, dict):
            continue
        if f.get("generated"):
            continue
        path = str(f.get("path", ""))
        if not path:
            continue
        non_gen_files.add(path)
        try:
            non_gen_lines += int(f.get("lines_changed", 0) or 0)
        except (ValueError, TypeError):
            pass
    return non_gen_lines, len(non_gen_files)


def _predicate_d_non_trivial(inc: IncrementEvidence, *, L: int, M: int) -> Dict[str, Any]:
    """(d) non-triviality coded predicate (PRINCIPAL.md:78).

    Passes IFF ANY of:
      - touches ≥L non-generated source lines across ≥M files; OR
      - adds/changes ≥1 test (``has_test_changes``); OR
      - provably exercised by the (c) coordination (``coord_exercised`` flag
        on the increment — set when a bound envelope's body references the
        increment's commit in a coordination context).

    Fail-closed: empty/missing evidence → NOT non-trivial.
    """
    non_gen_lines, non_gen_files = _non_generated_lines(inc.files_touched)
    lines_files_pass = non_gen_lines >= L and non_gen_files >= M
    test_pass = bool(inc.has_test_changes)
    coord_exercised = bool(inc.raw.get("coord_exercised", False))
    non_trivial = lines_files_pass or test_pass or coord_exercised
    return {
        "non_generated_lines": non_gen_lines,
        "non_generated_files": non_gen_files,
        "lines_files_pass": lines_files_pass,
        "test_changes_pass": test_pass,
        "coord_exercised_pass": coord_exercised,
        "non_trivial": non_trivial,
    }


def _predicate_d_build_output(inc: IncrementEvidence) -> Dict[str, Any]:
    """(d) build-output gate (PRINCIPAL.md:78).

    Passes IFF:
      - CI conclusion == ``success`` (enumerated; everything else is
        not-pass, fail-closed); OR
      - a committed clean-env build/resolve/import recipe exited 0
        (``build_recipe_exit_zero`` flag on the increment).

    ``pending``/``null``/missing → NOT-PASS (fail-closed).
    """
    ci_pass = _ci_passes(inc.ci_conclusion)
    recipe_pass = bool(inc.raw.get("build_recipe_exit_zero", False))
    return {
        "ci_conclusion": inc.ci_conclusion,
        "ci_pass": ci_pass,
        "build_recipe_pass": recipe_pass,
        "build_output_pass": ci_pass or recipe_pass,
    }


def _increment_ref_set(inc: IncrementEvidence) -> Set[str]:
    """The set of refs that identify this increment (commit SHA + PR URL)."""
    refs: Set[str] = set()
    if inc.commit_sha:
        refs.add(inc.commit_sha)
        # Tolerate short SHAs — a 7-char prefix matches a 40-char full SHA.
        if len(inc.commit_sha) >= 7:
            refs.add(inc.commit_sha[:7])
    if inc.pr_url:
        refs.add(inc.pr_url)
    return refs


def _predicate_c(
    inc: IncrementEvidence,
    envelopes: List[Dict[str, Any]],
    *,
    K: int,
    X: float,
) -> Dict[str, Any]:
    """(c) causally substrate-attributed cross-vendor (PRINCIPAL.md:77).

    For this increment, find the envelopes BOUND to it (carrying one of its
    refs in ``artifact_refs``). Among the BOUND envelopes:
      - all must be anchor-verified (``from_verified=True``); pre-anchor
        envelopes are non-qualifying (v3 precondition);
      - the artifact_ref must be vendor-derived (``artifact_ref_source ==
        "vendor_derived"``); caller-input refs are non-qualifying (v3);
      - count distinct genuine vendor surfaces (excluding test_fixture /
        unknown / mixed);
      - anti-dominance: no single vendor surface supplies > X% of the K;
      - ≥K bound envelopes spanning ≥2 genuine vendor surfaces;
      - the ≥2-vendor span is satisfied by envelopes BOUND to THIS
        increment (the join: co-occurrence alone does not qualify).

    Returns the per-increment (c) verdict + the bound envelope details.
    """
    inc_refs = _increment_ref_set(inc)
    bound: List[Dict[str, Any]] = []
    for env in envelopes:
        if not inc_refs:
            break
        # Structured causal edge: envelope's artifact_refs intersects the
        # increment's ref set.
        if not (set(env["refs"]) & inc_refs):
            continue
        bound.append(env)

    # Filter: anchor-verified + vendor-derived artifact_ref (v3 preconditions).
    qualifying = [
        e for e in bound
        if e["from_verified"] and _is_vendor_derived_artifact_ref(e["msg"])
    ]
    non_qualifying = [e for e in bound if e not in qualifying]

    # Distinct genuine vendor surfaces among qualifying bound envelopes.
    surfaces: Counter = Counter()
    surface_to_envs: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for e in qualifying:
        s = e["surface"]
        if s in ("test_fixture", "unknown", "mixed"):
            continue
        surfaces[s] += 1
        surface_to_envs[s].append(e)
    genuine_surfaces = {s for s in surfaces if s not in ("test_fixture", "unknown", "mixed")}
    distinct_vendor_count = len(genuine_surfaces)

    K_bound = len(qualifying)
    min_two_vendors = distinct_vendor_count >= 2
    meets_K = K_bound >= K

    # Anti-dominance: no single vendor surface supplies > X% of the K bound.
    dominance_violation: Optional[str] = None
    if K_bound > 0:
        for s, n in surfaces.items():
            if s in ("test_fixture", "unknown", "mixed"):
                continue
            share = n / K_bound
            if share > X:
                dominance_violation = s
                break
    anti_dominance_pass = dominance_violation is None

    # The join: ≥2-vendor span satisfied by envelopes BOUND to this increment.
    # (Already enforced above — surfaces are counted only among bound+qualifying
    # envelopes. Co-windowed but unbound envelopes never enter ``surfaces``.)
    # Additional v3 clause: ≥2 of the K carry this increment's artifact_ref
    # across ≥2 surfaces, OR the ≥2 surfaces appear among envelopes sharing
    # the referencing envelope's thread/conversation. Since ``surfaces`` is
    # already bound-only, the thread clause is automatically satisfied when
    # distinct_vendor_count >= 2 from bound envelopes.
    join_pass = min_two_vendors  # bound-only span

    c_pass = bool(
        meets_K and min_two_vendors and anti_dominance_pass and join_pass
    )
    return {
        "increment_ref_set": sorted(inc_refs),
        "bound_envelope_count": len(bound),
        "qualifying_bound_count": K_bound,
        "non_qualifying_bound_count": len(non_qualifying),
        "distinct_vendor_surfaces": sorted(genuine_surfaces),
        "distinct_vendor_count": distinct_vendor_count,
        "meets_K": meets_K,
        "min_two_vendors": min_two_vendors,
        "anti_dominance_pass": anti_dominance_pass,
        "dominance_violation_surface": dominance_violation,
        "join_pass": join_pass,
        "by_surface": dict(surfaces.most_common()),
        "c_pass": c_pass,
        "_qualifying_envelopes": [
            {"id": e["id"], "surface": e["surface"], "bucket": e["bucket"]}
            for e in qualifying
        ],
    }


def _predicate_b(repo: Dict[str, Any]) -> Dict[str, Any]:
    """(b) on the spine — nucleus-initialized, has a ``.brain``."""
    spine = bool(repo.get("spine"))
    has_brain = bool(repo.get("has_brain"))
    return {"spine": spine, "has_brain": has_brain, "b_pass": spine and has_brain}


def _predicate_a(repo: Dict[str, Any]) -> Dict[str, Any]:
    """(a) outside vs substrate — the PARTITION label (NOT a qualifying conjunct)."""
    partition = str(repo.get("partition", "unclassified"))
    return {"partition": partition, "is_outside": partition == "outside"}


# ── Stringency check (anti degenerate-threshold) ──────────────────────────────
def _stringency_check(params: Dict[str, Any]) -> Dict[str, Any]:
    """Reject degenerate thresholds (PRINCIPAL.md:62 null/degenerate-threshold attack).

    A Δ=+1pp / F=1 / L=1 / M=1 freeze must FAIL the stringency check —
    these are arrange-low thresholds that let a trivial capture pass.
    The minimum stringency bars (mirroring the G0 derivation-rule floor):
      - Δ ≥ 0.02 (2 percentage points — anything smaller is noise);
      - F ≥ 2 (a single outside unit is not a "share");
      - L ≥ 5 (a 1-line stub is non-trivial only by the test/coord clauses);
      - M ≥ 1 (at least one file);
      - K ≥ 2 (crit-3 vendor floor; <2 envelopes is not "coordination");
      - X ≤ 0.60 (anti-dominance cap; >60% is single-vendor dominance).
    """
    fails: List[str] = []
    delta = float(params.get("delta", 0))
    F = int(params.get("absolute_floor", 0))
    L = int(params.get("min_lines", 0))
    M = int(params.get("min_files", 0))
    K = int(params.get("min_envelopes", 0))
    X = float(params.get("dominance_cap", 1.0))
    if delta < 0.02:
        fails.append(f"delta={delta} < 0.02 (degenerate threshold)")
    if F < 2:
        fails.append(f"absolute_floor={F} < 2 (single-unit is not a share)")
    if L < 5:
        fails.append(f"min_lines={L} < 5 (1-line stub threshold)")
    if M < 1:
        fails.append(f"min_files={M} < 1 (no file floor)")
    if K < 2:
        fails.append(f"min_envelopes={K} < 2 (crit-3 vendor floor)")
    if X > 0.60:
        fails.append(f"dominance_cap={X} > 0.60 (single-vendor dominance)")
    return {"stringent": not fails, "fails": fails}


# ── Default parameters (instantiated by the committed DERIVATION RULE) ────────
# These are the G1 crit-4 defaults. The chief re-runs with snapshot-derived
# values per the PRINCIPAL.md:64 derivation rule (Δ = max(2·stddev, 0.10);
# F = ceil(1.15 · baseline_outside_units); D_min = cap; K ≥ crit-3 floor;
# X ≤ 60%; L,M = p50 non-generated line/file size of the fleet's real merged
# increments). The defaults below are the FLOOR — the stringency check
# rejects anything below them.
DEFAULT_DELTA = 0.10           # Δ — minimum share delta over frozen baseline
DEFAULT_ABSOLUTE_FLOOR = 2     # F — minimum distinct outside-PRODUCTION units
DEFAULT_MIN_DENOMINATOR = 2    # D_min — minimum qualifying denominator
DEFAULT_MIN_ENVELOPES = 2      # K — minimum bound cross-vendor envelopes (≥ crit-3 floor)
DEFAULT_DOMINANCE_CAP = 0.60   # X — anti-dominance: no single vendor > 60% of K
DEFAULT_MIN_LINES = 5          # L — minimum non-generated source lines
DEFAULT_MIN_FILES = 1          # M — minimum non-generated files


def run_census(
    snapshot_dir: Path,
    *,
    frozen_baseline: float = 0.0,
    delta: float = DEFAULT_DELTA,
    absolute_floor: int = DEFAULT_ABSOLUTE_FLOOR,
    min_denominator: int = DEFAULT_MIN_DENOMINATOR,
    min_envelopes: int = DEFAULT_MIN_ENVELOPES,
    dominance_cap: float = DEFAULT_DOMINANCE_CAP,
    min_lines: int = DEFAULT_MIN_LINES,
    min_files: int = DEFAULT_MIN_FILES,
) -> Dict[str, Any]:
    """Run the cross-repo census over an immutable snapshot. Returns the report.

    The census is a PURE FUNCTION of the snapshot dir — no live git/gh calls,
    no filesystem mutation. An audit rerun over the same snapshot is
    bit-identical (same input + same params → same output).

    The gated verdict requires ALL of:
      (anchor) the snapshot's anchor regime has relay_sender_anchor AND
        engram_anchor both ON (v3 precondition; pre-anchor snapshots are
        non-qualifying → NOT-PASS);
      (stringency) the parameter set passes the degenerate-threshold check;
      (i) outside_share ≥ frozen_baseline + delta, with min-denominator
        guard (qualifying denominator < min_denominator → INCONCLUSIVE →
        NOT-PASS, fail-closed);
      (ii) ≥ absolute_floor distinct outside-PRODUCTION units.
    """
    snap = _load_snapshot(snapshot_dir)
    manifest = snap["manifest"]
    repos = snap["repos"]
    increments = snap["increments"]
    envelopes = snap["envelopes"]

    # v3 anchor precondition: snapshot must be captured under relay_sender +
    # engram anchor flags ON, AND artifact_ref_vendor_derived ON. Pre-anchor
    # snapshots are non-qualifying.
    regime = manifest.get("anchor_regime", {})
    anchor_regime_ok = bool(
        regime.get("relay_sender_anchor")
        and regime.get("engram_anchor")
        and regime.get("artifact_ref_vendor_derived")
    )

    params = {
        "frozen_baseline": frozen_baseline,
        "delta": delta,
        "absolute_floor": absolute_floor,
        "min_denominator": min_denominator,
        "min_envelopes": min_envelopes,
        "dominance_cap": dominance_cap,
        "min_lines": min_lines,
        "min_files": min_files,
    }
    stringency = _stringency_check(params)

    # Group increments by repo.
    increments_by_repo: Dict[str, List[IncrementEvidence]] = defaultdict(list)
    for inc in increments:
        if inc.repo_id:
            increments_by_repo[inc.repo_id].append(inc)

    # Evaluate each repo against (b), (c), (d). (a) is the partition label.
    per_repo: Dict[str, Any] = {}
    units_satisfying_bcd: List[str] = []
    outside_units: List[str] = []
    for repo_id, repo in repos.items():
        a = _predicate_a(repo)
        b = _predicate_b(repo)
        # (c)+(d): at least ONE increment on this repo passes both.
        repo_incs = increments_by_repo.get(repo_id, [])
        inc_verdicts: List[Dict[str, Any]] = []
        repo_c_pass = False
        repo_d_pass = False
        for inc in repo_incs:
            c = _predicate_c(inc, envelopes, K=min_envelopes, X=dominance_cap)
            d_build = _predicate_d_build_output(inc)
            d_nontriv = _predicate_d_non_trivial(inc, L=min_lines, M=min_files)
            d_pass = d_build["build_output_pass"] and d_nontriv["non_trivial"]
            inc_verdicts.append({
                "commit_sha": inc.commit_sha,
                "pr_url": inc.pr_url,
                "c": c,
                "d_build_output": d_build,
                "d_non_trivial": d_nontriv,
                "d_pass": d_pass,
                "cd_pass": c["c_pass"] and d_pass,
            })
            if c["c_pass"]:
                repo_c_pass = True
            if d_pass:
                repo_d_pass = True
        bcd_pass = bool(b["b_pass"] and repo_c_pass and repo_d_pass)
        per_repo[repo_id] = {
            "a_partition": a,
            "b_spine": b,
            "c_attribution": {
                "c_pass": repo_c_pass,
                "increments_evaluated": len(repo_incs),
                "increment_verdicts": inc_verdicts,
            },
            "d_build_output": {
                "d_pass": repo_d_pass,
            },
            "bcd_pass": bcd_pass,
            "is_outside_unit": bcd_pass and a["is_outside"],
        }
        if bcd_pass:
            units_satisfying_bcd.append(repo_id)
            if a["is_outside"]:
                outside_units.append(repo_id)

    denominator = len(units_satisfying_bcd)
    outside_count = len(outside_units)
    # Min-denominator guard: < D_min → INCONCLUSIVE → NOT-PASS (fail-closed).
    if denominator < min_denominator:
        outside_share: Optional[float] = None
        share_inconclusive = True
    else:
        outside_share = outside_count / denominator
        share_inconclusive = False

    # Pass = BOTH (i) and (ii), under anchor + stringency preconditions.
    criterion_i_pass = (
        not share_inconclusive
        and outside_share is not None
        and outside_share >= frozen_baseline + delta
    )
    criterion_ii_pass = outside_count >= absolute_floor

    preconditions_ok = anchor_regime_ok and stringency["stringent"]
    crit4_pass = bool(
        preconditions_ok and criterion_i_pass and criterion_ii_pass
    )

    fail_closed_reasons: List[str] = []
    if not anchor_regime_ok:
        fail_closed_reasons.append(
            "anchor regime not satisfied (relay_sender_anchor or engram_anchor OFF)"
        )
    if not stringency["stringent"]:
        fail_closed_reasons.append(f"degenerate thresholds: {stringency['fails']}")
    if share_inconclusive:
        fail_closed_reasons.append(
            f"qualifying denominator {denominator} < D_min {min_denominator} (inconclusive)"
        )
    elif not criterion_i_pass:
        fail_closed_reasons.append(
            f"outside_share {outside_share} < frozen_baseline+Δ ({frozen_baseline}+{delta})"
        )
    if not criterion_ii_pass:
        fail_closed_reasons.append(
            f"outside units {outside_count} < absolute floor {absolute_floor}"
        )

    return {
        "instrument": INSTRUMENT,
        "instrument_version": INSTRUMENT_VERSION,
        "principal_authority": PRINCIPAL_AUTHORITY,
        "principal_source_tag": PRINCIPAL_SOURCE_TAG,
        "computed_at_utc": datetime.now(timezone.utc).isoformat(),
        "snapshot_dir": str(snapshot_dir),
        "snapshot_manifest": {
            "captured_at_utc": manifest.get("captured_at_utc"),
            "snapshot_content_hash": manifest.get("snapshot_content_hash"),
            "classification_hash": manifest.get("classification_hash"),
            "relay_envelope_count": manifest.get("relay_envelope_count"),
            "repo_count": manifest.get("repo_count"),
            "increment_count": manifest.get("increment_count"),
        },
        "parameters": params,
        "anchor_regime": regime,
        "anchor_regime_ok": anchor_regime_ok,
        "stringency": stringency,
        "preconditions_ok": preconditions_ok,
        "metric": {
            "denominator": denominator,
            "outside_count": outside_count,
            "outside_share": outside_share,
            "share_inconclusive": share_inconclusive,
            "frozen_baseline": frozen_baseline,
            "threshold": frozen_baseline + delta,
        },
        "per_repo": per_repo,
        "units_satisfying_bcd": sorted(units_satisfying_bcd),
        "outside_units": sorted(outside_units),
        "verdict": {
            "crit4_pass": crit4_pass,
            "criterion_i_share_delta": criterion_i_pass,
            "criterion_ii_absolute_floor": criterion_ii_pass,
            "fail_closed_reasons": fail_closed_reasons or ["all criteria met"],
        },
    }


# ── Anti-gaming self-test corpus ──────────────────────────────────────────────
# PRINCIPAL.md:62 G0 item (5) (applied to G1 crit-4): the census ships an
# anti-gaming self-test whose corpus is validated as SUFFICIENT — each attack
# is provably unable to move the gated PASS. The corpus lives in
# tests/test_cross_repo_census.py; the registry below is the census-side
# declaration of the expected corpus so the chief can audit coverage.
ANTI_GAMING_CORPUS: Tuple[str, ...] = (
    "relabel",                       # swap partition label outside↔substrate
    "commit_churn",                  # fabricated increments, no real CI/build
    "repo_mint",                     # throwaway repo, no spine
    "genuine_traffic_repoint",       # real envelopes routed at throwaway repo, no artifact_ref
    "coordination_theater",          # envelopes present but unbound (no artifact_ref)
    "unbound_breadth",               # ≥2-vendor span from co-windowed unbound envelopes
    "baseline_suppression",          # CI/cross-vendor routing withheld during capture
    "denominator_suppression",       # hash-binding withheld on genuine increments
    "single_vendor_dominance",       # one vendor surface > X% of K
    "null_degenerate_threshold",     # Δ=+1pp / F=1 / L=1 / M=1 freeze
    "pre_anchor_snapshot",           # v3: snapshot captured before anchor flags ON
    "caller_input_artifact_ref",     # v3: caller-typed artifact_ref masquerading as causation
)


def anti_gaming_corpus_coverage() -> Dict[str, Any]:
    """Declare the anti-gaming corpus the census is hardened against.

    The chief audits this against ``tests/test_cross_repo_census.py`` to
    confirm every attack has a passing regression test (PRINCIPAL.md:62
    "corpus validated as SUFFICIENT"). A missing attack = BLOCKING.
    """
    return {
        "instrument": INSTRUMENT,
        "corpus_version": 1,
        "principal_authority": PRINCIPAL_AUTHORITY,
        "attacks": [
            {"name": a, "expected_outcome": "NOT-PASS (fail-closed)"}
            for a in ANTI_GAMING_CORPUS
        ],
        "coverage_note": (
            "Every attack in this corpus MUST have a passing regression "
            "test in tests/test_cross_repo_census.py. The chief audits "
            "coverage before G1 crit-4 may pass."
        ),
    }


# ── CLI ───────────────────────────────────────────────────────────────────────
def _format_human(report: Dict[str, Any]) -> str:
    v = report["verdict"]
    m = report["metric"]
    p = report["parameters"]
    lines: List[str] = []
    lines.append(f"=== Cross-Repo Census @ {report['computed_at_utc']} ===")
    lines.append(f"authority: {report['principal_authority']}")
    lines.append(f"snapshot: {report['snapshot_dir']}")
    lines.append(f"snapshot_hash: {report['snapshot_manifest']['snapshot_content_hash']}")
    lines.append("")
    lines.append("PRECONDITIONS:")
    lines.append(f"  anchor_regime_ok: {report['anchor_regime_ok']}  "
                 f"(relay_sender={report['anchor_regime'].get('relay_sender_anchor')}, "
                 f"engram={report['anchor_regime'].get('engram_anchor')})")
    lines.append(f"  stringency_ok:    {report['stringency']['stringent']}")
    if report["stringency"]["fails"]:
        lines.append(f"    fails: {report['stringency']['fails']}")
    lines.append("")
    lines.append("PARAMETERS:")
    lines.append(f"  frozen_baseline={p['frozen_baseline']}  delta={p['delta']}  "
                 f"abs_floor={p['absolute_floor']}  D_min={p['min_denominator']}")
    lines.append(f"  K={p['min_envelopes']}  X={p['dominance_cap']}  "
                 f"L={p['min_lines']}  M={p['min_files']}")
    lines.append("")
    lines.append("METRIC:")
    lines.append(f"  denominator (b∧c∧d): {m['denominator']}")
    lines.append(f"  outside units:       {m['outside_count']}")
    if m["share_inconclusive"]:
        lines.append(f"  outside_share:       INCONCLUSIVE (denominator < D_min)")
    else:
        lines.append(f"  outside_share:       {m['outside_share']:.4f}  "
                     f"(threshold {m['threshold']:.4f})")
    lines.append("")
    lines.append("PER-REPO:")
    for repo_id, r in sorted(report["per_repo"].items()):
        bcd = "✓" if r["bcd_pass"] else "✗"
        outside = "outside" if r["a_partition"]["is_outside"] else r["a_partition"]["partition"]
        lines.append(f"  {bcd} {repo_id:30s} partition={outside:12s} "
                     f"b={r['b_spine']['b_pass']} c={r['c_attribution']['c_pass']} "
                     f"d={r['d_build_output']['d_pass']}")
    lines.append("")
    lines.append("VERDICT:")
    lines.append(f"  crit4_pass: {v['crit4_pass']}")
    lines.append(f"  (i) share+delta:  {v['criterion_i_share_delta']}")
    lines.append(f"  (ii) abs floor:   {v['criterion_ii_absolute_floor']}")
    for r in v["fail_closed_reasons"]:
        lines.append(f"  reason: {r}")
    return "\n".join(lines)


def _cmd_capture(args: argparse.Namespace) -> int:
    brain = Path(args.brain_path)
    if not brain.is_dir():
        print(f"ERROR: brain path not found: {brain}", file=sys.stderr)
        return 2
    manifest = capture_snapshot(
        brain,
        out_dir=Path(args.out),
        anchor_regime={
            "relay_sender_anchor": os.environ.get("NUCLEUS_RELAY_SENDER_ANCHOR", "").strip().lower() in {"1", "true", "on", "yes"},
            "engram_anchor": os.environ.get("NUCLEUS_ENGRAM_ANCHOR", "").strip().lower() in {"1", "true", "on", "yes"},
        },
    )
    print(json.dumps(manifest, indent=2, default=str))
    return 0


def _cmd_census(args: argparse.Namespace) -> int:
    snap = Path(args.snapshot)
    if not snap.is_dir():
        print(f"ERROR: snapshot dir not found: {snap}", file=sys.stderr)
        return 2
    report = run_census(
        snap,
        frozen_baseline=args.frozen_baseline,
        delta=args.delta,
        absolute_floor=args.absolute_floor,
        min_denominator=args.min_denominator,
        min_envelopes=args.min_envelopes,
        dominance_cap=args.dominance_cap,
        min_lines=args.min_lines,
        min_files=args.min_files,
    )
    if args.save:
        out = Path(args.save)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
        print(f"report saved: {out}", file=sys.stderr)
    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        print(_format_human(report))
    return 0


def _cmd_corpus(args: argparse.Namespace) -> int:
    print(json.dumps(anti_gaming_corpus_coverage(), indent=2, default=str))
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)

    p_cap = sub.add_parser("capture", help="Freeze live evidence into an immutable snapshot dir")
    p_cap.add_argument("--brain-path", default=".brain")
    p_cap.add_argument("--out", required=True, help="Snapshot output dir")
    p_cap.set_defaults(func=_cmd_capture)

    p_cen = sub.add_parser("census", help="Run the census over an immutable snapshot (pure function)")
    p_cen.add_argument("--snapshot", required=True, help="Snapshot dir (from `capture`)")
    p_cen.add_argument("--json", action="store_true")
    p_cen.add_argument("--save", default=None)
    p_cen.add_argument("--frozen-baseline", type=float, default=0.0)
    p_cen.add_argument("--delta", type=float, default=DEFAULT_DELTA)
    p_cen.add_argument("--absolute-floor", type=int, default=DEFAULT_ABSOLUTE_FLOOR)
    p_cen.add_argument("--min-denominator", type=int, default=DEFAULT_MIN_DENOMINATOR)
    p_cen.add_argument("--min-envelopes", type=int, default=DEFAULT_MIN_ENVELOPES)
    p_cen.add_argument("--dominance-cap", type=float, default=DEFAULT_DOMINANCE_CAP)
    p_cen.add_argument("--min-lines", type=int, default=DEFAULT_MIN_LINES)
    p_cen.add_argument("--min-files", type=int, default=DEFAULT_MIN_FILES)
    p_cen.set_defaults(func=_cmd_census)

    p_cor = sub.add_parser("corpus", help="Print the anti-gaming corpus coverage declaration")
    p_cor.set_defaults(func=_cmd_corpus)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
