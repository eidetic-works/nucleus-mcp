#!/usr/bin/env python3
"""G0 census — PRINCIPAL v2 crit-4 (hardened, anti-gaming).

Implements the G1 exit-criterion-4 "Anti-circularity as substrate-attributed
production delta" (PRINCIPAL v2, tag ``principal-v2``). A repo is a qualifying
**outside-PRODUCTION unit** for a window IFF, each fact machine-read from a
committed snapshot (no human judgment):

  (b) ON THE SPINE — nucleus-initialized, has a ``.brain``.
  (c) CAUSALLY SUBSTRATE-ATTRIBUTED (cross-vendor): there exists an increment
      bound to >=K cross-vendor relay envelopes by a STRUCTURED CAUSAL EDGE —
      each counted envelope's ``body.dispatch_sig`` HMAC-VERIFIES with the
      machine key over its own body (an UN-FORGEABLE causal edge; unsigned or
      invalid envelopes are invisible to (c)); >=1 verified envelope's
      ``body.artifact_refs`` names the increment's PR/commit hash; the counted K
      envelopes span >=2 genuine vendor surfaces (dedup per crit-3, and deduped
      on ``dispatch_sig`` so verbatim replay cannot inflate K) under an
      ANTI-DOMINANCE cap (no single surface > X% of K); and the >=2-vendor span
      is satisfied by envelopes bound to the increment — either >=2 of the
      ref-carriers span >=2 surfaces (Path A), or the >=2 surfaces appear among
      envelopes sharing a ref-carrier's thread (Path B). The causal edge and the
      cross-vendor breadth are NOT disjoint envelope sets.
  (d) VERIFIABLE NON-TRIVIAL BUILD-OUTPUT: the increment's CI conclusion is
      ``success`` (every other enum value fails closed) OR a committed clean-env
      recipe exits 0; AND it is non-trivial by a coded predicate (>=L non-gen
      source lines across >=M files, OR >=1 test file). The old "provably
      exercised by the (c) coordination" OR-clause is REMOVED — no
      machine-checkable signal distinguishes "exercised by" from "named by"
      coordination today, so an empty diff must fail (d) even with genuine
      signed coordination.
  (a) outside vs substrate is the PARTITION label (versioned, hash-committed),
      NOT a qualifying conjunct.

SINGLE METRIC::

    outside_share = |units satisfying (b)^(c)^(d) ^ (a)=outside|
                    / |all units satisfying (b)^(c)^(d)|

evaluated as a PURE FUNCTION of an immutable committed evidence snapshot. An
audit rerun over the same snapshot is bit-identical.

PASS = BOTH:
  (i)  outside_share >= frozen_baseline + Delta, with a MINIMUM-DENOMINATOR
       guard (denominator < D_min => inconclusive => NOT-PASS, fail-closed); AND
  (ii) an ABSOLUTE FLOOR of >= F distinct outside-PRODUCTION units.

Architecture: capture is impure (reads relay FS + gh-API); scoring is a pure
function over the captured snapshot. The anti-gaming self-test
(tests/census/test_census_selftest.py) exercises the scorer with synthetic
snapshots and proves each attack vector cannot move the gated PASS.

This module lives under scripts/ + config/ (NOT src/) so the core/periphery
boundary checker is untouched.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import math
import os
import re
import statistics
import subprocess
import sys
from collections import Counter, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SCHEMA_VERSION = "census-v2"

# ── Derivation stringency floors (committed constants) ──────────────────────
# The DERIVATION RULE instantiates {Delta,F,L,M,K,X,D_min} from the measured
# baseline. These floors make an arranged-low / degenerate-threshold freeze
# self-test-detectable (crit-4 attack 9). A freeze whose derived params fall
# below any floor is DEGENERATE and cannot produce a PASS.
DELTA_FLOOR = 0.10       # Delta = max(2*stddev, 0.10)
F_FLOOR = 2              # absolute-floor F must be >= 2 (F=1 is degenerate)
L_FLOOR = 10             # p50 non-gen lines must be >= 10 (L=1 is degenerate)
M_FLOOR = 2              # p50 non-gen files must be >= 2 (M=1 is degenerate)
K_FLOOR = 2              # K >= crit-3 vendor floor
X_CEIL = 0.60            # anti-dominance cap: no single surface > 60% of K
D_MIN_FLOOR = 3          # minimum denominator to trust a ratio (per-window cap)

CRIT3_VENDOR_FLOOR = 2   # >=2 genuine vendor surfaces (crit-3)

# Relay-id regex mirrors runtime/relay/core.py:_is_shipped_artifact — a ref that
# matches a self-referencing relay id is NOT a shipped artifact.
_RELAY_ID_RE = re.compile(r"^relay_\d{8}_\d{6}_[a-f0-9]{8}")

# ── Vendor-surface map (crit-3 dedup) ───────────────────────────────────────
# from_provider is UNRELIABLE for cross-vendor captures: providers.yaml has no
# agy/devin prefix, so coerce_to_tuple stamps from_provider="unknown". The
# authoritative surface identity is VENDOR_SPECS (runtime/vendor_dispatch.py) +
# the canonical relay roles. We freeze the sender->surface FAMILY map into the
# snapshot at capture so scoring stays a pure function. "unknown" surfaces are
# NOT genuine and never count toward the >=2-vendor span.
_FROZEN_VENDOR_SURFACES: Dict[str, str] = {
    # cross-vendor CLI surfaces (mirror VENDOR_SPECS: vendor -> surface family)
    "agy": "antigravity",         # VendorSpec agy  -> model gemini, surface antigravity
    "devin": "devin",             # VendorSpec devin-> model glm,    surface devin
    "antigravity": "antigravity",
    "glm": "devin",
    # anthropic surface — main and peer are ONE genuine vendor surface (dedup)
    "claude_code": "anthropic",
    "claude_code_main": "anthropic",
    "claude_code_peer": "anthropic",
    "cowork": "anthropic",
    "claude_code_operator_assistant": "anthropic",
    # other genuine surfaces
    "cursor": "cursor",
    "gemini": "google_gemini",
    "gemini_cli": "google_gemini",
    "windsurf": "windsurf",
}


def _load_vendor_specs_surfaces() -> Dict[str, str]:
    """Best-effort sync with the live VENDOR_SPECS at capture time.

    Falls back to the frozen map when the src package is not importable (keeps
    the scorer/self-test fully offline — nothing under src is required)."""
    surfaces = dict(_FROZEN_VENDOR_SURFACES)
    try:  # soft import: capture-time only, never load-bearing for scoring
        from mcp_server_nucleus.runtime.vendor_dispatch import VENDOR_SPECS  # type: ignore

        for name, spec in VENDOR_SPECS.items():
            surface = None
            for tag in getattr(spec, "engram_tags", ()):  # ("vendor:x","surface:y")
                if str(tag).startswith("surface:"):
                    surface = str(tag).split(":", 1)[1]
            if surface:
                surfaces[name] = surface
                surfaces[spec.sender] = surface
    except Exception:
        pass
    return surfaces


# ── Canonicalization + hashing (relabel / consistency binding) ──────────────

def _canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def taxonomy_partition_hash(taxonomy: Dict[str, Any]) -> str:
    """sha256 over the canonicalized taxonomy BODY (schema_version, org_logins,
    partition map, default_partition) — EXCLUDING the recorded hashes. A relabel
    without a version bump changes this hash: tamper-evident, no identity leak."""
    body = {
        "schema_version": taxonomy.get("schema_version"),
        "org_logins": sorted(taxonomy.get("org_logins", [])),
        "partition": {k: taxonomy["partition"][k] for k in sorted(taxonomy.get("partition", {}))},
        "default_partition": taxonomy.get("default_partition", "substrate"),
    }
    return _sha256_hex(_canonical_json(body))


def taxonomy_public_hash(taxonomy: Dict[str, Any], operator_identities: List[str]) -> str:
    """PUBLIC consistency-binding hash of the TRIPLE {taxonomy, org-login set,
    operator identity set}. Operator identities are IDENTITY-FENCED — supplied
    out-of-band and NEVER committed in plaintext (memory HARD RULES legal-name /
    extended-id-strings). Only this hash is committed; it detects any change to
    the triple without leaking identities and without attesting completeness."""
    triple = {
        "partition_hash": taxonomy_partition_hash(taxonomy),
        "org_logins": sorted(taxonomy.get("org_logins", [])),
        "operator_identities": sorted(operator_identities),
    }
    return _sha256_hex(_canonical_json(triple))


# ── Cross-vendor dispatch signature verification (crit-4 v2.1) ───────────────
# A cross-vendor envelope counts as a genuine surface for clause (c) ONLY if its
# body.dispatch_sig HMAC-verifies, with the scanned brain's machine key, over
# that envelope's OWN body fields. This is verified with STDLIB ONLY (no src
# import) so the scorer/self-test stay fully offline-pure; a parity self-test
# asserts this recomputation agrees byte-for-byte with the src-side signer
# (SignatureGuard.sign_vendor_dispatch). At CAPTURE (the impure step) each
# envelope is stamped vendor_sig=valid|invalid|absent; scoring is then a pure
# function of the stamped snapshot.

def _vendor_dispatch_message(vendor: Any, model: Any, prompt_digest: Any,
                             artifact_refs: List[Any], result_sha256: Any,
                             status: Any, ts: Any) -> str:
    """Canonical UTF-8 signed byte-string. MUST match SignatureGuard's
    ``_vendor_dispatch_message`` byte-for-byte. Compact-JSON-array
    canonicalization (not pipe-joins) makes delimiter injection impossible."""
    return "v2:vdisp:" + json.dumps(
        [vendor, model, prompt_digest, sorted(str(r) for r in artifact_refs),
         result_sha256, status, ts],
        separators=(",", ":"), ensure_ascii=False,
    )


def _dispatch_hmac(key: bytes, message: str) -> str:
    """HMAC-SHA256 hex, 32-char truncation (128-bit) — matches _compute_hmac."""
    return hmac.new(key, message.encode("utf-8"), hashlib.sha256).hexdigest()[:32]


def read_brain_key(brain: Path) -> Optional[bytes]:
    """Read the raw 32-byte machine key for a scanned brain (owner-only 0600
    ``<brain>/secrets/.ipc_secret``). Absent => None => every envelope in that
    brain stamps ``vendor_sig=absent`` => fail-closed (the honest state for a
    brain that never ran a real dispatch)."""
    key_file = brain / "secrets" / ".ipc_secret"
    try:
        if key_file.is_file():
            return key_file.read_bytes()
    except OSError:
        pass
    return None


def verify_dispatch_sig(body: Dict[str, Any], key: Optional[bytes]) -> str:
    """Return ``valid`` | ``invalid`` | ``absent`` for a body's dispatch_sig,
    recomputed over the body's OWN fields and constant-time-compared. A real
    signature lifted onto different artifact_refs / result / status / ts
    recomputes to a different HMAC and returns ``invalid`` — that is the binding
    property. ``absent`` iff there is no signature or no key on the brain."""
    sig = body.get("dispatch_sig")
    if not sig or key is None:
        return "absent"
    try:
        message = _vendor_dispatch_message(
            body.get("vendor"), body.get("model"), body.get("prompt_digest"),
            list(body.get("artifact_refs") or []), body.get("result_sha256"),
            body.get("status"), body.get("ts"),
        )
        expected = _dispatch_hmac(key, message)
        return "valid" if hmac.compare_digest(expected, str(sig)) else "invalid"
    except Exception:
        return "invalid"


def _valid_signed_envelopes(envelopes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Clause-(c) uniform pre-filter: keep ONLY ``vendor_sig=='valid'``
    envelopes, deduped by ``dispatch_sig``. Unsigned/invalid envelopes are
    invisible to (c) — they cannot be ref-carriers, cannot anchor or join Path-B
    threads, and never count toward K or the >=2-surface span. This also closes
    the adjacent holes: a hand-written ``from: cursor`` / ``from: windsurf`` file
    no longer manufactures a genuine surface, and a forged unsigned carrier can no
    longer anchor a thread of real envelopes into Path B. Verbatim whole-body
    replay shares its ``dispatch_sig`` and is deduped to one — cosmetic
    K-inflation is removed."""
    seen: set = set()
    out: List[Dict[str, Any]] = []
    for e in envelopes:
        if e.get("vendor_sig") != "valid":
            continue
        sig = e.get("dispatch_sig")
        if sig is not None:
            if sig in seen:
                continue
            seen.add(sig)
        out.append(e)
    return out


# ── Ref / surface / path predicates ─────────────────────────────────────────

def is_shipped_artifact(ref: Any) -> bool:
    """True iff ``ref`` names a real commit SHA / PR / path (not a relay id).
    Mirrors runtime/relay/core.py:_is_shipped_artifact byte-for-byte."""
    head = str(ref).strip().split(" ", 1)[0].split("(", 1)[0].strip()
    return bool(head) and not _RELAY_ID_RE.match(head)


def _norm_ref(ref: Any) -> str:
    return str(ref).strip().split(" ", 1)[0].split("(", 1)[0].strip()


def shipped_refs(envelope: Dict[str, Any]) -> List[str]:
    return [_norm_ref(r) for r in (envelope.get("artifact_refs") or []) if is_shipped_artifact(r)]


def envelope_surface(envelope: Dict[str, Any], surfaces: Dict[str, str]) -> str:
    """Resolve an envelope to its genuine vendor surface family via the frozen
    sender->surface map. Unrecognized senders -> 'unknown' (never genuine)."""
    # an envelope may carry a pre-resolved surface (snapshot capture); trust it.
    pre = envelope.get("surface")
    if pre:
        return str(pre)
    sender = str(envelope.get("sender") or envelope.get("from") or "").strip().lower()
    return surfaces.get(sender, "unknown")


def is_generated_path(path: str) -> bool:
    p = str(path).lower()
    if not p:
        return True
    lockfiles = (
        "package-lock.json", "yarn.lock", "poetry.lock", "cargo.lock",
        "pipfile.lock", "go.sum", "composer.lock", "gemfile.lock",
    )
    base = p.rsplit("/", 1)[-1]
    if base in lockfiles:
        return True
    if base.endswith((".lock", ".map", ".snap")):
        return True
    if ".min." in base or ".generated." in base or "_pb2." in base or ".pb.go" in base:
        return True
    gen_dirs = ("/vendor/", "/vendored/", "/dist/", "/build/", "/node_modules/",
                "/__snapshots__/", "/.next/", "/out/")
    marker = "/" + p
    return any(d in marker for d in gen_dirs)


def is_test_path(path: str) -> bool:
    p = str(path).lower()
    base = p.rsplit("/", 1)[-1]
    if "/tests/" in ("/" + p) or "/test/" in ("/" + p):
        return True
    return (
        base.startswith("test_")
        or base.endswith(("_test.py", "_test.go", ".test.js", ".test.ts", ".spec.js", ".spec.ts"))
        or ".spec." in base
        or ".test." in base
    )


# ── Non-triviality + build-output (clause d) ────────────────────────────────

def numstat_nontrivial(numstat: List[Dict[str, Any]], L: int, M: int) -> bool:
    """Coded non-triviality predicate: (>=L non-gen added lines across >=M non-gen
    files) OR (>=1 test file). This is now the REAL coded predicate — an empty or
    near-empty diff fails (lines=0, files=0 < M_FLOOR), and the L_FLOOR/M_FLOOR
    stringency floors finally bite.

    crit-4 v2.1 (fix-d): the old ``exercised_by_c`` short-circuit — a hardcoded
    ``exercised_by_c=True`` at the call site that made this whole predicate dead
    code — is DELETED. No machine-checkable signal today distinguishes "exercised
    by coordination" from merely "named by coordination" (the ref-carrier edge is
    already clause (c)'s job, and the signed envelope binds refs + result hash,
    not runtime execution of the diff), so any computed variant would re-open the
    empty-diff qualify. If a genuine linkage signal is ever built (e.g. a signed
    envelope whose result provably ran the increment's tests), it re-enters via a
    reviewed PRINCIPAL amendment."""
    lines = 0
    files = 0
    has_test = False
    for f in numstat or []:
        path = f.get("path", "")
        if is_generated_path(path):
            continue
        files += 1
        added = f.get("added", 0)
        try:
            lines += int(added) if added not in ("-", None) else 0
        except (TypeError, ValueError):
            pass
        if is_test_path(path):
            has_test = True
    if has_test:
        return True
    return lines >= L and files >= M


def checks_pass(increment: Dict[str, Any]) -> bool:
    """(d) CI enum: success => PASS. neutral/skipped/cancelled/failure/timed_out/
    action_required/stale/None => NOT-PASS, FAIL-CLOSED. A committed clean-env
    recipe exiting 0 is the alternative pass path."""
    conclusion = str(increment.get("checks_conclusion") or "").strip().lower()
    if conclusion == "success":
        return True
    recipe = increment.get("recipe_exit")
    return recipe == 0


# ── Causal edge (clause c) ──────────────────────────────────────────────────

def _thread_component(anchor_key: str, envelopes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Connected component under the in_reply_to relation containing anchor.

    Undirected edges: e--e' iff e.in_reply_to == e'.id or e'.in_reply_to == e.id.
    Reconstructs the conversation/thread for the crit-3<->crit-4 causal join."""
    by_id: Dict[str, Dict[str, Any]] = {}
    keys: Dict[int, str] = {}
    for idx, e in enumerate(envelopes):
        k = str(e.get("id") or f"__idx{idx}")
        keys[idx] = k
        by_id[k] = e
    # child index: parent_id -> [child envelopes]
    children: Dict[str, List[Dict[str, Any]]] = {}
    for e in envelopes:
        parent = e.get("in_reply_to")
        if parent:
            children.setdefault(str(parent), []).append(e)
    seen = set()
    comp: List[Dict[str, Any]] = []
    q: deque = deque([anchor_key])
    while q:
        k = q.popleft()
        if k in seen or k not in by_id:
            continue
        seen.add(k)
        e = by_id[k]
        comp.append(e)
        parent = e.get("in_reply_to")
        if parent and str(parent) not in seen:
            q.append(str(parent))
        for child in children.get(k, []):
            ck = str(child.get("id") or "")
            if ck and ck not in seen:
                q.append(ck)
    return comp


def _counted_ok(genuine_envs: List[Dict[str, Any]], surfaces: Dict[str, str],
                K: int, X: float) -> Tuple[bool, Dict[str, Any]]:
    """The K counted envelopes must: be >=K, span >=2 genuine surfaces, and obey
    the anti-dominance cap (no single surface > X% of the counted set)."""
    counted = [e for e in genuine_envs if envelope_surface(e, surfaces) != "unknown"]
    n = len(counted)
    surf_counts = Counter(envelope_surface(e, surfaces) for e in counted)
    distinct = len(surf_counts)
    dominance = (max(surf_counts.values()) / n) if n else 1.0
    ok = (n >= K) and (distinct >= CRIT3_VENDOR_FLOOR) and (dominance <= X + 1e-9)
    return ok, {
        "counted": n,
        "distinct_surfaces": distinct,
        "surfaces": dict(surf_counts),
        "max_dominance": round(dominance, 4),
    }


def increment_causal(ref: str, envelopes: List[Dict[str, Any]], surfaces: Dict[str, str],
                     K: int, X: float) -> Dict[str, Any]:
    """(c) STRUCTURED CAUSAL EDGE for one increment ref. Returns dict with
    ``ok`` and evidence. Both breadth paths require binding to THIS increment AND
    a verifying signature: unsigned/invalid envelopes are pre-filtered out, so
    they can neither carry the ref nor supply breadth."""
    ref = _norm_ref(ref)
    # Signature pre-filter (crit-4 v2.1): only genuinely-signed envelopes are
    # visible to (c). A forged/unsigned envelope cannot be a ref-carrier, cannot
    # anchor a thread, and cannot contribute a surface.
    signed = _valid_signed_envelopes(envelopes)
    # ref-carriers: signed envelopes whose artifact_refs name THIS increment.
    carriers = [e for e in signed if ref in shipped_refs(e)]
    if not carriers:
        return {"ok": False, "reason": "no_signed_ref_carrier", "carriers": 0}

    # Path A — >=2 of the ref-carriers span >=2 surfaces (causal edge itself is
    # the breadth). Counted set = the carriers.
    a_ok, a_ev = _counted_ok(carriers, surfaces, K, X)
    if a_ok:
        return {"ok": True, "path": "A_ref_carried", "carriers": len(carriers), "evidence": a_ev}

    # Path B — the >=2 surfaces appear among SIGNED envelopes SHARING a carrier's
    # thread. The thread is bound to the increment because it contains a
    # ref-carrier; and it is reconstructed over the signed set ONLY, so an
    # unsigned intermediary cannot bridge two threads into false breadth.
    best = a_ev
    for anchor in carriers:
        anchor_key = str(anchor.get("id") or "")
        if not anchor_key:
            continue
        thread = _thread_component(anchor_key, signed)
        # bound-join guard: thread must contain a ref-carrier (the anchor is one)
        if not any(ref in shipped_refs(e) for e in thread):
            continue
        b_ok, b_ev = _counted_ok(thread, surfaces, K, X)
        if b_ok:
            return {"ok": True, "path": "B_thread", "carriers": len(carriers), "evidence": b_ev}
        best = b_ev
    return {"ok": False, "reason": "breadth_not_causally_joined", "carriers": len(carriers), "evidence": best}


# ── Unit qualification (b)^(c)^(d) ──────────────────────────────────────────

def score_unit(unit: Dict[str, Any], surfaces: Dict[str, str], params: "Params") -> Dict[str, Any]:
    """Does this repo satisfy (b)^(c)^(d)? Returns qualification + evidence."""
    if not unit.get("on_spine"):
        return {"qualifies": False, "reason": "off_spine", "qualifying_increments": []}
    envelopes = unit.get("envelopes", [])
    qualifying: List[Dict[str, Any]] = []
    for inc in unit.get("increments", []):
        ref = _norm_ref(inc.get("ref", ""))
        if not ref:
            continue
        c = increment_causal(ref, envelopes, surfaces, params.K, params.X)
        if not c["ok"]:
            continue
        # (d): CI success (fail-closed) AND coded non-triviality. crit-4 v2.1:
        # the hardcoded exercised_by_c=True bypass is GONE — a genuinely
        # coordinated increment with an empty/near-empty diff no longer qualifies.
        if not checks_pass(inc):
            continue
        if not numstat_nontrivial(inc.get("numstat", []), params.L, params.M):
            continue
        qualifying.append({"ref": ref, "causal": c})
    return {
        "qualifies": bool(qualifying),
        "qualifying_increments": qualifying,
        "reason": "ok" if qualifying else "no_qualifying_increment",
    }


# ── Derivation rule + stringency ────────────────────────────────────────────

class Params:
    """Frozen threshold set {Delta,F,L,M,K,X,D_min} + per-window unit-cap.
    Instantiated by the DERIVATION RULE, never by discretion."""

    __slots__ = ("delta", "F", "L", "M", "K", "X", "D_min", "unit_cap", "provenance")

    def __init__(self, delta: float, F: int, L: int, M: int, K: int, X: float,
                 D_min: int, unit_cap: int = 1, provenance: Optional[Dict[str, Any]] = None):
        self.delta = delta
        self.F = F
        self.L = L
        self.M = M
        self.K = K
        self.X = X
        self.D_min = D_min
        self.unit_cap = unit_cap
        self.provenance = provenance or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "delta": self.delta, "F": self.F, "L": self.L, "M": self.M,
            "K": self.K, "X": self.X, "D_min": self.D_min,
            "unit_cap": self.unit_cap, "provenance": self.provenance,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Params":
        return cls(d["delta"], d["F"], d["L"], d["M"], d["K"], d["X"], d["D_min"],
                   d.get("unit_cap", 1), d.get("provenance"))


def derive_params(baseline: Dict[str, Any]) -> Params:
    """DERIVATION RULE (committed, pre-registered). Maps the MEASURED baseline to
    the threshold set — mechanical, keyed to measured dispersion, not discretion.

      Delta = max(2 * baseline_stddev, 0.10)
      F     = ceil(1.15 * baseline_outside_units)
      L, M  = p50 non-gen line / file size of the fleet's real merged increments
      K     = max(K_FLOOR, crit3_vendor_floor)
      X     = 0.60 (anti-dominance cap)
      D_min = per-window minimum-denominator cap (D_MIN_FLOOR)
    """
    stddev = float(baseline.get("stddev", 0.0) or 0.0)
    outside_units = int(baseline.get("outside_units", 0) or 0)
    p50_lines = float(baseline.get("p50_lines", 0.0) or 0.0)
    p50_files = float(baseline.get("p50_files", 0.0) or 0.0)
    crit3_floor = int(baseline.get("crit3_vendor_floor", CRIT3_VENDOR_FLOOR) or CRIT3_VENDOR_FLOOR)
    return Params(
        delta=max(2.0 * stddev, DELTA_FLOOR),
        F=math.ceil(1.15 * outside_units),
        L=int(p50_lines),
        M=int(p50_files),
        K=max(K_FLOOR, crit3_floor),
        X=X_CEIL,
        D_min=D_MIN_FLOOR,
        unit_cap=1,
        provenance={"rule": "PRINCIPAL-v2 crit-4 derivation", "baseline": dict(baseline)},
    )


def validate_stringency(params: Params) -> Tuple[bool, List[str]]:
    """Reject a degenerate / arranged-low freeze (crit-4 attack 9). A freeze that
    fails ANY floor is DEGENERATE and cannot produce a PASS."""
    reasons: List[str] = []
    if params.delta < DELTA_FLOOR - 1e-9:
        reasons.append(f"delta {params.delta} < {DELTA_FLOOR}")
    if params.F < F_FLOOR:
        reasons.append(f"F {params.F} < {F_FLOOR}")
    if params.L < L_FLOOR:
        reasons.append(f"L {params.L} < {L_FLOOR}")
    if params.M < M_FLOOR:
        reasons.append(f"M {params.M} < {M_FLOOR}")
    if params.K < K_FLOOR:
        reasons.append(f"K {params.K} < {K_FLOOR}")
    if params.X > X_CEIL + 1e-9:
        reasons.append(f"X {params.X} > {X_CEIL}")
    if params.D_min < D_MIN_FLOOR:
        reasons.append(f"D_min {params.D_min} < {D_MIN_FLOOR}")
    return (len(reasons) == 0, reasons)


# ── The PURE evaluation (bit-identical over a fixed snapshot) ────────────────

def evaluate(snapshot: Dict[str, Any], params: Params, frozen_baseline: float,
             frozen_partition_hash: Optional[str] = None) -> Dict[str, Any]:
    """Score outside_share + gated PASS as a PURE FUNCTION of the snapshot.

    Reads the partition label from the taxonomy map (hash-bound), so a relabel
    without a version bump trips the consistency guard (tamper => NOT-PASS).

    ``frozen_partition_hash`` (passed by ``cmd_score`` from the frozen baseline)
    BINDS the partition into the freeze: a post-freeze relabel — even one whose
    in-body ``partition_hash`` was hand-corrected so it is internally consistent —
    changes the partition hash away from the frozen one and sets tamper => NOT-
    PASS. Moving a frozen run therefore requires RE-FREEZING (the chief-gated,
    redteam-reviewed PRINCIPAL amendment path), not an operator convenience."""
    surfaces = snapshot.get("vendor_surfaces") or dict(_FROZEN_VENDOR_SURFACES)
    taxonomy = snapshot.get("taxonomy", {})
    partition_map = taxonomy.get("partition", {})
    default_partition = taxonomy.get("default_partition", "substrate")

    # Relabel / tamper guard: the recorded partition_hash must match the body.
    recorded = taxonomy.get("partition_hash")
    recomputed = taxonomy_partition_hash(taxonomy) if taxonomy else None
    tamper = bool(recorded) and recorded != recomputed
    # Freeze-binding: an internally-consistent hand-rehash still cannot move a
    # frozen run — the scored partition hash must equal the frozen one.
    if frozen_partition_hash is not None and recomputed is not None \
            and recomputed != frozen_partition_hash:
        tamper = True

    denominator = 0
    numerator = 0
    unit_results: List[Dict[str, Any]] = []
    for unit in snapshot.get("units", []):
        res = score_unit(unit, surfaces, params)
        repo = unit.get("repo", "")
        partition = partition_map.get(repo, default_partition)
        if res["qualifies"]:
            denominator += 1
            if partition == "outside":
                numerator += 1
        unit_results.append({
            "repo": repo,
            "partition": partition,
            "qualifies": res["qualifies"],
            "reason": res["reason"],
            "qualifying_increments": [q["ref"] for q in res["qualifying_increments"]],
        })

    outside_share = (numerator / denominator) if denominator > 0 else None
    stringency_ok, stringency_reasons = validate_stringency(params)
    denom_ok = denominator >= params.D_min
    inconclusive = (not denom_ok) or (outside_share is None)
    threshold = frozen_baseline + params.delta
    share_ok = (outside_share is not None) and (outside_share >= threshold - 1e-9)
    floor_ok = numerator >= params.F

    passed = bool(
        stringency_ok and (not tamper) and denom_ok and (not inconclusive)
        and share_ok and floor_ok
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "pass": passed,
        "outside_share": outside_share,
        "numerator": numerator,
        "denominator": denominator,
        "frozen_baseline": frozen_baseline,
        "threshold": threshold,
        "inconclusive": inconclusive,
        "tamper": tamper,
        "gates": {
            "stringency_ok": stringency_ok,
            "stringency_reasons": stringency_reasons,
            "denom_ok": denom_ok,
            "share_ok": share_ok,
            "floor_ok": floor_ok,
            "tamper_free": not tamper,
        },
        "params": params.to_dict(),
        "units": unit_results,
    }


# ── Snapshot capture (IMPURE — reads relay FS + gh-API) ─────────────────────

def _repo_slug(repo_root: Path) -> str:
    try:
        out = subprocess.run(
            ["git", "-C", str(repo_root), "remote", "get-url", "origin"],
            capture_output=True, text=True, timeout=10,
        )
        url = out.stdout.strip()
        if url:
            m = re.search(r"[:/]([^/]+/[^/]+?)(?:\.git)?$", url)
            if m:
                return m.group(1)
    except Exception:
        pass
    return repo_root.name


_EXCLUDE_MARKERS = (".claude/worktrees", "_test_resume", "_test_summon",
                    "tmp_test", ".brain_test", "/output/demos/")


def _enumerate_spine_repos(roots: List[Path]) -> List[Path]:
    found: List[Path] = []
    seen = set()

    def _consider(p: Path) -> None:
        rp = p.resolve()
        if rp in seen:
            return
        s = str(rp)
        if any(m in s for m in _EXCLUDE_MARKERS):
            return
        if (rp / ".brain").is_dir():
            seen.add(rp)
            found.append(rp)

    for root in roots:
        root = root.resolve()
        _consider(root)
        if root.is_dir():
            for child in sorted(root.iterdir()):
                if child.is_dir():
                    _consider(child)
    return found


def _read_envelopes(brain: Path, surfaces: Dict[str, str]) -> List[Dict[str, Any]]:
    """Read relay envelopes honestly and STAMP each with vendor_sig.

    artifact_refs come from the canonical JSON-string body first (runtime schema),
    then top-level (skill-produced envelopes). The impure capture step also reads
    the scanned brain's machine key ONCE and stamps each envelope
    ``vendor_sig=valid|invalid|absent`` (verified over the envelope's OWN body
    fields with stdlib hmac) plus its ``dispatch_sig`` (for the pure scorer's
    dedup). Scoring downstream is a pure function of this stamped snapshot."""
    envelopes: List[Dict[str, Any]] = []
    relay = brain / "relay"
    if not relay.is_dir():
        return envelopes
    key = read_brain_key(brain)  # None => every envelope stamps vendor_sig=absent
    for f in sorted(relay.glob("*/*.json")):
        try:
            raw = f.read_text(encoding="utf-8")
            d = json.loads(raw)
        except Exception:
            continue
        if not isinstance(d, dict):
            continue
        refs: List[str] = []
        vendor_sig = "absent"
        dispatch_sig: Optional[str] = None
        body = d.get("body")
        if isinstance(body, str):
            try:
                pb = json.loads(body)
            except Exception:
                pb = None
            if isinstance(pb, dict):
                if isinstance(pb.get("artifact_refs"), list):
                    refs = [str(r) for r in pb["artifact_refs"]]
                dispatch_sig = pb.get("dispatch_sig")
                # Verify over the body's OWN fields with the scanned brain's key.
                vendor_sig = verify_dispatch_sig(pb, key)
        if not refs and isinstance(d.get("artifact_refs"), list):
            refs = [str(r) for r in d["artifact_refs"]]
        sender = str(d.get("from") or "").strip().lower()
        envelopes.append({
            "id": d.get("id"),
            "sender": sender,
            "surface": surfaces.get(sender, "unknown"),
            "in_reply_to": d.get("in_reply_to"),
            "artifact_refs": refs,
            "vendor_sig": vendor_sig,
            "dispatch_sig": dispatch_sig,
            "created_at": d.get("created_at"),
            "file_sha256": _sha256_hex(raw),
        })
    return envelopes


def _resolve_build_output(repo_slug: str, ref: str, repo_root: Path) -> Dict[str, Any]:
    """(d) evidence via gh-API. Best-effort; fail-closed to None on any error.

    Only invoked for increments that already pass (c) — a non-causal increment
    can never qualify, so leaving its build-output unresolved is score-neutral
    and keeps the honest baseline gh-call count near zero."""
    out: Dict[str, Any] = {"checks_conclusion": None, "numstat": [], "recipe_exit": None, "resolved": False}
    ref = _norm_ref(ref)
    is_sha = bool(re.fullmatch(r"[0-9a-f]{7,40}", ref))
    pr_num = None
    m = re.search(r"/pull/(\d+)", ref)
    if m:
        pr_num = m.group(1)
    elif re.fullmatch(r"#?\d+", ref):
        pr_num = ref.lstrip("#")
    try:
        if is_sha:
            r = subprocess.run(
                ["gh", "api", f"repos/{repo_slug}/commits/{ref}/check-runs",
                 "--jq", "[.check_runs[].conclusion]"],
                capture_output=True, text=True, timeout=30,
            )
            if r.returncode == 0 and r.stdout.strip():
                conclusions = [str(c).lower() for c in json.loads(r.stdout) if c]
                out["checks_conclusion"] = "success" if (conclusions and all(c == "success" for c in conclusions)) else (conclusions[0] if conclusions else None)
                out["resolved"] = True
            d = subprocess.run(
                ["git", "-C", str(repo_root), "diff", "--numstat", f"{ref}~1..{ref}"],
                capture_output=True, text=True, timeout=30,
            )
            if d.returncode == 0:
                out["numstat"] = _parse_numstat(d.stdout)
        elif pr_num:
            r = subprocess.run(
                ["gh", "pr", "checks", pr_num, "--repo", repo_slug, "--json", "bucket,state"],
                capture_output=True, text=True, timeout=30,
            )
            if r.returncode == 0 and r.stdout.strip():
                checks = json.loads(r.stdout)
                out["checks_conclusion"] = "success" if (checks and all(c.get("bucket") == "pass" for c in checks)) else "failure"
                out["resolved"] = True
    except Exception:
        pass
    return out


def _parse_numstat(text: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for line in text.splitlines():
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        added, deleted, path = parts
        rows.append({
            "added": 0 if added == "-" else int(added or 0),
            "deleted": 0 if deleted == "-" else int(deleted or 0),
            "path": path,
        })
    return rows


def capture_snapshot(roots: List[Path], taxonomy: Dict[str, Any], *, capturer: str,
                     capture_commit: str, resolve_build: bool = True) -> Dict[str, Any]:
    """Capture an immutable evidence snapshot. Impure step: reads relay FS and,
    for (c)-passing increments only, resolves gh-API build-output."""
    surfaces = _load_vendor_specs_surfaces()
    params_preview = derive_params({"crit3_vendor_floor": CRIT3_VENDOR_FLOOR})
    partition_map = taxonomy.get("partition", {})
    default_partition = taxonomy.get("default_partition", "substrate")

    units: List[Dict[str, Any]] = []
    for repo_root in _enumerate_spine_repos(roots):
        brain = repo_root / ".brain"
        slug = _repo_slug(repo_root)
        envelopes = _read_envelopes(brain, surfaces)
        # Candidate increments = distinct shipped refs that SIGNED coordination is
        # about. Refs that appear only in unsigned/invalid envelopes cannot form a
        # causal edge, so they never seed a candidate increment.
        candidate_refs = sorted({r for e in _valid_signed_envelopes(envelopes)
                                 for r in shipped_refs(e)})
        increments: List[Dict[str, Any]] = []
        for ref in candidate_refs:
            c = increment_causal(ref, envelopes, surfaces, params_preview.K, params_preview.X)
            inc: Dict[str, Any] = {"ref": ref, "causal_at_capture": c["ok"],
                                   "checks_conclusion": None, "numstat": [], "recipe_exit": None,
                                   "resolved": False}
            if resolve_build and c["ok"]:
                inc.update(_resolve_build_output(slug, ref, repo_root))
            increments.append(inc)
        units.append({
            "repo": slug,
            "repo_root": str(repo_root),
            "on_spine": True,
            "partition": partition_map.get(slug, default_partition),
            "envelope_count": len(envelopes),
            "envelopes": envelopes,
            "increments": increments,
        })

    return {
        "schema_version": SCHEMA_VERSION,
        "captured_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "capturer": capturer,
        "capture_commit": capture_commit,
        "roots": [str(r) for r in roots],
        "vendor_surfaces": surfaces,
        "taxonomy": taxonomy,
        "units": units,
    }


# ── Baseline measurement (over a snapshot) ──────────────────────────────────

def measure_baseline(snapshot: Dict[str, Any], historical_shares: Optional[List[float]] = None) -> Dict[str, Any]:
    """Compute the MEASURED baseline {outside_units, stddev, p50_lines, p50_files}
    from a snapshot — the input to the DERIVATION RULE. p50 is over the fleet's
    real (causal + built) merged increments so a below-median stub fails."""
    surfaces = snapshot.get("vendor_surfaces") or dict(_FROZEN_VENDOR_SURFACES)
    taxonomy = snapshot.get("taxonomy", {})
    partition_map = taxonomy.get("partition", {})
    default_partition = taxonomy.get("default_partition", "substrate")
    # Params only used to score qualification here; K/X are structural.
    pv = derive_params({"crit3_vendor_floor": CRIT3_VENDOR_FLOOR})

    outside_units = 0
    line_sizes: List[int] = []
    file_sizes: List[int] = []
    for unit in snapshot.get("units", []):
        if not unit.get("on_spine"):
            continue
        envelopes = unit.get("envelopes", [])
        repo = unit.get("repo", "")
        partition = partition_map.get(repo, default_partition)
        unit_qualifies = False
        for inc in unit.get("increments", []):
            ref = _norm_ref(inc.get("ref", ""))
            if not ref:
                continue
            c = increment_causal(ref, envelopes, surfaces, pv.K, pv.X)
            if not (c["ok"] and checks_pass(inc)):
                continue
            unit_qualifies = True
            lines = sum(f.get("added", 0) for f in inc.get("numstat", [])
                        if not is_generated_path(f.get("path", "")))
            files = sum(1 for f in inc.get("numstat", [])
                        if not is_generated_path(f.get("path", "")))
            line_sizes.append(lines)
            file_sizes.append(files)
        if unit_qualifies and partition == "outside":
            outside_units += 1

    shares = list(historical_shares or [])
    stddev = statistics.pstdev(shares) if len(shares) >= 2 else 0.0
    return {
        "outside_units": outside_units,
        "stddev": stddev,
        "p50_lines": statistics.median(line_sizes) if line_sizes else 0.0,
        "p50_files": statistics.median(file_sizes) if file_sizes else 0.0,
        "crit3_vendor_floor": CRIT3_VENDOR_FLOOR,
        "qualifying_increments": len(line_sizes),
    }


# ── Taxonomy loading (YAML with stdlib fallback) ────────────────────────────

def load_taxonomy(path: Path) -> Dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    try:
        import yaml  # PyYAML present in this repo; optional
        data = yaml.safe_load(text)
    except Exception:
        data = _minimal_yaml(text)
    if not isinstance(data, dict):
        raise ValueError(f"taxonomy at {path} did not parse to a mapping")
    data.setdefault("partition", {})
    data.setdefault("org_logins", [])
    data.setdefault("default_partition", "substrate")
    return data


def _minimal_yaml(text: str) -> Dict[str, Any]:
    """Tiny stdlib YAML subset (flat keys, a list, and a one-level 'partition:'
    map) — enough for the taxonomy file if PyYAML is unavailable."""
    out: Dict[str, Any] = {}
    section = None
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if not line.startswith(" "):
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip()
            if val == "":
                out[key] = {} if key == "partition" else []
                section = key
            else:
                out[key] = _yaml_scalar(val)
                section = None
        else:
            item = line.strip()
            if section == "partition":
                k, _, v = item.partition(":")
                out["partition"][k.strip()] = v.strip()
            elif item.startswith("- "):
                out.setdefault(section, []).append(_yaml_scalar(item[2:].strip()))
    return out


def _yaml_scalar(v: str) -> Any:
    v = v.strip().strip('"').strip("'")
    if v.isdigit():
        return int(v)
    if v.startswith("[") and v.endswith("]"):
        inner = v[1:-1].strip()
        return [s.strip().strip('"').strip("'") for s in inner.split(",")] if inner else []
    return v


def load_operator_identities() -> List[str]:
    """Load the IDENTITY-FENCED operator set out-of-band (never committed).

    Order: NUCLEUS_CENSUS_OPERATORS (comma-sep) -> .brain/census/operators.local.json.
    Absent => [] (public-hash verification degrades to consistency-only)."""
    env = os.environ.get("NUCLEUS_CENSUS_OPERATORS", "").strip()
    if env:
        return sorted({s.strip() for s in env.split(",") if s.strip()})
    try:
        brain = get_brain_dir()
        p = brain / "census" / "operators.local.json"
        if p.exists():
            data = json.loads(p.read_text(encoding="utf-8"))
            return sorted({str(s) for s in data.get("operator_identities", [])})
    except Exception:
        pass
    return []


def get_brain_dir() -> Path:
    cwd = Path.cwd()
    if (cwd / ".brain").is_dir():
        return cwd / ".brain"
    for parent in cwd.parents:
        if (parent / ".brain").is_dir():
            return parent / ".brain"
    return cwd / ".brain"


# ── CLI ─────────────────────────────────────────────────────────────────────

def _git_head(root: Path) -> str:
    try:
        r = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                           capture_output=True, text=True, timeout=10)
        return r.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def _default_taxonomy_path() -> Path:
    return Path(__file__).resolve().parents[1] / "config" / "census" / "taxonomy.yaml"


def cmd_snapshot(args: argparse.Namespace) -> int:
    roots = [Path(r) for r in (args.roots or [os.getcwd()])]
    taxonomy = load_taxonomy(Path(args.taxonomy) if args.taxonomy else _default_taxonomy_path())
    snap = capture_snapshot(
        roots, taxonomy,
        capturer=args.capturer,
        capture_commit=_git_head(roots[0]),
        resolve_build=not args.no_gh,
    )
    out = Path(args.out) if args.out else Path(
        f"census_snapshot_{snap['captured_at_utc'].replace(':', '').replace('-', '')}.json"
    )
    out.write_text(json.dumps(snap, indent=2, sort_keys=True), encoding="utf-8")
    print(f"snapshot -> {out}  ({len(snap['units'])} spine units)")
    return 0


def cmd_baseline(args: argparse.Namespace) -> int:
    snap = json.loads(Path(args.snapshot).read_text(encoding="utf-8"))
    hist = json.loads(args.historical_shares) if args.historical_shares else None
    baseline = measure_baseline(snap, hist)
    params = derive_params(baseline)
    ok, reasons = validate_stringency(params)
    snap_taxonomy = snap.get("taxonomy") or {}
    frozen = {
        "schema_version": SCHEMA_VERSION,
        "frozen_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "capturer": args.capturer,
        "capture_commit": snap.get("capture_commit"),
        "snapshot_captured_at": snap.get("captured_at_utc"),
        "baseline_outside_share": (0.0 if baseline["outside_units"] == 0 else None),
        "measured_baseline": baseline,
        "derived_params": params.to_dict(),
        # Bind the partition into the freeze (fix-a): a post-freeze relabel — even
        # a hand-consistent one — now trips the tamper guard in evaluate().
        "taxonomy_partition_hash": (taxonomy_partition_hash(snap_taxonomy) if snap_taxonomy else None),
        "stringency_ok": ok,
        "stringency_reasons": reasons,
        "freezable": ok,
    }
    if args.out:
        Path(args.out).write_text(json.dumps(frozen, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(frozen, indent=2, sort_keys=True))
    if not ok:
        print("\nNOTE: baseline is DEGENERATE and cannot be frozen yet "
              "(stringency floors unmet). This is the honest G0 state until G1 "
              "generates real cross-vendor traffic.", file=sys.stderr)
    return 0


def cmd_score(args: argparse.Namespace) -> int:
    snap = json.loads(Path(args.snapshot).read_text(encoding="utf-8"))
    frozen_partition_hash: Optional[str] = None
    if args.baseline:
        frozen = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
        params = Params.from_dict(frozen["derived_params"])
        frozen_share = frozen.get("baseline_outside_share") or 0.0
        frozen_partition_hash = frozen.get("taxonomy_partition_hash")
    else:
        baseline = measure_baseline(snap)
        params = derive_params(baseline)
        frozen_share = 0.0 if baseline["outside_units"] == 0 else 0.0
    result = evaluate(snap, params, frozen_share, frozen_partition_hash)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def compute_taxonomy_hashes(taxonomy: Dict[str, Any],
                            operators: Optional[List[str]] = None) -> Dict[str, Any]:
    """Compute the taxonomy integrity anchors WITHOUT writing anything.

    crit-4 v2.1 (fix-a): the self-service ``rehash`` SUBCOMMAND is GONE — there is
    no one-command tool that launders a relabel. The recorded ``partition_hash`` /
    ``public_hash`` in ``config/census/taxonomy.yaml`` are HAND-EDITED in the SAME
    reviewed commit that changes the partition map (so the diff visibly touches
    both), and the CI self-test ``test_committed_taxonomy_hash_is_consistent``
    recomputes and fails the build on any mismatch. This helper is retained only
    as the read-only computation primitive an author uses to obtain the values to
    paste; it never mutates the file."""
    partition_hash = taxonomy_partition_hash(taxonomy)
    ops = operators if operators is not None else load_operator_identities()
    return {
        "partition_hash": partition_hash,
        "public_hash": taxonomy_public_hash(taxonomy, ops),
        "operator_identities_bound": bool(ops),
    }


def cmd_run(args: argparse.Namespace) -> int:
    """Capture + measure + derive + score in one go (honest baseline run)."""
    roots = [Path(r) for r in (args.roots or [os.getcwd()])]
    taxonomy = load_taxonomy(Path(args.taxonomy) if args.taxonomy else _default_taxonomy_path())
    snap = capture_snapshot(roots, taxonomy, capturer=args.capturer,
                            capture_commit=_git_head(roots[0]), resolve_build=not args.no_gh)
    baseline = measure_baseline(snap)
    params = derive_params(baseline)
    ok, reasons = validate_stringency(params)
    result = evaluate(snap, params, 0.0)
    summary = {
        "captured_at_utc": snap["captured_at_utc"],
        "capturer": snap["capturer"],
        "capture_commit": snap["capture_commit"],
        "spine_units": len(snap["units"]),
        "measured_baseline": baseline,
        "derived_params": params.to_dict(),
        "baseline_freezable": ok,
        "stringency_reasons": reasons,
        "outside_share": result["outside_share"],
        "numerator": result["numerator"],
        "denominator": result["denominator"],
        "inconclusive": result["inconclusive"],
        "pass": result["pass"],
        "gates": result["gates"],
    }
    if args.out:
        Path(args.out).write_text(json.dumps({"summary": summary, "snapshot": snap, "result": result},
                                             indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="G0 census — PRINCIPAL v2 crit-4")
    sub = p.add_subparsers(dest="cmd", required=True)

    def _common(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("--capturer", default="chief")
        sp.add_argument("--taxonomy", default=None)

    sp = sub.add_parser("snapshot", help="capture an immutable evidence snapshot")
    sp.add_argument("--roots", nargs="+", default=None)
    sp.add_argument("--out", default=None)
    sp.add_argument("--no-gh", action="store_true", help="skip gh-API build-output resolution")
    _common(sp)
    sp.set_defaults(func=cmd_snapshot)

    sp = sub.add_parser("baseline", help="measure + derive the frozen baseline from a snapshot")
    sp.add_argument("--snapshot", required=True)
    sp.add_argument("--out", default=None)
    sp.add_argument("--historical-shares", default=None, help="JSON list for stddev")
    _common(sp)
    sp.set_defaults(func=cmd_baseline)

    sp = sub.add_parser("score", help="pure score of a snapshot against a frozen baseline")
    sp.add_argument("--snapshot", required=True)
    sp.add_argument("--baseline", default=None)
    _common(sp)
    sp.set_defaults(func=cmd_score)

    sp = sub.add_parser("run", help="capture + measure + score (honest baseline run)")
    sp.add_argument("--roots", nargs="+", default=None)
    sp.add_argument("--out", default=None)
    sp.add_argument("--no-gh", action="store_true")
    _common(sp)
    sp.set_defaults(func=cmd_run)

    # NOTE (crit-4 v2.1, fix-a): the self-service `rehash` subcommand was REMOVED.
    # Taxonomy hashes are hand-edited in the reviewed commit that relabels; the CI
    # self-test recomputes and fails on mismatch. Use compute_taxonomy_hashes() to
    # obtain the values to paste.
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
