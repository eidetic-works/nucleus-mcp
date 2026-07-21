"""DSoR loop-closure demo: PENDING decisions -> ground-truth verdicts.

This is the keystone. Nucleus's DecisionLedger already records every decision
with audit_status='PENDING' and deterministic_anchor='NONE' — and nothing in
the codebase ever moves them off those defaults. This demo runs the Verifier as
the missing auditor: it ingests the PENDING decisions, checks each against live
git/HTTP/filesystem ground truth, and drives audit_status PENDING -> verdict AND
fills the deterministic_anchor the schema reserved for exactly this.

Non-destructive: the ledger lives in a throwaway temp dir, never the real brain.
Run:  .venv/bin/python demo/verifier/ledger_loop_demo.py
"""
import hashlib
import json
import os
import tempfile
from pathlib import Path

# Repo the git/fs anchors resolve against — supplied at runtime, never baked in.
DEMO_REPO = os.environ.get("VERIFIER_DEMO_REPO", ".")

from mcp_server_nucleus.runtime.dsor import DecisionLedger
from mcp_server_nucleus.runtime.verifier import (
    Anchor,
    InjectedReasoner,
    ProbeEngine,
    Verifier,
    ingest_pending_ledger,
    render_report,
)

CURATED = Path(__file__).parent / "curated_claims.json"
# A representative spread across the verdict space.
SUBSET = {
    "one-shipped-live",
    "inr-scope-18695-items",
    "budget-honesty-guard-shipped",
    "welcome-email-fired-e2e",
    "inrdeals-56-merchants-active",
}


def _ctx_hash(text: str) -> str:
    return "ctx-" + hashlib.sha256(text.encode()).hexdigest()[:12]


def set_deterministic_anchor(ledger: DecisionLedger, decision_id: str, anchor: str) -> bool:
    """Fill the deterministic_anchor field the DSoR schema reserved.

    Additive here to keep dsor.py pristine; productizes as a 1-method addition
    to DecisionLedger (same jsonl-rewrite pattern as update_audit_status)."""
    f = ledger.ledger_file
    if not f.exists():
        return False
    rows, found = [], False
    for line in f.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        data = json.loads(line)
        if data["decision_id"] == decision_id:
            data["deterministic_anchor"] = anchor
            found = True
        rows.append(data)
    if found:
        f.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    return found


def _anchor_summary(anchor_dicts):
    parts = []
    for a in anchor_dicts:
        spec = a.get("spec", {})
        op = spec.get("op", "?")
        tgt = spec.get("sha") or spec.get("url") or spec.get("path") or spec.get("note", "")
        parts.append(f"{a['kind']}:{op} {str(tgt)[:40]}".strip())
    return " | ".join(parts)


def main():
    claims_raw = json.loads(CURATED.read_text())
    chosen = [c for c in claims_raw if c["claim_id"] in SUBSET]

    tmp = Path(tempfile.mkdtemp(prefix="dsor_demo_"))
    ledger = DecisionLedger(brain_path=tmp)

    # 1. Record decisions the way any Nucleus agent would — born PENDING.
    id_to_anchors = {}
    id_to_summary = {}
    for c in chosen:
        entry = ledger.record_decision(
            intent=c["assertion"][:140],
            reasoning=f"Asserted done in relay {c.get('raw', {}).get('relay', '?')}",
            context_hash=_ctx_hash(c["assertion"]),
        )
        id_to_anchors[entry.decision_id] = [Anchor(**a) for a in c["anchors"]]
        id_to_summary[entry.decision_id] = _anchor_summary(c["anchors"])

    print("=" * 78)
    print("BEFORE — the DSoR as it exists today (recorded, never audited):")
    print("=" * 78)
    for d in ledger.list_all():
        print(f"  {d['decision_id']}  audit_status={d['audit_status']:<9}  "
              f"deterministic_anchor={d['deterministic_anchor']}")
        print(f"      intent: {d['intent'][:70]}")

    # 2. Run the Verifier as the missing auditor.
    claims = ingest_pending_ledger(ledger)
    verifier = Verifier(
        reasoner=InjectedReasoner(anchor_map=id_to_anchors),
        probe_engine=ProbeEngine(default_repo=DEMO_REPO),
        ledger=ledger,
        record=True,  # writes audit_status back via the ledger's own public API
    )
    verdicts = verifier.verify_all(claims)

    # 3. Fill the reserved deterministic_anchor field (additive helper).
    for v in verdicts:
        set_deterministic_anchor(ledger, v.claim_id, id_to_summary.get(v.claim_id, ""))

    print("\n" + "=" * 78)
    print("AFTER — the same ledger, once the Verifier has run:")
    print("=" * 78)
    for d in ledger.list_all():
        print(f"  {d['decision_id']}  audit_status={d['audit_status']:<12}  "
              f"anchor={d['deterministic_anchor'][:60]}")
        notes = d.get("metadata", {}).get("auditor_notes", "")
        if notes:
            print(f"      verdict: {notes[:90]}")

    print("\n" + render_report(verdicts))
    print(f"\n(scratch ledger: {ledger.ledger_file} — throwaway, real brain untouched)")


if __name__ == "__main__":
    main()
