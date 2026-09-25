"""MCP tool facade for cross-vendor dispatch — the agent-facing delegate.

Exposes ``nucleus_delegate`` — a first-class MCP tool ANY agent connected to
nucleus sees in its tool list, so it can hand work to a cheap/diverse
cross-vendor lane (``devin``/GLM for builds, ``agy``/Gemini for a diverse
review / second-opinion lens) without knowing the CLI substrate exists.

This is a THIN facade over ``runtime.vendor_dispatch`` — it does NOT
reimplement dispatch, capture, or the enablement gate; it wraps them so the
agent surface is one MCP tool call instead of a shell-out.

Actions:
  dispatch - Hand a task to a cross-vendor lane.
      params: {vendor, prompt, artifact_ref, mode?, model?, expect_paths?, to?, timeout_s?}
      REQUIRED: vendor ∈ 'agy'|'devin', prompt, artifact_ref.
      mode ∈ 'write'|'read' (default 'write'):
        write = the vendor CHANGES things (edit files, run commands, build/fix).
        read  = the vendor only LOOKS and REPORTS (analyze/summarize); no file changes.
        When unsure use 'write': a read task still works in write mode, but a write
        task silently does NOTHING in read mode.
      model? — optional. Defaults to the vendor's verified model
        (agy → gemini-3.1-pro-high, devin → swe-2-max). These are ALREADY the
        defaults, so omitting model is sufficient; pass it only to be explicit or
        to override; pass "glm-5-2" to use GLM-5.2 High instead. The response
        echoes model_id — read model_id (NOT model_family) to confirm which model
        ran. A cross-wired model (e.g. glm-5-2 with agy) is rejected with the
        valid ids named.
      artifact_ref — a commit SHA / PR# / file path to bind the result to. No commit
        yet (a from-scratch build)? Pass the repo-relative path you will write,
        e.g. src/foo.py.
      expect_paths? — optional list of file paths you expect the vendor to change.
        If you pass them and the vendor changes none, status comes back NOT success
        ("no_files_touched") even if it narrated success. Without expect_paths,
        success means only that the vendor produced output — not that it edited
        anything, so ALWAYS confirm with your own `git diff`. (Paths are checked in
        the nucleus server process's working dir; pass paths valid there.)
      timeout_s? — optional int, seconds. Per-dispatch subprocess timeout. 0 means
        no timeout (the subprocess timeout becomes None and the CLI --print-timeout
        gets a 24h ceiling). Defaults to the executor's default (env
        NUCLEUS_VENDOR_TIMEOUT_S, else 3600s) if omitted. The response echoes the
        effective timeout used as `timeout_s` so you can verify the setting took
        effect rather than inferring it from success.
      You never pass CLI flags — the tool injects the right permissions per vendor.
  review   - Independent, different-model verdict on pasted code / a diff.
      params: {content, ref?, vendor?, model?, to?}
      content REQUIRED (paste the code/diff inline). Default vendor agy (Gemini,
      model gemini-3.1-pro-high) — a genuinely different model from the devin/GLM
      builder, so the review is diverse. Read-only, edits nothing. Returns a terse
      two-line verdict. For a devin/GLM second opinion pass vendor='devin'.
  list     - Show vendors, their selectable_models + default_model, the mode
      vocabulary, and whether cross-vendor is enabled. Needs no setup — call it
      first.
  plan_review_loop - Multi-round cross-vendor plan drafting + adversarial review.
      params: {prompt, author_vendor?, reviewer_vendor?, max_rounds?, context_files?,
               accepted_tradeoffs?, approval_criteria?, effort_level?, sandbox_test_cmd?,
               tiebreaker_vendor?, allow_same_vendor?, mode?, artifact_ref?,
               plan_output_path?, max_cost_usd?, author_model?, reviewer_model?}
      REQUIRED: prompt.
      DEFAULTS: author_vendor='agy' (Gemini), reviewer_vendor='agy' (Opus), reviewer_model='claude-opus-4-6-thinking', max_rounds=5, mode='async'.
      Iterates: author drafts plan → reviewer audits → feedback to author → loop
      until APPROVED or convergence cutoff or max_rounds. Returns plan_id immediately
      (async mode). Poll with plan_review_loop_status. Artifacts saved to
      .brain/plans/<plan_id>/.
      TERMINAL STATES: APPROVED, CONVERGED_WITH_MINOR_ISSUES, MAX_ROUNDS_EXHAUSTED,
        BUDGET_EXCEEDED, OSCILLATING, CANCELLED, ERROR.
  plan_review_loop_status - Query real-time state of a plan review loop.
      params: {plan_id}  REQUIRED: plan_id.
      Returns the full state.json including current_round, review_trail, cost, etc.
  plan_review_loop_cancel - Cancel a running plan review loop.
      params: {plan_id}  REQUIRED: plan_id.
      Sets cancel_requested=true; worker aborts before next round.

GATING: if action ∈ {'dispatch', 'review'} and cross_vendor_enabled() is
False, the tool returns a clear error string telling the caller to run
``nucleus onboard`` first — it does NOT crash and never invokes the executor.

This module follows the Super-Tools facade pattern used by other tool modules.
"""

import logging

from ._dispatch import async_dispatch, resolve_make_response
from ..runtime.vendor_dispatch import (
    DEFAULT_MODE,
    VENDOR_MODES,
    VENDOR_SPECS,
    _DEFAULT_VENDOR_TIMEOUT_S,
    cross_vendor_enabled,
    dispatch_and_capture,
    normalize_mode,
    resolve_model,
    resolve_model_family,
)

logger = logging.getLogger("nucleus.tool.vendor_delegate")

# Doctrine that travels WITH the tool — agents learn HOW from the tool itself.
_DOCTRINE = (
    "Delegate a task to a fungible cross-vendor lane — cheap, different "
    "intelligence you can hand work to. devin/GLM for builds; agy/Gemini for "
    "a diverse review / second-opinion lens (vendor default 'agy' — diverse "
    "Gemini lens; the earlier conversational drift was an agy CLI bug fixed "
    "upstream). Dispatch by reflex, but GATE the output yourself: a green "
    "vendor result is a hypothesis until you verify it on your own shell "
    "(zero-trust). Requires cross-vendor enabled — run `nucleus onboard` once. "
    "Actions: dispatch (mode write|read, model optional, expect_paths optional), "
    "review (read-only, default agy), list (safe first call)."
)

_DISABLED_MSG = (
    "cross-vendor dispatch is disabled. Run `nucleus onboard` once to enable, "
    "or set NUCLEUS_CROSS_VENDOR=1. No vendor CLI was invoked."
)

# HARDENED review preamble (baked in — this is why `review` beats raw `dispatch`
# for unattended one-shot verdicts; learned from the autonomous daemon). It
# forces a different-vendor reviewer into a non-interactive, terse, structured
# output posture: no clarifying questions, no offers to help, exactly two lines.
_REVIEW_PREAMBLE = (
    "You are an independent, different-vendor reviewer. Review the content "
    "below (it is complete — do NOT ask clarifying questions, do NOT offer to "
    "help). Output ONLY two lines: line 1 = a one-word verdict "
    "(SOUND / RISKY / BUGGY); line 2 = the single most important correctness "
    "/ edge-case / test-gap issue, or 'none'. Be terse. You are judging ONLY the "
    "text below — you cannot see the repository or any other file, so do not "
    "assume or invent context you were not given. Never echo secrets, tokens, or "
    "credentials verbatim."
)


def _is_success(out: dict) -> bool:
    """True iff the vendor produced output AND (when expect_paths was used) it
    actually touched at least one named file. ``effect == "unknown"`` (the
    no-expect_paths common case) does NOT fail the gate."""
    return out.get("status") == "ok" and out.get("effect") != "no_files_touched"


def _noop_error(out: dict) -> str:
    """Human-readable error for a NOT-success dispatch, keyed on status/effect."""
    s, eff = out.get("status"), out.get("effect")
    if eff == "no_files_touched":
        return (
            "vendor returned success but touched NONE of the files you named in "
            f"expect_paths ({out.get('changed_paths')}=[]) — treat as NOT done. "
            "Re-dispatch with a more explicit prompt naming the exact files/changes; "
            "do NOT hand-run the CLI. Then verify with your own `git diff`."
        )
    if s == "empty_output":
        return (
            "vendor exited 0 but produced NO output — a silent no-op, NOT success. "
            "Re-dispatch with a more explicit prompt; do NOT hand-run the CLI."
        )
    if s == "timed_out":
        return "vendor timed out before completing — partial/empty output; NOT success."
    if s == "not_found":
        return (
            "vendor CLI is not on PATH — cross-vendor may not be set up. "
            "Run `nucleus onboard` once, then retry."
        )
    if s == "budget_rejected":
        return f"dispatch rejected before running (status={s}); adjust and retry."
    return f"vendor did not succeed (status={s}); NOT a completed result."


def register(mcp, helpers):
    """Register the nucleus_delegate facade tool."""
    make_response = resolve_make_response(helpers)

    def _h_dispatch(**params):
        vendor = params.get("vendor", "")
        prompt = params.get("prompt", "")
        artifact_ref = params.get("artifact_ref", "")
        to_role = params.get("to") or "cross_vendor"

        # GATE: never invoke the executor when cross-vendor is off — return a
        # clear, actionable error instead of crashing. Gate BEFORE model/mode
        # validation so the disabled path never validates or invokes anything.
        if not cross_vendor_enabled():
            return make_response(False, error=_DISABLED_MSG)

        if vendor not in VENDOR_SPECS:
            return make_response(
                False,
                error=(
                    f"unknown vendor {vendor!r}; expected one of "
                    f"{sorted(VENDOR_SPECS)}"
                ),
            )
        if not prompt:
            return make_response(False, error="dispatch requires a non-empty 'prompt'")

        # v3 anchor precondition, UNCONDITIONAL (PRINCIPAL line 77): the tool
        # MUST NOT accept artifact_ref as caller input. Any value supplied by
        # the caller is discarded here; dispatch_and_capture stamps it from the
        # vendor worktree's git HEAD SHA and fails closed if git is unavailable.
        # Previously this was gated on NUCLEUS_ARTIFACT_REF_VENDOR_DERIVED, so
        # with the flag off a caller could hand-write the binding that G1 crit-4
        # reads as proof of cross-vendor coordination. See vendor_dispatch.py.
        #
        # The `artifact_ref` param is still ACCEPTED by the schema for backward
        # compatibility and is now inert. That is a remaining (harmless)
        # deviation from the letter of line 77 — the value can no longer reach
        # an envelope, but the schema still advertises it. Removing it is a
        # breaking API change and is tracked separately.
        artifact_ref = ""  # stamped from worktree SHA in dispatch_and_capture

        mode = params.get("mode", DEFAULT_MODE)
        expect_paths = params.get("expect_paths")   # list[str] | None
        try:
            resolved_model = resolve_model(vendor, params.get("model"))
            canon_mode = normalize_mode(mode)                     # validate (raises)
        except ValueError as exc:
            return make_response(False, error=str(exc))   # executor NEVER invoked

        # timeout_s — optional per-dispatch subprocess timeout in seconds. 0
        # means no-timeout (matches the executor's existing convention; the
        # Python subprocess timeout becomes None and the CLI --print-timeout
        # gets 86400s). Validated here so a bad value never reaches the
        # executor; negative or non-int values are rejected before invocation.
        timeout_s = params.get("timeout_s")
        if timeout_s is not None:
            if not isinstance(timeout_s, int) or isinstance(timeout_s, bool):
                return make_response(
                    False,
                    error=(
                        f"timeout_s must be a non-negative int, got "
                        f"{type(timeout_s).__name__}={timeout_s!r}"
                    ),
                )
            if timeout_s < 0:
                return make_response(
                    False,
                    error=(
                        f"timeout_s must be non-negative (0 means no timeout), "
                        f"got {timeout_s}"
                    ),
                )
        effective_timeout_s = (
            timeout_s if timeout_s is not None else _DEFAULT_VENDOR_TIMEOUT_S
        )

        # Warn (don't block) when mode=read but the prompt asks for binary
        # execution — read mode strips --permission-mode dangerous from devin,
        # so the vendor's sandbox blocks pip/nucleus/python invocations and the
        # dispatch thrashes.  The caller should use mode=write (the default)
        # for any task that needs to RUN things, not just read files.
        if canon_mode == "read":
            _EXEC_HINTS = (
                "pip install", "pip3 install", "nucleus-mcp", "nucleus ",
                "python ", "python3 ", "npm ", "node ", "cargo ",
                "pytest", "--help", "smoke-test", "smoke test",
                "run ", "execute ", "start the server",
            )
            _prompt_lower = prompt.lower()
            _hit = next((h for h in _EXEC_HINTS if h in _prompt_lower), None)
            if _hit:
                logger.warning(
                    "dispatch mode='read' with execution hint %r in prompt — "
                    "vendor sandbox will block binary execution; use mode='write' "
                    "for tasks that need to RUN commands, not just read files.",
                    _hit,
                )

        out = dispatch_and_capture(
            vendor, prompt, artifact_ref, to_role=to_role,
            model=resolved_model, mode=mode, expect_paths=expect_paths,
            timeout_s=effective_timeout_s,
        )
        if _is_success(out):
            return make_response(True, data=out)
        return make_response(False, data=out, error=_noop_error(out))

    def _h_list(**params):
        vendors = {
            name: {
                "model_family": resolve_model_family(spec.default_model, spec.model),
                "model_families": {
                    model_id: resolve_model_family(model_id, spec.model)
                    for model_id in spec.models
                },
                "selectable_models": list(spec.models),
                "default_model": spec.default_model,
                "model_flag": spec.model_flag,
                "binary": spec.binary,
                "to_default": spec.to_default,
            }
            for name, spec in VENDOR_SPECS.items()
        }
        return make_response(
            True,
            data={
                "vendors": sorted(vendors),
                "vendor_specs": vendors,
                "actions": ["dispatch", "review", "list",
                            "plan_review_loop", "plan_review_loop_status",
                            "plan_review_loop_cancel"],
                "modes": list(VENDOR_MODES),
                "default_mode": DEFAULT_MODE,
                "cross_vendor_enabled": cross_vendor_enabled(),
            },
        )

    def _h_review(**params):
        content = params.get("content", "")
        artifact_ref = params.get("ref") or "review"
        vendor = params.get("vendor") or "agy"
        to_role = params.get("to") or "cross_vendor"

        # GATE: same enablement gate as 'dispatch' — never invoke the executor
        # when cross-vendor is off; return a clear, actionable error instead.
        if not cross_vendor_enabled():
            return make_response(False, error=_DISABLED_MSG)

        if vendor not in VENDOR_SPECS:
            return make_response(
                False,
                error=(
                    f"unknown vendor {vendor!r}; expected one of "
                    f"{sorted(VENDOR_SPECS)}"
                ),
            )
        if not content:
            return make_response(
                False, error="review requires a non-empty 'content'"
            )

        try:
            resolved_model = resolve_model(vendor, params.get("model"))
        except ValueError as exc:
            return make_response(False, error=str(exc))

        # HARDENED prompt: bake the non-interactive verdict posture in so the
        # caller gets a structured one-shot review without hand-crafting a
        # prompt, then dispatch via the SAME captured path as 'dispatch'.
        # mode="read" is FORCED — a reviewer is never over-permissioned and
        # devin-review stays byte-identical when overridden to devin.
        prompt = f"{_REVIEW_PREAMBLE}\n\n{content}"
        out = dispatch_and_capture(
            vendor, prompt, artifact_ref, to_role=to_role,
            model=resolved_model, mode="read",
        )
        if _is_success(out):
            return make_response(True, data=out)
        return make_response(False, data=out, error=_noop_error(out))

    from .plan_review_loop import (
        execute_plan_review_loop,
        query_plan_review_loop_status,
        cancel_plan_review_loop,
        execute_plan_review_chief_amend,
    )

    def _h_plan_review_loop(**params):
        return execute_plan_review_loop(params, make_response)

    def _h_plan_review_loop_status(**params):
        plan_id = params.get("plan_id", "")
        return query_plan_review_loop_status(plan_id, make_response)

    def _h_plan_review_loop_cancel(**params):
        plan_id = params.get("plan_id", "")
        return cancel_plan_review_loop(plan_id, make_response)

    def _h_plan_review_chief_amend(**params):
        return execute_plan_review_chief_amend(params, make_response)

    ROUTER = {
        "dispatch": _h_dispatch,
        "review": _h_review,
        "list": _h_list,
        "plan_review_loop": _h_plan_review_loop,
        "plan_review_loop_status": _h_plan_review_loop_status,
        "plan_review_loop_cancel": _h_plan_review_loop_cancel,
        "plan_review_chief_amend": _h_plan_review_chief_amend,
    }

    # All seven handlers absorb **params, so _dispatch cannot read their
    # contract from the signature (see _dispatch._allowed_param_names). Declare
    # it. Every entry in ROUTER above needs one; a missing declaration does not
    # fail loudly, it just turns the unknown-param check off for that action.
    # Keys transcribed from each handler body; plan_review_loop's come from
    # execute_plan_review_loop() in plan_review_loop.py, which is handed the
    # params dict wholesale. `timeout_s` IS now in the dispatch contract: the
    # facade validates it (non-negative int, 0 = no-timeout per the executor's
    # convention) and passes it through to dispatch_and_capture, which already
    # handles 0=no-timeout and clamps negative/invalid values at the executor
    # layer. The effective timeout used is echoed back in the result
    # (`out["timeout_s"]`) so a caller can verify the setting took effect
    # rather than inferring it from success.
    _h_dispatch._nucleus_params = (
        "vendor", "prompt", "artifact_ref", "to", "mode", "expect_paths",
        "model", "timeout_s",
    )
    _h_review._nucleus_params = ("content", "ref", "vendor", "to", "model")
    _h_list._nucleus_params = ()
    _h_plan_review_loop._nucleus_params = (
        "prompt", "max_rounds", "author_vendor", "reviewer_vendor",
        "author_model", "reviewer_model", "tiebreaker_vendor", "allow_same_vendor",
        "effort_level",
        "max_cost_usd", "plan_output_path", "context_files",
        "accepted_tradeoffs", "approval_criteria", "sandbox_test_cmd",
    )
    _h_plan_review_loop_status._nucleus_params = ("plan_id",)
    _h_plan_review_loop_cancel._nucleus_params = ("plan_id",)
    # Added when the action was; it was the one handler of the seven with no
    # declaration, so _allowed_param_names returned None for it and _dispatch
    # SKIPPED the unknown-param check entirely — a misspelled key was silently
    # dropped rather than rejected, on this action alone (ledger DS-6). Keys
    # transcribed from execute_plan_review_chief_amend's own docstring and body
    # in plan_review_loop.py.
    _h_plan_review_chief_amend._nucleus_params = (
        "plan_id", "amended_plan", "chief_note",
    )
    _LOG_LABELS = {
        "dispatch": "nucleus_delegate dispatch failed",
        "review": "nucleus_delegate review failed",
        "list": "nucleus_delegate list failed",
        "plan_review_loop": "nucleus_delegate plan_review_loop failed",
        "plan_review_loop_status": "nucleus_delegate plan_review_loop_status failed",
        "plan_review_loop_cancel": "nucleus_delegate plan_review_loop_cancel failed",
    }

    @mcp.tool(
        title="Cross-Vendor Delegate",
        annotations={"readOnlyHint": False, "destructiveHint": False, "openWorldHint": True},
    )
    async def nucleus_delegate(action: str, params: dict = {}) -> str:
        """Hand a coding or review task to a cross-vendor lane — a cheap, non-Claude
agent that does the work for you. Use this INSTEAD OF shelling out to any CLI: it
picks the vendor, injects the correct per-vendor permission flags, captures all
output synchronously, and reports a real status. Do NOT run `agy`/`devin`
yourself in Bash — the raw CLIs take DIFFERENT per-vendor flags (pass the wrong
one and a build silently makes ZERO edits yet exits 0), and hand-driven
background calls flush output late (a finished call looks empty for tens of
seconds). This tool is the only robust path.

First call `list` — it needs no setup, confirms cross-vendor is enabled, and
shows each vendor's selectable_models + default_model. If dispatch/review return
a disabled error, cross-vendor is OFF: run `nucleus onboard` once (one-time),
then retry.

Actions:
  dispatch - Hand a task to a cross-vendor lane.
      params: {vendor, prompt, artifact_ref, mode?, model?, expect_paths?, to?, timeout_s?}
      REQUIRED: vendor ∈ 'agy'|'devin', prompt, artifact_ref.
      mode ∈ 'write'|'read' (default 'write'):
        write = the vendor CHANGES things (edit files, run commands, build/fix).
        read  = the vendor only LOOKS and REPORTS (analyze/summarize); no file changes.
        When unsure use 'write': a read task still works in write mode, but a write
        task silently does NOTHING in read mode.
      model? — optional. Defaults to the vendor's verified model
        (agy → gemini-3.1-pro-high, devin → swe-2-max). These are ALREADY the
        defaults, so omitting model is sufficient; pass it only to be explicit or
        to override; pass "glm-5-2" to use GLM-5.2 High instead. The response
        echoes model_id — read model_id (NOT model_family) to confirm which model
        ran. A cross-wired model (e.g. glm-5-2 with agy) is rejected with the
        valid ids named.
      artifact_ref — a commit SHA / PR# / file path to bind the result to. No commit
        yet (a from-scratch build)? Pass the repo-relative path you will write,
        e.g. src/foo.py.
      expect_paths? — optional list of file paths you expect the vendor to change.
        If you pass them and the vendor changes none, status comes back NOT success
        ("no_files_touched") even if it narrated success. Without expect_paths,
        success means only that the vendor produced output — not that it edited
        anything, so ALWAYS confirm with your own `git diff`. (Paths are checked in
        the nucleus server process's working dir; pass paths valid there.)
      timeout_s? — optional int, seconds. Per-dispatch subprocess timeout. 0 means
        no timeout (the subprocess timeout becomes None and the CLI --print-timeout
        gets a 24h ceiling). Defaults to the executor's default (env
        NUCLEUS_VENDOR_TIMEOUT_S, else 3600s) if omitted. The response echoes the
        effective timeout used as `timeout_s` so you can verify the setting took
        effect rather than inferring it from success.
      You never pass CLI flags — the tool injects the right permissions per vendor.
      Example (build): action="dispatch", params={"vendor":"devin","prompt":"<task>",
        "artifact_ref":"src/foo.py","mode":"write","model":"glm-5-2",
        "expect_paths":["src/foo.py"]}
  review - Independent, different-model verdict on pasted code / a diff.
      params: {content, ref?, vendor?, model?, to?}
      content REQUIRED (paste the code/diff inline). Default vendor agy (Gemini,
      model gemini-3.1-pro-high) — a genuinely different model from the devin/GLM
      builder, so the review is diverse. Read-only, edits nothing. Returns a terse
      two-line verdict. For a devin/GLM second opinion pass vendor='devin'.
      Example: action="review", params={"content":"<code or diff>",
        "model":"gemini-3.1-pro-high"}
  list - Show vendors, their selectable_models + default_model, the mode vocabulary,
      and whether cross-vendor is enabled. Needs no setup — call it first.

A green result is a hypothesis until you verify it on your own shell (zero-trust).
Read the response's `status` and `success`: 'ok' = produced output; 'empty_output'
/ 'no_files_touched' / 'timed_out' / 'error' come back success=false — NOT done.
(If NUCLEUS_ENVELOPE is on, gate on the INNER success flag, not the envelope's ok.)

Two caveats from real use:
- SECRET HYGIENE: vendor OUTPUT is best-effort secret-redacted (Bearer/JWT/API-key
  patterns -> <REDACTED>; the count is in the response `redacted` field). This is a
  BACKSTOP, not a guarantee — never put credentials in a prompt, and the tool CANNOT
  scrub a file the vendor writes itself, so review any vendor file-writes near secrets
  yourself before trusting them.
- REVIEW SEES ONLY WHAT YOU PASTE: 'review' (and 'dispatch') cannot read the repo, a
  diff, or any file — they judge only the text in your params. Paste the real code/diff
  or the reviewer will confidently critique things it cannot see. For a whole PR, paste
  the actual diff, not a description of it.
"""
        return await async_dispatch(
            action,
            params,
            ROUTER,
            "nucleus_delegate",
        )

    return [("nucleus_delegate", nucleus_delegate)]
