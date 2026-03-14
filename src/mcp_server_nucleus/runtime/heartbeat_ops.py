"""Heartbeat Operations — The Proactive Agent Brain.

v1.5.0: "The Alive Brain"

Design Thinking Output Reference:
  "Transform Nucleus from a reactive tool into an alive companion by adding
   context-triggered proactive engagement — the same pattern that made 
   Peter's agent check on him in the hospital, but sovereign and local-first."
  — design_thinking_heartbeat_proactive/10_stage8_synthesis.md

What it does:
  1. CHECK   — Read engrams, evaluate 4 context trigger signals
  2. INSTALL — Generate platform-native scheduling (launchd/systemd)
  3. NOTIFY  — Surface insights via native OS notifications
  4. CONFIG  — Configure interval, triggers, intensity threshold
  5. STATUS  — Report heartbeat daemon state

Context Trigger Signals:
  - STALE_BLOCKER:  intensity ≥8 + "blocker" keyword + >24h old
  - STALE_DECISION: Decision context + intensity ≥7 + >72h old  
  - VELOCITY_DROP:  <3 engram writes in 48h
  - SESSION_GAP:    No session save/resume in 24h+
"""

import json
import logging
import os
import platform
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("nucleus.heartbeat")

# ── Constants ─────────────────────────────────────────────────
DEFAULT_INTERVAL_MINUTES = 30
STALE_BLOCKER_HOURS = 24
STALE_DECISION_HOURS = 72
VELOCITY_WINDOW_HOURS = 48
VELOCITY_MIN_WRITES = 3
SESSION_GAP_HOURS = 24
LAUNCHD_LABEL = "dev.nucleusos.heartbeat"



def _load_heartbeat_state(brain: Path) -> Dict:
    state_file = brain / "meta" / "heartbeat_state.json"
    if state_file.exists():
        try:
            with open(state_file, "r") as f:
                return json.load(f)
        except:
            pass
    return {"last_alerted": {}}

def _save_heartbeat_state(brain: Path, state: Dict):
    state_file = brain / "meta" / "heartbeat_state.json"
    state_file.parent.mkdir(parents=True, exist_ok=True)
    with open(state_file, "w") as f:
        json.dump(state, f, indent=2)

def _filter_by_cooldown(triggers: List[Dict], state: Dict) -> List[Dict]:
    now = datetime.now()
    valid_triggers = []
    
    # Cooldowns in hours (The Centenary Heart - patient, non-nagging)
    cooldowns = {
        "STALE_BLOCKER": 48,
        "STALE_DECISION": 168, # 7 days
        "VELOCITY_DROP": 72,   # 3 days
        "SESSION_GAP": 48
    }
    
    for t in triggers:
        sig = t["signal"]
        key = t.get("key", sig)
        state_key = f"{sig}_{key}"
        
        last_alert_str = state.get("last_alerted", {}).get(state_key)
        if last_alert_str:
            last_alert = datetime.fromisoformat(last_alert_str)
            cooldown_hours = cooldowns.get(sig, 24)
            if (now - last_alert).total_seconds() < (cooldown_hours * 3600):
                continue # Still in cooldown, skip this trigger
                
        valid_triggers.append(t)
        state.setdefault("last_alerted", {})[state_key] = now.isoformat()
        
    return valid_triggers


def _trigger_autonomic_nervous_system(brain: Path, triggers: List[Dict]):
    """
    The Autonomic Nervous System: The Chief of Staff Protocol.
    When the Heart detects blockers, it bundles them into a single payload and spawns ONE
    'Chief of Staff' agent in the background. The LLM acts as the dependency resolver.
    """
    import subprocess
    import threading
    import json
    from .common import logger
    
    # Filter only actionable blockers for autonomic fixing
    blockers = [t for t in triggers if t.get("signal") == "STALE_BLOCKER"]
    if not blockers:
        return
        
    # Serialize the batch
    payload = json.dumps([{ "key": b.get("key"), "context": b.get("value_preview") } for b in blockers], indent=2)
    
    # Construct the Chief of Staff Meta-Prompt
    task_prompt = f"""AUTONOMIC DIRECTIVE - CHIEF OF STAFF OVERRIDE:
The Heartbeat just woke you up because the following {len(blockers)} system triggers fired:
{payload}

YOUR MANDATE:
1. DO NOT blindy execute them all at once. Act as the Prefrontal Cortex.
2. META-REFLECTION: For each item, ask 'Is this still relevant? Has it been solved elsewhere?' If it is obsolete, cross it off in .brain/task.md, write an engram explaining why, and drop it.
3. DEPENDENCY RESOLUTION: Look at the remaining valid tasks. If they touch the same files/repos, execute them SEQUENTIALLY to avoid git conflicts. If they are completely independent (e.g. one is a marketing post, one is a database fix), you may execute them sequentially in whatever order is most logical.
4. EXECUTION: You have authorization to diagnose the codebase, write code, and test it.
5. CLOSURE: When finished, update .brain/task.md checkboxes and write 'nucleus engram' entries for your resolutions. Do not wait for human input.
"""
    
    def run_coordinator():
        logger.info(f"🧠 [Autonomic] Spawning Chief of Staff for {len(blockers)} triggers.")
        try:
            # Create a unique TMUX session name for this batch
            import time
            tmux_session = f"nucleus_chief_of_staff_{int(time.time())}"
            
            # Escape single quotes so it survives the bash -c '...' wrapper
            safe_task = task_prompt.replace("'", "'\''")
            cmd_str = f"nucleus run coordinator --autopilot --gemini-yolo --task '{safe_task}'"


            # Escape quotes safely for TMUX bash execution
            safe_task = task_prompt.replace('"', '\\"').replace("'", "'\\''")
            cmd = [
                "nucleus", "run", "coordinator", 
                "--autopilot", 
                "--gemini-yolo", 
                "--task", f'"{safe_task}"'
            ]
            cmd_str = " ".join(cmd)

            
            tmux_cmd = [
                "tmux", "new-session", "-d", "-s", tmux_session,
                f"bash -c '{cmd_str}; echo \"Autonomic run complete. Session will close in 60s.\"; sleep 60'"
            ]
            
            # Spawn the TMUX multiplexer. This gives Gemini the TTY it demands.
            subprocess.Popen(
                tmux_cmd,
                cwd=str(brain.parent),
                env={
                    **os.environ, 
                    "NUCLEAR_BRAIN_PATH": str(brain),
                    "GOOGLE_APPLICATION_CREDENTIALS": str(Path.home() / ".config/gcloud/application_default_credentials.json"),
                    "GOOGLE_CLOUD_PROJECT": "gen-lang-client-0894185576",
                    "GOOGLE_CLOUD_LOCATION": "global",
                    "PATH": "/Users/lokeshgarg/.nvm/versions/node/v22.18.0/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:/Users/lokeshgarg/ai-mvp-backend/.venv/bin"
                }
            )
            logger.info(f"🧠 [Autonomic] Spawned TMUX session: {tmux_session}")
        except Exception as e:
            logger.error(f"❌ [Autonomic] Failed to spawn hands for {key}: {e}")

    # Fire and forget
    threading.Thread(target=run_coordinator, daemon=True).start()

def _heartbeat_check_impl(brain_path: Optional[str] = None) -> Dict:
    """
    Context-triggered proactive check-in.
    
    Reads engrams, checks for 4 types of staleness signals,
    and returns actionable insights only when something significant
    is detected. Quiet when nothing needs attention.
    
    Returns:
        Dict with triggers found, messages, and should_notify flag.
    """
    from .common import get_brain_path
    
    brain = Path(brain_path) if brain_path else get_brain_path()
    start = time.time()
    
    triggers: List[Dict] = []
    
    # ── Signal 1: Stale Blockers ────────────────────────────────
    stale_blockers = _check_stale_blockers(brain)
    triggers.extend(stale_blockers)
    
    # ── Signal 2: Stale Decisions ───────────────────────────────
    stale_decisions = _check_stale_decisions(brain)
    triggers.extend(stale_decisions)
    
    # ── Signal 3: Velocity Drop ─────────────────────────────────
    velocity_drop = _check_velocity_drop(brain)
    if velocity_drop:
        triggers.append(velocity_drop)
    
    # ── Signal 4: Session Gap ───────────────────────────────────
    session_gap = _check_session_gap(brain)
    if session_gap:
        triggers.append(session_gap)
        
    # ── Centenary State Filter (Cooldowns) ──────────────────────
    state = _load_heartbeat_state(brain)
    triggers = _filter_by_cooldown(triggers, state)
    if triggers:
        _save_heartbeat_state(brain, state)
    
    elapsed_ms = (time.time() - start) * 1000
    should_notify = len(triggers) > 0
    
    # ── Autonomic Nervous System (The Chief of Staff) ───────────
    _trigger_autonomic_nervous_system(brain, triggers)

    # Log the check
    _log_heartbeat_check(brain, triggers, elapsed_ms)
    
    result = {
        "timestamp": datetime.now().isoformat(),
        "triggers": triggers,
        "trigger_count": len(triggers),
        "should_notify": should_notify,
        "check_duration_ms": round(elapsed_ms, 1),
    }
    
    if should_notify:
        result["formatted"] = _format_heartbeat_output(triggers)
        result["notification_title"] = "🧠 Nucleus Heartbeat"
        result["notification_body"] = triggers[0]["message"]
    else:
        result["formatted"] = "💚 All clear — nothing needs attention right now."
    
    return result


def _check_stale_blockers(brain: Path) -> List[Dict]:
    """Signal 1: Find engrams with intensity ≥8 containing 'blocker' that are >24h old."""
    engram_path = brain / "engrams" / "ledger.jsonl"
    if not engram_path.exists():
        return []
    
    now = datetime.now()
    cutoff = now - timedelta(hours=STALE_BLOCKER_HOURS)
    stale = []
    
    try:
        with open(engram_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    e = json.loads(line)
                    if e.get("deleted", False):
                        continue
                    
                    intensity = e.get("intensity", 5)
                    value = str(e.get("value", "")).lower()
                    key = e.get("key", "unknown")
                    ts_str = e.get("timestamp", "")
                    
                    if intensity < 8:
                        continue
                    if "blocker" not in value and "blocked" not in value and "blocking" not in value:
                        continue
                    
                    if ts_str:
                        try:
                            ts = datetime.fromisoformat(ts_str)
                            if ts < cutoff:
                                age_hours = int((now - ts).total_seconds() / 3600)
                                stale.append({
                                    "signal": "STALE_BLOCKER",
                                    "key": key,
                                    "age_hours": age_hours,
                                    "intensity": intensity,
                                    "message": f"⏰ STALE BLOCKER: '{key}' is {age_hours}h old. Should we revisit?",
                                    "value_preview": str(e.get("value", ""))[:100],
                                })
                        except (ValueError, TypeError):
                            pass
                except json.JSONDecodeError:
                    continue
    except Exception as ex:
        logger.debug(f"Stale blocker check error: {ex}")
    
    return stale


def _check_stale_decisions(brain: Path) -> List[Dict]:
    """Signal 2: Find Decision-context engrams with intensity ≥7 that are >72h old."""
    engram_path = brain / "engrams" / "ledger.jsonl"
    if not engram_path.exists():
        return []
    
    now = datetime.now()
    cutoff = now - timedelta(hours=STALE_DECISION_HOURS)
    stale = []
    
    try:
        with open(engram_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    e = json.loads(line)
                    if e.get("deleted", False):
                        continue
                    
                    context = e.get("context", "")
                    intensity = e.get("intensity", 5)
                    key = e.get("key", "unknown")
                    ts_str = e.get("timestamp", "")
                    
                    if context != "Decision":
                        continue
                    if intensity < 7:
                        continue
                    
                    if ts_str:
                        try:
                            ts = datetime.fromisoformat(ts_str)
                            if ts < cutoff:
                                age_days = int((now - ts).total_seconds() / 86400)
                                stale.append({
                                    "signal": "STALE_DECISION",
                                    "key": key,
                                    "age_days": age_days,
                                    "intensity": intensity,
                                    "message": f"🤔 Decision '{key}' hasn't been revisited in {age_days}d. Still valid?",
                                    "value_preview": str(e.get("value", ""))[:100],
                                })
                        except (ValueError, TypeError):
                            pass
                except json.JSONDecodeError:
                    continue
    except Exception as ex:
        logger.debug(f"Stale decision check error: {ex}")
    
    # Return only top 3 most stale
    stale.sort(key=lambda x: x.get("age_days", 0), reverse=True)
    return stale[:3]


def _check_velocity_drop(brain: Path) -> Optional[Dict]:
    """Signal 3: Detect if engram write velocity has dropped below threshold."""
    engram_path = brain / "engrams" / "ledger.jsonl"
    if not engram_path.exists():
        return None
    
    now = datetime.now()
    window = now - timedelta(hours=VELOCITY_WINDOW_HOURS)
    recent_count = 0
    total_count = 0
    
    try:
        with open(engram_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    e = json.loads(line)
                    if e.get("deleted", False):
                        continue
                    total_count += 1
                    ts_str = e.get("timestamp", "")
                    if ts_str:
                        try:
                            ts = datetime.fromisoformat(ts_str)
                            if ts >= window:
                                recent_count += 1
                        except (ValueError, TypeError):
                            pass
                except json.JSONDecodeError:
                    continue
    except Exception as ex:
        logger.debug(f"Velocity check error: {ex}")
        return None
    
    # Only trigger if there are enough total engrams to establish a baseline
    if total_count < 10:
        return None
    
    if recent_count < VELOCITY_MIN_WRITES:
        return {
            "signal": "VELOCITY_DROP",
            "recent_writes": recent_count,
            "window_hours": VELOCITY_WINDOW_HOURS,
            "threshold": VELOCITY_MIN_WRITES,
            "message": f"📉 Only {recent_count} engram writes in the last {VELOCITY_WINDOW_HOURS}h. What's blocking?",
        }
    
    return None


def _check_session_gap(brain: Path) -> Optional[Dict]:
    """Signal 4: Check if there's been no session activity in 24h+."""
    sessions_path = brain / "ledger" / "sessions.jsonl"
    events_path = brain / "ledger" / "events.jsonl"
    
    now = datetime.now()
    cutoff = now - timedelta(hours=SESSION_GAP_HOURS)
    last_activity = None
    
    # Check sessions ledger
    if sessions_path.exists():
        try:
            with open(sessions_path, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        s = json.loads(line)
                        ts_str = s.get("timestamp", s.get("saved_at", ""))
                        if ts_str:
                            try:
                                ts = datetime.fromisoformat(ts_str)
                                if last_activity is None or ts > last_activity:
                                    last_activity = ts
                            except (ValueError, TypeError):
                                pass
                    except json.JSONDecodeError:
                        continue
        except Exception:
            pass
    
    # Check events for session-related activity
    if events_path.exists():
        try:
            with open(events_path, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        ev = json.loads(line)
                        event_type = ev.get("event_type", ev.get("event", ""))
                        if "session" in str(event_type).lower():
                            ts_str = ev.get("timestamp", "")
                            if ts_str:
                                try:
                                    ts = datetime.fromisoformat(ts_str)
                                    if last_activity is None or ts > last_activity:
                                        last_activity = ts
                                except (ValueError, TypeError):
                                    pass
                    except json.JSONDecodeError:
                        continue
        except Exception:
            pass
    
    if last_activity is None:
        return None  # No session data at all — don't trigger on empty state
    
    if last_activity < cutoff:
        gap_hours = int((now - last_activity).total_seconds() / 3600)
        return {
            "signal": "SESSION_GAP",
            "last_activity": last_activity.isoformat(),
            "gap_hours": gap_hours,
            "message": f"🔌 No session activity in {gap_hours}h. Everything okay?",
        }
    
    return None


def _format_heartbeat_output(triggers: List[Dict]) -> str:
    """Format triggers into a human-readable heartbeat report."""
    lines = []
    lines.append("=" * 56)
    lines.append("💓 NUCLEUS HEARTBEAT (Centenary Edition)")
    lines.append(f"   {datetime.now().strftime('%A, %B %d %I:%M %p')}")
    lines.append("=" * 56)
    
    for i, t in enumerate(triggers, 1):
        lines.append(f"\n  {i}. {t['message']}")
        if t.get("value_preview"):
            lines.append(f"     └─ {t['value_preview']}")
            
        # Add Coordinator Handoff Suggestion
        if t["signal"] == "STALE_BLOCKER":
            key = t.get("key", "")
            lines.append(f"     🤖 Fix via Autopilot:")
            lines.append(f"        nucleus run coordinator --autopilot --task \"Diagnose and resolve the stale blocker: {key}\"")
    
    lines.append("")
    lines.append(f"  {len(triggers)} item{'s' if len(triggers) != 1 else ''} need attention.")
    lines.append("=" * 56)
    
    return "\n".join(lines)


def _log_heartbeat_check(brain: Path, triggers: List[Dict], elapsed_ms: float):
    """Append heartbeat check to the heartbeat log."""
    log_dir = brain / "heartbeat"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "checks.jsonl"
    
    entry = {
        "timestamp": datetime.now().isoformat(),
        "trigger_count": len(triggers),
        "signals": [t["signal"] for t in triggers],
        "duration_ms": round(elapsed_ms, 1),
    }
    
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as ex:
        logger.debug(f"Failed to log heartbeat check: {ex}")


# ── Notification ─────────────────────────────────────────────

def _notify_native(title: str, body: str) -> bool:
    """Send a native OS notification. Returns True if sent."""
    system = platform.system()
    
    try:
        if system == "Darwin":
            # macOS: osascript (zero dependency)
            script = f'display notification "{body}" with title "{title}"'
            subprocess.run(
                ["osascript", "-e", script],
                capture_output=True, timeout=5,
            )
            return True
        elif system == "Linux":
            # Linux: notify-send (libnotify)
            subprocess.run(
                ["notify-send", title, body],
                capture_output=True, timeout=5,
            )
            return True
        else:
            logger.debug(f"No notification support for {system}")
            return False
    except FileNotFoundError:
        logger.debug("Notification binary not found")
        return False
    except Exception as ex:
        logger.debug(f"Notification failed: {ex}")
        return False


# ── Scheduler (launchd / systemd) ────────────────────────────

def _get_launchd_plist_path() -> Path:
    """Get the path for the launchd plist file."""
    return Path.home() / "Library" / "LaunchAgents" / f"{LAUNCHD_LABEL}.plist"


def _get_nucleus_executable() -> str:
    """Find the nucleus executable path."""
    import shutil
    path = shutil.which("nucleus")
    if path:
        return path
    # Fallback: use python -m
    return f"{sys.executable} -m mcp_server_nucleus"


def _heartbeat_install_impl(
    interval_minutes: int = DEFAULT_INTERVAL_MINUTES,
    brain_path: Optional[str] = None,
) -> Dict:
    """
    Install platform-native scheduling for heartbeat checks.
    
    macOS: Creates a launchd UserAgent plist.
    Linux: Creates a systemd user timer.
    """
    system = platform.system()
    
    if system == "Darwin":
        return _install_launchd(interval_minutes, brain_path)
    elif system == "Linux":
        return _install_systemd(interval_minutes, brain_path)
    else:
        return {
            "success": False,
            "error": f"Unsupported platform: {system}. Heartbeat install supports macOS and Linux.",
        }


def _install_launchd(interval_minutes: int, brain_path: Optional[str]) -> Dict:
    """Install a macOS launchd UserAgent plist."""
    plist_path = _get_launchd_plist_path()
    nucleus_bin = _get_nucleus_executable()
    
    brain_env = ""
    if brain_path:
        brain_env = f"""    <key>EnvironmentVariables</key>
    <dict>
        <key>NUCLEUS_BRAIN_PATH</key>
        <string>{brain_path}</string>
    </dict>"""
    
    plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{LAUNCHD_LABEL}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{nucleus_bin}</string>
        <string>heartbeat</string>
        <string>check</string>
        <string>--notify</string>
    </array>
    <key>StartInterval</key>
    <integer>{interval_minutes * 60}</integer>
    <key>RunAtLoad</key>
    <true/>
    <key>StandardOutPath</key>
    <string>{Path.home()}/.nucleus/heartbeat_stdout.log</string>
    <key>StandardErrorPath</key>
    <string>{Path.home()}/.nucleus/heartbeat_stderr.log</string>
{brain_env}
</dict>
</plist>"""
    
    try:
        plist_path.parent.mkdir(parents=True, exist_ok=True)
        plist_path.write_text(plist_content)
        
        # Load the agent
        subprocess.run(
            ["launchctl", "load", str(plist_path)],
            capture_output=True, timeout=10,
        )
        
        return {
            "success": True,
            "platform": "macOS",
            "plist_path": str(plist_path),
            "interval_minutes": interval_minutes,
            "command": f"{nucleus_bin} heartbeat check --notify",
            "message": f"✅ Heartbeat installed! Checks every {interval_minutes} minutes.",
            "uninstall": "nucleus heartbeat uninstall",
        }
    except Exception as ex:
        return {
            "success": False,
            "error": f"Failed to install launchd agent: {ex}",
        }


def _install_systemd(interval_minutes: int, brain_path: Optional[str]) -> Dict:
    """Install a Linux systemd user timer."""
    config_dir = Path.home() / ".config" / "systemd" / "user"
    config_dir.mkdir(parents=True, exist_ok=True)
    
    nucleus_bin = _get_nucleus_executable()
    brain_env = f"\nEnvironment=NUCLEUS_BRAIN_PATH={brain_path}" if brain_path else ""
    
    service_content = f"""[Unit]
Description=Nucleus Heartbeat Check

[Service]
Type=oneshot
ExecStart={nucleus_bin} heartbeat check --notify{brain_env}
"""
    
    timer_content = f"""[Unit]
Description=Nucleus Heartbeat Timer

[Timer]
OnBootSec=5min
OnUnitActiveSec={interval_minutes}min
Persistent=true

[Install]
WantedBy=timers.target
"""
    
    try:
        (config_dir / "nucleus-heartbeat.service").write_text(service_content)
        (config_dir / "nucleus-heartbeat.timer").write_text(timer_content)
        
        subprocess.run(["systemctl", "--user", "daemon-reload"], capture_output=True, timeout=10)
        subprocess.run(["systemctl", "--user", "enable", "--now", "nucleus-heartbeat.timer"],
                       capture_output=True, timeout=10)
        
        return {
            "success": True,
            "platform": "Linux",
            "timer_path": str(config_dir / "nucleus-heartbeat.timer"),
            "interval_minutes": interval_minutes,
            "message": f"✅ Heartbeat installed! Checks every {interval_minutes} minutes.",
            "uninstall": "nucleus heartbeat uninstall",
        }
    except Exception as ex:
        return {"success": False, "error": f"Failed to install systemd timer: {ex}"}


def _heartbeat_uninstall_impl() -> Dict:
    """Remove platform-native heartbeat scheduling."""
    system = platform.system()
    
    if system == "Darwin":
        plist_path = _get_launchd_plist_path()
        try:
            subprocess.run(["launchctl", "unload", str(plist_path)],
                           capture_output=True, timeout=10)
            if plist_path.exists():
                plist_path.unlink()
            return {
                "success": True,
                "message": "✅ Heartbeat uninstalled. No more proactive check-ins.",
            }
        except Exception as ex:
            return {"success": False, "error": str(ex)}
    
    elif system == "Linux":
        try:
            subprocess.run(["systemctl", "--user", "disable", "--now", "nucleus-heartbeat.timer"],
                           capture_output=True, timeout=10)
            config_dir = Path.home() / ".config" / "systemd" / "user"
            for f in ["nucleus-heartbeat.service", "nucleus-heartbeat.timer"]:
                p = config_dir / f
                if p.exists():
                    p.unlink()
            subprocess.run(["systemctl", "--user", "daemon-reload"], capture_output=True, timeout=10)
            return {
                "success": True,
                "message": "✅ Heartbeat uninstalled. No more proactive check-ins.",
            }
        except Exception as ex:
            return {"success": False, "error": str(ex)}
    
    return {"success": False, "error": f"Unsupported platform: {system}"}


def _heartbeat_status_impl(brain_path: Optional[str] = None) -> Dict:
    """Check heartbeat daemon installation status and recent activity."""
    from .common import get_brain_path
    
    brain = Path(brain_path) if brain_path else get_brain_path()
    system = platform.system()
    
    # Check installation
    installed = False
    platform_info = {}
    
    if system == "Darwin":
        plist_path = _get_launchd_plist_path()
        installed = plist_path.exists()
        platform_info = {
            "platform": "macOS",
            "plist_path": str(plist_path),
            "installed": installed,
        }
    elif system == "Linux":
        timer_path = Path.home() / ".config" / "systemd" / "user" / "nucleus-heartbeat.timer"
        installed = timer_path.exists()
        platform_info = {
            "platform": "Linux",
            "timer_path": str(timer_path),
            "installed": installed,
        }
    
    # Check recent heartbeat log
    log_path = brain / "heartbeat" / "checks.jsonl"
    recent_checks = []
    total_checks = 0
    total_triggers = 0
    
    if log_path.exists():
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        entry = json.loads(line)
                        total_checks += 1
                        total_triggers += entry.get("trigger_count", 0)
                        recent_checks.append(entry)
                    except json.JSONDecodeError:
                        continue
        except Exception:
            pass
    
    # Keep only last 5
    recent_checks = recent_checks[-5:]
    
    formatted_lines = []
    formatted_lines.append("=" * 56)
    formatted_lines.append("💓 NUCLEUS HEARTBEAT STATUS")
    formatted_lines.append("=" * 56)
    formatted_lines.append(f"  Installed: {'✅ YES' if installed else '❌ NO'}")
    formatted_lines.append(f"  Platform:  {platform_info.get('platform', 'Unknown')}")
    formatted_lines.append(f"  Total checks: {total_checks}")
    formatted_lines.append(f"  Total triggers fired: {total_triggers}")
    
    if recent_checks:
        formatted_lines.append(f"\n  Last {len(recent_checks)} checks:")
        for c in reversed(recent_checks):
            ts = c.get("timestamp", "?")[:19]
            count = c.get("trigger_count", 0)
            signals = ", ".join(c.get("signals", []))
            icon = "🔴" if count > 0 else "💚"
            formatted_lines.append(f"    {icon} {ts} — {count} trigger{'s' if count != 1 else ''}" +
                                   (f" ({signals})" if signals else ""))
    
    if not installed:
        formatted_lines.append(f"\n  → Install with: nucleus heartbeat install")
    
    formatted_lines.append("=" * 56)
    
    return {
        "installed": installed,
        "platform": platform_info,
        "total_checks": total_checks,
        "total_triggers": total_triggers,
        "recent_checks": recent_checks,
        "formatted": "\n".join(formatted_lines),
    }
