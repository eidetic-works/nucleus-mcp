"""
Opposed-pair scoping tests for `is_nucleus_owned`.

Each True case is paired with a structurally-identical False case so the
only varying signal is the ownership marker — proving the predicate keys
on Nucleus markers and not on incidental shape (same source, same command
template, same metadata keys).

Location: tests/test_liveness_scoping.py
"""

import pytest
from unittest.mock import patch

from mcp_server_nucleus.runtime.liveness import (
    LivenessItem,
    LivenessReport,
    LivenessSource,
    enumerate_all_liveness,
    format_liveness_table,
    is_nucleus_owned,
)


def _item(id, name, command, metadata=None):
    return LivenessItem(
        id=id,
        name=name,
        source=LivenessSource.CRON,
        command=command,
        schedule="* * * * *",
        metadata=metadata or {},
    )


# ── Opposed pair: launchd label ─────────────────────────────────────

@pytest.mark.parametrize(
    "item,expected",
    [
        (
            # Ownership is decided by the LABEL alone here: only the id
            # carries a marker ("nucleus"); name and command are neutral.
            # NOTE: this fixture must NOT use a bare "com.eidetic." label.
            # That prefix was deliberately REMOVED from the marker set — it
            # matched 33 unrelated third-party jobs (a separate product's
            # pipelines, tunnels, a resolver backup) none of which contain
            # "nucleus" anywhere, and it matched nothing at all on a machine
            # that is not the author's. A company-wide launchd namespace is
            # not an ownership signal.
            _item(
                "com.eidetic.nucleus-relay-daemon",
                "CCR Relay Daemon (main)",
                "bash scripts/ccr_w1_relay_daemon.sh",
            ),
            True,
        ),
        (
            _item(
                "com.adobe.AdobeCreativeCloud",
                "Adobe Creative Cloud Daemon",
                "/usr/local/bin/AdobeCreativeCloud --daemon",
            ),
            False,
        ),
    ],
    ids=["nucleus-launchd-label", "adobe-launchd-label"],
)
def test_launchd_label_opposed_pair(item, expected):
    assert is_nucleus_owned(item) is expected


# ── Opposed pair: command path ──────────────────────────────────────

@pytest.mark.parametrize(
    "item,expected",
    [
        (
            _item(
                "job_brain_mirror",
                "Brain Mirror Sync",
                "python3 -m mcp_server_nucleus.scripts.mirror_brain",
            ),
            True,
        ),
        (
            _item(
                "job_python_backup",
                "Plain Python Backup",
                "python3 /scripts/backup.py --daily",
            ),
            False,
        ),
    ],
    ids=["nucleus-command-path", "plain-python-command-path"],
)
def test_command_path_opposed_pair(item, expected):
    assert is_nucleus_owned(item) is expected


# ── Opposed pair: metadata string value ─────────────────────────────

@pytest.mark.parametrize(
    "item,expected",
    [
        (
            _item(
                "job_growth",
                "Growth Engine Trickle",
                "bash run.sh",
                metadata={"artifact_dir": "/home/testuser/.brain/relay/main/"},
            ),
            False,
        ),
        (
            _item(
                "job_google_sync",
                "Google Drive Sync",
                "bash run.sh",
                metadata={"artifact_dir": "/home/testuser/GoogleDrive/relay/main/"},
            ),
            False,
        ),
    ],
    ids=["nucleus-metadata-brain", "google-metadata-drive"],
)
def test_metadata_value_opposed_pair(item, expected):
    assert is_nucleus_owned(item) is expected


# ── Opposed pair: name only ─────────────────────────────────────────

@pytest.mark.parametrize(
    "item,expected",
    [
        (
            _item(
                "job_anon_1",
                "nucleus scheduler heartbeat",
                "bash heartbeat.sh",
            ),
            True,
        ),
        (
            _item(
                "job_anon_2",
                "system scheduler heartbeat",
                "bash heartbeat.sh",
            ),
            False,
        ),
    ],
    ids=["nucleus-name", "generic-name"],
)
def test_name_only_opposed_pair(item, expected):
    assert is_nucleus_owned(item) is expected


# ── Opposed pair: NUCLEUS_ env var in command ───────────────────────

@pytest.mark.parametrize(
    "item,expected",
    [
        (
            _item(
                "job_env_nucleus",
                "Env-Driven Nucleus Job",
                "NUCLEUS_RELAY_SUBSCRIBE_DISABLED=1 bash relay.sh",
            ),
            True,
        ),
        (
            _item(
                "job_env_generic",
                "Env-Driven Generic Job",
                "APP_RELAY_SUBSCRIBE_DISABLED=1 bash relay.sh",
            ),
            False,
        ),
    ],
    ids=["nucleus-env-var", "generic-env-var"],
)
def test_env_var_opposed_pair(item, expected):
    assert is_nucleus_owned(item) is expected


# ── Opposed pair: growth-engine path ────────────────────────────────

@pytest.mark.parametrize(
    "item,expected",
    [
        (
            _item(
                "job_growth_engine",
                "Growth Engine Stage Reddit",
                "/usr/bin/python3 ~/growth-engine/scripts/stage_reddit.py",
            ),
            False,
        ),
        (
            _item(
                "job_other_engine",
                "Other Engine Stage Reddit",
                "/usr/bin/python3 ~/other-engine/scripts/stage_reddit.py",
            ),
            False,
        ),
    ],
    ids=["nucleus-growth-engine", "non-nucleus-engine"],
)
def test_growth_engine_opposed_pair(item, expected):
    assert is_nucleus_owned(item) is expected


# ── Boundary: empty / fully-unrelated item is False ─────────────────

def test_empty_item_is_false():
    item = _item("job_x", "Task X", "bash run.sh")
    assert is_nucleus_owned(item) is False


# ── Boundary: non-string metadata values are skipped, not crashed ───

def test_non_string_metadata_skipped():
    item = _item(
        "job_meta_int",
        "Task With Int Metadata",
        "bash run.sh",
        metadata={"port": 8080, "enabled": True, "nested": {"x": 1}},
    )
    # No Nucleus marker anywhere -> False, and no TypeError raised.
    assert is_nucleus_owned(item) is False


# ── Default scoping: 1 of 4 survives, summary total = 1 ─────────────

def _scoping_fixture_items():
    """Four items: exactly one Nucleus-owned, three unowned."""
    return [
        # The one owned job: its LABEL carries the "nucleus" marker. A bare
        # "com.eidetic." prefix is deliberately NOT used — see the note on
        # test_launchd_label_opposed_pair for why that marker was removed.
        _item(
            "com.eidetic.nucleus-relay-daemon",
            "CCR Relay Daemon (main)",
            "bash scripts/ccr_w1_relay_daemon.sh",
        ),
        _item(
            "com.adobe.AdobeCreativeCloud",
            "Adobe Creative Cloud Daemon",
            "/usr/local/bin/AdobeCreativeCloud --daemon",
        ),
        _item(
            "job_backup",
            "Daily Backup",
            "python3 /scripts/backup.py --daily",
        ),
        _item(
            "job_google_sync",
            "Google Drive Sync",
            "bash gsync.sh",
        ),
    ]


def _leaf_side_effect(include_unowned=False, **_kwargs):
    """side_effect mirroring real leaf behavior for the scoping fixture.

    Real leaves (``enumerate_cron_jobs`` / ``enumerate_launchd_jobs``) accept
    ``include_unowned`` and filter internally — the wrapper
    ``enumerate_all_liveness`` calls them with ``include_unowned=True`` and
    owns the single filtering decision. This helper reproduces that contract:
    it returns the full four-item fixture when ``include_unowned`` is True and
    only the owned subset (the single ``com.eidetic.nucleus-relay-daemon``
    item) when False.

    Use this as a mock's ``side_effect`` (NEVER ``return_value``). A
    ``return_value`` ignores the ``include_unowned`` argument, so broken code
    that calls a leaf with ``include_unowned=False`` (double-filter bug) and
    correct code that calls with ``True`` both receive the same list and
    produce identical reports — the bug is invisible. This side_effect keys on
    the argument, so a caller passing the wrong value gets a different list
    and the discrepancy surfaces in the assertion.
    """
    items = _scoping_fixture_items()
    if include_unowned:
        return items
    return [it for it in items if is_nucleus_owned(it)]


def test_default_scoping_one_of_four_survives():
    """Default include_unowned=False drops the 3 unowned jobs; 1 survives."""
    items = _scoping_fixture_items()
    with patch(
        "mcp_server_nucleus.runtime.liveness.enumerate_cron_jobs",
        return_value=items,
    ), patch(
        "mcp_server_nucleus.runtime.liveness.enumerate_launchd_jobs",
        return_value=[],
    ):
        report = enumerate_all_liveness()

    assert isinstance(report, LivenessReport)
    assert len(report.items) == 1
    assert report.items[0].id == "com.eidetic.nucleus-relay-daemon"
    assert sum(report.summary.values()) == 1


# ── Opposed: include_unowned=True keeps all 4, total = 4 ─────────────

def test_include_unowned_true_four_survive():
    """Opposed case: include_unowned=True retains all 4 jobs; total = 4."""
    items = _scoping_fixture_items()
    with patch(
        "mcp_server_nucleus.runtime.liveness.enumerate_cron_jobs",
        return_value=items,
    ), patch(
        "mcp_server_nucleus.runtime.liveness.enumerate_launchd_jobs",
        return_value=[],
    ):
        report = enumerate_all_liveness(include_unowned=True)

    assert isinstance(report, LivenessReport)
    assert len(report.items) == 4
    assert sum(report.summary.values()) == 4


# ── Wrapper widening: include_unowned=True must strictly exceed the default ──

def test_wrapper_all_widens_beyond_default():
    """Regression guard: the wrapper must call its leaves unscoped
    (``include_unowned=True``) and own the single filtering decision itself.

    Against the unfixed (double-filter) code — where the wrapper called its
    leaves bare (``include_unowned=False`` default) and then re-filtered on
    top — both modes return only the owned subset, so the strict-greater
    assertion (1) below fails. The ``_leaf_side_effect`` keys on the
    ``include_unowned`` argument (a ``return_value`` would mask the bug by
    ignoring the argument), so a wrapper that calls its leaves with the
    wrong value receives a different list and the discrepancy surfaces.
    """
    expected_ids = {
        "com.eidetic.nucleus-relay-daemon",
        "com.adobe.AdobeCreativeCloud",
        "job_backup",
        "job_google_sync",
    }

    with patch(
        "mcp_server_nucleus.runtime.liveness.enumerate_cron_jobs",
        side_effect=_leaf_side_effect,
    ), patch(
        "mcp_server_nucleus.runtime.liveness.enumerate_launchd_jobs",
        return_value=[],
    ):
        default_report = enumerate_all_liveness()
        widened_report = enumerate_all_liveness(include_unowned=True)

    # (1) Regression guard: widening must STRICTLY increase the row count.
    # Against the double-filter bug both calls yield the same owned subset,
    # so this assertion fails there.
    assert len(widened_report.items) > len(default_report.items)

    # (2) Default call returns exactly the owned subset: one row, the
    # Nucleus relay daemon.
    assert len(default_report.items) == 1
    assert default_report.items[0].id == "com.eidetic.nucleus-relay-daemon"

    # (3) Widened call returns every fixture item: four rows, all ids.
    assert len(widened_report.items) == 4
    assert {it.id for it in widened_report.items} == expected_ids

    # (4) The summary total must match the row count in BOTH modes — the
    # report must not claim a total that differs from the rows it carries.
    assert sum(default_report.summary.values()) == len(default_report.items)
    assert sum(widened_report.summary.values()) == len(widened_report.items)


# ── Honest-empty: only third-party jobs → empty_scope True, no health claim ──

def test_only_third_party_jobs_is_empty_scope_no_health_claim():
    """When every enumerated job is third-party (none Nucleus-owned), the
    default-scoped report is empty_scope=True and the rendered text states
    no Nucleus-managed jobs were found — it must NOT claim healthy.
    """
    third_party_only = [
        _item(
            "com.adobe.AdobeCreativeCloud",
            "Adobe Creative Cloud Daemon",
            "/usr/local/bin/AdobeCreativeCloud --daemon",
        ),
        _item(
            "job_backup",
            "Daily Backup",
            "python3 /scripts/backup.py --daily",
        ),
    ]
    with patch(
        "mcp_server_nucleus.runtime.liveness.enumerate_cron_jobs",
        return_value=third_party_only,
    ), patch(
        "mcp_server_nucleus.runtime.liveness.enumerate_launchd_jobs",
        return_value=[],
    ):
        report = enumerate_all_liveness()

    assert report.empty_scope is True
    assert len(report.items) == 0
    assert sum(report.summary.values()) == 0

    rendered = format_liveness_table(report)
    assert "no Nucleus-managed jobs found" in rendered
    # An empty scope is an absence of evidence, not a health verdict.
    assert "healthy" not in rendered.lower()
    assert "HEALTHY" not in rendered


# ── The wrapper is what the CLI calls ────────────────────────────────
#
# Everything above this point exercises the LEAF enumerators or the
# predicate. That is exactly how a real bug shipped: the leaves were
# correct (102 unscoped / 15 scoped on the reference host) while
# `enumerate_all_liveness` — the function the `nucleus alive` CLI
# actually calls — accepted `include_unowned` and never passed it down.
# It called the leaves BARE, so they applied their own default scoping
# first, and the wrapper's own filter then ran over an already-filtered
# list. A double filter: `--all` could never widen the result, and the
# escape hatch silently escaped nothing.
#
# The leaf-level suite was green throughout. These tests drive the
# wrapper so that can't happen again.


def _patch_leaves():
    """Patch both leaves with the argument-respecting side_effect.

    ``side_effect`` and never ``return_value`` — see _leaf_side_effect.
    """
    return (
        patch(
            "mcp_server_nucleus.runtime.liveness.enumerate_cron_jobs",
            side_effect=_leaf_side_effect,
        ),
        patch(
            "mcp_server_nucleus.runtime.liveness.enumerate_launchd_jobs",
            side_effect=lambda include_unowned=False, **kw: [],
        ),
    )


def test_wrapper_default_returns_only_owned():
    """Default mode returns exactly the owned subset, by count and by id."""
    cron_patch, launchd_patch = _patch_leaves()
    with cron_patch, launchd_patch:
        report = enumerate_all_liveness()

    assert len(report.items) == 1
    assert report.items[0].id == "com.eidetic.nucleus-relay-daemon"


def test_wrapper_all_returns_every_fixture_item():
    """include_unowned=True returns every job, owned and unowned alike."""
    expected_ids = {it.id for it in _scoping_fixture_items()}
    cron_patch, launchd_patch = _patch_leaves()
    with cron_patch, launchd_patch:
        report = enumerate_all_liveness(include_unowned=True)

    assert {it.id for it in report.items} == expected_ids


@pytest.mark.parametrize("include_unowned", [False, True])
def test_wrapper_summary_total_matches_rows_returned(include_unowned):
    """The summary must never claim a total the report does not carry.

    A count that disagrees with the rows is its own false signal, so it is
    checked in BOTH modes rather than only the one that happened to work.
    """
    cron_patch, launchd_patch = _patch_leaves()
    with cron_patch, launchd_patch:
        report = enumerate_all_liveness(include_unowned=include_unowned)

    assert sum(report.summary.values()) == len(report.items)
