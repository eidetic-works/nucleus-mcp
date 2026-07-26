"""
Nucleus Runtime — Scheduled Task & Process Liveness Engine
==========================================================
Provides data models, platform enumerators (cron, launchd), schedule & interval logic,
classification rules (healthy, stale, failed, disabled, unknown), credential redaction,
and human-readable table / structured JSON formatters.
"""

from __future__ import annotations

import json
import logging
import os
import plistlib
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger("nucleus.runtime.liveness")


# ── Liveness Models & Enums ───────────────────────────────────

class LivenessStatus(str, Enum):
    HEALTHY = "HEALTHY"
    STALE = "STALE"
    FAILED = "FAILED"
    DISABLED = "DISABLED"
    UNKNOWN = "UNKNOWN"


class LivenessSource(str, Enum):
    CRON = "cron"
    LAUNCHD = "launchd"
    SYSTEMD = "systemd"
    PROCESS = "process"
    NUCLEUS_SCHEDULER = "nucleus_scheduler"
    CUSTOM = "custom"


@dataclass
class LivenessItem:
    """Represents a single scheduled task or process liveness target."""

    id: str
    name: str
    source: Union[LivenessSource, str]
    command: str
    schedule: str
    interval_seconds: Optional[float] = None
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    status: LivenessStatus = LivenessStatus.UNKNOWN
    last_exit_code: Optional[int] = None
    error_message: Optional[str] = None
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    redacted: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert item to JSON-serializable dictionary."""
        source_val = self.source.value if isinstance(self.source, Enum) else str(self.source)
        status_val = self.status.value if isinstance(self.status, Enum) else str(self.status)
        return {
            "id": self.id,
            "name": self.name,
            "source": source_val,
            "command": self.command,
            "schedule": self.schedule,
            "interval_seconds": self.interval_seconds,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "next_run": self.next_run.isoformat() if self.next_run else None,
            "status": status_val,
            "last_exit_code": self.last_exit_code,
            "error_message": self.error_message,
            "enabled": self.enabled,
            "metadata": self.metadata,
            "redacted": self.redacted,
        }


@dataclass
class LivenessReport:
    """Represents a unified liveness audit report across multiple sources."""

    timestamp: datetime
    items: List[LivenessItem]
    summary: Dict[str, int] = field(default_factory=dict)
    host_info: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to JSON-serializable dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "summary": self.summary,
            "host_info": self.host_info,
            "item_count": len(self.items),
            "items": [item.to_dict() for item in self.items],
        }


# ── Secret Redaction Logic ────────────────────────────────────

_SECRET_PATTERNS = [
    # Key-value secret formats (e.g., API_KEY=xxx, password: yyy, key=zzz)
    (re.compile(r'(?i)(api[_-]?key|secret|token|password|passwd|auth|bearer)\s*[=:]\s*([^\s;\'"]+)', re.IGNORECASE), r'\1=<REDACTED>'),
    # Specific known token formats
    (re.compile(r'(sk-[a-zA-Z0-9]{20,})'), r'<REDACTED_OPENAI_KEY>'),
    (re.compile(r'(ghp_[a-zA-Z0-9]{36})'), r'<REDACTED_GITHUB_TOKEN>'),
    (re.compile(r'(eyJ[a-zA-Z0-9_-]+\.eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+)'), r'<REDACTED_JWT>'),
    (re.compile(r'(AKIA[0-9A-Z]{16})'), r'<REDACTED_AWS_KEY>'),
    # CLI parameters (--password mypass, -p secret, --key secret, --secret foo)
    (re.compile(r'(-p|--password|--token|--api-key|--key|--secret|-k)\s+([^\s]+)', re.IGNORECASE), r'\1 <REDACTED>'),
    # Basic Auth URLs (https://user:pass@host)
    (re.compile(r'(https?://[^:]+):([^@]+)@'), r'\1:<REDACTED>@'),
]


def redact_secrets(text: str) -> Tuple[str, bool]:
    """Redact credentials, tokens, and secrets from string input.

    Returns:
        (redacted_text, was_redacted)
    """
    if not text:
        return text, False

    original = text
    redacted_text = original
    for pattern, replacement in _SECRET_PATTERNS:
        redacted_text = pattern.sub(replacement, redacted_text)

    return redacted_text, (redacted_text != original)


def redact_liveness_item(item: LivenessItem) -> LivenessItem:
    """Return a copy of LivenessItem with sensitive data redacted."""
    cmd_redacted, cmd_was = redact_secrets(item.command)
    name_redacted, name_was = redact_secrets(item.name)
    err_redacted, err_was = redact_secrets(item.error_message) if item.error_message else (None, False)

    meta_redacted: Dict[str, Any] = {}
    meta_was = False
    for k, v in item.metadata.items():
        if isinstance(v, str):
            rv, rwas = redact_secrets(v)
            meta_redacted[k] = rv
            if rwas:
                meta_was = True
        else:
            meta_redacted[k] = v

    is_redacted = item.redacted or cmd_was or name_was or err_was or meta_was

    return LivenessItem(
        id=item.id,
        name=name_redacted,
        source=item.source,
        command=cmd_redacted,
        schedule=item.schedule,
        interval_seconds=item.interval_seconds,
        last_run=item.last_run,
        next_run=item.next_run,
        status=item.status,
        last_exit_code=item.last_exit_code,
        error_message=err_redacted,
        enabled=item.enabled,
        metadata=meta_redacted,
        redacted=is_redacted,
    )


# ── Schedule & Interval Logic ─────────────────────────────────

_CRON_NICKNAMES: Dict[str, Optional[float]] = {
    "@reboot": None,
    "@hourly": 3600.0,
    "@daily": 86400.0,
    "@midnight": 86400.0,
    "@weekly": 604800.0,
    "@monthly": 2592000.0,
    "@yearly": 31536000.0,
    "@annually": 31536000.0,
}


def parse_cron_interval(cron_expr: str) -> Optional[float]:
    """Parse standard 5-part cron syntax or nicknames to estimate interval seconds."""
    expr = cron_expr.strip()
    if not expr:
        return None

    if expr in _CRON_NICKNAMES:
        return _CRON_NICKNAMES[expr]

    parts = expr.split()
    if len(parts) < 5:
        return None

    min_spec, hour_spec, dom_spec, mon_spec, dow_spec = parts[:5]

    # Every N minutes (e.g. */5 * * * * or 0,15,30,45 * * * *)
    if min_spec.startswith("*/"):
        try:
            step = int(min_spec[2:])
            return float(step * 60)
        except ValueError:
            pass
    elif "," in min_spec and hour_spec == "*":
        try:
            mins = [int(m) for m in min_spec.split(",")]
            if len(mins) > 1:
                mins.sort()
                diffs = [mins[i + 1] - mins[i] for i in range(len(mins) - 1)]
                avg_diff = sum(diffs) / len(diffs)
                return float(avg_diff * 60)
        except ValueError:
            pass
    elif min_spec == "*" and hour_spec == "*":
        return 60.0
    elif min_spec != "*" and hour_spec == "*":
        return 3600.0
    elif hour_spec.startswith("*/"):
        try:
            step = int(hour_spec[2:])
            return float(step * 3600)
        except ValueError:
            pass
    elif dom_spec == "*" and mon_spec == "*" and dow_spec == "*":
        return 86400.0
    elif dow_spec != "*":
        return 604800.0
    elif dom_spec != "*":
        return 2592000.0

    return 86400.0


def parse_launchd_interval(plist_data: Dict[str, Any]) -> Tuple[Optional[float], str]:
    """Extract nominal interval (seconds) and human-readable schedule from launchd plist."""
    if "StartInterval" in plist_data:
        try:
            interval = float(plist_data["StartInterval"])
            return interval, f"Every {int(interval)}s"
        except (ValueError, TypeError):
            pass

    if "StartCalendarInterval" in plist_data:
        cal = plist_data["StartCalendarInterval"]
        if isinstance(cal, dict):
            if "Minute" in cal and "Hour" in cal and "Weekday" not in cal:
                return 86400.0, f"Daily at {cal.get('Hour', 0):02d}:{cal.get('Minute', 0):02d}"
            elif "Minute" in cal and "Hour" not in cal:
                return 3600.0, f"Hourly at min {cal.get('Minute', 0)}"
            elif "Weekday" in cal:
                return 604800.0, f"Weekly (Day {cal.get('Weekday')})"
            else:
                return 86400.0, "Calendar scheduled"
        elif isinstance(cal, list) and len(cal) > 0:
            return 86400.0 / max(len(cal), 1), f"Calendar scheduled ({len(cal)} slots)"

    if plist_data.get("KeepAlive") is True or plist_data.get("RunAtLoad") is True:
        return None, "Continuous / On-Demand"

    return None, "Manual / Event Triggered"


def calculate_staleness(
    item: LivenessItem,
    now: Optional[datetime] = None,
    grace_multiplier: float = 1.5,
) -> Tuple[bool, float]:
    """Determine whether an item is stale based on its interval and last_run.

    Returns:
        (is_stale, overdue_seconds)
    """
    if not item.last_run or not item.interval_seconds or item.interval_seconds <= 0:
        return False, 0.0

    now_dt = now or datetime.now(timezone.utc)
    last_run_utc = item.last_run.replace(tzinfo=timezone.utc) if item.last_run.tzinfo is None else item.last_run

    elapsed = (now_dt - last_run_utc).total_seconds()
    threshold = item.interval_seconds * grace_multiplier

    if elapsed > threshold:
        return True, (elapsed - item.interval_seconds)
    return False, 0.0


# ── Classification Rules ──────────────────────────────────────

def classify_liveness_item(
    item: LivenessItem,
    grace_multiplier: float = 1.5,
    now: Optional[datetime] = None,
) -> LivenessStatus:
    """Classify a LivenessItem into HEALTHY, STALE, FAILED, DISABLED, or UNKNOWN."""
    if not item.enabled:
        return LivenessStatus.DISABLED

    if item.last_exit_code is not None and item.last_exit_code != 0:
        return LivenessStatus.FAILED

    is_stale, _ = calculate_staleness(item, now=now, grace_multiplier=grace_multiplier)
    if is_stale:
        return LivenessStatus.STALE

    if item.last_run is not None:
        return LivenessStatus.HEALTHY

    if item.interval_seconds is not None or item.schedule:
        return LivenessStatus.UNKNOWN

    return LivenessStatus.HEALTHY if item.enabled else LivenessStatus.DISABLED


# ── Platform Enumerators ──────────────────────────────────────

def enumerate_cron_jobs(user: Optional[str] = None) -> List[LivenessItem]:
    """Enumerate cron jobs for user via `crontab -l`."""
    items: List[LivenessItem] = []
    try:
        cmd = ["crontab", "-l"]
        if user:
            cmd.extend(["-u", user])
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        if proc.returncode != 0:
            logger.debug("crontab -l exited with return code %d", proc.returncode)
            return items

        lines = proc.stdout.splitlines()
        job_idx = 0
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line and not line.startswith("@"):
                continue

            parts = line.split(maxsplit=5)
            if line.startswith("@"):
                schedule = parts[0]
                command = parts[1] if len(parts) > 1 else ""
            elif len(parts) >= 6:
                schedule = " ".join(parts[:5])
                command = parts[5]
            else:
                continue

            job_idx += 1
            interval = parse_cron_interval(schedule)
            item_id = f"cron_{user or 'user'}_{job_idx}"
            name = f"Cron #{job_idx}: {command[:30]}..." if len(command) > 30 else f"Cron #{job_idx}: {command}"

            item = LivenessItem(
                id=item_id,
                name=name,
                source=LivenessSource.CRON,
                command=command,
                schedule=schedule,
                interval_seconds=interval,
                enabled=True,
                metadata={"cron_user": user or os.environ.get("USER", "current")},
            )
            item.status = classify_liveness_item(item)
            items.append(redact_liveness_item(item))

    except Exception as ex:
        logger.warning("Failed to enumerate cron jobs: %s", ex)

    return items


def _get_launchd_plist_dirs() -> List[Path]:
    """Return existing standard launchd agent/daemon directories."""
    home = Path.home()
    dirs = [
        home / "Library" / "LaunchAgents",
        Path("/Library/LaunchAgents"),
        Path("/Library/LaunchDaemons"),
    ]
    return [d for d in dirs if d.exists() and d.is_dir()]


def _query_launchctl_status() -> Dict[str, Dict[str, Any]]:
    """Query `launchctl list` mapping label -> {pid, exit_code}."""
    status_map: Dict[str, Dict[str, Any]] = {}
    try:
        proc = subprocess.run(["launchctl", "list"], capture_output=True, text=True, timeout=5)
        if proc.returncode == 0:
            for line in proc.stdout.splitlines():
                parts = line.strip().split("\t")
                if len(parts) >= 3:
                    pid_str, exit_str, label = parts[0], parts[1], parts[2]
                    pid = int(pid_str) if pid_str.isdigit() else None
                    exit_code = int(exit_str) if exit_str.lstrip("-").isdigit() else None
                    status_map[label] = {"pid": pid, "exit_code": exit_code}
    except Exception as ex:
        logger.debug("Failed to query launchctl status: %s", ex)

    return status_map


def enumerate_launchd_jobs(target_dirs: Optional[List[Path]] = None) -> List[LivenessItem]:
    """Enumerate launchd services from plist files and launchctl list."""
    items: List[LivenessItem] = []
    if sys.platform != "darwin":
        return items

    search_dirs = target_dirs or _get_launchd_plist_dirs()
    launchctl_map = _query_launchctl_status()

    for pdir in search_dirs:
        try:
            for plist_file in pdir.glob("*.plist"):
                try:
                    with open(plist_file, "rb") as f:
                        data = plistlib.load(f)

                    label = data.get("Label", plist_file.stem)
                    disabled = data.get("Disabled", False)
                    prog = data.get("Program")
                    prog_args = data.get("ProgramArguments", [])

                    if prog_args:
                        cmd = " ".join(str(a) for a in prog_args)
                    elif prog:
                        cmd = str(prog)
                    else:
                        cmd = label

                    interval, schedule_str = parse_launchd_interval(data)
                    launch_info = launchctl_map.get(label, {})
                    pid = launch_info.get("pid")
                    exit_code = launch_info.get("exit_code")

                    item = LivenessItem(
                        id=f"launchd_{label}",
                        name=label,
                        source=LivenessSource.LAUNCHD,
                        command=cmd,
                        schedule=schedule_str,
                        interval_seconds=interval,
                        last_exit_code=exit_code,
                        enabled=not disabled,
                        metadata={
                            "plist_path": str(plist_file),
                            "pid": pid,
                            "run_at_load": data.get("RunAtLoad", False),
                            "keep_alive": data.get("KeepAlive", False),
                        },
                    )
                    item.status = classify_liveness_item(item)
                    items.append(redact_liveness_item(item))

                except Exception as ex:
                    logger.debug("Error parsing plist %s: %s", plist_file, ex)
        except Exception as ex:
            logger.warning("Error reading launchd dir %s: %s", pdir, ex)

    return items


def enumerate_all_liveness(
    grace_multiplier: float = 1.5,
    redact: bool = True,
) -> LivenessReport:
    """Enumerate cron and launchd liveness targets into a unified report."""
    now = datetime.now(timezone.utc)
    items: List[LivenessItem] = []

    items.extend(enumerate_cron_jobs())
    items.extend(enumerate_launchd_jobs())

    processed_items: List[LivenessItem] = []
    summary: Dict[str, int] = {
        LivenessStatus.HEALTHY.value: 0,
        LivenessStatus.STALE.value: 0,
        LivenessStatus.FAILED.value: 0,
        LivenessStatus.DISABLED.value: 0,
        LivenessStatus.UNKNOWN.value: 0,
    }

    for item in items:
        item.status = classify_liveness_item(item, grace_multiplier=grace_multiplier, now=now)
        final_item = redact_liveness_item(item) if redact else item
        processed_items.append(final_item)
        status_key = str(final_item.status.value if isinstance(final_item.status, LivenessStatus) else final_item.status)
        summary[status_key] = summary.get(status_key, 0) + 1

    host_info = {
        "platform": sys.platform,
        "python_version": sys.version.split()[0],
        "user": os.environ.get("USER", "unknown"),
        "timestamp": now.isoformat(),
    }

    return LivenessReport(
        timestamp=now,
        items=processed_items,
        summary=summary,
        host_info=host_info,
    )


# ── Formatters (Table & JSON) ─────────────────────────────────

def format_liveness_table(
    report_or_items: Union[LivenessReport, List[LivenessItem]],
    redact: bool = True,
) -> str:
    """Format liveness report or list of items into an ASCII table."""
    if isinstance(report_or_items, LivenessReport):
        report = report_or_items
        items = report.items
    else:
        report = None
        items = report_or_items

    if redact:
        items = [redact_liveness_item(it) for it in items]

    if not items:
        return "No scheduled jobs or liveness items found."

    headers = ["ID / Name", "Source", "Schedule", "Interval", "Status", "Exit Code", "Command"]
    rows = []
    for item in items:
        name_str = item.name[:25] + "..." if len(item.name) > 28 else item.name
        source_str = str(item.source.value if isinstance(item.source, LivenessSource) else item.source)
        sched_str = item.schedule[:20] + "..." if len(item.schedule) > 23 else item.schedule
        interval_str = f"{int(item.interval_seconds)}s" if item.interval_seconds else "-"
        status_str = str(item.status.value if isinstance(item.status, LivenessStatus) else item.status)
        exit_str = str(item.last_exit_code) if item.last_exit_code is not None else "-"
        cmd_str = item.command[:35] + "..." if len(item.command) > 38 else item.command
        rows.append([name_str, source_str, sched_str, interval_str, status_str, exit_str, cmd_str])

    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, val in enumerate(row):
            col_widths[i] = max(col_widths[i], len(val))

    def make_line(sep="+", pad="-"):
        return sep + sep.join(pad * (w + 2) for w in col_widths) + sep

    header_line = "| " + " | ".join(f"{headers[i]:<{col_widths[i]}}" for i in range(len(headers))) + " |"
    divider = make_line("+", "-")

    table_lines = [divider, header_line, make_line("+", "=")]
    for row in rows:
        row_line = "| " + " | ".join(f"{row[i]:<{col_widths[i]}}" for i in range(len(row))) + " |"
        table_lines.append(row_line)
    table_lines.append(divider)

    if report:
        summary_str = f"Summary: Total: {len(items)} | Healthy: {report.summary.get(LivenessStatus.HEALTHY.value, 0)} | Stale: {report.summary.get(LivenessStatus.STALE.value, 0)} | Failed: {report.summary.get(LivenessStatus.FAILED.value, 0)} | Disabled: {report.summary.get(LivenessStatus.DISABLED.value, 0)} | Unknown: {report.summary.get(LivenessStatus.UNKNOWN.value, 0)}"
        table_lines.append(summary_str)

    return "\n".join(table_lines)


def format_liveness_json(
    target: Union[LivenessReport, List[LivenessItem], LivenessItem],
    redact: bool = True,
    indent: int = 2,
) -> str:
    """Format liveness report, items list, or single item into a JSON string."""
    if isinstance(target, LivenessReport):
        items = [redact_liveness_item(it) if redact else it for it in target.items]
        rep = LivenessReport(
            timestamp=target.timestamp,
            items=items,
            summary=target.summary,
            host_info=target.host_info,
        )
        data = rep.to_dict()
    elif isinstance(target, list):
        items = [redact_liveness_item(it) if redact else it for it in target]
        data = [it.to_dict() for it in items]
    elif isinstance(target, LivenessItem):
        item = redact_liveness_item(target) if redact else target
        data = item.to_dict()
    else:
        data = {"error": "Invalid target type for JSON formatting"}

    return json.dumps(data, indent=indent)
