"""
Unit tests for src/mcp_server_nucleus/runtime/liveness.py
"""

import json
import plistlib
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mcp_server_nucleus.cli import handle_alive_command
from mcp_server_nucleus.runtime.liveness import (
    LivenessItem,
    LivenessReport,
    LivenessSource,
    LivenessStatus,
    calculate_staleness,
    classify_liveness_item,
    enumerate_all_liveness,
    enumerate_cron_jobs,
    enumerate_launchd_jobs,
    format_liveness_json,
    format_liveness_table,
    parse_cron_interval,
    parse_launchd_interval,
    redact_liveness_item,
    redact_secrets,
)


def test_liveness_item_and_report_serialization():
    now = datetime.now(timezone.utc)
    item = LivenessItem(
        id="test_1",
        name="Test Job",
        source=LivenessSource.NUCLEUS_SCHEDULER,
        command="python3 -m script --token secret123",
        schedule="Every 300s",
        interval_seconds=300.0,
        last_run=now,
        status=LivenessStatus.HEALTHY,
        last_exit_code=0,
    )
    d = item.to_dict()
    assert d["id"] == "test_1"
    assert d["source"] == "nucleus_scheduler"
    assert d["status"] == "HEALTHY"
    assert d["interval_seconds"] == 300.0

    report = LivenessReport(
        timestamp=now,
        items=[item],
        summary={"HEALTHY": 1},
        host_info={"platform": "darwin"},
    )
    rd = report.to_dict()
    assert rd["item_count"] == 1
    assert rd["summary"]["HEALTHY"] == 1
    assert len(rd["items"]) == 1


def test_redact_secrets():
    text = "run_app --api-key sk-abcdef12345678901234567890 --password mysecretpass -p supersecret"
    redacted, was_redacted = redact_secrets(text)
    assert was_redacted is True
    assert "sk-abcdef12345678901234567890" not in redacted
    assert "mysecretpass" not in redacted
    assert "supersecret" not in redacted
    assert "<REDACTED" in redacted


def test_redact_secrets_whitespace_env_commands():
    """Whitespace-separated env-set commands (no =/: separator) must redact the
    value when KEY names a secret. `launchctl setenv KEY VALUE` was leaking live
    because the key-value pattern requires =/: — this is the regression guard."""
    # POSITIVE: separatorless secret leaks (setenv / export forms of the class)
    for leak, needle in [
        ("launchctl setenv TELEGRAM_BOT_TOKEN 7891234567:AAExampleFakeValue", "AAExampleFakeValue"),
        ("export API_SECRET myp4ssw0rd", "myp4ssw0rd"),
    ]:
        red, was = redact_secrets(leak)
        assert was is True, f"leak not flagged: {leak!r} -> {red!r}"
        assert needle not in red, f"value survived redaction: {red!r}"

    # NEGATIVE (load-bearing): benign non-secret KEY passes through untouched.
    # If this ever flips to was=True, the pattern is over-broad, not fixed.
    for benign, keep in [
        ("launchctl setenv PATH /usr/local/bin", "/usr/local/bin"),
        ("export GOPATH /opt/go", "/opt/go"),
    ]:
        red, was = redact_secrets(benign)
        assert was is False, f"benign wrongly redacted: {benign!r} -> {red!r}"
        assert keep in red

    # KEY=value form must STILL redact (no regression on the pre-existing path).
    red, was = redact_secrets("launchctl setenv TELEGRAM_BOT_TOKEN=7891234567:AAsecret")
    assert was is True and "AAsecret" not in red


def test_redact_liveness_item():
    item = LivenessItem(
        id="test_2",
        name="Secret Job password=supersecret",
        source=LivenessSource.CRON,
        command="curl https://user:secretpass@example.com",
        schedule="* * * * *",
        error_message="Auth failed for token=secrettoken",
        metadata={"token": "bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.secret"},
    )
    redacted_item = redact_liveness_item(item)
    assert redacted_item.redacted is True
    assert "supersecret" not in redacted_item.name
    assert "secretpass" not in redacted_item.command
    assert "secrettoken" not in redacted_item.error_message


def test_parse_cron_interval():
    assert parse_cron_interval("*/5 * * * *") == 300.0
    assert parse_cron_interval("*/15 * * * *") == 900.0
    assert parse_cron_interval("0 * * * *") == 3600.0
    assert parse_cron_interval("0 0 * * *") == 86400.0
    assert parse_cron_interval("@hourly") == 3600.0
    assert parse_cron_interval("@daily") == 86400.0
    assert parse_cron_interval("@weekly") == 604800.0
    assert parse_cron_interval("") is None
    assert parse_cron_interval("invalid cron") is None


def test_parse_launchd_interval():
    plist_interval = {"StartInterval": 600}
    interval, sched = parse_launchd_interval(plist_interval)
    assert interval == 600.0
    assert "600s" in sched

    plist_cal = {"StartCalendarInterval": {"Hour": 3, "Minute": 30}}
    interval_cal, sched_cal = parse_launchd_interval(plist_cal)
    assert interval_cal == 86400.0
    assert "03:30" in sched_cal

    plist_continuous = {"KeepAlive": True}
    interval_cont, sched_cont = parse_launchd_interval(plist_continuous)
    assert interval_cont is None
    assert "Continuous" in sched_cont


def test_calculate_staleness():
    now = datetime.now(timezone.utc)
    recent_run = now - timedelta(seconds=100)
    old_run = now - timedelta(seconds=1000)

    healthy_item = LivenessItem(
        id="h1", name="H1", source=LivenessSource.CRON, command="cmd", schedule="5m",
        interval_seconds=300.0, last_run=recent_run
    )
    stale_item = LivenessItem(
        id="s1", name="S1", source=LivenessSource.CRON, command="cmd", schedule="5m",
        interval_seconds=300.0, last_run=old_run
    )

    is_stale, overdue = calculate_staleness(healthy_item, now=now, grace_multiplier=1.5)
    assert is_stale is False
    assert overdue == 0.0

    is_stale_2, overdue_2 = calculate_staleness(stale_item, now=now, grace_multiplier=1.5)
    assert is_stale_2 is True
    assert overdue_2 > 0.0


def test_classify_liveness_item():
    now = datetime.now(timezone.utc)

    # Disabled
    disabled_item = LivenessItem(
        id="d1", name="D1", source=LivenessSource.CRON, command="cmd", schedule="5m", enabled=False
    )
    assert classify_liveness_item(disabled_item, now=now) == LivenessStatus.DISABLED

    # Failed exit code
    failed_item = LivenessItem(
        id="f1", name="F1", source=LivenessSource.CRON, command="cmd", schedule="5m", last_exit_code=1
    )
    assert classify_liveness_item(failed_item, now=now) == LivenessStatus.FAILED

    # Stale
    stale_item = LivenessItem(
        id="s1", name="S1", source=LivenessSource.CRON, command="cmd", schedule="5m",
        interval_seconds=300.0, last_run=now - timedelta(seconds=1000)
    )
    assert classify_liveness_item(stale_item, now=now) == LivenessStatus.STALE

    # Healthy
    healthy_item = LivenessItem(
        id="h1", name="H1", source=LivenessSource.CRON, command="cmd", schedule="5m",
        interval_seconds=300.0, last_run=now - timedelta(seconds=100)
    )
    assert classify_liveness_item(healthy_item, now=now) == LivenessStatus.HEALTHY

    # Unknown (no execution history)
    unknown_item = LivenessItem(
        id="u1", name="U1", source=LivenessSource.CRON, command="cmd", schedule="5m"
    )
    assert classify_liveness_item(unknown_item, now=now) == LivenessStatus.UNKNOWN


def test_format_liveness_table():
    now = datetime.now(timezone.utc)
    items = [
        LivenessItem(
            id="job1", name="Backup Database", source=LivenessSource.CRON,
            command="pg_dump db --password supersecret", schedule="0 2 * * *",
            interval_seconds=86400.0, last_run=now, status=LivenessStatus.HEALTHY, last_exit_code=0
        ),
        LivenessItem(
            id="job2", name="Sync Logs", source=LivenessSource.LAUNCHD,
            command="aws s3 sync /var/log s3://bucket", schedule="Every 300s",
            interval_seconds=300.0, last_run=now - timedelta(seconds=2000), status=LivenessStatus.STALE
        )
    ]
    report = LivenessReport(timestamp=now, items=items, summary={"HEALTHY": 1, "STALE": 1})
    table_str = format_liveness_table(report, redact=True)

    assert "Backup Database" in table_str
    assert "Sync Logs" in table_str
    assert "HEALTHY" in table_str
    assert "STALE" in table_str
    assert "supersecret" not in table_str
    assert "Summary: Total: 2" in table_str


def test_format_liveness_json():
    now = datetime.now(timezone.utc)
    item = LivenessItem(
        id="job1", name="Cleanup Temp", source=LivenessSource.CRON,
        command="rm -rf /tmp/* --token secrettoken", schedule="*/15 * * * *",
        interval_seconds=900.0, status=LivenessStatus.HEALTHY
    )

    json_str = format_liveness_json(item, redact=True)
    data = json.loads(json_str)
    assert data["id"] == "job1"
    assert "secrettoken" not in data["command"]
    assert data["redacted"] is True


def test_enumerate_cron_jobs_mock():
    crontab_output = (
        "# Sample crontab\n"
        "PATH=/usr/local/bin\n"
        "*/5 * * * * /usr/bin/python3 /scripts/health.py --key secret123\n"
        "0 0 * * * /usr/bin/backup.sh\n"
    )

    with patch("subprocess.run") as mock_run:
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = crontab_output
        mock_run.return_value = mock_proc

        # This test covers crontab PARSING (schedule, interval, redaction),
        # not ownership. Its fixtures are deliberately generic jobs with no
        # nucleus markers, so the default nucleus-owned scoping would filter
        # them all out. Enumerate unscoped to keep the parsing assertions
        # meaningful; ownership scoping is covered in test_liveness_scoping.py.
        items = enumerate_cron_jobs(include_unowned=True)
        assert len(items) == 2
        assert items[0].schedule == "*/5 * * * *"
        assert items[0].interval_seconds == 300.0
        assert "secret123" not in items[0].command


def test_enumerate_launchd_jobs_mock(tmp_path):
    plist_content = {
        "Label": "com.nucleus.testdaemon",
        "ProgramArguments": ["/usr/local/bin/nucleus-daemon", "--token", "secrettoken123"],
        "StartInterval": 300,
        "RunAtLoad": True,
    }
    plist_path = tmp_path / "com.nucleus.testdaemon.plist"
    with open(plist_path, "wb") as f:
        plistlib.dump(plist_content, f)

    with patch("sys.platform", "darwin"), \
         patch("mcp_server_nucleus.runtime.liveness._get_launchd_plist_dirs", return_value=[tmp_path]), \
         patch("mcp_server_nucleus.runtime.liveness._query_launchctl_status", return_value={"com.nucleus.testdaemon": {"pid": 1234, "exit_code": 0}}):

        items = enumerate_launchd_jobs(target_dirs=[tmp_path])
        assert len(items) == 1
        item = items[0]
        assert item.name == "com.nucleus.testdaemon"
        assert item.interval_seconds == 300.0
        assert item.last_exit_code == 0
        assert item.metadata["pid"] == 1234
        assert "secrettoken123" not in item.command


def test_enumerate_all_liveness():
    report = enumerate_all_liveness()
    assert isinstance(report, LivenessReport)
    assert isinstance(report.summary, dict)
    assert "platform" in report.host_info


def test_handle_alive_command(capsys):
    from mcp_server_nucleus.cli import handle_alive_command

    class DummyArgs:
        redact = True
        grace_multiplier = 1.5
        source = "all"
        json = False
        format = None

    handle_alive_command(DummyArgs())
    captured = capsys.readouterr()
    assert "Source" in captured.out or "No scheduled jobs" in captured.out

    DummyArgs.json = True
    handle_alive_command(DummyArgs())
    captured_json = capsys.readouterr()
    data = json.loads(captured_json.out)
    assert "items" in data or "summary" in data

    DummyArgs.json = False
    DummyArgs.source = "cron"
    handle_alive_command(DummyArgs())
    captured_cron = capsys.readouterr()
    assert captured_cron.out is not None

    DummyArgs.source = "launchd"
    handle_alive_command(DummyArgs())
    captured_launchd = capsys.readouterr()
    assert captured_launchd.out is not None


# ── Exit-Code Contract: FAILED nucleus-owned → 1, UNKNOWN-only → 0 ──

class TestExitCodeContract:
    """The `nucleus alive` exit code is the machine-readable verdict.

    Contract:
      - Any FAILED nucleus-owned item  → exit 1 (gate fails)
      - Only UNKNOWN items (no FAILED) → exit 0 (UNKNOWN is honest ignorance, not failure)

    These tests pin the contract so a future refactor cannot silently revert
    to always-exit-0 (the false-green this command was built to detect) or
    coerce UNKNOWN into a failure (the mistake the docstring guards against).
    """

    def _args_all(self):
        class Args:
            redact = True
            grace_multiplier = 1.5
            source = "all"
            json = False
            format = None
        return Args()

    def test_failed_nucleus_owned_exits_1(self, capsys):
        """A nucleus-owned job in FAILED state must produce exit code 1."""
        failed_item = LivenessItem(
            id="com.eidetic.ccr-relay-daemon-main",
            name="CCR Relay Daemon (main)",
            source=LivenessSource.LAUNCHD,
            command="bash scripts/ccr_w1_relay_daemon.sh",
            schedule="Every 5s",
            interval_seconds=5.0,
            status=LivenessStatus.FAILED,
            last_exit_code=1,
            enabled=True,
        )
        report = LivenessReport(
            timestamp=datetime.now(timezone.utc),
            items=[failed_item],
            summary={LivenessStatus.FAILED.value: 1},
            host_info={},
        )
        with patch("mcp_server_nucleus.runtime.liveness.enumerate_all_liveness", return_value=report):
            rc = handle_alive_command(self._args_all())
        assert rc == 1

    def test_unknown_only_exits_0(self, capsys):
        """UNKNOWN-only scope must produce exit code 0 — ignorance is not failure."""
        unknown_item = LivenessItem(
            id="com.eidetic.ccr-relay-daemon-peer",
            name="CCR Relay Daemon (peer)",
            source=LivenessSource.LAUNCHD,
            command="bash scripts/ccr_w1_relay_daemon.sh",
            schedule="Every 5s",
            interval_seconds=5.0,
            status=LivenessStatus.UNKNOWN,
            last_run=None,
            enabled=True,
        )
        report = LivenessReport(
            timestamp=datetime.now(timezone.utc),
            items=[unknown_item],
            summary={LivenessStatus.UNKNOWN.value: 1},
            host_info={},
        )
        with patch("mcp_server_nucleus.runtime.liveness.enumerate_all_liveness", return_value=report):
            rc = handle_alive_command(self._args_all())
        assert rc == 0

    def test_failed_among_unknown_still_exits_1(self, capsys):
        """One FAILED mixed with UNKNOWN items still fails the gate (exit 1)."""
        failed_item = LivenessItem(
            id="com.eidetic.ccr-relay-daemon-main",
            name="CCR Relay Daemon (main)",
            source=LivenessSource.LAUNCHD,
            command="bash scripts/ccr_w1_relay_daemon.sh",
            schedule="Every 5s",
            interval_seconds=5.0,
            status=LivenessStatus.FAILED,
            last_exit_code=2,
            enabled=True,
        )
        unknown_item = LivenessItem(
            id="com.eidetic.ccr-relay-daemon-peer",
            name="CCR Relay Daemon (peer)",
            source=LivenessSource.LAUNCHD,
            command="bash scripts/ccr_w1_relay_daemon.sh",
            schedule="Every 5s",
            interval_seconds=5.0,
            status=LivenessStatus.UNKNOWN,
            last_run=None,
            enabled=True,
        )
        report = LivenessReport(
            timestamp=datetime.now(timezone.utc),
            items=[failed_item, unknown_item],
            summary={LivenessStatus.FAILED.value: 1, LivenessStatus.UNKNOWN.value: 1},
            host_info={},
        )
        with patch("mcp_server_nucleus.runtime.liveness.enumerate_all_liveness", return_value=report):
            rc = handle_alive_command(self._args_all())
        assert rc == 1

    def test_empty_scope_exits_0(self, capsys):
        """An empty scope (no nucleus-owned jobs) is not a failure — exit 0."""
        report = LivenessReport(
            timestamp=datetime.now(timezone.utc),
            items=[],
            summary={},
            host_info={},
            empty_scope=True,
        )
        with patch("mcp_server_nucleus.runtime.liveness.enumerate_all_liveness", return_value=report):
            rc = handle_alive_command(self._args_all())
        assert rc == 0

