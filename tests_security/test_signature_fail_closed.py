"""The signature guard must fail closed with no key, not open (AU-6).

`_compute_hmac` used to return the fixed string "unsigned-placeholder" when the
secret was falsy. `verify_dict` and `verify_payload` compute the expected value by
calling `sign_*`, so with a falsy key BOTH sides became that same constant and
`compare_digest` returned True. Sending that literal string as the signature
validated any payload at all.

A falsy key is reachable: the file's own comment describes a 0-byte
`secrets/.ipc_secret` left by a racing first-mint.

The same class already had the right posture one method away —
`sign_vendor_dispatch` raises rather than emitting the placeholder, on the stated
grounds that "an un-verifiable placeholder would be worse than a missing
signature". This brings the rest of the class in line.

    PYTHONPATH=src python3 -m pytest tests_security -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

guard_mod = pytest.importorskip("mcp_server_nucleus.runtime.auth.signature_guard")
SignatureGuard = guard_mod.SignatureGuard

SENTINEL = "unsigned-placeholder"


@pytest.fixture
def keyless(tmp_path):
    """A guard whose secret is empty, the 0-byte-file case."""
    g = SignatureGuard(brain_path=tmp_path)
    g._secret_key = b""
    return g


@pytest.fixture
def keyed(tmp_path):
    return SignatureGuard(brain_path=tmp_path)


# --- the bypass itself ----------------------------------------------------

def test_the_sentinel_no_longer_validates_an_arbitrary_payload(keyless):
    """The exact attack: send the literal sentinel as the signature."""
    assert keyless.verify_dict({"amount": 1_000_000, "to": "attacker"}, SENTINEL) is False


def test_the_sentinel_no_longer_validates_an_arbitrary_task(keyless):
    assert keyless.verify_payload("task-1", "rm -rf /", SENTINEL) is False


def test_verification_fails_closed_for_any_signature_without_a_key(keyless):
    for candidate in (SENTINEL, "deadbeef", "0" * 32, "x"):
        assert keyless.verify_dict({"k": "v"}, candidate) is False


def test_signing_raises_rather_than_emitting_a_placeholder(keyless):
    with pytest.raises(RuntimeError, match="HMAC secret"):
        keyless.sign_dict({"k": "v"})
    with pytest.raises(RuntimeError, match="HMAC secret"):
        keyless.sign_payload("task-1", "do a thing")


def test_no_method_can_still_produce_the_sentinel(keyless):
    """Nothing should hand a caller a signature that means 'unsigned'."""
    for call in (lambda: keyless.sign_dict({"k": "v"}),
                 lambda: keyless.sign_payload("t", "d")):
        try:
            assert call() != SENTINEL
        except RuntimeError:
            pass  # raising is the intended behaviour


# --- the normal path must be untouched ------------------------------------

def test_a_real_key_still_signs_and_verifies(keyed):
    data = {"task": "deploy", "env": "prod"}
    sig = keyed.sign_dict(data)
    assert sig and sig != SENTINEL and len(sig) == 32
    assert keyed.verify_dict(data, sig) is True


def test_a_tampered_payload_still_fails(keyed):
    sig = keyed.sign_dict({"amount": 1})
    assert keyed.verify_dict({"amount": 1_000_000}, sig) is False


def test_an_empty_signature_is_still_rejected(keyed):
    assert keyed.verify_dict({"k": "v"}, "") is False
    assert keyed.verify_payload("t", "d", "") is False
