"""The IPC provider must not advertise a security feature it does not have.

Its class docstring listed "HMAC signatures for integrity" under Security
Features. `_compute_signature` is implemented -- and has ZERO callers. No token
field stores a signature and nothing verifies one, so token contents are not
integrity-protected.

The gap itself is survivable. The CLAIM is not: a caller reading that list would
reasonably stop worrying about token tampering, which is exactly the reliance a
false security claim buys and cannot pay for.

Wiring real HMAC integrity is a design change (token schema, a check in
validate_token, a migration for in-flight tokens). Removing the false claim is
not, so that is what was done, with the gap stated explicitly instead of
implied.
"""

import inspect


def _doc():
    from mcp_server_nucleus.runtime.auth.ipc_provider import IPCAuthProvider
    return IPCAuthProvider.__doc__ or ""


def test_does_not_claim_hmac_integrity_it_does_not_have():
    assert "HMAC signatures for integrity" not in _doc(), (
        "the class advertises HMAC token integrity; _compute_signature has no "
        "callers and no token field stores a signature"
    )


def test_the_gap_is_stated_not_merely_omitted():
    """Deleting the line silently would leave the next reader to rediscover
    this. The docstring must say the machinery exists and is unwired."""
    d = _doc()
    # Substring checks are line-wrap sensitive; the docstring wraps between
    # "ZERO" and "callers".
    flat = " ".join(d.split())
    assert "_compute_signature" in flat and "ZERO callers" in flat


def test_the_premise_still_holds_compute_signature_is_uncalled():
    """CONTROL. If someone wires it later, this fails and the docstring is due
    an update -- so the note cannot quietly rot into being wrong."""
    import subprocess
    from pathlib import Path
    repo = Path(__file__).resolve().parents[2]
    r = subprocess.run(
        ["grep", "-rn", "_compute_signature",
         "mcp-server-nucleus/src", "scripts"],
        capture_output=True, text=True, cwd=str(repo),
    )
    # Exclude: the definition, compiled artifacts, and the DOCSTRING that
    # explains there are no callers. The first version of this check counted
    # its own documentation as a caller -- a checker matching the artifact its
    # own process wrote, which is the failure it exists to catch.
    calls = [
        ln for ln in r.stdout.splitlines()
        if ln.strip()
        and "def _compute_signature" not in ln
        and "__pycache__" not in ln
        and ".pyc" not in ln
        and "`_compute_signature`" not in ln
    ]
    assert not calls, (
        f"_compute_signature now HAS callers: {calls[:3]} — the docstring note "
        f"saying it is unwired is stale and must be updated"
    )


def test_validate_token_request_hash_is_dead_weight_not_a_dropped_check():
    """The related finding, pinned so its severity is not re-inflated. No caller
    passes request_hash to validate_token; agent.py sends it to consume_token,
    which stores it. Dead parameter, not a silently skipped verification."""
    from mcp_server_nucleus.runtime.auth import ipc_provider
    src = inspect.getsource(ipc_provider.IPCAuthProvider.validate_token)
    assert "request_hash" in src, "parameter gone — update this test"
    body = src.split("\n", 1)[1]
    uses = [l for l in body.splitlines()
            if "request_hash" in l and "request_hash:" not in l]
    assert not uses, f"validate_token now USES request_hash: {uses}"
