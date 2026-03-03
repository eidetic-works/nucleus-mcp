#!/usr/bin/env python3
"""
Commitment Ledger - Core module for PEFS Phase 2
Tracks all commitments, aging, context, and closure methods
"""

import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from .runtime.storage import read_brain_file, write_brain_file, brain_file_exists
from .runtime.locking import get_lock

def get_ledger_path(brain_path: Path) -> Path:
    """Get path to commitment ledger"""
    return brain_path / "commitments" / "ledger.json"

def load_ledger(brain_path: Path) -> Dict:
    """Load commitment ledger from disk"""
    ledger_path = get_ledger_path(brain_path)
    
    if brain_file_exists(ledger_path):
        return json.loads(read_brain_file(ledger_path))
    
    # Default empty ledger
    return {
        "commitments": [],
        "last_scan": None,
        "last_interaction": None,  # MDR_010: Usage telemetry
        "notifications_sent": 0,   # MDR_010: Value Ratio denominator
        "high_impact_closed": 0,   # MDR_010: Value Ratio numerator
        "notifications_paused": False,  # MDR_010: Kill Switch
        "manual_overrides_count": 0,  # MDR_010: Tracks when user fights the system
        "estimated_time_saved_minutes": 0,  # MDR_010: Accumulated time saved estimate
        "stats": {
            "total_open": 0,
            "green_tier": 0,
            "yellow_tier": 0,
            "red_tier": 0
        }
    }

def save_ledger(brain_path: Path, ledger: Dict) -> None:
    """Save commitment ledger to disk"""
    ledger_path = get_ledger_path(brain_path)
    write_brain_file(ledger_path, json.dumps(ledger, indent=2))

def analyze_context(description: str, source_file: str) -> Dict:
    """
    Analyze commitment context for routing decisions.
    Returns novelty, dopamine, urgency, emotional_load.
    """
    desc_lower = description.lower()
    
    # Novelty detection
    if any(k in desc_lower for k in ["first time", "new", "never"]):
        novelty = "high"
    elif any(k in desc_lower for k in ["repeat", "again", "another"]):
        novelty = "low"
    else:
        novelty = "medium"
    
    # Dopamine level (boring vs. fun tasks)
    boring_keywords = ["fix", "bug", "setup", "config", "admin", "cron", "env"]
    fun_keywords = ["build", "create", "design", "implement"]
    
    if any(k in desc_lower for k in boring_keywords):
        dopamine = "low"
    elif any(k in desc_lower for k in fun_keywords):
        dopamine = "high"
    else:
        dopamine = "medium"
    
    # Urgency detection
    if any(k in desc_lower for k in ["deadline", "urgent", "asap", "today"]):
        urgency = "high"
    elif any(k in desc_lower for k in ["soon", "this week"]):
        urgency = "medium"
    else:
        urgency = None
    
    # Emotional load (guilt triggers)
    guilt_keywords = ["should", "need to", "must", "haven't", "forgot"]
    emotional_load = sum(1 for k in guilt_keywords if k in desc_lower) * 2
    emotional_load = min(emotional_load, 10)  # Cap at 10
    
    return {
        "novelty": novelty,
        "dopamine": dopamine,
        "urgency": urgency,
        "emotional_load": emotional_load
    }

def suggest_action(commitment: Dict) -> tuple[str, str]:
    """
    Suggest closure action based on context and age.
    Returns (action, reason) tuple.
    """
    age = commitment["age_days"]
    context = commitment["context"]
    
    # Check learned patterns first
    # We need to pass patterns in, or load them here (loading slightly inefficient but safe)
    # Ideally suggest_action would take patterns as arg
    # For now, we'll do best effort detection if patterns exist nearby or just use heuristic
    pass 
    
    # Archive old items
    if age > 30:
        return ("archive", f"Stale ({age} days old)")
    
    # High novelty always needs Chairman
    if context["novelty"] == "high":
        return ("schedule", "High novelty, needs Chairman attention")
    
    # Low dopamine tasks schedule for morning
    if context["dopamine"] == "low" and age < 7:
        return ("schedule", "Low dopamine task, schedule for morning energy")
    
    # Urgent items
    if context["urgency"] == "high":
        return ("do_now", "Urgent deadline")
    
    # Recent simple tasks
    if age < 3 and context["novelty"] == "low":
        return ("do_now", "Recent and simple, quick win")
    
    # Default
    return ("schedule", "Needs focused time")

def add_commitment(
    brain_path: Path,
    source_file: str,
    source_line: int,
    description: str,
    comm_type: str,
    source: str = "auto_detected",
    priority: int = 3,
    required_skills: List[str] = None
) -> Dict:
    """
    Add a new commitment to the ledger.
    Returns the created commitment.
    
    Args:
        brain_path: Path to brain directory
        source_file: File where commitment was found
        source_line: Line number in source file
        description: What the commitment is
        comm_type: Type of commitment (task, todo, draft, decision)
        source: Where it came from (auto_detected, manual, migrated)
        priority: 1-5, lower is higher priority
        required_skills: Skills needed to complete
    """
    # Transaction: Read -> Modify -> Write protected by Lock
    with get_lock("ledger", brain_path).section():
        ledger = load_ledger(brain_path)
        
        # Generate ID
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        comm_id = f"comm_{timestamp}_{len(ledger['commitments'])}"
        
        # Analyze context
        context = analyze_context(description, source_file)
        
        # Create commitment
        commitment = {
            "id": comm_id,
            "created": datetime.now().isoformat(),
            "source_file": source_file,
            "source_line": source_line,
            "type": comm_type,
            "source": source,
            "description": description,
            "context": context,
            "age_days": 0,
            "tier": "green",
            "priority": priority,
            "required_skills": required_skills or [],
            "suggested_action": None,
            "suggested_reason": None,
            "status": "open",
            "closed_at": None,
            "closed_method": None
        }
        
        # Add suggested action
        try:
            # Re-load patterns inside lock if needed, but patterns file has its own lock ideally.
            # For now, simplistic approach.
            patterns = load_patterns(brain_path)
            pattern_suggestion = suggest_pattern_action(commitment, patterns)
        except Exception:
            pattern_suggestion = None
        
        if pattern_suggestion:
            action, reason = pattern_suggestion
        else:
            action, reason = suggest_action(commitment)
            
        commitment["suggested_action"] = action
        commitment["suggested_reason"] = reason
        
        ledger["commitments"].append(commitment)
        save_ledger(brain_path, ledger)
        
    return commitment

def update_commitment_ages(brain_path: Path) -> Dict:
    """
    Update age and tier for all open commitments.
    Returns updated ledger with stats.
    """
    with get_lock("ledger", brain_path).section():
        ledger = load_ledger(brain_path)
        
        for comm in ledger["commitments"]:
            if comm["status"] == "open":
                # Calculate age
                created = datetime.fromisoformat(comm["created"])
                comm["age_days"] = (datetime.now() - created).days
                
                # Update tier
                if comm["age_days"] < 3:
                    comm["tier"] = "green"
                elif comm["age_days"] < 7:
                    comm["tier"] = "yellow"
                else:
                    comm["tier"] = "red"
                
                # Update suggestion
                action, reason = suggest_action(comm)
                comm["suggested_action"] = action
                comm["suggested_reason"] = reason
        
        # Update stats
        open_comms = [c for c in ledger["commitments"] if c["status"] == "open"]
        
        # Count by type
        by_type = {}
        for c in open_comms:
            t = c.get("type", "unknown")
            by_type[t] = by_type.get(t, 0) + 1
        
        ledger["stats"] = {
            "total_open": len(open_comms),
            "green_tier": len([c for c in open_comms if c["tier"] == "green"]),
            "yellow_tier": len([c for c in open_comms if c["tier"] == "yellow"]),
            "red_tier": len([c for c in open_comms if c["tier"] == "red"]),
            "by_type": by_type
        }
        
        ledger["last_scan"] = datetime.now().isoformat()
        save_ledger(brain_path, ledger)
        
    return ledger

def close_commitment(
    brain_path: Path,
    comm_id: str,
    method: str
) -> Dict:
    """
    Close a commitment with specified method.
    Returns updated commitment.
    """
    with get_lock("ledger", brain_path).section():
        ledger = load_ledger(brain_path)
        
        for comm in ledger["commitments"]:
            if comm["id"] == comm_id:
                comm["status"] = "closed"
                comm["closed_at"] = datetime.now().isoformat()
                comm["closed_method"] = method
                save_ledger(brain_path, ledger)
                return comm
    
    raise ValueError(f"Commitment {comm_id} not found")

# ============================================================
# WEEKLY CHALLENGE SYSTEM
# ============================================================

def get_challenge_path(brain_path: Path) -> Path:
    """Get path to weekly challenge file"""
    return brain_path / "challenges" / "current_challenge.json"

def load_challenge(brain_path: Path) -> Dict:
    """Load current weekly challenge"""
    path = get_challenge_path(brain_path)
    if brain_file_exists(path):
        return json.loads(read_brain_file(path))
    return None

def set_challenge(brain_path: Path, challenge: Dict) -> None:
    """Set current weekly challenge"""
    path = get_challenge_path(brain_path)
    write_brain_file(path, json.dumps(challenge, indent=2))

def get_starter_challenges() -> List[Dict]:
    """Get list of starter challenges"""
    return [
        {
            "id": "red_slayer",
            "title": "Red Slayer",
            "description": "Close 3 red-tier items this week",
            "target_type": "tier",
            "target_value": "red",
            "target_count": 3,
            "reward": "Guilt-free weekend"
        },
        {
            "id": "draft_finisher",
            "title": "Draft Finisher",
            "description": "Turn 2 drafts into published/final docs",
            "target_type": "type",
            "target_value": "draft",
            "target_count": 2,
            "reward": "Clarity boost"
        },
        {
            "id": "frog_eater",
            "title": "Frog Eater",
            "description": "Close 1 item older than 20 days",
            "target_type": "age",
            "target_min_days": 20,
            "target_count": 1,
            "reward": "Massive dopamine hit"
        },
        {
            "id": "inbox_zero",
            "title": "Inbox Zero",
            "description": "Get total open loops under 5",
            "target_type": "total_count",
            "target_max": 5,
            "reward": "Zen mind"
        },
        {
            "id": "quick_wins",
            "title": "Quick Wins",
            "description": "Close 5 green-tier items in one day",
            "target_type": "velocity",
            "target_count": 5,
            "reward": "Momentum builder"
        }
    ]

def check_challenge_progress(brain_path: Path) -> Dict:
    """Check progress on current challenge"""
    challenge = load_challenge(brain_path)
    if not challenge:
        return None
    
    load_ledger(brain_path)
    
    # Future expansion: track closed items history
    return {
        "challenge": challenge,
        "status": "in_progress",
        "progress_note": "Tracking implemented in next iteration"
    }

# ============================================================
# PATTERN MATCHING SYSTEM-
# ============================================================

def get_patterns_path(brain_path: Path) -> Path:
    return brain_path / "patterns" / "learned_patterns.json"

def load_patterns(brain_path: Path) -> List[Dict]:
    path = get_patterns_path(brain_path)
    if brain_file_exists(path):
        return json.loads(read_brain_file(path))
    return []

def save_patterns(brain_path: Path, patterns: List[Dict]) -> None:
    path = get_patterns_path(brain_path)
    write_brain_file(path, json.dumps(patterns, indent=2))

def suggest_pattern_action(commitment: Dict, patterns: List[Dict]) -> Optional[tuple]:
    """Suggest action based on learned patterns"""
    # Simple keyword matching for MVP
    desc = commitment["description"].lower()
    
    for pattern in patterns:
        if any(k in desc for k in pattern["keywords"]):
            return (pattern["action"], f"Pattern match: {pattern['name']}")
            
    return None

def learn_patterns(brain_path: Path) -> List[Dict]:
    """Analyze closed commitments to learn patterns"""
    ledger = load_ledger(brain_path)
    closed = [c for c in ledger["commitments"] if c["status"] == "closed"]
    patterns = load_patterns(brain_path)
    
    # Simple heuristic: If we closed 3+ items with same keyword using same method
    keywords = {}
    for c in closed:
        words = c["description"].lower().split()
        method = c.get("closed_method", "unknown")
        
        for w in words:
            if len(w) > 4: # Skip short words
                key = (w, method)
                keywords[key] = keywords.get(key, 0) + 1
                
    # Detect new patterns
    new_found = 0
    for (word, method), count in keywords.items():
        if count >= 3:
            # Check if exists
            if not any(word in p["keywords"] and p["action"] == method for p in patterns):
                patterns.append({
                    "name": f"Successful {word} via {method}",
                    "keywords": [word],
                    "action": method,
                    "confidence": 0.8,
                    "source": "auto_learned"
                })
                new_found += 1
                
    if new_found > 0:
        save_patterns(brain_path, patterns)
        
    return patterns

# ============================================================
# COORDINATION METRICS
# ============================================================

def calculate_metrics(brain_path: Path) -> Dict:
    """Calculate coordination metrics (velocity, load, trends)"""
    ledger = load_ledger(brain_path)
    commitments = ledger["commitments"]
    
    # 1. Closure Velocity (last 7 days)
    closed_last_7d = []
    now = datetime.now()
    
    for c in commitments:
        if c["status"] == "closed" and c["closed_at"]:
            closed_time = datetime.fromisoformat(c["closed_at"])
            if (now - closed_time).days <= 7:
                closed_last_7d.append(c)
                
    velocity = len(closed_last_7d)
    
    # Avg days to close
    avg_days_to_close = 0
    if velocity > 0:
        total_days = sum(c["age_days"] for c in closed_last_7d)
        avg_days_to_close = round(total_days / velocity, 1)
        
    # 2. Closure Rate by Type
    by_type = {}
    total_closed = len([c for c in commitments if c["status"] == "closed"])
    
    if total_closed > 0:
        for c in commitments:
            if c["status"] == "closed":
                t = c.get("type", "unknown")
                by_type[t] = by_type.get(t, 0) + 1
        
        # Convert to percentage
        for t in by_type:
            by_type[t] = f"{round((by_type[t] / total_closed) * 100)}%"
            
    # 3. Mental Load Trend (Current snapshop vs History?)
    # For MVP, we'll just return current load which nightly agent logs historically
    stats = ledger.get("stats", {})
    
    return {
        "velocity_7d": velocity,
        "avg_days_to_close": avg_days_to_close,
        "closure_rates": by_type,
        "current_load": {
            "total": stats.get("total_open", 0),
            "red": stats.get("red_tier", 0)
        },
        # MDR_010: Value Ratio
        "value_ratio": calculate_value_ratio(brain_path)
    }

# ============================================================
# MDR_010: USAGE TELEMETRY & FEEDBACK
# ============================================================

def record_interaction(brain_path: Path) -> None:
    """Record a user interaction timestamp (MDR_010)"""
    with get_lock("ledger", brain_path).section():
        ledger = load_ledger(brain_path)
        ledger["last_interaction"] = datetime.now().isoformat()
        save_ledger(brain_path, ledger)

def increment_notifications(brain_path: Path, count: int = 1) -> None:
    """Increment notifications sent counter (MDR_010)"""
    with get_lock("ledger", brain_path).section():
        ledger = load_ledger(brain_path)
        ledger["notifications_sent"] = ledger.get("notifications_sent", 0) + count
        save_ledger(brain_path, ledger)

def mark_high_impact_closure(brain_path: Path) -> None:
    """Increment high-impact closures counter (MDR_010)"""
    with get_lock("ledger", brain_path).section():
        ledger = load_ledger(brain_path)
        ledger["high_impact_closed"] = ledger.get("high_impact_closed", 0) + 1
        save_ledger(brain_path, ledger)

def calculate_value_ratio(brain_path: Path) -> Dict:
    """Calculate Value Ratio metric (MDR_010)"""
    ledger = load_ledger(brain_path)
    notifications = ledger.get("notifications_sent", 0)
    high_impact = ledger.get("high_impact_closed", 0)
    
    if notifications == 0:
        ratio = None
        verdict = "No notifications sent yet"
    else:
        ratio = round(high_impact / notifications, 3)
        if ratio >= 0.2:
            verdict = "✅ EXCELLENT (1 impact per 5 notifications)"
        elif ratio >= 0.1:
            verdict = "🟡 GOOD (1 impact per 10 notifications)"
        elif ratio >= 0.01:
            verdict = "🔴 POOR (1 impact per 100 notifications)"
        else:
            verdict = "❌ FAILURE - consider pausing notifications"
    
    return {
        "notifications_sent": notifications,
        "high_impact_closed": high_impact,
        "ratio": ratio,
        "verdict": verdict
    }

def record_manual_override(brain_path: Path, reason: str = "") -> None:
    """Record when user fights/overrides the system (MDR_010)"""
    with get_lock("ledger", brain_path).section():
        ledger = load_ledger(brain_path)
        ledger["manual_overrides_count"] = ledger.get("manual_overrides_count", 0) + 1
        save_ledger(brain_path, ledger)

def estimate_time_saved(brain_path: Path, minutes: int) -> None:
    """Add estimated time saved to running total (MDR_010)"""
    with get_lock("ledger", brain_path).section():
        ledger = load_ledger(brain_path)
        ledger["estimated_time_saved_minutes"] = ledger.get("estimated_time_saved_minutes", 0) + minutes
        save_ledger(brain_path, ledger)

def get_weekly_summary(brain_path: Path) -> Dict:
    """
    Generate Sunday weekly summary with time saved (MDR_010).
    Returns metrics for the weekly briefing.
    """
    ledger = load_ledger(brain_path)
    metrics = calculate_metrics(brain_path)
    value_ratio = calculate_value_ratio(brain_path)
    
    time_saved = ledger.get("estimated_time_saved_minutes", 0)
    overrides = ledger.get("manual_overrides_count", 0)
    
    # Estimate: each auto-archived item saves ~5 mins of mental overhead
    auto_archive_savings = metrics.get("archived_count", 0) * 5
    total_time_saved = time_saved + auto_archive_savings
    
    return {
        "velocity_7d": metrics.get("velocity_7d", 0),
        "avg_days_to_close": metrics.get("avg_days_to_close", 0),
        "value_ratio": value_ratio,
        "estimated_time_saved_hours": round(total_time_saved / 60, 1),
        "manual_overrides": overrides,
        "friction_score": "HIGH" if overrides > 5 else "MEDIUM" if overrides > 2 else "LOW"
    }

def get_days_since_interaction(brain_path: Path) -> int:
    """Get days since last user interaction (MDR_010)"""
    ledger = load_ledger(brain_path)
    last = ledger.get("last_interaction")
    if not last:
        return -1  # Never interacted
    
    last_dt = datetime.fromisoformat(last)
    return (datetime.now() - last_dt).days

def check_kill_switch(brain_path: Path) -> Dict:
    """Check if Kill Switch should activate (MDR_010)"""
    ledger = load_ledger(brain_path)
    days = get_days_since_interaction(brain_path)
    paused = ledger.get("notifications_paused", False)
    
    if paused:
        return {"action": "paused", "message": "Notifications already paused by user"}
    
    if days >= 14:
        return {
            "action": "escalate",
            "message": f"No interaction for {days} days. Send kill switch prompt.",
            "days_inactive": days
        }
    elif days >= 7:
        return {
            "action": "warn",
            "message": f"Low engagement ({days} days). Consider reducing frequency.",
            "days_inactive": days
        }
    else:
        return {"action": "continue", "days_inactive": days}

def pause_notifications(brain_path: Path) -> None:
    """Pause all notifications (Kill Switch activated)"""
    with get_lock("ledger", brain_path).section():
        ledger = load_ledger(brain_path)
        ledger["notifications_paused"] = True
        save_ledger(brain_path, ledger)

def resume_notifications(brain_path: Path) -> None:
    """Resume notifications after pause"""
    with get_lock("ledger", brain_path).section():
        ledger = load_ledger(brain_path)
        ledger["notifications_paused"] = False
        save_ledger(brain_path, ledger)

def get_feedback_path(brain_path: Path) -> Path:
    """Get path to feedback log"""
    return brain_path / "commitments" / "feedback_log.json"

def load_feedback(brain_path: Path) -> List[Dict]:
    """Load feedback log"""
    path = get_feedback_path(brain_path)
    if brain_file_exists(path):
        return json.loads(read_brain_file(path))
    return []

def save_feedback(brain_path: Path, feedback: List[Dict]) -> None:
    """Save feedback log"""
    path = get_feedback_path(brain_path)
    write_brain_file(path, json.dumps(feedback, indent=2))

def record_feedback(
    brain_path: Path,
    notification_type: str,
    score: int,
    response_time_seconds: int = None
) -> Dict:
    """Record user feedback on a notification (MDR_010)"""
    # Feedback log also needs locking if simultaneous
    with get_lock("feedback", brain_path).section():
        feedback = load_feedback(brain_path)
        
        entry = {
            "timestamp": datetime.now().isoformat(),
            "notification_type": notification_type,
            "score": score,  # 1-5 or 0/1 for Y/N
            "response_time_seconds": response_time_seconds
        }
        
        feedback.append(entry)
        save_feedback(brain_path, feedback)
    
    # Also record interaction
    record_interaction(brain_path)
    
    # If positive feedback (4-5 or 1 for Y/N), mark as high impact
    if score >= 4 or score == 1:
        mark_high_impact_closure(brain_path)
    
    return entry


# ============================================================
# LIBRARIAN LOGIC (Moved from nightly_agent.py)
# ============================================================

def scan_for_commitments(brain_path: Path) -> Dict:
    """
    Scan artifacts for new commitments using ripgrep.
    Returns stats of scan.
    """
    # Scan artifacts folder (was artifacts_path, now root to catch task.md)
    artifacts_path = brain_path
    
    # Scan for checklist items
    try:
        result = subprocess.run(
            ["rg", "--type", "md", "-n", "--no-heading", "--glob", "!*.resolved.*", "--glob", "!*.resolved", "--glob", "!archive/*", "--glob", "!SPEC_*.md", "--glob", "!NUCLEUS_VISION.md", "--", r"- \[ \]", str(artifacts_path)],
            capture_output=True,
            text=True
        )
        
        count = 0
        if result.stdout:
            ledger = load_ledger(brain_path)
            
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                
                parts = line.split(':', 2)
                if len(parts) >= 3:
                    file_path = parts[0]
                    # Robust parsing for line number
                    try:
                        line_num = int(parts[1])
                    except ValueError:
                        continue

                    # Content is the rest
                    content = parts[2]

                    description = content.strip().replace('- [ ]', '').strip()
                    
                    # Check if already in ledger
                    existing = any(
                        c["source_file"] == file_path and 
                        c["source_line"] == int(line_num) and 
                        c["status"] == "open"
                        for c in ledger["commitments"]
                    )
                    
                    if not existing:
                        add_commitment(
                            brain_path, 
                            file_path, 
                            int(line_num), 
                            description, 
                            "checklist_item",
                            source="scanned"
                        )
                        count += 1
                        
    except Exception as e:
        print(f"Checklist scan failed: {e}")
        return {"error": str(e)}
    
    # Update ages for all
    update_commitment_ages(brain_path)
    
    return {"new_found": count}

def auto_archive_stale(brain_path: Path) -> int:
    """
    Automatically archive commitments older than 30 days.
    Returns count of archived items.
    """
    ledger = load_ledger(brain_path)
    archived_count = 0
    
    for comm in ledger["commitments"]:
        if comm["status"] == "open":
            # Ensure age is set
            created = datetime.fromisoformat(comm["created"])
            age_days = (datetime.now() - created).days
            
            if age_days > 30:
                comm["status"] = "closed"
                comm["closed_at"] = datetime.now().isoformat()
                comm["closed_method"] = "auto_archived"
                archived_count += 1
    
    if archived_count > 0:
        save_ledger(brain_path, ledger)
        
    return archived_count


# ============================================================
# IP STRATEGY (MDR_008)
# ============================================================

def load_brainignore(brain_path: Path) -> List[str]:
    """Load matching patterns from .brain/.brainignore"""
    ignore_file = brain_path / ".brainignore"
    patterns = []
    
    if brain_file_exists(ignore_file):
        for line in read_brain_file(ignore_file).splitlines():
            line = line.strip()
            if line and not line.startswith('#'):
                patterns.append(line)
                
    # Add default safety ignores if not present
    defaults = [".DS_Store", "__pycache__", "*.pyc", "*.git*"]
    for d in defaults:
        if d not in patterns:
            patterns.append(d)
            
    return patterns

def export_brain(brain_path: Path) -> str:
    """
    Export brain content to a zip file, respecting .brainignore.
    Returns path to export file.
    """
    import zipfile
    import fnmatch
    import os
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    export_dir = brain_path / "exports"
    export_dir.mkdir(parents=True, exist_ok=True)
    
    export_file = export_dir / f"brain_export_{timestamp}.zip"
    
    ignore_patterns = load_brainignore(brain_path)
    # Also ignore the exports directory itself to prevent recursion loops
    ignore_patterns.append("exports/*")
    
    file_count = 0
    
    with zipfile.ZipFile(export_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(brain_path):
            Path(root).relative_to(brain_path)
            
            # Skip hidden dirs (like .git) if configured, but allow .brain itself
            # .brainignore handles specific exclusions
            
            for file in files:
                file_path = Path(root) / file
                rel_path = file_path.relative_to(brain_path)
                str_path = str(rel_path)
                
                # Check ignores
                ignored = False
                for pattern in ignore_patterns:
                    if fnmatch.fnmatch(str_path, pattern) or fnmatch.fnmatch(file, pattern):
                        ignored = True
                        break
                
                if not ignored:
                    zipf.write(file_path, arcname=str_path)
                    file_count += 1
                    
    return f"Exported {file_count} files to {export_file.name}"






