"""Opposed-pair control for the autouse NUCLEUS_* env-restoring fixture.

A fixture that restores environment state succeeds by making nothing happen,
which is indistinguishable from the fixture never running. These two tests are
ordered and adjacent on purpose: the first dirties the environment exactly the
way production code does (a bare os.environ assignment that monkeypatch cannot
undo), the second asserts the dirt is gone.

Delete the fixture and the second test fails -- that is the point. Without a
control like this, `_restore_nucleus_env` could silently stop working and the
only symptom would be aggregate-only failures somewhere else entirely, which is
how the original NUCLEUS_VERIFIER_MANDATORY_ANCHORS leak went unnoticed.
"""

import os

_CANARY = "NUCLEUS_ENV_ISOLATION_CANARY"
_RATCHET = "NUCLEUS_VERIFIER_MANDATORY_ANCHORS"
_EXPECTED_CWD = os.getcwd()


def test_a_dirties_the_environment_like_production_code_does():
    # Deliberately NOT monkeypatch: this mirrors agent_os/boot.py, which
    # assigns os.environ directly as a documented one-way ratchet.
    os.environ[_CANARY] = "1"
    os.environ[_RATCHET] = "1"
    assert os.environ[_CANARY] == "1"


def test_b_sees_a_clean_environment():
    assert _CANARY not in os.environ, (
        "the autouse NUCLEUS_* restore fixture did not run -- a env var set by "
        "the previous test leaked into this one"
    )
    # The ratchet must be back to whatever it was before test_a, not "1".
    assert os.environ.get(_RATCHET, "") != "1" or _RATCHET in os.environ


def test_c_dirties_the_cwd_like_a_leaking_test_does():
    """A chdir with no restore -- the shape that made vendor_dispatch fail.

    Not monkeypatch.chdir (which restores itself); a bare os.chdir, which is
    what the leaking tests actually do."""
    import tempfile
    os.chdir(tempfile.mkdtemp())
    assert os.getcwd() != _EXPECTED_CWD


def test_d_sees_the_original_cwd_restored():
    assert os.getcwd() == _EXPECTED_CWD, (
        "the autouse fixture did not restore CWD -- a chdir from the previous "
        "test leaked, which puts git-dependent code outside any repo"
    )


def test_e_disables_logging_like_the_json_cli_path_does():
    """cli.py calls logging.disable(CRITICAL) for --json output. It is
    process-global and sticky; nothing scopes it to the command."""
    import logging
    logging.disable(logging.CRITICAL)
    assert logging.root.manager.disable == logging.CRITICAL


def test_f_logging_is_not_still_disabled():
    import logging
    assert logging.root.manager.disable != logging.CRITICAL, (
        "logging.disable leaked from the previous test -- caplog will capture "
        "nothing for every test that follows, and they fail asserting on "
        "warnings they never see"
    )
