"""Nucleus Agent OS — Stage 0: THE FIRST CELL (the boot).

The keystone the manifesto names: make ONE agent's model-loop route THROUGH the
Nucleus gateway, with memory injected before it thinks and its turn recorded
after. This is the INVERSION of MCP — the agent stops being a sovereign caller
and becomes a process whose cognition is mediated by the OS.

The minimal REAL loop, three seams:

  1. THINK  → the model call routes through ``NucleusGateway`` — which emits a
     real ``LLM_GENERATE`` DSoR event (``event_ops._emit_event``) and delegates
     generation to a Nucleus LLM engine (``llm_client.get_llm_client``). A raw
     ``anthropic.Anthropic()`` call would emit no event and write no interaction
     log; the presence of both is the proof the call went through Nucleus, not
     around it. If no provider is reachable in the environment (no API key), the
     FINAL provider call — and only that — is served by a deterministic stub;
     the mediation (event + interaction capture) stays real.

  2. RECALL → before the agent thinks, ``recall_and_inject`` runs the real
     ``nucleus_wedge`` recall (``_do_recall_query`` over ``memories.db``, the
     production projection of ``engrams/history.jsonl``) and injects the
     recalled memory strings into the prompt. Memory arrives by the physics of
     the membrane, not because the agent asked.

  3. RECORD → after the turn, ``record_turn_to_flywheel`` writes a real
     ``LoopTurn`` via ``ArchivePipeline.record_turn`` into
     ``.brain/training/loop_turns.jsonl`` — the flywheel that forges the next
     model.

Gated behind ``NUCLEUS_AGENT_OS_BOOT`` (default OFF). Importing this module
runs nothing; ``boot_cell`` refuses to run unless the flag is on.
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Optional

logger = logging.getLogger("nucleus.agent_os.boot")

BOOT_FLAG = "NUCLEUS_AGENT_OS_BOOT"
# Force the deterministic offline model-response stub even if a provider could
# be constructed (used by the demo for reproducibility).
STUB_FLAG = "NUCLEUS_AGENT_OS_STUB_LLM"
# Stage-1 unlock: the working-set pager (selective memory recall). Mirrors
# ``runtime.agent_os.pager.PAGER_FLAG``; duplicated here so the flag check in
# ``recall_and_inject`` does NOT import the pager module when the flag is OFF
# (byte-identical-OFF contract — the pager is imported lazily, only on the
# flag-ON branch).
PAGER_FLAG = "NUCLEUS_AGENT_OS_PAGER"
# Stage-1 referee: label each recorded turn with a verified verdict (the MOAT —
# verified-labeled trajectories). Default OFF; byte-identical-OFF contract.
VERIFIED_RECORD_FLAG = "NUCLEUS_AGENT_OS_VERIFIED_RECORD"

_TRUTHY = frozenset({"1", "true", "yes", "on"})

_DEFAULT_SYSTEM = (
    "You are an agent living INSIDE Nucleus. Your cognition is mediated by the "
    "OS: memory is recalled and injected before you think, and every turn you "
    "take is recorded to the flywheel. Use the recalled memory; do not pretend "
    "to remember what was not injected."
)


def boot_flag_enabled() -> bool:
    """True iff ``NUCLEUS_AGENT_OS_BOOT`` is set truthy (default False)."""
    return os.environ.get(BOOT_FLAG, "").strip().lower() in _TRUTHY


def verified_record_enabled() -> bool:
    """True iff ``NUCLEUS_AGENT_OS_VERIFIED_RECORD`` is set truthy (default False)."""
    return os.environ.get(VERIFIED_RECORD_FLAG, "").strip().lower() in _TRUTHY


def _stub_forced() -> bool:
    return os.environ.get(STUB_FLAG, "").strip().lower() in _TRUTHY


def _ensure_brain_scaffold(brain_path: Optional[str] = None) -> Path:
    """Create the brain subdirs the membrane writes into.

    The Nucleus daemon normally scaffolds these via ``_ensure_initialized``; the
    boot loop can run against a cold brain, so it materializes the dirs that
    ``event_ops`` / ``archive_pipeline`` / the raw interaction log require. The
    append-mode writers in those modules do not ``mkdir`` their own parents.
    """
    try:
        from ..common import get_brain_path

        root = Path(brain_path) if brain_path else get_brain_path()
    except Exception:  # noqa: BLE001
        root = Path(brain_path) if brain_path else Path(os.environ.get("NUCLEUS_BRAIN_PATH", ".brain"))
    for sub in ("ledger", "training", "raw", "engrams"):
        (root / sub).mkdir(parents=True, exist_ok=True)
    return root


# ── Seam 1: THINK — the gateway (the membrane) ──────────────────────────────


@dataclass
class GatewayResult:
    """Outcome of one mediated model call."""

    text: str
    engine: str                 # real engine label ("NEW"/"ANTHROPIC"/"GROQ"/...) or "STUB"
    mediated: bool              # did the Nucleus gateway emit its LLM_GENERATE event?
    event_id: Optional[str]     # the DSoR event id proving mediation
    model: str
    stubbed: bool               # was the provider call served by the offline stub?
    note: str = ""              # why stubbed / which real engine was tried


class NucleusGateway:
    """The membrane. Every model call the inside-agent makes flows through here.

    On each call it emits a real ``LLM_GENERATE`` DSoR event (Nucleus is now
    *between the agent and its own mind*) and delegates the actual generation to
    a Nucleus LLM engine. If no engine is reachable, only the provider call is
    stubbed — the mediation is real either way.

    Provider selection (MEMBRANE §1 — the cognition scheduler): if no
    ``provider`` argument or ``NUCLEUS_LLM_PROVIDER`` env var is set, the
    gateway calls ``scheduler.schedule_engine`` to pick the cheapest capable
    provider automatically. The agent holds no key and picks no model.
    """

    def __init__(self, system_instruction: Optional[str] = None, provider: Optional[str] = None):
        self.system_instruction = system_instruction
        self._provider = provider or os.environ.get("NUCLEUS_LLM_PROVIDER")

    def _try_real_engine(self, capability: str = "any", skip: list = None):
        """Construct a real Nucleus LLM client, or return (None, reason).

        Uses the cognition scheduler (MEMBRANE §1) when no explicit provider
        is set — tries cheapest-capable-first across all available providers.
        """
        from .scheduler import schedule_engine

        client, label, attempts = schedule_engine(
            capability=capability,
            system_instruction=self.system_instruction,
            force_provider=self._provider,
            skip=skip,
        )
        if client is not None:
            return client, label
        # All providers failed — summarize for the note.
        reasons = "; ".join(f"{a.provider}={a.error}" for a in attempts if a.error)
        return None, f"unavailable:{reasons or 'no provider'}"

    def generate(
        self,
        prompt: str,
        *,
        session_id: str = "agent-os-cell",
        agent_id: str = "cell-0",
        capability: str = "any",
    ) -> GatewayResult:
        # 1. Emit the real Nucleus mediation event — THIS is what "inside" means.
        _ensure_brain_scaffold()
        event_id: Optional[str] = None
        try:
            from ..event_ops import _emit_event

            event_id = _emit_event(
                event_type="LLM_GENERATE",
                emitter="NucleusGateway",
                data={
                    "session_id": session_id,
                    "agent_id": agent_id,
                    "membrane": "agent_os.boot",
                    "prompt_preview": prompt[:120],
                },
                description="Agent cognition routed THROUGH the Nucleus gateway (Stage 0 boot)",
            )
        except Exception:  # noqa: BLE001 — mediation event is best-effort
            event_id = None
        # ``_emit_event`` returns an error STRING (not a raise) on failure; only a
        # real ``evt-*`` id counts as genuine mediation.
        if not (isinstance(event_id, str) and event_id.startswith("evt-")):
            event_id = None

        # 2. Delegate to a real Nucleus engine; stub ONLY the provider call if
        #    unreachable. The mediation above is real regardless.
        #    The scheduler (MEMBRANE §1) picks the cheapest capable provider.
        #    On provider failure (429/402/etc), retry with the next provider
        #    before falling back to the stub — the membrane falls through.
        skip: list = []
        for _attempt in range(5):  # max 5 providers in the priority list
            client, label = self._try_real_engine(capability=capability, skip=skip)
            if client is None or _stub_forced():
                break
            try:
                resp = client.generate_content(prompt, _agent_id=agent_id)
                text = getattr(resp, "text", "") or ""
                return GatewayResult(
                    text=text,
                    engine=label,
                    mediated=event_id is not None,
                    event_id=event_id,
                    model=getattr(client, "model_name", label),
                    stubbed=False,
                    note="real provider call via get_llm_client",
                )
            except Exception as exc:  # noqa: BLE001 — provider blocked
                # Identify which provider failed so we can skip it next round.
                failed_provider = getattr(client, "_provider_id", None) or label
                skip.append(failed_provider)
                label = f"{label}->error:{type(exc).__name__}"
                logger.info("gateway: provider %s failed (%s), trying next", failed_provider, type(exc).__name__)
                continue

        text = _stub_response(prompt)
        _log_stub_interaction(prompt, text, session_id, agent_id)
        return GatewayResult(
            text=text,
            engine="STUB",
            mediated=event_id is not None,
            event_id=event_id,
            model="stub-deterministic-v0",
            stubbed=True,
            note=(
                f"provider {label}; offline deterministic model response "
                "(recall + record remain real)"
            ),
        )


def _stub_response(prompt: str) -> str:
    """Deterministic, offline model output.

    Not a language model — a fixed function of the prompt, so the demo is
    reproducible with no network. It reads back the injected memory block (if
    present) to make the loop visibly coherent: an agent that used what the
    membrane gave it.
    """
    recalled_line = ""
    for line in prompt.splitlines():
        s = line.strip()
        if s.startswith("- ") and "MEMORY" not in s:
            recalled_line = s[2:].strip()
            break
    intent = ""
    marker = "TASK:"
    if marker in prompt:
        intent = prompt.split(marker, 1)[1].strip().splitlines()[0].strip()
    parts = ["[cognition mediated by the Nucleus gateway]"]
    if recalled_line:
        parts.append(
            f"I recalled from a prior session: \"{recalled_line}\". "
            "I will act on that rather than re-deriving it."
        )
    else:
        parts.append("No prior memory was injected for this task.")
    if intent:
        parts.append(f"Plan for '{intent}': proceed using the recalled context above.")
    parts.append("MISSION_COMPLETE")
    return " ".join(parts)


def _log_stub_interaction(prompt: str, text: str, session_id: str, agent_id: str) -> None:
    """Mirror the real engines' interaction capture so the stubbed call is still
    recorded through Nucleus subsystems (raw interaction log + budget manager)."""
    try:
        from ..common import get_brain_path

        raw_path = get_brain_path() / "raw"
        raw_path.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
        (raw_path / f"llm_interaction_{ts}.json").write_text(
            json.dumps(
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "engine": "STUB",
                    "model": "stub-deterministic-v0",
                    "session_id": session_id,
                    "agent_id": agent_id,
                    "prompt": str(prompt)[:5000],
                    "response_text": text,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    except Exception:  # noqa: BLE001 — capture is best-effort
        pass
    try:
        from ..token_budget import estimate_tokens, get_budget_manager

        get_budget_manager().record_usage(
            model="stub-deterministic-v0",
            input_tokens=estimate_tokens(str(prompt)),
            output_tokens=estimate_tokens(text),
            session_id=session_id,
            agent_id=agent_id,
        )
    except Exception:  # noqa: BLE001
        pass


# ── Seam 2: RECALL — memory injected before the agent thinks ────────────────


def recall_and_inject(
    query: str,
    *,
    brain_path: Optional[str] = None,
    kind: Optional[str] = None,
    tags: Optional[List[str]] = None,
    limit: int = 5,
) -> tuple[str, list[dict]]:
    """Run the real ``nucleus_wedge`` recall and format an injected context block.

    Returns ``(injected_context_str, raw_recall_rows)``. The rows are the real
    ``memories.db`` projection hits: ``{text, tags, created_at, source, kind}``.

    When ``NUCLEUS_AGENT_OS_PAGER`` is ON (Stage-1 unlock, MEMBRANE §2), the raw
    recall candidates are run through the working-set pager
    (``runtime.agent_os.pager.page``) before injection: scored by
    relevance × recency × verified-trust and packed best-first into a context
    budget, evicting the near-misses that caused the Stage-0 "blur". When the
    flag is OFF, this function is byte-identical to the pre-pager path — the
    pager module is not imported and the raw recall rows are injected as-is.
    """
    from nucleus_wedge.recall_cmd import _do_recall_query

    rows = _do_recall_query(
        query=query,
        limit=limit,
        kind=kind,
        tags=tags,
        since=None,
        source_filter=None,
        brain_path_arg=str(brain_path) if brain_path else None,
    )

    # Stage-1 pager: reselect the working set from the raw recall candidates.
    # Flag-OFF = byte-identical no-op: the pager module is NOT imported and the
    # raw recall rows are injected as-is (the pre-pager path, unchanged). Only
    # the flag-ON branch imports ``page`` lazily and reselects the working set.
    if os.environ.get(PAGER_FLAG, "").strip().lower() in _TRUTHY:
        from .pager import page

        rows = page(query, rows)

    recalled = [r.get("text", "") for r in rows if r.get("text")]
    if recalled:
        block = "\n".join(f"- {t}" for t in recalled)
        injected = f"[NUCLEUS MEMORY — recalled before you think]\n{block}"
    else:
        injected = "[NUCLEUS MEMORY — no prior memory matched this task]"
    return injected, rows


def _build_prompt(system: str, injected_context: str, intent: str) -> str:
    return f"{system}\n\n{injected_context}\n\nTASK: {intent}\n\nRespond:"


# ── Seam 3: RECORD — the turn lands in the flywheel ─────────────────────────


def record_turn_to_flywheel(
    *,
    intent: str,
    recalled_rows: list[dict],
    gateway_result: GatewayResult,
    brain_path: Optional[str] = None,
    tools_used: Optional[List[str]] = None,
    verified_label: Optional[dict] = None,
) -> Any:
    """Write a real ``LoopTurn`` to ``.brain/training/loop_turns.jsonl``.

    ``verified_label`` (the referee verdict) is persisted into the turn record
    when present (flag-ON). When ``None`` (flag OFF) it is not passed to
    ``record_turn`` → the jsonl line is byte-identical to the pre-verified-record
    shape.
    """
    from ..archive_pipeline import ArchivePipeline

    archive = ArchivePipeline(brain_path=Path(brain_path) if brain_path else None)
    signal_absorbed = [
        f"{r.get('source', 'memory')}::{(r.get('text') or '')[:60]}" for r in recalled_rows
    ]
    record_kwargs: dict = dict(
        brother="code",
        intent=intent,
        actions=[
            f"recalled {len(recalled_rows)} memory row(s) via nucleus_wedge",
            "routed the model call THROUGH NucleusGateway (mediated cognition)",
            f"generated a response inside the membrane (engine={gateway_result.engine})",
        ],
        tools_used=tools_used
        or ["nucleus_wedge.recall", "NucleusGateway.generate", "archive_pipeline.record_turn"],
        decisions=[
            "injected recalled memory into the agent's context before it thought",
            f"cognition mediated by Nucleus (LLM_GENERATE event={gateway_result.event_id})",
        ],
        outcome=(gateway_result.text or "")[:500],
        signal_absorbed=signal_absorbed,
        signal_produced=["loop_turn (flywheel training datum)"],
        confidence=0.9 if not gateway_result.stubbed else 0.7,
        context="Nucleus Agent OS — Stage 0, the first cell",
        metadata={
            "mediated_by": "NucleusGateway",
            "engine": gateway_result.engine,
            "llm_event_id": gateway_result.event_id,
            "stubbed_llm": gateway_result.stubbed,
            "recalled_count": len(recalled_rows),
            "stage": "agent_os_stage0_first_cell",
        },
    )
    if verified_label is not None:
        record_kwargs["verified_label"] = verified_label
    turn = archive.record_turn(**record_kwargs)
    return turn


# ── The loop: one cell, alive ───────────────────────────────────────────────


@dataclass
class BootResult:
    intent: str
    injected_context: str
    recalled_rows: list[dict]
    gateway_result: GatewayResult
    turn: Any                       # the LoopTurn written to the flywheel
    brain_path: Optional[str]
    verified_label: Optional[dict] = None  # referee verdict (flag-ON only)
    recalled_from_memory: bool = field(init=False)

    def __post_init__(self):
        self.recalled_rows = self.recalled_rows or []
        self.recalled_from_memory = len(self.recalled_rows) > 0


def boot_cell(
    intent: str,
    *,
    recall_query: Optional[str] = None,
    brain_path: Optional[str] = None,
    system_instruction: Optional[str] = None,
    kind: Optional[str] = None,
    tags: Optional[List[str]] = None,
    tools_used: Optional[List[str]] = None,
    require_flag: bool = True,
) -> BootResult:
    """Boot one cell: recall → inject → think-through-gateway → record.

    The whole point of Stage 0: after this call, the agent has (1) thought via
    the Nucleus gateway, (2) had memory injected before thinking, and (3) had
    its turn recorded to the flywheel — it lived inside for one turn.
    """
    if require_flag and not boot_flag_enabled():
        raise RuntimeError(
            f"{BOOT_FLAG} is OFF — the cell does not boot. Set {BOOT_FLAG}=1 to run."
        )

    brain_path = brain_path or os.environ.get("NUCLEUS_BRAIN_PATH")
    _ensure_brain_scaffold(brain_path)

    # 2. RECALL + INJECT (before thinking).
    injected, rows = recall_and_inject(
        recall_query or intent, brain_path=brain_path, kind=kind, tags=tags
    )

    # 1. THINK through the gateway (mediated cognition).
    system = system_instruction or _DEFAULT_SYSTEM
    prompt = _build_prompt(system, injected, intent)
    gateway = NucleusGateway(system_instruction=system)
    gres = gateway.generate(prompt)

    # 2. (optional) LABEL the turn with a referee verdict — the MOAT:
    #    verified-labeled trajectories. Computed BEFORE the turn is recorded so
    #    the verdict is persisted into loop_turns.jsonl (not just attached
    #    ephemerally to BootResult). Flag-OFF = byte-identical no-op
    #    (verified_label stays None; the verified_record module is not imported).
    verified_label: Optional[dict] = None
    if verified_record_enabled():
        try:
            from .verified_record import label_turn

            outcome = getattr(gres, "text", "") or intent
            verified_label = label_turn(outcome, context=injected)
        except Exception:  # noqa: BLE001 — labeling must never break a boot
            verified_label = None

    # 3. RECORD the turn to the flywheel (after thinking) — with the verified
    #    label threaded in so the corpus on disk is REFEREE-verified, not just
    #    the in-memory result.
    turn = record_turn_to_flywheel(
        intent=intent,
        recalled_rows=rows,
        gateway_result=gres,
        brain_path=brain_path,
        tools_used=tools_used,
        verified_label=verified_label,
    )

    return BootResult(
        intent=intent,
        injected_context=injected,
        recalled_rows=rows,
        gateway_result=gres,
        turn=turn,
        brain_path=brain_path,
        verified_label=verified_label,
    )


# ── Runnable demo entrypoint ────────────────────────────────────────────────


def demo() -> int:
    """Self-contained demo. Isolates a temp brain, seeds a 'prior session'
    memory, boots one cell, and prints the three proofs by reading the actual
    files Nucleus wrote. Run: ``python -m mcp_server_nucleus.runtime.agent_os.boot``.
    """
    import tempfile

    tmp = Path(tempfile.mkdtemp(prefix="agent_os_cell_"))
    os.environ["NUCLEUS_BRAIN_PATH"] = str(tmp)
    os.environ[BOOT_FLAG] = "1"
    os.environ[STUB_FLAG] = "1"  # deterministic offline model response for the demo
    os.environ.setdefault("NUCLEUS_DISABLE_ARTERY_4", "1")  # no trigger fan-out in demo

    def hr(title: str):
        print("\n" + "=" * 72)
        print(title)
        print("=" * 72)

    hr("NUCLEUS AGENT OS — STAGE 0: THE FIRST CELL")
    print(f"Isolated brain: {tmp}")

    # --- Prior session: write a memory the future cell must recall. -----------
    from nucleus_wedge.store import Store

    prior = (
        "The Nucleus gateway routes an agent's model calls through the OS; agents "
        "live INSIDE via the gateway, they do not call in via MCP."
    )
    Store(tmp).append(
        value=prior,
        kind="note",
        tags=["topic:gateway", "session:prior"],
        source_agent="prior-session-agent",
    )
    Store(tmp).append(
        value="Unrelated memory: the coffee machine on floor 3 is broken.",
        kind="note",
        tags=["topic:office"],
        source_agent="prior-session-agent",
    )
    print(f"\n[prior session] wrote 2 memories to {tmp}/engrams/history.jsonl")
    print(f"  target memory: {prior!r}")

    # --- Boot the cell (recall → think → record). -----------------------------
    intent = "How should this agent route its model calls — inside Nucleus or out?"
    result = boot_cell(intent, recall_query="gateway", brain_path=str(tmp))

    # --- PROOF 1: the model call went through the Nucleus engine, not raw. -----
    hr("PROOF 1 — cognition was MEDIATED by the Nucleus gateway (not raw Anthropic)")
    g = result.gateway_result
    print(f"  engine        : {g.engine}   (stubbed_provider_call={g.stubbed})")
    print(f"  model         : {g.model}")
    print(f"  mediated      : {g.mediated}  (Nucleus emitted its own LLM_GENERATE event)")
    print(f"  LLM_GENERATE  : {g.event_id}")
    print(f"  note          : {g.note}")
    events_path = tmp / "ledger" / "events.jsonl"
    found_event = None
    if events_path.exists():
        for line in events_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            ev = json.loads(line)
            if ev.get("type") == "LLM_GENERATE":
                found_event = ev
    print(f"\n  events.jsonl LLM_GENERATE row (a raw provider call would write NONE):")
    print("    " + json.dumps(found_event, ensure_ascii=False) if found_event else "    <none>")
    raw_logs = list((tmp / "raw").glob("llm_interaction_*.json")) if (tmp / "raw").exists() else []
    print(f"  interaction captured to .brain/raw/: {len(raw_logs)} file(s)")

    # --- PROOF 2: a real recalled memory appeared in the injected context. -----
    hr("PROOF 2 — real recalled MEMORY was injected before the agent thought")
    print(f"  recalled_from_memory: {result.recalled_from_memory} "
          f"({len(result.recalled_rows)} row(s) from memories.db)")
    print("\n  injected context block:")
    for ln in result.injected_context.splitlines():
        print("    " + ln)
    target_recalled = any(prior in (r.get("text") or "") for r in result.recalled_rows)
    print(f"\n  target prior-session memory present in recall: {target_recalled}")

    # --- PROOF 3: the turn was written to the flywheel. ------------------------
    hr("PROOF 3 — the turn was RECORDED to the flywheel (LoopTurn)")
    turns_path = tmp / "training" / "loop_turns.jsonl"
    turn_rows = []
    if turns_path.exists():
        turn_rows = [json.loads(l) for l in turns_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    print(f"  loop_turns.jsonl rows: {len(turn_rows)}")
    if turn_rows:
        t = turn_rows[-1]
        print(f"  turn_id       : {t.get('turn_id')}")
        print(f"  intent        : {t.get('intent')}")
        print(f"  tools_used    : {t.get('tools_used')}")
        print(f"  signal_absorbed: {t.get('signal_absorbed')}")
        print(f"  metadata      : {json.dumps(t.get('metadata', {}), ensure_ascii=False)}")
        print(f"  outcome       : {t.get('outcome')[:200]}")

    # --- Verdict. -------------------------------------------------------------
    hr("VERDICT — is the cell alive?")
    alive = bool(found_event) and target_recalled and bool(turn_rows)
    print(f"  (1) cognition mediated by Nucleus gateway : {bool(found_event)}")
    print(f"  (2) real memory injected before thinking  : {target_recalled}")
    print(f"  (3) turn recorded to the flywheel         : {bool(turn_rows)}")
    print(f"\n  ONE AGENT LIVED INSIDE NUCLEUS FOR ONE TURN: {alive}")
    print(f"  (model-response seam STUBBED offline; recall + record are REAL)")
    return 0 if alive else 1


if __name__ == "__main__":
    raise SystemExit(demo())
