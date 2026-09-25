"""Anti-gaming self-test for the G0 census (PRINCIPAL v2 crit-4).

This IS the un-gameability proof that gates G0 exit-crit-5. Each attack in the
corpus (crit-4 "ANTI-GAMING SELF-TEST CORPUS") is exercised against the PURE
scorer with SYNTHETIC fixtures (no real data) and must be provably unable to
move the gated PASS:

  1. relabel                      -> partition is (a), not a qualifying conjunct;
                                     unversioned relabel trips the hash guard.
  2. commit-churn                 -> below-median stubs fail non-triviality (d).
  3. repo-mint (fabricated)       -> no real green CI => (d) fails closed.
  4. genuine-traffic re-point     -> envelopes name OTHER increments => no (c).
  5. coordination-theater         -> unbound envelopes (no shipped ref) => no (c).
  6. unbound-breadth              -> 2nd surface not thread/ref-joined => no (c).
  7. baseline-suppression +       -> degenerate baseline fails stringency;
     denominator-suppression         sub-D_min denominator => inconclusive.
  8. single-vendor-dominance      -> one surface > X% of K => anti-dominance fail.
  9. null/degenerate-threshold    -> Delta=+1pp / F=1 / L=1 / M=1 fails stringency.

crit-4 v2.1 additions (signed-capture hardening):
  F. FORGED-ENVELOPE (signature)  -> unsigned / wrong-key / lifted-sig cross-vendor
                                     envelopes are invisible to (c); hand-written
                                     `from: cursor|windsurf` files manufacture no
                                     surface; verbatim replay is deduped on
                                     dispatch_sig. A real signer (SignatureGuard)
                                     over a temp brain proves the stdlib verifier's
                                     parity, lifted-sig / status-flip / wrong-key /
                                     corrupted-byte => invalid, absent-key => absent.
  fix-d. non-triviality is LIVE    -> the hardcoded exercised_by_c=True bypass is
                                     gone: an EMPTY-diff increment with genuine
                                     signed cross-vendor coordination must NOT
                                     qualify; sub-L/M non-test diff must NOT; >=L/M
                                     and test-bearing diffs DO.
  fix-a. relabel is gated          -> the self-service `rehash` subcommand is
                                     removed; a post-freeze relabel with an
                                     internally-consistent hand-rehash still trips
                                     the frozen-partition binding (tamper).

Every test also carries a POSITIVE control so the gate is not vacuously False.
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import census_v2 as C  # noqa: E402


# ── Fixture builders ────────────────────────────────────────────────────────

_CTR = {"n": 0}


def _rid() -> str:
    _CTR["n"] += 1
    return f"env_{_CTR['n']:04d}"


def env(sender: str, refs, rid=None, reply=None, vendor_sig="valid", dispatch_sig=None):
    """Build a relay envelope with its surface resolved from the frozen map and a
    ``vendor_sig`` STAMP (as the impure capture step produces).

    Genuine envelopes default to ``vendor_sig='valid'`` with a UNIQUE synthetic
    ``dispatch_sig`` (so distinct genuine dispatches are not deduped together);
    forged fixtures pass ``vendor_sig='absent'`` (unsigned) or ``'invalid'``
    (wrong-key / lifted). Scoring is a pure function of these stamps — the actual
    HMAC verification is proven separately against a real SignatureGuard."""
    rid = rid or _rid()
    return {
        "id": rid,
        "sender": sender,
        "surface": C._FROZEN_VENDOR_SURFACES.get(sender, "unknown"),
        "in_reply_to": reply,
        "artifact_refs": list(refs),
        "vendor_sig": vendor_sig,
        "dispatch_sig": dispatch_sig if dispatch_sig is not None else f"sig_{rid}",
    }


def cross_vendor_carriers(ref, senders=("agy", "devin")):
    """Envelopes each carrying ``ref`` from distinct genuine (signed) surfaces."""
    return [env(s, [ref]) for s in senders]


def forged_carriers(ref, senders=("agy", "devin"), vendor_sig="absent"):
    """Cross-vendor ref-carriers that FAIL signature verification (unsigned or
    wrong-key) — the Goodhart re-attack made un-forgeable."""
    return [env(s, [ref], vendor_sig=vendor_sig) for s in senders]


def _nontrivial_numstat():
    """A diff that clears the healthy PARAMS floors (L=45, M=3): 3 non-generated
    files x 20 added lines = 60 lines across 3 files."""
    return [{"added": 20, "deleted": 0, "path": f"src/mod{i}.py"} for i in range(3)]


def increment(ref, conclusion="success", numstat=None):
    return {
        "ref": ref,
        "checks_conclusion": conclusion,
        # Default is now genuinely NON-TRIVIAL: with fix-d live, a qualifying
        # increment must clear the L/M floors (the old exercised_by_c bypass is
        # gone). Attacks that need a trivial diff pass numstat=[] explicitly.
        "numstat": numstat if numstat is not None else _nontrivial_numstat(),
    }


def unit(repo, partition, envelopes, increments, on_spine=True):
    return {"repo": repo, "partition": partition, "on_spine": on_spine,
            "envelopes": envelopes, "increments": increments}


def mk_taxonomy(partition_map, schema_version=1, rehash=True):
    tax = {
        "schema_version": schema_version,
        "org_logins": ["eidetic-works"],
        "default_partition": "substrate",
        "partition": dict(partition_map),
    }
    if rehash:
        tax["partition_hash"] = C.taxonomy_partition_hash(tax)
    return tax


def snapshot(units, extra_partition=None):
    partition = {u["repo"]: u["partition"] for u in units}
    if extra_partition:
        partition.update(extra_partition)
    return {
        "schema_version": C.SCHEMA_VERSION,
        "vendor_surfaces": dict(C._FROZEN_VENDOR_SURFACES),
        "taxonomy": mk_taxonomy(partition),
        "units": units,
    }


def qualifying_unit(repo, partition):
    """A genuinely qualifying unit: cross-vendor causal edge + green CI."""
    ref = f"deadbeef{repo[-4:]}"[:12]
    return unit(repo, partition, cross_vendor_carriers(ref), [increment(ref)])


# Healthy frozen params derived from a synthetic non-degenerate baseline.
HEALTHY_BASELINE = {"outside_units": 4, "stddev": 0.03, "p50_lines": 45,
                    "p50_files": 3, "crit3_vendor_floor": 2}
PARAMS = C.derive_params(HEALTHY_BASELINE)
FROZEN_BASELINE = 0.20  # baseline outside_share


def _ev(snap, params=PARAMS, baseline=FROZEN_BASELINE):
    return C.evaluate(snap, params, baseline)


# ── Sanity: the gate is NOT vacuously False (positive control) ──────────────

def test_healthy_params_are_non_degenerate():
    ok, reasons = C.validate_stringency(PARAMS)
    assert ok, reasons
    assert PARAMS.F == 5 and PARAMS.L == 45 and PARAMS.M == 3
    assert PARAMS.K == 2 and PARAMS.X == 0.60 and PARAMS.D_min == 3
    assert PARAMS.delta == 0.10


def test_legit_fleet_passes():
    """6 outside + 4 substrate genuinely-qualifying units => PASS."""
    units = [qualifying_unit(f"eidetic-works/out{i}", "outside") for i in range(6)]
    units += [qualifying_unit(f"eidetic-works/sub{i}", "substrate") for i in range(4)]
    res = _ev(snapshot(units))
    assert res["denominator"] == 10 and res["numerator"] == 6
    assert res["outside_share"] == 0.6
    assert res["pass"] is True, res["gates"]


def test_evaluation_is_bit_identical():
    units = [qualifying_unit(f"eidetic-works/out{i}", "outside") for i in range(6)]
    snap = snapshot(units)
    a = json.dumps(_ev(snap), sort_keys=True)
    b = json.dumps(_ev(copy.deepcopy(snap)), sort_keys=True)
    assert a == b


# ── Attack 1: RELABEL ───────────────────────────────────────────────────────

def test_attack1_relabel_without_rehash_is_tamper():
    """Flipping a partition label without bumping/rehashing trips the hash guard
    => tamper => NOT-PASS, fail-closed."""
    units = [qualifying_unit(f"eidetic-works/out{i}", "outside") for i in range(6)]
    units += [qualifying_unit(f"eidetic-works/sub{i}", "substrate") for i in range(4)]
    snap = snapshot(units)
    assert _ev(snap)["pass"] is True  # honest baseline passes
    # Attacker relabels a substrate unit -> outside but leaves partition_hash stale.
    snap["taxonomy"]["partition"]["eidetic-works/sub0"] = "outside"
    res = _ev(snap)
    assert res["tamper"] is True
    assert res["pass"] is False


def test_attack1_relabel_nonqualifying_unit_is_inert():
    """Relabeling a NON-qualifying repo to outside (even with a correct rehash)
    cannot move the metric: (a) is applied only to (b)^(c)^(d)-qualifying units."""
    non_qual = unit("eidetic-works/fake", "substrate",
                    [env("agy", ["someref"])],          # single surface, no breadth
                    [increment("someref")])
    units = [qualifying_unit(f"eidetic-works/out{i}", "outside") for i in range(6)]
    units += [qualifying_unit(f"eidetic-works/sub{i}", "substrate") for i in range(4)]
    units.append(non_qual)
    before = _ev(snapshot(units))
    # Attacker relabels the non-qualifier outside AND rehashes (versioned move).
    snap = snapshot(units, extra_partition={"eidetic-works/fake": "outside"})
    after = _ev(snap)
    assert after["tamper"] is False
    assert after["numerator"] == before["numerator"]       # no inflation
    assert after["denominator"] == before["denominator"]
    assert after["outside_share"] == before["outside_share"]


# ── Attack 2: COMMIT-CHURN ──────────────────────────────────────────────────

def test_attack2_commit_churn_adds_no_qualifying_units():
    ref = "realcommit01"
    churn = [increment(f"churn{i}", numstat=[{"added": 1, "deleted": 0, "path": "x.py"}])
             for i in range(50)]
    u = unit("eidetic-works/repo", "outside", cross_vendor_carriers(ref),
             [increment(ref)] + churn)
    res = C.score_unit(u, C._FROZEN_VENDOR_SURFACES, PARAMS)
    assert res["qualifies"] is True
    assert [q["ref"] for q in res["qualifying_increments"]] == [ref]  # churn contributes 0


def test_attack2_below_median_stub_fails_nontriviality():
    stub = [{"added": 1, "deleted": 0, "path": "x.py"}]
    assert C.numstat_nontrivial(stub, PARAMS.L, PARAMS.M) is False
    big = [{"added": 50, "deleted": 0, "path": f"f{i}.py"} for i in range(3)]
    assert C.numstat_nontrivial(big, PARAMS.L, PARAMS.M) is True
    test_only = [{"added": 2, "deleted": 0, "path": "tests/test_x.py"}]
    assert C.numstat_nontrivial(test_only, PARAMS.L, PARAMS.M) is True


# ── Attack 3: REPO-MINT (fabricated traffic) ────────────────────────────────

@pytest.mark.parametrize("conclusion",
                         [None, "neutral", "skipped", "cancelled", "failure",
                          "timed_out", "action_required", "stale"])
def test_attack3_fabricated_traffic_fails_closed_on_ci(conclusion):
    """A minted repo can fabricate envelopes but not a genuine green CI. Every
    non-`success` CI enum fails closed => (d) fails => not in the denominator."""
    ref = "mintedref01"
    minted = unit("eidetic-works/minted", "outside",
                  cross_vendor_carriers(ref), [increment(ref, conclusion=conclusion)])
    res = C.score_unit(minted, C._FROZEN_VENDOR_SURFACES, PARAMS)
    assert res["qualifies"] is False
    # And it cannot move a fleet-level PASS.
    fleet = [qualifying_unit(f"eidetic-works/sub{i}", "substrate") for i in range(3)]
    fleet.append(minted)
    r = _ev(snapshot(fleet))
    assert r["numerator"] == 0 and r["pass"] is False


# ── Attack 4: GENUINE-TRAFFIC RE-POINT ──────────────────────────────────────

def test_attack4_genuine_traffic_repoint_not_bound_to_increment():
    """Real cross-vendor envelopes routed at a throwaway repo, but naming OTHER
    increments -> no envelope carries THIS increment's ref -> no causal edge."""
    u = unit("eidetic-works/throwaway", "outside",
             cross_vendor_carriers("OTHER_ref_abc"),      # real refs, wrong target
             [increment("SELF_ref_xyz")])
    res = C.score_unit(u, C._FROZEN_VENDOR_SURFACES, PARAMS)
    assert res["qualifies"] is False


# ── Attack 5: COORDINATION-THEATER ──────────────────────────────────────────

def test_attack5_unbound_envelopes_no_causal_edge():
    ref = "themacommit"
    # envelopes present but carry NO shipped ref (empty + a self-referencing relay id)
    theater = [env("agy", []), env("devin", ["relay_20260709_101112_deadbeef"])]
    u = unit("eidetic-works/theater", "outside", theater, [increment(ref)])
    res = C.score_unit(u, C._FROZEN_VENDOR_SURFACES, PARAMS)
    assert res["qualifies"] is False


# ── Attack 6: UNBOUND-BREADTH ───────────────────────────────────────────────

def test_attack6_unbound_second_vendor_fails():
    """A 2nd genuine surface exists in the repo but is neither a ref-carrier nor
    in the ref-carrier's thread => breadth not causally joined => no (c)."""
    ref = "breadthcommit"
    anchor = env("agy", [ref], rid="A1")
    co_windowed_devin = env("devin", ["UNRELATED"], rid="D9", reply=None)  # not bound, not threaded
    u = unit("eidetic-works/breadth", "outside", [anchor, co_windowed_devin], [increment(ref)])
    assert C.score_unit(u, C._FROZEN_VENDOR_SURFACES, PARAMS)["qualifies"] is False


def test_attack6_positive_control_thread_joined_breadth_qualifies():
    """Same two surfaces, but the devin envelope shares the anchor's thread
    (in_reply_to = anchor.id) => breadth is causally joined => qualifies."""
    ref = "breadthcommit"
    anchor = env("agy", [ref], rid="A1")
    devin_in_thread = env("devin", ["UNRELATED"], rid="D9", reply="A1")
    u = unit("eidetic-works/breadth", "outside", [anchor, devin_in_thread], [increment(ref)])
    assert C.score_unit(u, C._FROZEN_VENDOR_SURFACES, PARAMS)["qualifies"] is True


# ── Attack 7: BASELINE-SUPPRESSION + DENOMINATOR-SUPPRESSION ────────────────

def test_attack7a_suppressed_baseline_cannot_be_frozen():
    """Arrange-low: a zeroed baseline derives F=0/L=0/M=0 -> stringency fails ->
    no PASS is possible even against a 100%-outside snapshot."""
    degen = C.derive_params({"outside_units": 0, "stddev": 0.0, "p50_lines": 0, "p50_files": 0})
    ok, reasons = C.validate_stringency(degen)
    assert ok is False and any("F" in r for r in reasons)
    fat = [qualifying_unit(f"eidetic-works/out{i}", "outside") for i in range(8)]
    res = C.evaluate(snapshot(fat), degen, 0.0)
    assert res["gates"]["stringency_ok"] is False
    assert res["pass"] is False


def test_attack7b_sub_dmin_denominator_is_inconclusive():
    """Shrinking the qualifying denominator below D_min => inconclusive =>
    NOT-PASS, even at a 100% outside share."""
    two = [qualifying_unit(f"eidetic-works/out{i}", "outside") for i in range(2)]
    res = _ev(snapshot(two))
    assert res["denominator"] == 2 and res["outside_share"] == 1.0
    assert res["inconclusive"] is True and res["pass"] is False


def test_attack7b_no_denominator_exclusion_knob():
    """The scorer counts EVERY (b)^(c)^(d) unit; an injected 'excluded'/'hidden'
    field cannot shrink the denominator (denominator-suppression defense)."""
    units = [qualifying_unit(f"eidetic-works/sub{i}", "substrate") for i in range(3)]
    base = _ev(snapshot(units))["denominator"]
    units[0]["excluded"] = True
    units[1]["hidden"] = True
    units[2]["suppress"] = True
    assert _ev(snapshot(units))["denominator"] == base == 3


# ── Attack 8: SINGLE-VENDOR-DOMINANCE ───────────────────────────────────────

def test_attack8_single_vendor_dominance_fails():
    """K envelopes span >=2 surfaces but one supplies > X% (4/5 = 80% > 60%)."""
    ref = "domcommit"
    carriers = [env("agy", [ref]) for _ in range(4)] + [env("devin", [ref])]
    u = unit("eidetic-works/dom", "outside", carriers, [increment(ref)])
    assert C.score_unit(u, C._FROZEN_VENDOR_SURFACES, PARAMS)["qualifies"] is False


def test_attack8_positive_control_balanced_surfaces_qualify():
    ref = "domcommit"
    carriers = [env("agy", [ref]) for _ in range(2)] + [env("devin", [ref]) for _ in range(2)]
    u = unit("eidetic-works/dom", "outside", carriers, [increment(ref)])
    assert C.score_unit(u, C._FROZEN_VENDOR_SURFACES, PARAMS)["qualifies"] is True


# ── Attack 9: NULL / DEGENERATE-THRESHOLD ───────────────────────────────────

def test_attack9_degenerate_thresholds_fail_stringency():
    degen = C.Params(delta=0.01, F=1, L=1, M=1, K=2, X=0.60, D_min=3)
    ok, reasons = C.validate_stringency(degen)
    assert ok is False
    joined = " ".join(reasons)
    assert "delta" in joined and "F" in joined and "L" in joined and "M" in joined


def test_attack9_degenerate_thresholds_cannot_manufacture_pass():
    degen = C.Params(delta=0.01, F=1, L=1, M=1, K=2, X=0.60, D_min=3)
    fat = [qualifying_unit(f"eidetic-works/out{i}", "outside") for i in range(8)]
    res = C.evaluate(snapshot(fat), degen, 0.0)
    assert res["gates"]["stringency_ok"] is False
    assert res["pass"] is False


# ── Committed taxonomy file integrity ───────────────────────────────────────

def test_committed_taxonomy_hash_is_consistent():
    """The on-disk config/census/taxonomy.yaml partition_hash matches its body,
    and any relabel of that body changes the hash (tamper-evident)."""
    tax_path = Path(__file__).resolve().parents[2] / "config" / "census" / "taxonomy.yaml"
    tax = C.load_taxonomy(tax_path)
    assert tax["partition_hash"] == C.taxonomy_partition_hash(tax)
    tampered = copy.deepcopy(tax)
    # relabel the substrate itself -> outside: hash must change
    tampered["partition"]["eidetic-works/mcp-server-nucleus"] = "outside"
    assert C.taxonomy_partition_hash(tampered) != tax["partition_hash"]


# ── Attack F: FORGED-ENVELOPE (signature) — pure scorer, stamped snapshot ────
#
# The Goodhart re-attack: hand-write two JSON files naming a target commit with
# `from: agy` / `from: devin`. In v2.1 those files carry no VALID dispatch_sig,
# so capture stamps them vendor_sig=absent|invalid and the pure scorer treats
# them as invisible to clause (c). All of the following must NOT qualify.

def test_attackF_unsigned_pair_no_qualify():
    """Two unsigned cross-vendor ref-carriers (vendor_sig=absent) => invisible to
    (c) => no signed ref-carrier => no qualify."""
    ref = "forgedref01"
    u = unit("eidetic-works/forge", "outside",
             forged_carriers(ref, vendor_sig="absent"), [increment(ref)])
    assert C.score_unit(u, C._FROZEN_VENDOR_SURFACES, PARAMS)["qualifies"] is False


def test_attackF_wrongkey_pair_no_qualify():
    """Two cross-vendor carriers signed with the WRONG key => capture stamps
    vendor_sig=invalid => invisible to (c) => no qualify."""
    ref = "forgedref02"
    u = unit("eidetic-works/forge", "outside",
             forged_carriers(ref, vendor_sig="invalid"), [increment(ref)])
    assert C.score_unit(u, C._FROZEN_VENDOR_SURFACES, PARAMS)["qualifies"] is False


def test_attackF_lifted_sig_carrier_no_qualify():
    """A real signature lifted onto a different ref/vendor is stamped invalid at
    capture: only the one genuine surface remains => breadth fails => no qualify."""
    ref = "forgedref03"
    genuine_devin = env("devin", [ref], vendor_sig="valid")
    lifted_agy = env("agy", [ref], vendor_sig="invalid")  # sig didn't verify
    u = unit("eidetic-works/forge", "outside",
             [genuine_devin, lifted_agy], [increment(ref)])
    assert C.score_unit(u, C._FROZEN_VENDOR_SURFACES, PARAMS)["qualifies"] is False


def test_attackF_handwritten_cursor_windsurf_manufacture_no_surface():
    """Adjacent hole: hand-written `from: cursor` / `from: windsurf` files can no
    longer manufacture a second genuine surface (they are unsigned)."""
    ref = "forgedref04"
    genuine = env("agy", [ref], vendor_sig="valid")
    fake_cursor = env("cursor", [ref], vendor_sig="absent")
    fake_windsurf = env("windsurf", [ref], vendor_sig="absent")
    u = unit("eidetic-works/forge", "outside",
             [genuine, fake_cursor, fake_windsurf], [increment(ref)])
    # 1 valid surface (agy); the two unsigned surfaces are invisible => no breadth.
    assert C.score_unit(u, C._FROZEN_VENDOR_SURFACES, PARAMS)["qualifies"] is False


def test_attackF_unsigned_carrier_cannot_anchor_path_b():
    """A forged unsigned ref-carrier cannot anchor a Path-B thread of real
    envelopes: the anchor itself is filtered out, so there is no ref-carrier."""
    ref = "forgedref05"
    forged_anchor = env("agy", [ref], rid="FA", vendor_sig="absent")
    real_devin = env("devin", ["UNRELATED"], rid="RD", reply="FA", vendor_sig="valid")
    real_agy = env("agy", ["UNRELATED2"], rid="RA", reply="FA", vendor_sig="valid")
    u = unit("eidetic-works/forge", "outside",
             [forged_anchor, real_devin, real_agy], [increment(ref)])
    assert C.score_unit(u, C._FROZEN_VENDOR_SURFACES, PARAMS)["qualifies"] is False


def test_attackF_verbatim_replay_deduped_by_dispatch_sig():
    """Verbatim whole-body replay shares its dispatch_sig and is deduped: copying
    one signed agy envelope 9 more times cannot inflate the counted K past 2."""
    ref = "replayref06"
    agy = env("agy", [ref], dispatch_sig="agy-uniq")
    devin = env("devin", [ref], dispatch_sig="devin-uniq")
    base = C.increment_causal(ref, [agy, devin], C._FROZEN_VENDOR_SURFACES, PARAMS.K, PARAMS.X)
    assert base["ok"] is True and base["evidence"]["counted"] == 2
    replays = [env("agy", [ref], dispatch_sig="agy-uniq") for _ in range(9)]
    infl = C.increment_causal(ref, [agy, devin] + replays,
                              C._FROZEN_VENDOR_SURFACES, PARAMS.K, PARAMS.X)
    assert infl["evidence"]["counted"] == 2  # deduped, not 11


def test_attackF_positive_two_signed_surfaces_qualify():
    """Positive control: two GENUINELY signed agy + devin carriers => qualifies."""
    ref = "genuineref07"
    u = unit("eidetic-works/genuine", "outside",
             cross_vendor_carriers(ref), [increment(ref)])
    assert C.score_unit(u, C._FROZEN_VENDOR_SURFACES, PARAMS)["qualifies"] is True


def test_attackF_unsigned_pair_cannot_move_fleet_pass():
    """Fleet-level: a forged outside unit cannot enter the numerator or move a
    PASS — it never qualifies (b)^(c)^(d)."""
    fleet = [qualifying_unit(f"eidetic-works/sub{i}", "substrate") for i in range(3)]
    forged = unit("eidetic-works/forge", "outside",
                  forged_carriers("forgedref08", vendor_sig="absent"),
                  [increment("forgedref08")])
    fleet.append(forged)
    res = _ev(snapshot(fleet))
    assert res["numerator"] == 0 and res["pass"] is False


# ── Attack F (real signer): stdlib verifier parity + binding, temp brain ─────
#
# These exercise the ACTUAL HMAC path against a real SignatureGuard over a
# hermetic temp brain (needs PYTHONPATH=src; skips cleanly otherwise), proving
# the census stdlib verifier agrees with the signer and that lifted / status-
# flipped / wrong-key / corrupted signatures do not verify.

def _load_signature_guard():
    try:
        from mcp_server_nucleus.runtime.auth.signature_guard import SignatureGuard
    except Exception:  # pragma: no cover - offline-pure environments skip
        pytest.skip("SignatureGuard not importable (needs PYTHONPATH=src)")
    return SignatureGuard


def _signed_body(guard, *, vendor="devin", model="glm", prompt_digest="sha256:abc",
                 artifact_refs=None, result="result-text", status="ok", ts=1720000000):
    artifact_refs = artifact_refs if artifact_refs is not None else ["PR#123"]
    result_sha256 = C._sha256_hex(result)
    sig = guard.sign_vendor_dispatch(
        vendor=vendor, model=model, prompt_digest=prompt_digest,
        artifact_refs=artifact_refs, result_sha256=result_sha256, status=status, ts=ts,
    )
    return {
        "vendor": vendor, "model": model, "prompt_digest": prompt_digest,
        "result": result, "result_sha256": result_sha256, "status": status,
        "ts": ts, "artifact_refs": artifact_refs, "dispatch_sig": sig,
    }


def test_realsig_stdlib_verifier_parity(tmp_path):
    """The census stdlib recomputation agrees byte-for-byte with the src signer,
    and verify_dispatch_sig => valid over the signed body."""
    SignatureGuard = _load_signature_guard()
    brain = tmp_path / ".brain"
    guard = SignatureGuard(brain_path=brain)
    key = C.read_brain_key(brain)
    assert key is not None and len(key) == 32
    body = _signed_body(guard, artifact_refs=["PR#7", "abc123"])
    msg = C._vendor_dispatch_message(
        body["vendor"], body["model"], body["prompt_digest"],
        body["artifact_refs"], body["result_sha256"], body["status"], body["ts"])
    assert C._dispatch_hmac(key, msg) == body["dispatch_sig"]
    assert C.verify_dispatch_sig(body, key) == "valid"


def test_realsig_load_secret_persists_key_across_instances(tmp_path):
    """Hardening (1): _load_secret MINTS-AND-PERSISTS, so a fresh guard (the
    out-of-process capture) and the census stdlib reader share the SAME key."""
    SignatureGuard = _load_signature_guard()
    brain = tmp_path / ".brain"
    g1 = SignatureGuard(brain_path=brain)
    body = _signed_body(g1)
    g2 = SignatureGuard(brain_path=brain)   # simulates the separate capture process
    assert g2.verify_vendor_dispatch(
        body["vendor"], body["model"], body["prompt_digest"], body["artifact_refs"],
        body["result_sha256"], body["status"], body["ts"], body["dispatch_sig"]) is True
    key = C.read_brain_key(brain)
    assert C.verify_dispatch_sig(body, key) == "valid"


def test_realsig_lifted_onto_different_refs_is_invalid(tmp_path):
    SignatureGuard = _load_signature_guard()
    brain = tmp_path / ".brain"
    guard = SignatureGuard(brain_path=brain)
    key = C.read_brain_key(brain)
    body = _signed_body(guard, artifact_refs=["PR#100"])
    lifted = dict(body)
    lifted["artifact_refs"] = ["PR#999"]  # same sig, different target increment
    assert C.verify_dispatch_sig(lifted, key) == "invalid"


def test_realsig_status_flipped_is_invalid(tmp_path):
    """A timed_out capture cannot be flipped to ok: status is signed."""
    SignatureGuard = _load_signature_guard()
    brain = tmp_path / ".brain"
    guard = SignatureGuard(brain_path=brain)
    key = C.read_brain_key(brain)
    body = _signed_body(guard, status="timed_out")
    flipped = dict(body)
    flipped["status"] = "ok"
    assert C.verify_dispatch_sig(flipped, key) == "invalid"


def test_realsig_wrong_key_is_invalid(tmp_path):
    SignatureGuard = _load_signature_guard()
    guard = SignatureGuard(brain_path=tmp_path / "b1" / ".brain")
    body = _signed_body(guard)
    _ = SignatureGuard(brain_path=tmp_path / "b2" / ".brain")  # mints a different key
    key2 = C.read_brain_key(tmp_path / "b2" / ".brain")
    assert key2 is not None
    assert C.verify_dispatch_sig(body, key2) == "invalid"


def test_realsig_corrupted_byte_is_invalid(tmp_path):
    """The signed-smoke rejection in miniature: flip one hex char => invalid."""
    SignatureGuard = _load_signature_guard()
    brain = tmp_path / ".brain"
    guard = SignatureGuard(brain_path=brain)
    key = C.read_brain_key(brain)
    body = _signed_body(guard)
    assert C.verify_dispatch_sig(body, key) == "valid"
    sig = body["dispatch_sig"]
    corrupt = dict(body)
    corrupt["dispatch_sig"] = ("0" if sig[0] != "0" else "1") + sig[1:]
    assert C.verify_dispatch_sig(corrupt, key) == "invalid"


def test_realsig_absent_key_or_missing_sig_is_absent(tmp_path):
    SignatureGuard = _load_signature_guard()
    brain = tmp_path / ".brain"
    guard = SignatureGuard(brain_path=brain)
    key = C.read_brain_key(brain)
    body = _signed_body(guard)
    assert C.verify_dispatch_sig(body, None) == "absent"     # no key on the brain
    nosig = dict(body)
    nosig.pop("dispatch_sig")
    assert C.verify_dispatch_sig(nosig, key) == "absent"     # unsigned body


def test_realsig_sign_raises_without_key(tmp_path):
    """Hardening (2): sign_vendor_dispatch RAISES rather than emitting the
    'unsigned-placeholder' fallback when the key is unavailable."""
    SignatureGuard = _load_signature_guard()
    guard = SignatureGuard(brain_path=tmp_path / ".brain")
    guard._secret_key = b""  # simulate an unavailable key
    with pytest.raises(RuntimeError):
        guard.sign_vendor_dispatch(
            vendor="devin", model="glm", prompt_digest="sha256:x",
            artifact_refs=["PR#1"], result_sha256="deadbeef", status="ok", ts=1)


# ── fix-d: NON-TRIVIALITY IS A LIVE PREDICATE (exercised_by_c bypass gone) ────

def test_fixd_no_exercised_by_c_param():
    import inspect
    assert "exercised_by_c" not in inspect.signature(C.numstat_nontrivial).parameters


def test_fixd_empty_diff_with_genuine_coordination_no_qualify():
    """Headline fix-d: an EMPTY-diff increment with genuine signed cross-vendor
    coordination + green CI must NOT qualify (the old bypass qualified it)."""
    ref = "emptyref01"
    u = unit("eidetic-works/empty", "outside", cross_vendor_carriers(ref),
             [increment(ref, numstat=[])])
    assert C.score_unit(u, C._FROZEN_VENDOR_SURFACES, PARAMS)["qualifies"] is False


def test_fixd_generated_only_diff_no_qualify():
    ref = "genref02"
    gen = [{"added": 900, "deleted": 0, "path": "dist/bundle.min.js"},
           {"added": 400, "deleted": 0, "path": "package-lock.json"}]
    u = unit("eidetic-works/gen", "outside", cross_vendor_carriers(ref),
             [increment(ref, numstat=gen)])
    assert C.score_unit(u, C._FROZEN_VENDOR_SURFACES, PARAMS)["qualifies"] is False


def test_fixd_sub_LM_nontest_diff_no_qualify():
    ref = "subref03"
    small = [{"added": 5, "deleted": 0, "path": "src/a.py"}]  # < L, < M, no test
    u = unit("eidetic-works/sub", "outside", cross_vendor_carriers(ref),
             [increment(ref, numstat=small)])
    assert C.score_unit(u, C._FROZEN_VENDOR_SURFACES, PARAMS)["qualifies"] is False


def test_fixd_LM_diff_qualifies():
    ref = "bigref04"
    big = [{"added": 20, "deleted": 0, "path": f"src/m{i}.py"} for i in range(3)]
    u = unit("eidetic-works/big", "outside", cross_vendor_carriers(ref),
             [increment(ref, numstat=big)])
    assert C.score_unit(u, C._FROZEN_VENDOR_SURFACES, PARAMS)["qualifies"] is True


def test_fixd_testfile_diff_qualifies():
    ref = "testref05"
    tf = [{"added": 3, "deleted": 0, "path": "tests/test_thing.py"}]
    u = unit("eidetic-works/tf", "outside", cross_vendor_carriers(ref),
             [increment(ref, numstat=tf)])
    assert C.score_unit(u, C._FROZEN_VENDOR_SURFACES, PARAMS)["qualifies"] is True


# ── fix-a: RELABEL GATING (no self-service rehash; freeze binding) ───────────

def test_fixa_no_rehash_command():
    """The self-service `rehash` subcommand and cmd_rehash are removed; the other
    subcommands still parse."""
    assert not hasattr(C, "cmd_rehash")
    parser = C.build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["rehash"])
    ns = parser.parse_args(["snapshot"])
    assert ns.cmd == "snapshot"


def test_fixa_post_freeze_relabel_with_consistent_hash_is_tamper():
    """A post-freeze relabel — even with an internally-consistent hand-rehash
    (recorded == recomputed, so the self-consistency guard is silent) — trips the
    FROZEN-partition binding => tamper => NOT-PASS."""
    units = [qualifying_unit(f"eidetic-works/out{i}", "outside") for i in range(6)]
    units += [qualifying_unit(f"eidetic-works/sub{i}", "substrate") for i in range(4)]
    snap = snapshot(units)
    frozen_hash = C.taxonomy_partition_hash(snap["taxonomy"])
    assert C.evaluate(snap, PARAMS, FROZEN_BASELINE, frozen_hash)["pass"] is True
    # Attacker relabels a substrate unit -> outside AND hand-rehashes consistently.
    snap["taxonomy"]["partition"]["eidetic-works/sub0"] = "outside"
    snap["taxonomy"]["partition_hash"] = C.taxonomy_partition_hash(snap["taxonomy"])
    res = C.evaluate(snap, PARAMS, FROZEN_BASELINE, frozen_hash)
    assert res["tamper"] is True    # freeze binding catches the moved partition
    assert res["pass"] is False


def test_fixa_prefreeze_relabel_needs_matching_hash():
    """Pre-freeze (no frozen hash): a relabel lands ONLY with a matching
    recomputed hash; leaving the hash stale trips the self-consistency guard."""
    units = [qualifying_unit(f"eidetic-works/out{i}", "outside") for i in range(6)]
    units += [qualifying_unit(f"eidetic-works/sub{i}", "substrate") for i in range(4)]
    snap = snapshot(units)
    snap["taxonomy"]["partition"]["eidetic-works/sub0"] = "outside"
    snap["taxonomy"]["partition_hash"] = C.taxonomy_partition_hash(snap["taxonomy"])
    assert C.evaluate(snap, PARAMS, FROZEN_BASELINE)["tamper"] is False
    # Now change another label WITHOUT rehashing -> stale hash -> tamper.
    snap["taxonomy"]["partition"]["eidetic-works/sub1"] = "outside"
    assert C.evaluate(snap, PARAMS, FROZEN_BASELINE)["tamper"] is True
