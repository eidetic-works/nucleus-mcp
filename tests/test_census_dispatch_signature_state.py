"""The census must actually read the signature it was documented to check.

Why this exists: vendor_dispatch stamps `dispatch_sig` on every envelope, and
its docstring promises the envelope "will not count in the census (fail-closed
at the census, not at dispatch)". That promise was never implemented.
capture_census.py had ZERO references to signatures, and
`verify_vendor_dispatch` -- fully written and constant-time -- had zero callers
anywhere in the repo. A forged envelope could not be detected, because nothing
read the field.

First live reading after wiring it: 336 verified, 1156 unsigned, 0 unverified.
The signing mechanism was working the whole time; it had no reader.

The load-bearing test here is the TAMPERED one. A signature checker that has
only ever been observed saying "verified" is indistinguishable from one that
returns True unconditionally.
"""

import json

from mcp_server_nucleus.runtime.capture_census import _dispatch_sig_state


def _signed_body():
    from mcp_server_nucleus.runtime.auth.signature_guard import get_signature_guard
    fields = dict(vendor="devin", model="glm", prompt_digest="sha256:abc",
                  artifact_refs=["docs/x.md"], result_sha256="d" * 64,
                  status="ok", ts=1700000000)
    sig = get_signature_guard().sign_vendor_dispatch(**fields)
    return {**fields, "dispatch_sig": sig}


def test_an_envelope_with_no_signature_is_unsigned():
    """'unsigned' must stay distinct from 'unverified': no claim made is not
    the same as a claim that does not hold."""
    assert _dispatch_sig_state({"body": json.dumps({"vendor": "devin"})}) == "unsigned"


def test_a_correctly_signed_envelope_verifies():
    assert _dispatch_sig_state({"body": json.dumps(_signed_body())}) == "verified"


def test_a_TAMPERED_envelope_is_unverified():
    """THE CONTROL. Flip one field after signing; the signature must no longer
    hold. Without this, 'verified' could mean the checker never says no."""
    body = _signed_body()
    body["result_sha256"] = "f" * 64  # forge the result the signature binds
    assert _dispatch_sig_state({"body": json.dumps(body)}) == "unverified"


def test_a_garbage_signature_is_unverified():
    body = _signed_body()
    body["dispatch_sig"] = "not-a-real-signature"
    assert _dispatch_sig_state({"body": json.dumps(body)}) == "unverified"


def test_a_json_STRING_body_is_parsed():
    """The bug this function shipped with. Envelope bodies are stored as JSON
    strings, not nested dicts. The first version handled only the dict case and
    reported all 336 genuinely-signed envelopes as 'unsigned' -- a checker
    returning a confident zero because it read the wrong shape."""
    assert _dispatch_sig_state({"body": json.dumps(_signed_body())}) == "verified"
    # and the dict form must keep working
    assert _dispatch_sig_state({"body": _signed_body()}) == "verified"


def test_a_broken_verifier_reports_unverifiable_not_unverified():
    """OPPOSED: if the checker itself cannot run, that says nothing about the
    envelope. Reporting 'unverified' would blame the data for a broken checker
    -- the same mistake as calling an absent witness log a definitive 'no'."""
    body = _signed_body()
    body["ts"] = "not-an-int"  # forces int() to raise inside the classifier
    assert _dispatch_sig_state({"body": json.dumps(body)}) == "unverifiable"
