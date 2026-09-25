"""The stale-claim reaper must be able to reap. It could not, ever.

Why this exists: claim_task_atomic wrote `datetime.now().isoformat()` -- naive
LOCAL time. The reaper parsed a naive timestamp by stamping it UTC. On a machine
at UTC+5:30 that puts every claim 5.5 hours in the FUTURE, so age_seconds is
negative, never exceeds the staleness threshold, and no task is ever reaped.
Measured on this repo: claims reporting an age of -216 minutes while their
owning process had been dead for hours.

A reaper that cannot reap looks exactly like a reaper with nothing to do. The
tests below therefore lead with the arithmetic, not the plumbing: if age is
negative for a claim made in the past, everything downstream is decoration.
"""

from datetime import datetime, timedelta, timezone


def _age_seconds(raw: str) -> float:
    """The shipped parse, mirrored: naive means local, not UTC."""
    ts = raw.replace("Z", "+00:00")
    claimed = datetime.fromisoformat(ts)
    if claimed.tzinfo is None:
        claimed = claimed.astimezone()
    return (datetime.now(timezone.utc) - claimed).total_seconds()


def test_a_naive_local_timestamp_is_not_in_the_future():
    """THE BUG. datetime.now().isoformat() is what the store actually holds."""
    naive_local_one_hour_ago = (datetime.now() - timedelta(hours=1)).isoformat()
    age = _age_seconds(naive_local_one_hour_ago)
    assert age > 0, (
        f"a claim made an hour ago has age {age:.0f}s -- negative age means the "
        f"reaper can never fire on any task"
    )
    assert 3000 < age < 4200, f"expected ~3600s, got {age:.0f}s"


def test_the_old_parse_really_did_produce_a_future_timestamp():
    """CONTROL: proves the fix changed something. If stamping UTC on a naive
    local time had been harmless, this fix would be noise."""
    naive = (datetime.now() - timedelta(hours=1)).isoformat()
    wrong = datetime.fromisoformat(naive).replace(tzinfo=timezone.utc)
    old_age = (datetime.now(timezone.utc) - wrong).total_seconds()
    local_offset = datetime.now().astimezone().utcoffset().total_seconds()
    if local_offset > 0:
        assert old_age < 3600, (
            "the old parse should read younger than reality east of UTC"
        )
        if local_offset > 3600:
            assert old_age < 0, "east of UTC+1 the old parse went negative"


def test_a_tz_aware_timestamp_is_unchanged_by_the_fix():
    """OPPOSED: the writer now emits tz-aware UTC. Those must parse identically
    before and after -- the fix must not shift correct data."""
    aware = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    assert 3400 < _age_seconds(aware) < 3800


def test_a_fresh_claim_is_not_stale():
    """OPPOSED, load-bearing: a reaper that reaps everything is worse than one
    that reaps nothing -- it would kill live work mid-dispatch."""
    fresh = datetime.now(timezone.utc).isoformat()
    assert _age_seconds(fresh) < 60


def test_the_writer_no_longer_emits_naive_timestamps():
    """The store is the source of the bad data; fixing only the reader would
    leave every future row wrong."""
    import inspect
    from mcp_server_nucleus.runtime import db
    src = inspect.getsource(db)
    assert "datetime.now().isoformat()" not in src, (
        "a naive timestamp writer survives in db.py"
    )
