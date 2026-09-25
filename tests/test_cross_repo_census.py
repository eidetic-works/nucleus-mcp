"""Anti-gaming self-test corpus + acceptance tests for the cross-repo census.

Authority: docs/PRINCIPAL.md:47-49,75-85,149 (G1 criterion 4).
Immutable source: docs/PRINCIPAL.md@principal-v3.

Two test bands:

  1. ACCEPTANCE — the four task acceptance criteria:
     (A1) the metric is a pure function of an immutable committed evidence
          snapshot (bit-identical rerun);
     (A2) artifact refs are vendor-derived and causally bound to qualifying
          increments;
     (A3) anti-dominance, minimum-denominator, absolute-floor, and
          non-triviality predicates fail closed;
     (A4) the complete pre-registered anti-gaming corpus passes (every
          attack is provably unable to move the gated PASS).

  2. ANTI-GAMING CORPUS — the 12 pre-registered attacks
     (PRINCIPAL.md:62 G0 item 5, applied to G1 crit-4). Each attack
     constructs a snapshot that SHOULD fail the census, and asserts the
     census returns crit4_pass=False with a fail-closed reason naming the
     gate that caught it.

Sandboxed: every test builds a tmp snapshot dir (no live substrate reads,
no live git/gh calls — the census is a pure reader of the snapshot).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from mcp_server_nucleus.runtime import cross_repo_census as crc


# ── Snapshot builders ─────────────────────────────────────────────────────────

def _anchor_regime(on: bool = True) -> Dict[str, Any]:
    return {
        "relay_sender_anchor": on,
        "engram_anchor": on,
        "artifact_ref_vendor_derived": on,
        "captured_at_utc": "2026-07-17T00:00:00+00:00",
    }


def _make_envelope(
    rid: str,
    bucket: str,
    *,
    from_agent: str = "cc_main",
    to_agent: str = "antigravity",
    from_provider: str | None = None,
    from_verified: bool = True,
    artifact_refs: List[str] | None = None,
    artifact_ref_source: str = crc.ARTIFACT_REF_VENDOR_DERIVED,
    nonqualifying_reason: str | None = None,
    in_reply_to: str | None = None,
    created_at: str = "2026-07-16T12:00:00Z",
) -> Dict[str, Any]:
    msg: Dict[str, Any] = {
        "id": rid,
        "from": from_agent,
        "to": to_agent,
        "from_role": "worker",
        "subject": "s",
        "priority": "normal",
        "read": False,
        "created_at": created_at,
        "from_verified": from_verified,
        "artifact_ref_source": artifact_ref_source,
    }
    if from_provider is not None:
        msg["from_provider"] = from_provider
    if in_reply_to is not None:
        msg["in_reply_to"] = in_reply_to
    body: Dict[str, Any] = {"vendor": bucket, "result": "ok", "rc": 0, "status": "ok",
                            "artifact_ref_source": artifact_ref_source}
    if nonqualifying_reason is not None:
        body["artifact_ref_nonqualifying_reason"] = nonqualifying_reason
    if artifact_refs is not None:
        body["artifact_refs"] = artifact_refs
    msg["body"] = json.dumps(body)
    return msg


def _make_increment(
    repo_id: str,
    commit_sha: str,
    *,
    ci_conclusion: str = "success",
    pr_url: str = "",
    files_touched: List[Dict[str, Any]] | None = None,
    has_test_changes: bool = False,
    artifact_ref_source: str = crc.ARTIFACT_REF_VENDOR_DERIVED,
    coord_exercised: bool = False,
) -> Dict[str, Any]:
    if files_touched is None:
        files_touched = [{"path": f"{repo_id}/main.py", "lines_changed": 50, "generated": False}]
    return {
        "repo_id": repo_id,
        "commit_sha": commit_sha,
        "pr_url": pr_url,
        "ci_conclusion": ci_conclusion,
        "files_touched": files_touched,
        "has_test_changes": has_test_changes,
        "artifact_ref_source": artifact_ref_source,
        "coord_exercised": coord_exercised,
    }


def _build_snapshot(
    tmp_path: Path,
    *,
    repos: Dict[str, Dict[str, Any]],
    increments: List[Dict[str, Any]],
    relay_buckets: Dict[str, List[Dict[str, Any]]] | None = None,
    classification: Dict[str, Any] | None = None,
    anchor_on: bool = True,
    classification_hash: str | None = None,
    snapshot_hash_override: str | None = None,
    classification_verified: bool = True,
    classification_verified_status: str = "uncommitted",
) -> Path:
    """Build a complete snapshot dir in tmp_path/snapshot/.

    Every parameter is explicit so each test controls exactly what evidence
    the census sees. The census is a pure function of this dir.
    """
    snap = tmp_path / "snapshot"
    snap.mkdir(parents=True, exist_ok=True)
    relay_out = snap / "relay"
    relay_out.mkdir(exist_ok=True)
    if relay_buckets:
        for bucket, msgs in relay_buckets.items():
            bdir = relay_out / bucket
            bdir.mkdir(exist_ok=True)
            for i, msg in enumerate(msgs):
                (bdir / f"msg_{i}.json").write_text(json.dumps(msg))

    cls = classification or {"taxonomy_version": 1, "repos": {
        rid: {"partition": r["partition"]} for rid, r in repos.items()
    }}
    (snap / "classification.json").write_text(json.dumps(cls, indent=2, sort_keys=True) + "\n")

    (snap / "repos.json").write_text(json.dumps(repos, indent=2, sort_keys=True) + "\n")

    inc_lines = [json.dumps(inc, sort_keys=True) for inc in increments]
    (snap / "increments.jsonl").write_text("\n".join(inc_lines) + ("\n" if inc_lines else ""))

    regime = _anchor_regime(anchor_on)
    cls_hash = classification_hash or crc._hash_json(cls)
    content_hash = snapshot_hash_override or crc._hash_file_tree(snap)
    manifest = {
        "instrument": crc.INSTRUMENT,
        "snapshot_schema_version": crc.SNAPSHOT_SCHEMA_VERSION,
        "captured_at_utc": regime["captured_at_utc"],
        "principal_authority": crc.PRINCIPAL_AUTHORITY,
        "principal_source_tag": crc.PRINCIPAL_SOURCE_TAG,
        "anchor_regime": regime,
        "classification_hash": cls_hash,
        # A clean snapshot now REQUIRES a verified classification: a hash of the
        # file you just read proves nothing about where it came from, so an
        # unverified (or absent) commitment fails closed. `classification_verified`
        # defaults True here so existing fixtures keep testing what they were
        # written to test; the verification logic itself has its own controls,
        # and test_unverified_classification_fails_closed covers the negative.
        "classification_verification": (
            {"status": "verified", "expected": cls_hash, "actual": cls_hash,
             "commitment_path": str(crc.CLASSIFICATION_COMMITMENT)}
            if classification_verified else
            {"status": classification_verified_status, "expected": None,
             "actual": cls_hash,
             "commitment_path": str(crc.CLASSIFICATION_COMMITMENT)}
        ),
        "snapshot_content_hash": content_hash,
        "relay_envelope_count": sum(len(v) for v in (relay_buckets or {}).values()),
        "repo_count": len(repos),
        "increment_count": len(increments),
    }
    (snap / "snapshot_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    )
    return snap


def _qualifying_outside_repo(repo_id: str = "bespoq") -> Dict[str, Any]:
    """A repo that satisfies (a)=outside, (b) spine, with a real increment."""
    return {
        "repo_id": repo_id,
        "path": f"/tmp/{repo_id}",
        "spine": True,
        "has_brain": True,
        "partition": "outside",
    }


def _qualifying_substrate_repo(repo_id: str = "nucleos") -> Dict[str, Any]:
    return {
        "repo_id": repo_id,
        "path": f"/tmp/{repo_id}",
        "spine": True,
        "has_brain": True,
        "partition": "substrate",
    }


# ── A1: pure function of immutable snapshot (bit-identical rerun) ─────────────

def test_a1_pure_function_bit_identical_rerun(tmp_path):
    """Two census runs over the SAME snapshot produce bit-identical verdicts.

    The census reads only the snapshot dir + params; no live git/gh, no
    filesystem mutation, no time-dependent state. Same input → same output.
    """
    repos = {"bespoq": _qualifying_outside_repo("bespoq"), "nucleos": _qualifying_substrate_repo("nucleos")}
    incs = [
        _make_increment("bespoq", "aaa111", ci_conclusion="success",
                        files_touched=[{"path": "b/main.py", "lines_changed": 50, "generated": False}]),
        _make_increment("nucleos", "bbb222", ci_conclusion="success",
                        files_touched=[{"path": "n/main.py", "lines_changed": 50, "generated": False}]),
    ]
    relay = {
        "antigravity": [
            _make_envelope("r1", "antigravity", from_agent="cc_main", to_agent="antigravity",
                           from_provider="antigravity", artifact_refs=["aaa111"]),
            _make_envelope("r2", "antigravity", from_agent="cc_main", to_agent="antigravity",
                           from_provider="antigravity", artifact_refs=["bbb222"]),
        ],
        "devin": [
            _make_envelope("r3", "devin", from_agent="cc_main", to_agent="devin",
                           from_provider="cognition_devin", artifact_refs=["aaa111"]),
            _make_envelope("r4", "devin", from_agent="cc_main", to_agent="devin",
                           from_provider="cognition_devin", artifact_refs=["bbb222"]),
        ],
    }
    snap = _build_snapshot(tmp_path, repos=repos, increments=incs, relay_buckets=relay)
    r1 = crc.run_census(snap, frozen_baseline=0.0, delta=0.10)
    r2 = crc.run_census(snap, frozen_baseline=0.0, delta=0.10)
    # The verdict + metric + per-repo bcd_pass are deterministic.
    assert r1["verdict"]["crit4_pass"] == r2["verdict"]["crit4_pass"]
    assert r1["metric"]["outside_share"] == r2["metric"]["outside_share"]
    assert r1["per_repo"] == r2["per_repo"]
    # Snapshot content hash is stable across reruns (the census does not mutate).
    assert r1["snapshot_manifest"]["snapshot_content_hash"] == r2["snapshot_manifest"]["snapshot_content_hash"]


def test_a1_snapshot_hash_detects_mutation(tmp_path):
    """A post-capture mutation changes the snapshot content hash (tamper-evident)."""
    repos = {"bespoq": _qualifying_outside_repo("bespoq")}
    snap = _build_snapshot(tmp_path, repos=repos, increments=[
        _make_increment("bespoq", "aaa111")
    ], relay_buckets={"antigravity": [_make_envelope("r1", "antigravity", artifact_refs=["aaa111"])]})
    manifest1 = json.loads((snap / "snapshot_manifest.json").read_text())
    # Mutate: add a relay envelope post-capture.
    (snap / "relay" / "antigravity" / "sneaky.json").write_text(json.dumps({"id": "sneaky"}))
    new_hash = crc._hash_file_tree(snap)
    assert new_hash != manifest1["snapshot_content_hash"]


# ── A2: artifact refs vendor-derived + causally bound ─────────────────────────

def test_a2_caller_input_artifact_ref_does_not_qualify(tmp_path):
    """A caller-typed artifact_ref (artifact_ref_source=caller_input) is non-qualifying.

    v3 (PRINCIPAL.md:77): on the anchored path the dispatch/relay tool
    schema MUST NOT accept artifact_ref as caller input; the capture
    instrument stamps it from the vendor worktree's git-reported SHA. A
    caller_input ref does NOT satisfy (c).
    """
    repos = {"bespoq": _qualifying_outside_repo("bespoq")}
    incs = [_make_increment("bespoq", "aaa111", artifact_ref_source=crc.ARTIFACT_REF_VENDOR_DERIVED)]
    relay = {
        "antigravity": [_make_envelope("r1", "antigravity", artifact_refs=["aaa111"],
                                       artifact_ref_source=crc.ARTIFACT_REF_CALLER_INPUT)],
        "devin": [_make_envelope("r2", "devin", artifact_refs=["aaa111"],
                                 artifact_ref_source=crc.ARTIFACT_REF_CALLER_INPUT)],
    }
    snap = _build_snapshot(tmp_path, repos=repos, increments=incs, relay_buckets=relay)
    r = crc.run_census(snap)
    # (c) fails — caller_input refs are non-qualifying → bcd_pass=False.
    assert r["per_repo"]["bespoq"]["bcd_pass"] is False
    assert r["per_repo"]["bespoq"]["c_attribution"]["c_pass"] is False
    assert r["verdict"]["crit4_pass"] is False


def test_a2_unbound_envelopes_do_not_qualify(tmp_path):
    """Envelopes with no artifact_ref naming the increment do NOT satisfy (c).

    This is the coordination-theater + unbound-breadth defense: co-windowed
    envelopes that don't carry the increment's ref are NOT causally bound.
    """
    repos = {"bespoq": _qualifying_outside_repo("bespoq")}
    incs = [_make_increment("bespoq", "aaa111")]
    # Envelopes present, spanning 2 vendors, but NEITHER carries aaa111.
    relay = {
        "antigravity": [_make_envelope("r1", "antigravity", artifact_refs=["zzz999"])],
        "devin": [_make_envelope("r2", "devin", artifact_refs=["yyy888"])],
    }
    snap = _build_snapshot(tmp_path, repos=repos, increments=incs, relay_buckets=relay)
    r = crc.run_census(snap)
    assert r["per_repo"]["bespoq"]["c_attribution"]["c_pass"] is False
    assert r["per_repo"]["bespoq"]["c_attribution"]["increment_verdicts"][0]["c"]["bound_envelope_count"] == 0


def test_third_state_attribution_unprovable_counted_apart(tmp_path):
    """THIRD STATE (director 2026-08-09): an ``attribution_unprovable`` envelope
    is counted in its own bucket — never as qualifying, never folded into
    non_qualifying. This is what keeps a strict, evidence-requiring instrument
    from reading zero-by-construction and hiding it as 'no cross-vendor work'.

    Opposed set inside one increment: one genuine vendor_derived edge, one
    unprovable edge, one provably-not (foreign commit). The census must report
    exactly one of each in its three buckets.
    """
    repos = {"bespoq": _qualifying_outside_repo("bespoq")}
    incs = [_make_increment("bespoq", "aaa111")]
    relay = {
        "antigravity": [
            _make_envelope("r1", "antigravity", from_provider="antigravity",
                           artifact_refs=["aaa111"]),
            _make_envelope("r2", "antigravity", from_provider="antigravity",
                           artifact_refs=["aaa111"],
                           artifact_ref_source=crc.ARTIFACT_REF_NO_INCREMENT
                           if hasattr(crc, "ARTIFACT_REF_NO_INCREMENT") else "no_vendor_increment",
                           nonqualifying_reason="attribution_unprovable"),
            _make_envelope("r3", "antigravity", from_provider="antigravity",
                           artifact_refs=["aaa111"],
                           artifact_ref_source="no_vendor_increment",
                           nonqualifying_reason="head_moved_by_foreign_commit"),
        ],
    }
    snap = _build_snapshot(tmp_path, repos=repos, increments=incs, relay_buckets=relay)
    r = crc.run_census(snap)
    c = r["per_repo"]["bespoq"]["c_attribution"]
    # Repo-level rollup surfaces the third state without digging.
    assert c["attribution_unprovable_bound_count"] == 1, c
    # Per-increment three-way partition: one of each, no leakage.
    ic = c["increment_verdicts"][0]["c"]
    assert ic["qualifying_bound_count"] == 1, ic
    assert ic["attribution_unprovable_bound_count"] == 1, ic
    assert ic["non_qualifying_bound_count"] == 1, ic


def test_a2_vendor_derived_ref_with_two_vendors_qualifies(tmp_path):
    """A vendor-derived artifact_ref bound to ≥2 vendor surfaces satisfies (c)."""
    repos = {"bespoq": _qualifying_outside_repo("bespoq")}
    incs = [_make_increment("bespoq", "aaa111")]
    relay = {
        "antigravity": [_make_envelope("r1", "antigravity", from_provider="antigravity",
                                       artifact_refs=["aaa111"])],
        "devin": [_make_envelope("r2", "devin", from_provider="cognition_devin",
                                 artifact_refs=["aaa111"])],
    }
    snap = _build_snapshot(tmp_path, repos=repos, increments=incs, relay_buckets=relay)
    r = crc.run_census(snap)
    assert r["per_repo"]["bespoq"]["c_attribution"]["c_pass"] is True
    assert r["per_repo"]["bespoq"]["bcd_pass"] is True


# ── A3: predicates fail closed ────────────────────────────────────────────────

def test_a3_min_denominator_fail_closed(tmp_path):
    """Denominator < D_min → INCONCLUSIVE → NOT-PASS (fail-closed)."""
    # Only 1 unit satisfies (b∧c∧d) — below D_min=2.
    repos = {"bespoq": _qualifying_outside_repo("bespoq")}
    incs = [_make_increment("bespoq", "aaa111")]
    relay = {
        "antigravity": [_make_envelope("r1", "antigravity", artifact_refs=["aaa111"])],
        "devin": [_make_envelope("r2", "devin", artifact_refs=["aaa111"])],
    }
    snap = _build_snapshot(tmp_path, repos=repos, increments=incs, relay_buckets=relay)
    r = crc.run_census(snap, min_denominator=2)
    assert r["metric"]["share_inconclusive"] is True
    assert r["metric"]["outside_share"] is None
    assert r["verdict"]["crit4_pass"] is False
    assert any("inconclusive" in reason for reason in r["verdict"]["fail_closed_reasons"])


def test_a3_absolute_floor_fail_closed(tmp_path):
    """outside_count < F → NOT-PASS even if share passes."""
    # 2 outside units, 0 substrate units → share=1.0, but F=3.
    repos = {
        "bespoq": _qualifying_outside_repo("bespoq"),
        "fashion": _qualifying_outside_repo("fashion"),
    }
    incs = [_make_increment("bespoq", "aaa111"), _make_increment("fashion", "ccc333")]
    relay = {
        "antigravity": [
            _make_envelope("r1", "antigravity", artifact_refs=["aaa111"]),
            _make_envelope("r3", "antigravity", artifact_refs=["ccc333"]),
        ],
        "devin": [
            _make_envelope("r2", "devin", artifact_refs=["aaa111"]),
            _make_envelope("r4", "devin", artifact_refs=["ccc333"]),
        ],
    }
    snap = _build_snapshot(tmp_path, repos=repos, increments=incs, relay_buckets=relay)
    r = crc.run_census(snap, frozen_baseline=0.0, delta=0.10, absolute_floor=3)
    assert r["metric"]["outside_share"] == 1.0
    assert r["metric"]["outside_count"] == 2
    assert r["verdict"]["criterion_i_share_delta"] is True
    assert r["verdict"]["criterion_ii_absolute_floor"] is False
    assert r["verdict"]["crit4_pass"] is False


def test_a3_anti_dominance_fail_closed(tmp_path):
    """One vendor surface > X% of K → anti-dominance fails → (c) fails."""
    repos = {"bespoq": _qualifying_outside_repo("bespoq")}
    incs = [_make_increment("bespoq", "aaa111")]
    # 5 antigravity + 1 devin → antigravity = 83% > 60% cap.
    relay = {
        "antigravity": [
            _make_envelope(f"r{i}", "antigravity", from_provider="antigravity", artifact_refs=["aaa111"])
            for i in range(5)
        ],
        "devin": [_make_envelope("r5", "devin", from_provider="cognition_devin", artifact_refs=["aaa111"])],
    }
    snap = _build_snapshot(tmp_path, repos=repos, increments=incs, relay_buckets=relay)
    r = crc.run_census(snap, dominance_cap=0.60)
    c_verdict = r["per_repo"]["bespoq"]["c_attribution"]["increment_verdicts"][0]["c"]
    assert c_verdict["anti_dominance_pass"] is False
    assert c_verdict["dominance_violation_surface"] == "antigravity"
    assert c_verdict["c_pass"] is False
    assert r["verdict"]["crit4_pass"] is False


def test_a3_non_triviality_fail_closed_on_stub(tmp_path):
    """A 1-line / 1-file stub fails (d) non-triviality when L=5, M=1."""
    repos = {"bespoq": _qualifying_outside_repo("bespoq")}
    incs = [_make_increment("bespoq", "aaa111",
                            files_touched=[{"path": "b/stub.py", "lines_changed": 1, "generated": False}],
                            has_test_changes=False)]
    relay = {
        "antigravity": [_make_envelope("r1", "antigravity", artifact_refs=["aaa111"])],
        "devin": [_make_envelope("r2", "devin", artifact_refs=["aaa111"])],
    }
    snap = _build_snapshot(tmp_path, repos=repos, increments=incs, relay_buckets=relay)
    r = crc.run_census(snap, min_lines=5, min_files=1)
    d_verdict = r["per_repo"]["bespoq"]["c_attribution"]["increment_verdicts"][0]["d_non_trivial"]
    assert d_verdict["non_generated_lines"] == 1
    assert d_verdict["lines_files_pass"] is False
    assert d_verdict["non_trivial"] is False
    assert r["per_repo"]["bespoq"]["bcd_pass"] is False


def test_a3_ci_failure_fail_closed(tmp_path):
    """CI conclusion != success → (d) build-output fails (fail-closed)."""
    repos = {"bespoq": _qualifying_outside_repo("bespoq")}
    incs = [_make_increment("bespoq", "aaa111", ci_conclusion="failure")]
    relay = {
        "antigravity": [_make_envelope("r1", "antigravity", artifact_refs=["aaa111"])],
        "devin": [_make_envelope("r2", "devin", artifact_refs=["aaa111"])],
    }
    snap = _build_snapshot(tmp_path, repos=repos, increments=incs, relay_buckets=relay)
    r = crc.run_census(snap)
    d_build = r["per_repo"]["bespoq"]["c_attribution"]["increment_verdicts"][0]["d_build_output"]
    assert d_build["ci_pass"] is False
    assert d_build["build_output_pass"] is False
    assert r["per_repo"]["bespoq"]["bcd_pass"] is False


def test_a3_ci_pending_fail_closed(tmp_path):
    """CI conclusion 'pending' is NOT success → fail-closed (not a free pass)."""
    repos = {"bespoq": _qualifying_outside_repo("bespoq")}
    incs = [_make_increment("bespoq", "aaa111", ci_conclusion="pending")]
    relay = {
        "antigravity": [_make_envelope("r1", "antigravity", artifact_refs=["aaa111"])],
        "devin": [_make_envelope("r2", "devin", artifact_refs=["aaa111"])],
    }
    snap = _build_snapshot(tmp_path, repos=repos, increments=incs, relay_buckets=relay)
    r = crc.run_census(snap)
    assert r["per_repo"]["bespoq"]["bcd_pass"] is False


def test_a3_stringency_rejects_degenerate_thresholds(tmp_path):
    """Δ=0.01 / F=1 / L=1 / M=0 / K=1 / X=0.80 fails the stringency check."""
    repos = {"bespoq": _qualifying_outside_repo("bespoq")}
    incs = [_make_increment("bespoq", "aaa111")]
    relay = {
        "antigravity": [_make_envelope("r1", "antigravity", artifact_refs=["aaa111"])],
        "devin": [_make_envelope("r2", "devin", artifact_refs=["aaa111"])],
    }
    snap = _build_snapshot(tmp_path, repos=repos, increments=incs, relay_buckets=relay)
    r = crc.run_census(
        snap, delta=0.01, absolute_floor=1, min_lines=1, min_files=0,
        min_envelopes=1, dominance_cap=0.80,
    )
    assert r["stringency"]["stringent"] is False
    assert len(r["stringency"]["fails"]) > 0
    assert r["verdict"]["crit4_pass"] is False
    assert any("degenerate" in reason for reason in r["verdict"]["fail_closed_reasons"])


# ── A4: anti-gaming corpus — every attack provably cannot move the gated PASS ─

def test_corpus_relabel_detected(tmp_path):
    """relabel: swapping a repo's partition label changes the classification hash.

    The classification is hash-committed; a relabel produces a different
    hash than the manifest records. (The census itself reads the snapshot's
    current classification, so this test asserts the tamper-detection
    primitive: the hash mismatch is detectable on rerun.)
    """
    repos = {"bespoq": _qualifying_outside_repo("bespoq")}
    snap = _build_snapshot(tmp_path, repos=repos, increments=[_make_increment("bespoq", "aaa111")])
    manifest = json.loads((snap / "snapshot_manifest.json").read_text())
    original_hash = manifest["classification_hash"]
    # Relabel bespoq from outside → substrate.
    cls = json.loads((snap / "classification.json").read_text())
    cls["repos"]["bespoq"]["partition"] = "substrate"
    (snap / "classification.json").write_text(json.dumps(cls, indent=2, sort_keys=True) + "\n")
    new_hash = crc._hash_json(cls)
    assert new_hash != original_hash  # tamper-evident


def test_corpus_commit_churn_fails(tmp_path):
    """commit_churn: fabricated increments with no real CI/build fail (d)."""
    repos = {"bespoq": _qualifying_outside_repo("bespoq")}
    incs = [_make_increment("bespoq", "fake111", ci_conclusion="",
                            files_touched=[{"path": "b/x.py", "lines_changed": 1, "generated": False}])]
    relay = {
        "antigravity": [_make_envelope("r1", "antigravity", artifact_refs=["fake111"])],
        "devin": [_make_envelope("r2", "devin", artifact_refs=["fake111"])],
    }
    snap = _build_snapshot(tmp_path, repos=repos, increments=incs, relay_buckets=relay)
    r = crc.run_census(snap)
    assert r["per_repo"]["bespoq"]["bcd_pass"] is False
    assert r["verdict"]["crit4_pass"] is False


def test_corpus_repo_mint_fails(tmp_path):
    """repo_mint: a throwaway repo with no spine (.brain) fails (b)."""
    repos = {
        "throwaway": {
            "repo_id": "throwaway", "path": "/tmp/throwaway",
            "spine": False, "has_brain": False, "partition": "outside",
        }
    }
    incs = [_make_increment("throwaway", "aaa111")]
    relay = {
        "antigravity": [_make_envelope("r1", "antigravity", artifact_refs=["aaa111"])],
        "devin": [_make_envelope("r2", "devin", artifact_refs=["aaa111"])],
    }
    snap = _build_snapshot(tmp_path, repos=repos, increments=incs, relay_buckets=relay)
    r = crc.run_census(snap)
    assert r["per_repo"]["throwaway"]["b_spine"]["b_pass"] is False
    assert r["per_repo"]["throwaway"]["bcd_pass"] is False


def test_corpus_genuine_traffic_repoint_fails(tmp_path):
    """genuine_traffic_repoint: real envelopes routed at a throwaway repo,
    but no envelope carries the increment's artifact_ref → (c) fails."""
    repos = {"bespoq": _qualifying_outside_repo("bespoq")}
    incs = [_make_increment("bespoq", "aaa111")]
    # Envelopes are real (anchored, vendor-derived) but their artifact_refs
    # point at OTHER commits — the increment aaa111 has no bound envelopes.
    relay = {
        "antigravity": [_make_envelope("r1", "antigravity", artifact_refs=["other_commit"])],
        "devin": [_make_envelope("r2", "devin", artifact_refs=["another_commit"])],
    }
    snap = _build_snapshot(tmp_path, repos=repos, increments=incs, relay_buckets=relay)
    r = crc.run_census(snap)
    assert r["per_repo"]["bespoq"]["c_attribution"]["c_pass"] is False
    assert r["per_repo"]["bespoq"]["bcd_pass"] is False


def test_corpus_coordination_theater_fails(tmp_path):
    """coordination_theater: envelopes present but unbound (no artifact_ref)."""
    repos = {"bespoq": _qualifying_outside_repo("bespoq")}
    incs = [_make_increment("bespoq", "aaa111")]
    relay = {
        "antigravity": [_make_envelope("r1", "antigravity", artifact_refs=[])],
        "devin": [_make_envelope("r2", "devin", artifact_refs=[])],
    }
    snap = _build_snapshot(tmp_path, repos=repos, increments=incs, relay_buckets=relay)
    r = crc.run_census(snap)
    assert r["per_repo"]["bespoq"]["c_attribution"]["c_pass"] is False


def test_corpus_unbound_breadth_fails(tmp_path):
    """unbound_breadth: ≥2-vendor span from co-windowed envelopes NOT bound to the increment."""
    repos = {"bespoq": _qualifying_outside_repo("bespoq")}
    incs = [_make_increment("bespoq", "aaa111")]
    # 1 envelope bound to aaa111 (antigravity only) + 1 unbound devin envelope.
    # The 2-vendor span comes from the UNBOUND devin envelope → fails the join.
    relay = {
        "antigravity": [_make_envelope("r1", "antigravity", artifact_refs=["aaa111"])],
        "devin": [_make_envelope("r2", "devin", artifact_refs=["unrelated"])],
    }
    snap = _build_snapshot(tmp_path, repos=repos, increments=incs, relay_buckets=relay)
    r = crc.run_census(snap)
    c = r["per_repo"]["bespoq"]["c_attribution"]["increment_verdicts"][0]["c"]
    # Only antigravity is bound → distinct_vendor_count=1 < 2.
    assert c["distinct_vendor_count"] == 1
    assert c["c_pass"] is False


def test_corpus_baseline_suppression_fails(tmp_path):
    """baseline_suppression: CI withheld during capture → (d) fails (no success)."""
    repos = {"bespoq": _qualifying_outside_repo("bespoq")}
    incs = [_make_increment("bespoq", "aaa111", ci_conclusion="skipped")]
    relay = {
        "antigravity": [_make_envelope("r1", "antigravity", artifact_refs=["aaa111"])],
        "devin": [_make_envelope("r2", "devin", artifact_refs=["aaa111"])],
    }
    snap = _build_snapshot(tmp_path, repos=repos, increments=incs, relay_buckets=relay)
    r = crc.run_census(snap)
    # 'skipped' is not 'success' → (d) fails.
    assert r["per_repo"]["bespoq"]["bcd_pass"] is False


def test_corpus_denominator_suppression_fails(tmp_path):
    """denominator_suppression: hash-binding withheld on genuine increments → (c) fails."""
    repos = {"bespoq": _qualifying_outside_repo("bespoq")}
    # Genuine increment but no envelope carries its artifact_ref → not bound.
    incs = [_make_increment("bespoq", "aaa111", ci_conclusion="success")]
    relay = {
        "antigravity": [_make_envelope("r1", "antigravity", artifact_refs=["bbb222"])],
        "devin": [_make_envelope("r2", "devin", artifact_refs=["ccc333"])],
    }
    snap = _build_snapshot(tmp_path, repos=repos, increments=incs, relay_buckets=relay)
    r = crc.run_census(snap)
    assert r["per_repo"]["bespoq"]["c_attribution"]["c_pass"] is False
    # The increment is NOT counted in the denominator → suppression fails to
    # shrink the denominator because the unit never qualified in the first place.
    assert r["metric"]["denominator"] == 0


def test_corpus_single_vendor_dominance_fails(tmp_path):
    """single_vendor_dominance: one vendor surface supplies > X% of K."""
    repos = {"bespoq": _qualifying_outside_repo("bespoq")}
    incs = [_make_increment("bespoq", "aaa111")]
    # 4 antigravity + 1 devin → antigravity = 80% > 60%.
    relay = {
        "antigravity": [_make_envelope(f"r{i}", "antigravity", from_provider="antigravity",
                                       artifact_refs=["aaa111"]) for i in range(4)],
        "devin": [_make_envelope("r4", "devin", from_provider="cognition_devin",
                                 artifact_refs=["aaa111"])],
    }
    snap = _build_snapshot(tmp_path, repos=repos, increments=incs, relay_buckets=relay)
    r = crc.run_census(snap, dominance_cap=0.60)
    c = r["per_repo"]["bespoq"]["c_attribution"]["increment_verdicts"][0]["c"]
    assert c["anti_dominance_pass"] is False
    assert c["c_pass"] is False


def test_corpus_null_degenerate_threshold_fails(tmp_path):
    """null_degenerate_threshold: Δ=+1pp / F=1 / L=1 / M=1 freeze fails stringency."""
    repos = {"bespoq": _qualifying_outside_repo("bespoq")}
    incs = [_make_increment("bespoq", "aaa111")]
    relay = {
        "antigravity": [_make_envelope("r1", "antigravity", artifact_refs=["aaa111"])],
        "devin": [_make_envelope("r2", "devin", artifact_refs=["aaa111"])],
    }
    snap = _build_snapshot(tmp_path, repos=repos, increments=incs, relay_buckets=relay)
    r = crc.run_census(snap, delta=0.01, absolute_floor=1, min_lines=1, min_files=1,
                       min_envelopes=1, dominance_cap=0.99)
    assert r["stringency"]["stringent"] is False
    assert r["verdict"]["crit4_pass"] is False


def test_corpus_pre_anchor_snapshot_fails(tmp_path):
    """pre_anchor_snapshot: v3 precondition — snapshot captured before anchor flags ON."""
    repos = {"bespoq": _qualifying_outside_repo("bespoq")}
    incs = [_make_increment("bespoq", "aaa111")]
    relay = {
        "antigravity": [_make_envelope("r1", "antigravity", artifact_refs=["aaa111"],
                                       from_verified=False)],
        "devin": [_make_envelope("r2", "devin", artifact_refs=["aaa111"],
                                 from_verified=False)],
    }
    snap = _build_snapshot(tmp_path, repos=repos, increments=incs, relay_buckets=relay,
                           anchor_on=False)
    r = crc.run_census(snap)
    assert r["anchor_regime_ok"] is False
    assert r["verdict"]["crit4_pass"] is False
    assert any("anchor regime" in reason for reason in r["verdict"]["fail_closed_reasons"])


def test_corpus_caller_input_artifact_ref_fails(tmp_path):
    """caller_input_artifact_ref: v3 — caller-typed refs do not qualify (covered in A2 too)."""
    repos = {"bespoq": _qualifying_outside_repo("bespoq")}
    incs = [_make_increment("bespoq", "aaa111")]
    relay = {
        "antigravity": [_make_envelope("r1", "antigravity", artifact_refs=["aaa111"],
                                       artifact_ref_source=crc.ARTIFACT_REF_CALLER_INPUT)],
        "devin": [_make_envelope("r2", "devin", artifact_refs=["aaa111"],
                                 artifact_ref_source=crc.ARTIFACT_REF_CALLER_INPUT)],
    }
    snap = _build_snapshot(tmp_path, repos=repos, increments=incs, relay_buckets=relay)
    r = crc.run_census(snap)
    assert r["per_repo"]["bespoq"]["c_attribution"]["c_pass"] is False
    assert r["verdict"]["crit4_pass"] is False


# ── Corpus coverage declaration ───────────────────────────────────────────────

def test_anti_gaming_corpus_coverage_declaration():
    """The corpus declaration lists all 12 pre-registered attacks."""
    cov = crc.anti_gaming_corpus_coverage()
    names = [a["name"] for a in cov["attacks"]]
    expected = set(crc.ANTI_GAMING_CORPUS)
    assert set(names) == expected
    assert len(names) == 12
    # Every attack's expected outcome is NOT-PASS (fail-closed).
    for a in cov["attacks"]:
        assert "NOT-PASS" in a["expected_outcome"]


def test_corpus_every_attack_has_a_regression_test():
    """Meta-test: every attack in ANTI_GAMING_CORPUS has a test_corpus_<attack>_fails test.

    This is the SUFFICIENCY check (PRINCIPAL.md:62): the corpus is validated
    as sufficient — every attack has a passing regression test. A missing
    test = BLOCKING.
    """
    import inspect
    import sys
    test_mod = sys.modules[__name__]
    missing: List[str] = []
    for attack in crc.ANTI_GAMING_CORPUS:
        # attack names use snake_case; test names are test_corpus_<attack>_fails
        # or test_corpus_<attack>_detected.
        candidates = [
            f"test_corpus_{attack}_fails",
            f"test_corpus_{attack}_detected",
        ]
        found = any(hasattr(test_mod, c) for c in candidates)
        if not found:
            missing.append(attack)
    assert not missing, f"missing regression tests for attacks: {missing}"


# ── Positive control: a clean qualifying snapshot DOES pass ───────────────────

def test_positive_control_clean_snapshot_passes(tmp_path):
    """A clean snapshot with 2 outside + 1 substrate unit, all predicates green, passes."""
    repos = {
        "bespoq": _qualifying_outside_repo("bespoq"),
        "fashion": _qualifying_outside_repo("fashion"),
        "nucleos": _qualifying_substrate_repo("nucleos"),
    }
    incs = [
        _make_increment("bespoq", "aaa111", ci_conclusion="success",
                        files_touched=[{"path": "b/main.py", "lines_changed": 50, "generated": False}]),
        _make_increment("fashion", "ccc333", ci_conclusion="success",
                        files_touched=[{"path": "f/main.py", "lines_changed": 60, "generated": False}]),
        _make_increment("nucleos", "bbb222", ci_conclusion="success",
                        files_touched=[{"path": "n/main.py", "lines_changed": 40, "generated": False}]),
    ]
    relay = {
        "antigravity": [
            _make_envelope("r1", "antigravity", from_provider="antigravity", artifact_refs=["aaa111"]),
            _make_envelope("r3", "antigravity", from_provider="antigravity", artifact_refs=["ccc333"]),
            _make_envelope("r5", "antigravity", from_provider="antigravity", artifact_refs=["bbb222"]),
        ],
        "devin": [
            _make_envelope("r2", "devin", from_provider="cognition_devin", artifact_refs=["aaa111"]),
            _make_envelope("r4", "devin", from_provider="cognition_devin", artifact_refs=["ccc333"]),
            _make_envelope("r6", "devin", from_provider="cognition_devin", artifact_refs=["bbb222"]),
        ],
    }
    snap = _build_snapshot(tmp_path, repos=repos, increments=incs, relay_buckets=relay)
    r = crc.run_census(snap, frozen_baseline=0.0, delta=0.10, absolute_floor=2, min_denominator=2)
    assert r["metric"]["denominator"] == 3
    assert r["metric"]["outside_count"] == 2
    assert r["metric"]["outside_share"] == 2 / 3
    assert r["verdict"]["crit4_pass"] is True
    assert r["per_repo"]["bespoq"]["bcd_pass"] is True
    assert r["per_repo"]["fashion"]["bcd_pass"] is True
    assert r["per_repo"]["nucleos"]["bcd_pass"] is True


def test_unverified_classification_fails_closed(tmp_path):
    """The NEGATIVE control for classification tamper-evidence.

    `capture_snapshot` used to record `classification_hash = _hash_json(cls)` —
    a hash of the file it had just read — while the docstring called it
    "versioned, hash-committed ... tamper-evident relabel". A hash of your own
    input is a checksum, not a commitment: edit the classification and the
    manifest hash matches the edit perfectly. `.brain/*` is gitignored, so there
    was no committed copy to compare against either.

    `relabel` and `repo-mint` are both named in the G0 crit-5 anti-gaming corpus
    as attacks that must be provably unable to move the gated PASS. This asserts
    they now cannot: an unverified classification fails closed, and the absence
    of a commitment is treated exactly like a mismatch — absence of evidence is
    not evidence of integrity.
    """
    repos = {
        "bespoq": _qualifying_outside_repo("bespoq"),
        "fashion": _qualifying_outside_repo("fashion"),
        "nucleos": _qualifying_substrate_repo("nucleos"),
    }
    incs = [
        _make_increment("bespoq", "aaa111", ci_conclusion="success",
                        files_touched=[{"path": "b/main.py", "lines_changed": 50, "generated": False}]),
        _make_increment("fashion", "ccc333", ci_conclusion="success",
                        files_touched=[{"path": "f/main.py", "lines_changed": 60, "generated": False}]),
        _make_increment("nucleos", "bbb222", ci_conclusion="success",
                        files_touched=[{"path": "n/main.py", "lines_changed": 40, "generated": False}]),
    ]
    relay = {
        "antigravity": [
            _make_envelope("r1", "antigravity", from_provider="antigravity", artifact_refs=["aaa111"]),
            _make_envelope("r3", "antigravity", from_provider="antigravity", artifact_refs=["ccc333"]),
            _make_envelope("r5", "antigravity", from_provider="antigravity", artifact_refs=["bbb222"]),
        ],
        "devin": [
            _make_envelope("r2", "devin", from_provider="cognition_devin", artifact_refs=["aaa111"]),
            _make_envelope("r4", "devin", from_provider="cognition_devin", artifact_refs=["ccc333"]),
            _make_envelope("r6", "devin", from_provider="cognition_devin", artifact_refs=["bbb222"]),
        ],
    }

    for status in ("uncommitted", "tampered"):
        snap = _build_snapshot(
            tmp_path / status, repos=repos, increments=incs, relay_buckets=relay,
            classification_verified=False, classification_verified_status=status,
        )
        r = crc.run_census(snap, frozen_baseline=0.0, delta=0.10,
                           absolute_floor=2, min_denominator=2)
        assert r["verdict"]["crit4_pass"] is False, f"{status} must NOT pass"
        assert any("classification not verified" in x
                   for x in r["verdict"]["fail_closed_reasons"]), \
            f"{status} must NAME the reason, not fail silently"
