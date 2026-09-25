"""`nucleus dream` — the door.

The pass was fully built and fully tested while having zero importers and no
surface that invoked it. These tests are about reachability and refusal: that
the verb exists, that its exit codes are usable from a script, and above all
that it CANNOT accept its own proposals.
"""

import argparse
import json

import pytest

from mcp_server_nucleus.flywheel import proposals, trigger
from mcp_server_nucleus.flywheel.dream_cli import add_dream_parser, handle_dream_command


def _args(**kw):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cli_command")
    add_dream_parser(sub)
    argv = ["dream"]
    # dest -> flag, where argparse's dest is not the flag spelling
    spelling = {"list_proposals": "--list"}
    for k, v in kw.items():
        flag = spelling.get(k, "--" + k.replace("_", "-"))
        if v is True:
            argv.append(flag)
        elif v is not False and v is not None:
            argv += [flag, str(v)]
    return ap.parse_args(argv)


def _corpus(tmp_path, n, text="widget exploded"):
    root = tmp_path / "projects" / "p"
    root.mkdir(parents=True, exist_ok=True)
    for i in range(n):
        (root / f"s{i}.jsonl").write_text(
            json.dumps({"message": {"content": [{"type": "text", "text": text}]}}) + "\n")
    return tmp_path / "projects"


@pytest.fixture
def brain(tmp_path):
    b = tmp_path / "brain"
    b.mkdir()
    return b


# --- exit codes are the scriptable surface ---------------------------------

def test_check_exits_zero_when_due(tmp_path, brain, capsys):
    roots = _corpus(tmp_path, 3)
    rc = handle_dream_command(_args(check=True, brain_path=brain, roots=roots))
    assert rc == 0
    assert "DUE" in capsys.readouterr().out


def test_check_exits_one_when_not_due(tmp_path, brain, capsys):
    roots = _corpus(tmp_path, 3)
    trigger.record_pass(brain)
    rc = handle_dream_command(_args(check=True, brain_path=brain, roots=roots))
    assert rc == 1, "a script could not tell 'due' from 'not due'"
    assert "not due" in capsys.readouterr().out


def test_a_pass_refuses_to_run_when_nothing_accumulated(tmp_path, brain, capsys):
    roots = _corpus(tmp_path, 3)
    trigger.record_pass(brain)
    cand = tmp_path / "c.json"
    cand.write_text(json.dumps([{"pattern": "widget exploded", "memory": "m"}]))
    rc = handle_dream_command(_args(candidates=cand, brain_path=brain, roots=roots))
    assert rc == 1
    assert proposals.all_proposals(brain) == []


def test_force_overrides_the_activity_gate(tmp_path, brain):
    roots = _corpus(tmp_path, 3)
    trigger.record_pass(brain)
    cand = tmp_path / "c.json"
    cand.write_text(json.dumps([{"pattern": "widget exploded", "memory": "m"}]))
    rc = handle_dream_command(
        _args(candidates=cand, brain_path=brain, roots=roots, force=True, min_sessions=2))
    assert rc == 0
    assert len(proposals.all_proposals(brain)) == 1


# --- THE CENTRAL REFUSAL: the verb cannot accept ---------------------------

def test_a_pass_records_proposals_but_writes_no_memory(tmp_path, brain):
    """Accepting writes to memory and is the operator's act, not the agent's."""
    roots = _corpus(tmp_path, 3)
    cand = tmp_path / "c.json"
    cand.write_text(json.dumps([{"pattern": "widget exploded", "memory": "widgets explode"}]))
    handle_dream_command(_args(candidates=cand, brain_path=brain, roots=roots, min_sessions=2))

    assert len(proposals.pending(brain)) == 1, "nothing was proposed"
    assert all(r["status"] == "pending" for r in proposals.all_proposals(brain))
    hist = brain / "engrams" / "history.jsonl"
    assert not hist.exists() or hist.read_text().strip() == "", (
        "the verb wrote to memory without anyone accepting"
    )


def test_the_verb_offers_no_accept_flag():
    """Structural: the door to memory is not in this room."""
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cli_command")
    add_dream_parser(sub)
    flags = {o for a in sub.choices["dream"]._actions for o in a.option_strings}
    assert not any("accept" in f for f in flags), f"an accept flag exists: {flags}"


# --- the listing surfaces the third state ----------------------------------

def test_list_marks_a_proposal_that_cannot_be_accepted(tmp_path, brain, capsys):
    from mcp_server_nucleus.flywheel.prevalence import Prevalence

    pv = Prevalence(pattern="p", sessions_matched=3, sessions_scanned=10,
                    complete=False, insufficient_reason="the cap was reached")
    proposals.propose(brain, "a memory", pv, pattern="p")
    handle_dream_command(_args(list_proposals=True, brain_path=brain))
    assert "INSUFFICIENT" in capsys.readouterr().out


def test_list_is_quiet_when_there_is_nothing_to_decide(brain, capsys):
    handle_dream_command(_args(list_proposals=True, brain_path=brain))
    assert "no proposals" in capsys.readouterr().out


# --- precision through the door -------------------------------------------

def _run_a_pass(tmp_path, brain):
    roots = _corpus(tmp_path, 8)
    cand = tmp_path / "c.json"
    cand.write_text(json.dumps([{"pattern": "widget exploded", "memory": "widgets explode"}]))
    handle_dream_command(_args(candidates=cand, brain_path=brain, roots=roots, min_sessions=2))
    return proposals.pending(brain)[0]["proposal_id"]


def test_sample_writes_the_matches_a_labeller_needs(tmp_path, brain, capsys):
    pid = _run_a_pass(tmp_path, brain)
    out = tmp_path / "sample.txt"
    handle_dream_command(_args(sample=out, brain_path=brain))
    text = out.read_text()
    assert pid in text and "widget exploded" in text and "[1]" in text
    assert "true" in capsys.readouterr().out, "the labelling prompt was not shown"


def test_labels_through_the_door_make_a_proposal_acceptable(tmp_path, brain):
    pid = _run_a_pass(tmp_path, brain)
    n = len(proposals.pending(brain)[0]["evidence"]["sample"])
    lab = tmp_path / "labels.json"
    lab.write_text(json.dumps({pid: [True] * n}))
    assert handle_dream_command(_args(labels=lab, brain_path=brain)) == 0
    assert proposals.accept(brain, pid)["status"] == "accepted"


def test_mislabelled_input_is_refused_through_the_door(tmp_path, brain, capsys):
    pid = _run_a_pass(tmp_path, brain)
    lab = tmp_path / "labels.json"
    lab.write_text(json.dumps({pid: [True, True]}))
    assert handle_dream_command(_args(labels=lab, brain_path=brain)) == 1
    assert "REFUSED" in capsys.readouterr().out


def test_list_says_when_precision_is_unmeasured(tmp_path, brain, capsys):
    _run_a_pass(tmp_path, brain)
    capsys.readouterr()
    handle_dream_command(_args(list_proposals=True, brain_path=brain))
    assert "precision NOT measured" in capsys.readouterr().out


def test_mine_lists_a_recurring_flagged_error_through_the_door(tmp_path, brain, capsys):
    root = tmp_path / "projects" / "p"
    root.mkdir(parents=True)
    for i in range(6):
        (root / f"s{i}.jsonl").write_text(json.dumps({"type": "user", "message": {"content": [
            {"type": "tool_result", "tool_use_id": "t", "is_error": True,
             "content": f"File does not exist: /srv/x/f{i}.py"}]}}) + "\n")
    rc = handle_dream_command(_args(mine=True, brain_path=brain, roots=tmp_path / "projects"))
    out = capsys.readouterr().out
    assert rc == 0 and "6 sessions" in out and "file does not exist" in out
    assert proposals.all_proposals(brain) == [], "mining must not create proposals"
