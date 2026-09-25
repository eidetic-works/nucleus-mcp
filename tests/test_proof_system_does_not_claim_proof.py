"""A document titled "Proof" must not be a verbatim echo of the caller's claims.

`_generate_proof` wrote a file headed `# Proof: {feature_id}` containing
thinking, deployed_url, files_changed, risk_level and rollback_time — every one
CALLER-SUPPLIED — and verified none of them. It returned {"success": True}
unconditionally. An agent could assert any URL and any file list and get a
document that reads as evidence to whoever finds it later.

That is this repo's entire thesis inverted, inside a file named
proof_system.py.

The fix is not to invent verification (what to verify, and how hard, is a design
decision). It is to stop the false claim and to actually check the one thing
that is cheaply checkable — whether the declared files exist — reporting each as
verified / MISSING / UNVERIFIABLE rather than echoing the list.
"""

import os
import pathlib
import tempfile

import pytest


@pytest.fixture
def proof_doc(monkeypatch):
    """monkeypatch, not os.environ directly — it restores on teardown.

    The first version of this fixture assigned os.environ["NUCLEUS_BRAIN_PATH"]
    and never restored it, leaking a temp path into every test that ran
    afterwards in the same process. That is precisely the cross-test
    contamination that makes files pass alone and fail in aggregate, and I
    introduced it while fixing a different bug.
    """
    def _make(**kwargs):
        with tempfile.TemporaryDirectory() as td:
            monkeypatch.setenv("NUCLEUS_BRAIN_PATH", str(pathlib.Path(td) / ".brain"))
            from mcp_server_nucleus.runtime.capabilities.proof_system import ProofSystem
            args = {"feature_id": "demo", "thinking": "t",
                    "deployed_url": "https://not-real.example", "files_changed": []}
            args.update(kwargs)
            r = ProofSystem()._generate_proof(args)
            return pathlib.Path(r["path"]).read_text()
    return _make


def test_the_document_does_not_call_itself_a_proof(proof_doc):
    """THE BUG: a '# Proof:' heading over unverified self-report."""
    doc = proof_doc()
    assert not doc.lstrip().startswith("# Proof:")
    assert "Self-reported record" in doc


def test_it_says_outright_that_it_is_not_a_proof(proof_doc):
    """Renaming the heading alone would still let a reader assume verification.
    The document has to say so."""
    assert "NOT a proof" in proof_doc()


def test_a_fabricated_file_path_is_marked_MISSING(proof_doc):
    """The load-bearing check. A claimed file that does not exist must be
    reported as missing, not echoed back as though it were evidence."""
    doc = proof_doc(files_changed=["totally/fabricated/file.py"])
    assert "MISSING" in doc
    assert "0 confirmed to exist" in doc


def test_a_real_file_path_is_marked_verified(proof_doc):
    """OPPOSED: a checker that marks everything MISSING is as useless as one
    that marks everything verified."""
    doc = proof_doc(files_changed=["README.md"])
    assert "verified: exists" in doc
    assert "1 confirmed to exist" in doc


def test_mixed_claims_are_counted_correctly(proof_doc):
    doc = proof_doc(files_changed=["README.md", "nope/not/here.py"])
    assert "2 — **1 confirmed to exist" in doc
    assert "verified: exists" in doc and "MISSING" in doc


def test_the_url_is_declared_unchecked_rather_than_implied_live(proof_doc):
    """Silence about the URL would read as endorsement. The document states
    plainly that no request was made."""
    doc = proof_doc(deployed_url="https://example.invalid")
    assert "NOT checked" in doc
    assert "no request was made" in doc


def test_caller_prose_is_labelled_unverified(proof_doc):
    doc = proof_doc(thinking="I am certain this works.")
    assert "I am certain this works." in doc          # preserved verbatim
    assert "unverified" in doc.lower()                 # and labelled
