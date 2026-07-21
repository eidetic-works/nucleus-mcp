"""Agent-OS probe: can one model call run THROUGH the gateway with NO API key?

The decision-relevant question for the Agent OS is whether an agent's cognition
can be mediated by Nucleus on a *subscription / OAuth* bearer — no per-token API
key. This probe routes ONE real generation through ``NucleusGateway`` using the
``claude_oauth`` provider (Max-plan OAuth bearer via ``oauth.exchange``) with the
offline stub explicitly OFF, and reports exactly where the path lands:

  - engine == "CLAUDE_OAUTH" and stubbed is False → a REAL no-API-key call
    happened (subscription cognition through the membrane). WORKING.
  - engine == "STUB" with note "unavailable:ClaudeOAuthError" → the wiring is
    real and was attempted, but no valid bearer is resolvable in this env
    (expired/absent token). NOT REACHABLE — needs a fresh Claude.app sessionKey
    (browser login) to re-mint, or the remote shim (oauth.nucleusos.dev) up.

It asserts NO ``*_API_KEY`` env var is set, so a success is provably keyless.

Run:  NUCLEUS_LLM_PROVIDER=claude_oauth python -m \
        mcp_server_nucleus.runtime.agent_os.oauth_probe

Exit 0 iff a real, non-stubbed, no-API-key generation went through the gateway.
This is a read-only diagnostic — it writes only to an isolated temp brain.
"""
from __future__ import annotations

import os
import tempfile

_API_KEY_VARS = (
    "NUCLEUS_ANTHROPIC_API_KEY",
    "ANTHROPIC_API_KEY",
    "GEMINI_API_KEY",
    "NUCLEUS_GROQ_API_KEY",
)


def probe() -> int:
    # Route through the subscription path; never let the offline stub mask a
    # real provider outcome; isolate all writes to a throwaway brain.
    os.environ.setdefault("NUCLEUS_LLM_PROVIDER", "claude_oauth")
    os.environ["NUCLEUS_AGENT_OS_STUB_LLM"] = "0"
    os.environ.setdefault("NUCLEUS_DISABLE_ARTERY_4", "1")
    os.environ["NUCLEUS_BRAIN_PATH"] = tempfile.mkdtemp(prefix="agent_os_oauth_probe_")

    keyed = [k for k in _API_KEY_VARS if os.environ.get(k)]
    from .boot import NucleusGateway

    gw = NucleusGateway(system_instruction="Reply in one short sentence.")
    res = gw.generate(
        "Say the single word ALIVE and nothing else.",
        session_id="oauth-probe",
        agent_id="cell-oauth",
    )

    print("=" * 72)
    print("AGENT OS — NO-API-KEY (SUBSCRIPTION/OAUTH) GATEWAY PROBE")
    print("=" * 72)
    print(f"  provider requested : {os.environ['NUCLEUS_LLM_PROVIDER']}")
    print(f"  API-key env vars   : {keyed or 'NONE (call is provably keyless)'}")
    print(f"  engine             : {res.engine}")
    print(f"  model              : {res.model}")
    print(f"  mediated (event)   : {res.mediated}  event_id={res.event_id}")
    print(f"  stubbed provider   : {res.stubbed}")
    print(f"  note               : {res.note}")
    print(f"  text               : {res.text[:160]!r}")

    real_keyless = (not res.stubbed) and (not keyed) and res.engine == "CLAUDE_OAUTH"
    print("-" * 72)
    if real_keyless:
        print("  VERDICT: REAL no-API-key model call ran THROUGH the gateway. WORKING.")
        return 0
    if res.engine == "STUB" and "ClaudeOAuthError" in (res.note or ""):
        print("  VERDICT: wiring REAL + attempted, but no valid OAuth bearer here.")
        print("  NEXT STEP: place a fresh Claude.app sessionKey and re-mint —")
        print("    python -c \"from mcp_server_nucleus.oauth import exchange as e; \\")
        print("      print(e.get_access_token('bespoq_cowork', session_key='<sessionKey>'))\"")
        print("    (or bring the remote shim oauth.nucleusos.dev back up), then re-run.")
        return 2
    print("  VERDICT: gateway did not complete a keyless OAuth call (see note).")
    return 1


if __name__ == "__main__":
    raise SystemExit(probe())
