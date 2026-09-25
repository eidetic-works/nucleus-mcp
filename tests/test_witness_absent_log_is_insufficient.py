"""An absent witness log is INSUFFICIENT, not "no".

Why this exists: query_shell_exec and query_deployment returned False when the
witness log did not exist. False means "that never happened". The truth was
"nothing was ever recorded" -- a definitive negative manufactured out of absent
data.

That mattered in the live system rather than in theory. The log is written only
by scripts/witness_bridge.py, and NOTHING invokes that bridge: 0 references in
.claude/scripts/src, 0 launchd plists, 0 crontab entries. So the absent-log
branch was the ONLY branch, and every referee query returned a confident False.

verifier.py already carried the third state -- Evidence(verdict=None) -- and
used it for "no cmd_query specified" and for exceptions. It was simply
unreachable for this case, because the query collapsed the distinction before
the verifier could see it.
"""

import tempfile
from pathlib import Path

from mcp_server_nucleus.runtime.agent_os.witness_shell import (
    log_shell_exec,
    query_shell_exec,
)
from mcp_server_nucleus.runtime.agent_os.witness_deployment import (
    log_deployment,
    query_deployment,
)


def test_absent_shell_log_returns_insufficient_not_false():
    """THE BUG. No log must not read as 'the command did not run'."""
    with tempfile.TemporaryDirectory() as td:
        got = query_shell_exec("pytest", brain_path=str(Path(td) / ".brain"))
        assert got is None, f"absent log returned {got!r}; None means INSUFFICIENT"
        assert got is not False, "absent log manufactured a definitive negative"


def test_absent_deployment_log_returns_insufficient_not_false():
    with tempfile.TemporaryDirectory() as td:
        got = query_deployment(url="https://x.example", brain_path=str(Path(td) / ".brain"))
        assert got is None


def test_a_real_miss_is_still_False_not_None():
    """OPPOSED, load-bearing. With a log PRESENT and the command genuinely
    absent from it, the answer really is 'no' -- and must stay False. If this
    returns None the fix has destroyed the referee's ability to say no at all,
    which is worse than the bug."""
    with tempfile.TemporaryDirectory() as td:
        brain = str(Path(td) / ".brain")
        log_shell_exec(command="npm run build", brain_path=brain)
        assert query_shell_exec("pytest", brain_path=brain) is False


def test_a_real_hit_is_still_True():
    """OPPOSED: the positive path must survive."""
    with tempfile.TemporaryDirectory() as td:
        brain = str(Path(td) / ".brain")
        log_shell_exec(command="pytest tests/test_foo.py -v", brain_path=brain)
        assert query_shell_exec("pytest", brain_path=brain) is True


def test_a_real_deployment_miss_is_still_False():
    with tempfile.TemporaryDirectory() as td:
        brain = str(Path(td) / ".brain")
        log_deployment(url="https://a.example", brain_path=brain)
        assert query_deployment(url="https://b.example", brain_path=brain) is False


def test_existing_truthiness_callers_are_unaffected():
    """None is falsy, so `if found:` behaves exactly as before. The fix adds a
    distinction for callers that want it without changing any that do not."""
    with tempfile.TemporaryDirectory() as td:
        got = query_shell_exec("pytest", brain_path=str(Path(td) / ".brain"))
        assert not got


def test_the_verifier_reports_insufficient_for_an_absent_log():
    """The consumer half. A verdict of False here would tell a referee the
    command demonstrably did not run."""
    import inspect
    from mcp_server_nucleus.runtime import verifier
    src = inspect.getsource(verifier)
    assert "if found is None:" in src, "verifier does not distinguish INSUFFICIENT"
    assert "no witness log — cannot verify" in src
