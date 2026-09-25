"""Three-state lane verdicts, tested against a hostile vendor.

Why this exists: the lane's verdict was binary -- >=5 changed lines or failure --
so a doc that was genuinely accurate was indistinguishable from a vendor that
did nothing. Both read "PAUSED: 0 real lines". "Done" collapsed into "stopped".

Adding CLEAN as a PASSING outcome is the dangerous half of this change: claiming
CLEAN is cheaper than doing the audit. So the tests that matter here are the
ones where CLEAN must be REFUSED. A judge that only ever accepts is not a judge,
and would be strictly worse than the binary bar it replaces -- it would convert
"no work done" from a visible failure into a silent pass.
"""

import tempfile
from pathlib import Path

import pytest

from mcp_server_nucleus.runtime.lane import verdict as V


DOC = "docs/AUDITED.md"
TASK = "sweep_docs_audited_md"


@pytest.fixture()
def repo():
    """A real git repo: evidence paths must be TRACKED, not merely present."""
    import subprocess
    with tempfile.TemporaryDirectory() as td:
        r = Path(td)
        subprocess.run(["git", "init", "-q", str(r)], check=True)
        for k, v in (("user.email", "t@t.t"), ("user.name", "t")):
            subprocess.run(["git", "-C", str(r), "config", k, v], check=True)
        (r / "src").mkdir()
        # Each source file shares one distinctive token with the doc.
        (r / "src" / "alpha.py").write_text("def claim_survival_rate():\n    pass\n")
        (r / "src" / "beta.py").write_text("MAX_CONCURRENT_LANES = 3\n")
        (r / "src" / "gamma.py").write_text("class EngramWriter:\n    pass\n")
        (r / "docs").mkdir()
        (r / DOC.split("/")[1] if False else r / "docs" / "AUDITED.md").write_text(
            "# Audited\n"
            "Nucleus computes `claim_survival_rate()` per lane.\n"
            "Concurrency is capped by `MAX_CONCURRENT_LANES`.\n"
            "Engrams are written by `EngramWriter`.\n"
        )
        subprocess.run(["git", "-C", str(r), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(r), "commit", "-qm", "base"], check=True)
        yield r


def _block(claims=4, rows=None, verdict="CLEAN", task=TASK):
    rows = rows if rows is not None else [
        "- CSR is computed | TRUE | src/alpha.py | claim_survival_rate",
        "- concurrency capped | TRUE | src/beta.py:1 | MAX_CONCURRENT_LANES",
        "- engrams written | TRUE | src/gamma.py | EngramWriter",
    ]
    head = f"VERDICT: {verdict}\nTASK_ID: {task}\nCLAIMS_CHECKED: {claims}\nEVIDENCE:\n"
    return head + "\n".join(rows)


def _judge(repo, block, diff=False):
    return V.judge_clean(V.parse_verdict(block), repo, has_in_scope_diff=diff,
                         doc_path=DOC, task_id=TASK)


def test_a_real_audit_is_accepted(repo):
    """POSITIVE: a vendor that checked claims and cited real paths gets CLEAN.
    Without this the third state is unreachable and the feature is dead."""
    j = _judge(repo, _block())
    assert j.accepted and j.verdict == V.CLEAN, j.reason


def test_fabricated_paths_are_refused(repo):
    """OPPOSED, load-bearing: a vendor that never opened the repo cites
    plausible paths that do not exist. This is the cheapest possible forgery and
    must be the one the judge catches."""
    rows = [
        "- a | TRUE | src/does_not_exist.py | claim_survival_rate",
        "- b | TRUE | src/also_missing.py | MAX_CONCURRENT_LANES",
        "- c | TRUE | src/imaginary.py | EngramWriter",
    ]
    j = _judge(repo, _block(rows=rows))
    assert not j.accepted, "fabricated paths were accepted as evidence"
    assert j.verdict == V.INSUFFICIENT
    assert j.real_paths == 0


def test_a_bare_claim_count_is_not_evidence(repo):
    """OPPOSED: CLAIMS_CHECKED is an integer the vendor typed. Emitting a high
    number with no evidence rows must not pass."""
    j = _judge(repo, f"VERDICT: CLEAN\nTASK_ID: {TASK}\nCLAIMS_CHECKED: 99\n")
    assert not j.accepted and "evidence row" in j.reason


def test_one_real_path_cited_three_times_is_not_three_checks(repo):
    """OPPOSED: distinctness is the point. Citing the same file repeatedly is
    one act of verification dressed as three."""
    rows = ["- claim %d | TRUE | src/alpha.py | claim_survival_rate" % i for i in range(3)]
    j = _judge(repo, _block(rows=rows))
    assert not j.accepted, "repeated citation of one file passed as three checks"


def test_clean_while_also_editing_the_file_is_incoherent(repo):
    """OPPOSED: either the doc was already correct or it needed changing. A
    vendor claiming both is not describing a real outcome."""
    j = _judge(repo, _block(), diff=True)
    assert not j.accepted and "incoherent" in j.reason


def test_clean_citing_its_own_false_claim_is_refused(repo):
    """OPPOSED: self-contradiction. The vendor found a stale claim and then
    reported the doc clean."""
    rows = [
        "- CSR is computed | TRUE | src/alpha.py | claim_survival_rate",
        "- cap is current | STALE | src/beta.py | MAX_CONCURRENT_LANES",
        "- engrams written | TRUE | src/gamma.py | EngramWriter",
    ]
    j = _judge(repo, _block(rows=rows))
    assert not j.accepted and "contradict" in j.reason


def test_too_few_claims_is_refused(repo):
    """OPPOSED: one checked claim is not an audit."""
    rows = ["- CSR | TRUE | src/alpha.py | claim_survival_rate"]
    j = _judge(repo, _block(claims=1, rows=rows))
    assert not j.accepted


def test_no_verdict_block_at_all_yields_insufficient(repo):
    """A vendor that emitted nothing structured is INSUFFICIENT -- a real,
    readable outcome. It must not be silently treated as either pass or crash."""
    j = _judge(repo, "I looked at the file and it seems fine.")
    assert j.verdict == V.INSUFFICIENT and not j.accepted


def test_parser_does_not_judge(repo):
    """The parser must report what was written, including a hostile claim, and
    leave the judging to judge_clean. Merging the two makes hostile input
    untestable."""
    p = V.parse_verdict(_block(rows=["- x | TRUE | totally/fake.py | tok"]))
    assert p.verdict == V.CLEAN, "parser refused to parse a claim it should judge later"
    assert p.evidence[0].path == "totally/fake.py"


def test_line_suffixes_do_not_break_path_resolution(repo):
    """OPPOSED direction -- over-strictness. 'src/alpha.py:42' is a normal,
    correct citation format and must not be rejected as a missing file. A
    control that rejects good work makes the third state useless."""
    syms = ("claim_survival_rate", "MAX_CONCURRENT_LANES", "EngramWriter")
    rows = [f"- c{i} | TRUE | src/{n}:{i+1} | {syms[i]}"
            for i, n in enumerate(("alpha.py", "beta.py", "gamma.py"))]
    j = _judge(repo, _block(rows=rows))
    assert j.accepted, f"line-numbered citations wrongly refused: {j.reason}"


# --- the instrument must stay reachable -------------------------------------
# A judge that no vendor is ever told how to satisfy is dead by construction:
# it would run every cycle, refuse everything, and look like a working guard.
# These pin the protocol into the dispatch prompt itself.

def _prompt():
    from unittest.mock import MagicMock
    from mcp_server_nucleus.runtime.lane.executor_daemon import ExecutorDaemon
    d = ExecutorDaemon.__new__(ExecutorDaemon)
    d.config = MagicMock()
    d.config.repo_root = "/repo"
    d.agent_id, d.vendor = "lane_test", "devin"
    return d._build_prompt({"id": "t1", "description": "Audit `docs/X.md`"})


def test_the_vendor_is_actually_told_how_to_declare_clean():
    """Without this the CLEAN path is unreachable: judge_clean would refuse
    every task forever while looking like a working guard."""
    p = _prompt()
    for token in ("VERDICT: CLEAN", "CLAIMS_CHECKED:", "EVIDENCE:", "VERDICT: INSUFFICIENT"):
        assert token in p, f"dispatch prompt no longer teaches {token!r}"


def test_the_prompt_states_the_checkable_constraints():
    """The vendor must know the bar is machine-checked, or it will cite
    plausible-looking paths and be refused for a reason it was never told."""
    p = _prompt()
    assert "DIFFERENT files that git" in p and "TRACKS" in p
    assert "Files you create yourself do not count" in p
    assert "exactly ONE" in p, "hedging rule not taught"
    # The symbol is the anti-guessing control; a vendor not told about it will
    # be refused for a rule it was never given.
    assert "<SYMBOL>" in p and "appears in BOTH" in p
    assert "TASK_ID:" in p


def test_the_prompt_no_longer_orders_the_vendor_to_commit():
    """It used to say 'commit the result, mark the task DONE with the commit
    SHA' while the preamble forbade git state changes -- two subsystems built on
    opposite assumptions, which failed every LLM task structurally."""
    p = _prompt()
    assert "commit the result" not in p
    assert "DO NOT run git commit" in p


def test_the_prompt_says_finding_nothing_is_not_a_failure():
    """The pressure that produces invented edits is a bar you can only clear by
    changing something."""
    p = _prompt()
    assert "not a failure" in p.lower()
    assert "do NOT invent an edit" in p or "invent an edit" in p


# --- the five bypasses an adversarial panel found in the FIRST design --------
# Each of these defeated the original controls (>=3 claims, >=3 distinct paths
# that exist on disk). They are kept as named tests because the controls that
# stop them are not obvious, and a future simplification would silently
# reopen them.

def test_bypass_guessable_paths_with_the_doc_never_opened(repo):
    """BYPASS 1 -- the cheapest forgery. Every model can guess pyproject.toml,
    AGENTS.md, DECISIONS.md from the repo name alone. They exist, they are
    tracked, they are distinct, and none of them requires opening the doc.
    Only the shared-symbol check refuses this."""
    import subprocess
    for n in ("pyproject.toml", "AGENTS.md", "DECISIONS.md"):
        (repo / n).write_text("unrelated content\n")
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "guessables"], check=True)
    rows = [
        "- ships as a package | TRUE | pyproject.toml | packaging",
        "- guardrails documented | TRUE | AGENTS.md | guardrails",
        "- decisions recorded | TRUE | DECISIONS.md | decisions",
    ]
    j = _judge(repo, _block(rows=rows))
    assert not j.accepted, "guessable real paths passed with the doc never opened"
    assert "BOTH" in j.reason


def test_bypass_vendor_creates_the_files_it_cites(repo):
    """BYPASS 2 -- the vendor has write access to the live tree. An UNTRACKED
    file exists on disk and produces no diff, satisfying 'exists' and 'no edit'
    at once. Only the git-tracked check refuses this."""
    (repo / "src" / "made_up_a.py").write_text("claim_survival_rate\n")
    (repo / "src" / "made_up_b.py").write_text("MAX_CONCURRENT_LANES\n")
    (repo / "src" / "made_up_c.py").write_text("EngramWriter\n")
    rows = [
        "- CSR | TRUE | src/made_up_a.py | claim_survival_rate",
        "- cap | TRUE | src/made_up_b.py | MAX_CONCURRENT_LANES",
        "- engram | TRUE | src/made_up_c.py | EngramWriter",
    ]
    j = _judge(repo, _block(rows=rows))
    assert not j.accepted, "vendor-created untracked files were accepted as evidence"
    assert "tracked" in j.reason


def test_bypass_replaying_a_block_accepted_for_another_task(repo):
    """BYPASS 3 -- accepted blocks are stored in the ledger and echoed in relay
    bodies, both readable by the vendor. An unbound block can be lifted verbatim
    and replayed against a different doc. Only the TASK_ID binding refuses it."""
    j = _judge(repo, _block(task="sweep_some_other_doc_md"))
    assert not j.accepted, "a block bound to another task was accepted"
    assert "replayed" in j.reason or "TASK_ID" in j.reason


def test_bypass_hedging_with_two_verdict_blocks(repo):
    """BYPASS 4 -- print CLEAN early and INSUFFICIENT in a closing summary, and
    pass on whichever the parser reaches first."""
    j = _judge(repo, _block() + "\n\nOn reflection:\nVERDICT: INSUFFICIENT\n")
    assert not j.accepted, "a hedged double verdict was accepted"
    assert "VERDICT lines" in j.reason


def test_bypass_borrowed_commit_sha_is_no_longer_readable(repo):
    """BYPASS 5 -- `git log -20 --format=%H | tail -1` printed by a vendor that
    did nothing used to be scraped from stdout and verified as this run's work.
    The scraper now refuses to read any SHA at all."""
    from unittest.mock import MagicMock
    from mcp_server_nucleus.runtime.lane.executor_daemon import ExecutorDaemon
    d = ExecutorDaemon.__new__(ExecutorDaemon)
    d.config = MagicMock()
    borrowed = "a" * 40
    assert d._extract_commit_sha({"result": f"Committed as {borrowed}"}) == "unknown", (
        "vendor stdout is still being mined for a commit SHA"
    )
    assert d._extract_commit_sha({"result": "deadbeef"}) == "unknown"


def test_a_genuine_audit_still_passes_after_all_five_controls(repo):
    """The control that matters most: none of the above may cost a real audit.
    Five refusals and zero acceptances would be a dead judge -- indistinguishable
    from a working one, and the exact failure this session has been about."""
    j = _judge(repo, _block())
    assert j.accepted, f"real audit refused after hardening: {j.reason}"


def test_the_prompt_forbids_writing_absolute_home_paths():
    """Vendors get the repo root as an absolute path in their prompt and paste it
    back into prose. That leaks the operator's identity into the corpus and the
    pseudonymity hook blocks the commit, failing the whole task for a rule the
    vendor was never told. Observed on 3 of 8 stranded edits, 2026-08-19."""
    p = _prompt()
    assert "NEVER write an absolute home path" in p
    assert "~/" in p


def test_a_refused_verdict_is_logged_with_the_evidence_it_refused():
    """A gate whose rejections cannot be reviewed cannot be calibrated.

    When judge_clean refused a CLEAN in the wild ("0 of 5 cited paths are
    git-tracked"), the vendor's actual evidence was gone -- nothing persisted it
    -- so a CORRECT refusal and an OVER-STRICT one were indistinguishable from
    outside. This repo's design law is that trust requires a second party able
    to evaluate the meaning; a one-line reason is not enough to be that party.
    """
    import inspect
    from mcp_server_nucleus.runtime.lane.executor_daemon import ExecutorDaemon
    src = inspect.getsource(ExecutorDaemon)
    assert "clean_refusals.jsonl" in src, "refused verdicts are not persisted"
    # The evidence itself must be written, not just the verdict label -- the
    # cited paths and symbols are the whole point of the audit.
    i = src.find("clean_refusals.jsonl")
    block = src[i:i + 1200]
    for field in ('"evidence"', '"path"', '"symbol"', '"reason"'):
        assert field in block, f"refusal log omits {field}"


def test_logging_a_refusal_cannot_break_the_task_result():
    """OPPOSED: bookkeeping must never cost the verdict. If the refusal log
    cannot be written, the task must still fail for its real reason."""
    import inspect
    from mcp_server_nucleus.runtime.lane.executor_daemon import ExecutorDaemon
    src = inspect.getsource(ExecutorDaemon)
    i = src.find("clean_refusals.jsonl")
    block = src[i - 400:i + 1400]
    assert "except Exception" in block, "refusal logging is not best-effort"


def test_clean_is_refused_when_the_doc_was_edited_but_never_committed():
    """THE FALSE ACCEPT. has_in_scope_diff used to be derived from whether a
    COMMIT happened, not from whether the doc CHANGED. A vendor that edited the
    file and whose commit returned "unknown" -- no declared-scope match, a failed
    commit, or the executor killed mid-dispatch -- looked like "no diff", so
    CLEAN was accepted alongside a real edit.

    Measured in the wild: 9 docs marked verification_status=clean while carrying
    staged, uncommitted edits to those same docs.
    """
    import inspect
    from mcp_server_nucleus.runtime.lane.executor_daemon import ExecutorDaemon
    src = inspect.getsource(ExecutorDaemon)
    i = src.find("has_in_scope_diff=")
    assert i > 0, "judge_clean call not found"
    call = src[max(0, i - 900):i + 120]
    assert "_worktree_state()" in call and "pre_state.get" in call, (
        "has_in_scope_diff is not derived from the worktree -- a CLEAN can "
        "still be accepted alongside an uncommitted edit"
    )
    assert "has_in_scope_diff=_edited" in src


def test_the_judge_itself_still_refuses_a_declared_edit():
    """The judge half of the same guarantee -- kept separate so a regression in
    either the caller or the judge is attributable."""
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        import subprocess
        r = Path(td)
        subprocess.run(["git", "init", "-q", str(r)], check=True)
        j = V.judge_clean(V.parse_verdict("VERDICT: CLEAN\nCLAIMS_CHECKED: 5\n"),
                          r, has_in_scope_diff=True)
        assert not j.accepted and "incoherent" in j.reason


def test_a_symbol_wrapped_in_report_formatting_still_matches(repo):
    """OVER-STRICTNESS, caught by the refusal log on its first real entry.

    Vendors format the cited symbol as code -- `Sovereign Monolith` -- because
    that is how you present an identifier in a report. The doc and the source
    file contain it BARE. Comparing the decorated string against both sides
    rejected a vendor that had done exactly the right thing: the symbol appeared
    bare in the doc 3x and in the cited JSX file, and the backticks were the
    vendor's own formatting.

    A control that rejects correct work is not a stricter control, it is a
    broken one -- it makes the third state unreachable while looking rigorous.
    """
    rows = [
        "- CSR is computed | TRUE | src/alpha.py | `claim_survival_rate`",
        '- concurrency capped | TRUE | src/beta.py:1 | "MAX_CONCURRENT_LANES"',
        "- engrams written | TRUE | src/gamma.py | **EngramWriter**",
    ]
    j = _judge(repo, _block(rows=rows))
    assert j.accepted, f"report formatting on the symbol caused a false refusal: {j.reason}"


def test_normalization_does_not_let_an_empty_symbol_through(repo):
    """OPPOSED: stripping must not turn a decoration-only symbol into a match.
    '``' and '**' carry no evidence and must still fail."""
    rows = [
        "- a | TRUE | src/alpha.py | ``",
        "- b | TRUE | src/beta.py | **",
        "- c | TRUE | src/gamma.py | \"\"",
    ]
    j = _judge(repo, _block(rows=rows))
    assert not j.accepted, "an empty symbol passed as corroboration"


def test_a_filename_cited_as_the_symbol_corroborates(repo):
    """Second false-refusal found by the refusal log's first entry.

    The commonest doc claim is "X.jsx exists". The natural evidence is the file
    at its path -- but a file does not normally contain its own filename, so
    content-only matching rejected it. Both refused rows were real, tracked
    files named in the doc.
    """
    import subprocess
    (repo / "src" / "SovereignGateway.jsx").write_text("export default function G(){}\n")
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "add jsx"], check=True)
    doc = repo / "docs" / "AUDITED.md"
    doc.write_text(doc.read_text() + "The portal lives in SovereignGateway.jsx.\n")
    rows = [
        "- CSR is computed | TRUE | src/alpha.py | claim_survival_rate",
        "- cap | TRUE | src/beta.py | MAX_CONCURRENT_LANES",
        "- portal exists | TRUE | src/SovereignGateway.jsx | SovereignGateway.jsx",
    ]
    j = _judge(repo, _block(rows=rows))
    assert j.accepted, f"a filename cited as evidence was refused: {j.reason}"


def test_a_filename_symbol_still_requires_the_doc_to_mention_it(repo):
    """OPPOSED, load-bearing: accepting filenames must NOT become a free pass.
    Citing a real tracked file the doc never mentions is exactly the
    guessable-path bypass -- pyproject.toml exists in every repo."""
    import subprocess
    (repo / "src" / "unmentioned.py").write_text("x = 1\n")
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "add"], check=True)
    rows = [
        "- a | TRUE | src/unmentioned.py | unmentioned.py",
        "- b | TRUE | src/beta.py | beta.py",
        "- c | TRUE | src/gamma.py | gamma.py",
    ]
    j = _judge(repo, _block(rows=rows))
    assert not j.accepted, (
        "filenames the doc never mentions were accepted -- the guessable-path "
        "bypass is reopened"
    )
