"""``nucleus dream`` — the door to the discovery pass.

The pass was built and then had no way in: `discovery`, `trigger` and
`scan_many` had zero importers and no surface invoked them. Code nothing can
call is not a feature, however well tested.

The verb is deliberately in four steps rather than one, because the expensive
step and the irreversible step must both be things you choose:

    nucleus dream --check        is a pass due?            (under a second)
    nucleus dream --batch F      write what an agent reads (seconds)
    nucleus dream --candidates F measure them              (~24 min, full corpus)
    nucleus dream --list         show what is awaiting a decision

Accepting is NOT here. `accept` writes to memory and is the operator's act;
a verb that could accept its own proposals would be an agent marking its own
homework, which is the thing this whole subsystem exists to prevent.

The agent step is external on purpose. `discovery.discover` takes an injected
``propose_fn`` so the discoverer can be a Haiku subagent, a free vendor lane or
a person -- none of which is a subprocess this CLI should be spawning.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, List, Optional

DISCOVERY_PROMPT = """\
You are the DISCOVERY half of a memory flywheel. Notice recurring patterns.
Do NOT count anything: a deterministic counter measures prevalence over the
full corpus, and any number you assert is discarded.

Read the batch file. It holds excerpts from recent sessions, one block each,
headed `--- session <id> ---`.

Look for RECURRING OPERATIONAL FAILURE MODES -- things that went wrong more
than once, across different sessions, under different wordings. Ignore one-off
content and ordinary successful work.

Return ONLY a JSON array of at most 6 objects, no prose, no markdown fence:
  {"pattern": "<python regex, IGNORECASE, must NOT match the empty string.
                SHORT: 2-3 literal words or a single distinctive phrase, with
                `|` alternation for wordings. Do NOT chain words with `.*` --
                that requires every word on one line in order and undercounts
                badly. No ^ or $ anchors>",
   "memory":  "<one sentence: the durable lesson>",
   "rationale": "<why it recurs -- no counts, no frequencies>"}

Returning [] is a correct answer. Do not invent patterns to fill the list.
"""


LABEL_PROMPT = """\
You are the PRECISION half of a memory flywheel. For each numbered excerpt, say
whether it actually shows the failure described by the MEMORY line above it.

A regex found these by matching words, so many will be ordinary sentences that
merely share vocabulary. Judge the failure, not the words.

  true   the excerpt shows this failure happening
  false  it does not (ordinary text, a discussion of the topic, an unrelated use)
  null   you cannot tell from the excerpt

Do NOT count anything and do NOT estimate a rate. Return ONLY JSON, one array
per proposal id, one entry per excerpt IN ORDER:
  {"prop_...": [true, false, null, ...]}
"""


def add_dream_parser(subparsers: Any) -> Any:
    p = subparsers.add_parser(
        "dream",
        help="Discovery pass: find recurring patterns and measure them honestly",
    )
    p.add_argument("--check", action="store_true",
                   help="Only ask whether a pass is due. Exit 0 if due, 1 if not.")
    p.add_argument("--batch", metavar="FILE",
                   help="Write the reading sample for a discovering agent")
    p.add_argument("--candidates", metavar="FILE",
                   help="Verify agent-proposed candidates (JSON array) over the full corpus")
    p.add_argument("--mine", action="store_true",
                   help="Rank recurring harness-flagged errors by distinct sessions "
                        "(no agent; every count is of a real is_error result)")
    p.add_argument("--mine-min-sessions", type=int, default=5,
                   help="Distinct sessions an error signature needs to be listed (default: 5)")
    p.add_argument("--sample", metavar="FILE",
                   help="Write the sampled matches for a labeller to judge precision")
    p.add_argument("--labels", metavar="FILE",
                   help="Record a labeller's judgements (JSON: {proposal_id: [true,false,null,...]})")
    p.add_argument("--list", dest="list_proposals", action="store_true",
                   help="Show proposals awaiting a decision")
    p.add_argument("--brain-path", metavar="DIR", help="Brain directory (default: resolved)")
    p.add_argument("--roots", metavar="DIR", action="append",
                   help="Transcript root(s); repeatable. Default: ~/.claude/projects")
    p.add_argument("--min-new-sessions", type=int, default=20,
                   help="Sessions of new activity required to be due (default: 20)")
    p.add_argument("--min-sessions", type=int, default=2,
                   help="Distinct sessions a pattern needs to be proposed (default: 2)")
    p.add_argument("--max-batch-sessions", type=int, default=25,
                   help="Sessions to put in the reading batch (default: 25)")
    p.add_argument("--oldest", action="store_true",
                   help="Batch from the OLDEST sessions instead of the newest")
    p.add_argument("--force", action="store_true",
                   help="Run even when the activity gate says no work has accumulated")
    p.add_argument("--json", dest="json_output", action="store_true",
                   help="Machine-readable output")
    return p


def _brain(args: Any) -> Path:
    if getattr(args, "brain_path", None):
        return Path(args.brain_path)
    from nucleus_wedge.store import Store
    return Store.brain_path()


def _roots(args: Any) -> Optional[List[Path]]:
    r = getattr(args, "roots", None)
    return [Path(x) for x in r] if r else None


def handle_dream_command(args: Any) -> int:
    from . import proposals, trigger
    from .discovery import Candidate, gather_batch, verify

    brain = _brain(args)
    roots = _roots(args)

    if getattr(args, "list_proposals", False):
        rows = proposals.pending(brain)
        if args.json_output:
            print(json.dumps(rows, indent=2))
        elif not rows:
            print("no proposals awaiting a decision.")
        else:
            print(f"{len(rows)} proposal(s) awaiting YOUR decision:\n")
            for r in rows:
                ev = r.get("evidence") or {}
                print(f"  {r['proposal_id']}")
                print(f"    memory:  {r['proposed_memory']}")
                print(f"    pattern: {r['pattern']}")
                print(f"    evidence: {ev.get('summary', '(none)')}")
                if not ev.get("complete", False):
                    print("    ** INSUFFICIENT — cannot be accepted **")
                pr = ev.get("precision")
                if pr:
                    print(f"    precision: {pr['positive']} of {pr['labeled']} sampled "
                          f"matches showed the failure (lower bound {pr['wilson_lower']:.0%})")
                elif ev.get("precision_required"):
                    print("    ** precision NOT measured — cannot be accepted "
                          "(nucleus dream --sample) **")
                print()
        return 0

    if getattr(args, "mine", False):
        from .mining import mine
        m = mine(roots=roots, min_sessions=args.mine_min_sessions)
        if args.json_output:
            print(json.dumps([c.as_dict() for c in m.clusters], indent=2))
            return 0
        print(f"read {m.sessions_scanned} session(s); excluded {m.sessions_excluded} dreaming "
              f"session(s); {m.sessions_with_errors} had a flagged error "
              f"({m.errors_seen} errors in all).\n")
        for cl in m.clusters:
            print(f"{cl.sessions:5d} sessions  {cl.occurrences:6d} occurrences  {cl.signature}")
            print(f"        e.g. {cl.example[:150]}")
        return 0

    if getattr(args, "sample", None):
        rows = [r for r in proposals.pending(brain)
                if (r.get("evidence") or {}).get("precision_required")
                and not (r.get("evidence") or {}).get("precision")]
        lines = []
        for r in rows:
            ev = r["evidence"]
            lines.append(f"=== {r['proposal_id']} ===")
            lines.append(f"MEMORY: {r['proposed_memory']}")
            lines.append(f"PATTERN: {r['pattern']}   ({ev.get('sessions_matched')} sessions matched)")
            for i, e in enumerate(ev.get("sample") or [], 1):
                lines.append(f"  [{i}] {e.get('excerpt', '')}")
            lines.append("")
        out = Path(args.sample); out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("\n".join(lines), encoding="utf-8")
        print(f"wrote samples for {len(rows)} unlabelled proposal(s) to {out}")
        if rows:
            print("\nGive a cheap agent this file and the prompt below, then run:")
            print("  nucleus dream --labels <its-json-output>\n")
            print(LABEL_PROMPT)
        return 0

    if getattr(args, "labels", None):
        raw = json.loads(Path(args.labels).read_text(encoding="utf-8"))
        bad = 0
        for pid, labs in raw.items():
            try:
                row = proposals.label(brain, pid, labs, by="labeller-agent")
                pr = row["evidence"]["precision"]
                print(f"{pid}: {pr['positive']} of {pr['labeled']} showed the failure "
                      f"(lower bound {pr['wilson_lower']:.0%})")
            except ValueError as exc:
                bad += 1
                print(f"{pid}: REFUSED — {exc}")
        return 1 if bad else 0

    decision = trigger.should_run(brain, roots=roots,
                                  min_new_sessions=args.min_new_sessions)

    if args.check:
        if args.json_output:
            print(json.dumps(decision.as_dict(), indent=2))
        else:
            print(("DUE: " if decision.should_run else "not due: ") + decision.reason)
        return 0 if decision.should_run else 1

    if not decision.should_run and not args.force:
        print(f"not due: {decision.reason}")
        print("\nNothing to do. Use --force to run anyway.")
        return 1

    if args.batch:
        batch = gather_batch(roots=roots, max_sessions=args.max_batch_sessions,
                             oldest=args.oldest)
        out = Path(args.batch)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(batch.as_prompt(), encoding="utf-8")
        print(f"wrote {len(batch.excerpts)} session(s) to {out}")
        if batch.sampled:
            print(f"  (sampled from {batch.sessions_available}; a batch is a "
                  f"prompt, not a measurement — nothing here is counted)")
        print("\nGive a cheap agent this file and the prompt below, then run:")
        print(f"  nucleus dream --candidates <its-json-output>\n")
        print(DISCOVERY_PROMPT)
        return 0

    if args.candidates:
        raw = json.loads(Path(args.candidates).read_text(encoding="utf-8"))
        cands = [
            Candidate(pattern=c.get("pattern", ""), memory=c.get("memory", ""),
                      rationale=c.get("rationale", ""))
            for c in raw
        ]
        print(f"measuring {len(cands)} candidate(s) over the full corpus. "
              f"This reads everything once and takes a while.", flush=True)
        d = verify(cands, brain_path=brain, roots=roots, min_sessions=args.min_sessions)
        if args.json_output:
            print(json.dumps([v.as_dict() for v in d.verdicts], indent=2, default=str))
        else:
            print(f"\n{d.summary()}\n")
            for v in d.verdicts:
                if v.refused:
                    print(f"REFUSED  {v.candidate.pattern[:46]}\n         {v.refused}")
                else:
                    pv = v.prevalence
                    print(f"PROPOSED {v.candidate.pattern[:46]}")
                    print(f"         {pv.sessions_matched} of {pv.sessions_scanned} "
                          f"sessions | complete={pv.complete}")
                    if not pv.complete:
                        print(f"         INSUFFICIENT — cannot be accepted: "
                              f"{pv.insufficient_reason}")
        # Every measured count, refused or not. A near-miss (14 sessions against
        # a floor of 50) is information for a human, not something to discard.
        measured = sorted(
            (v for v in d.verdicts if v.prevalence is not None),
            key=lambda v: -v.prevalence.sessions_matched,
        )
        if measured and not args.json_output:
            print("\nALL MEASURED COUNTS (highest first):")
            for v in measured:
                pv = v.prevalence
                tag = "proposed" if v.proposed else "refused"
                print(f"  {pv.sessions_matched:5d} / {pv.sessions_scanned}  [{tag}]  {v.candidate.pattern[:60]}")
        trigger.record_pass(brain, proposals_made=len(d.proposed))
        if d.proposed:
            print(f"\n{len(d.proposed)} proposal(s) recorded. Nothing has been "
                  f"written to memory.\nReview with:  nucleus dream --list")
        return 0

    # No mode given: say what is true and what to do next.
    print(f"DUE: {decision.reason}")
    print("\nA pass is three steps, because the slow one and the irreversible "
          "one should both be chosen:")
    print("  1. nucleus dream --batch /tmp/batch.txt      # seconds")
    print("  2. give it to a cheap agent (prompt is printed by step 1)")
    print("  3. nucleus dream --candidates /tmp/cands.json # reads the whole corpus")
    print("\nAccepting is not one of these. It writes memory, and it is yours.")
    return 0
