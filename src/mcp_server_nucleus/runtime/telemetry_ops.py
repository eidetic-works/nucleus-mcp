"""
Nucleus Runtime - Telemetry Operations (MDR_010)
================================================
Core logic for usage telemetry, value ratio, and kill switch.
Moves MDR_010 compliance tools out of __init__.py.
"""


# Relative import from parent package (mcp_server_nucleus)
from .. import commitment_ledger
from .common import get_brain_path

def _brain_record_interaction_impl() -> str:
    """Record a user interaction timestamp (MDR_010)."""
    try:
        brain = get_brain_path()
        commitment_ledger.record_interaction(brain)
        return "✅ Interaction recorded"
    except Exception as e:
        return f"Error: {e}"

def _brain_value_ratio_impl() -> str:
    """Get the Value Ratio metric (MDR_010)."""
    try:
        brain = get_brain_path()
        ratio = commitment_ledger.calculate_value_ratio(brain)
        output = "## 📊 Value Ratio (MDR_010)\n\n"
        output += f"**Notifications Sent:** {ratio['notifications_sent']}\n"
        output += f"**High Impact Closures:** {ratio['high_impact_closed']}\n"
        output += f"**Ratio:** {ratio['ratio']}\n"
        output += f"**Verdict:** {ratio['verdict']}\n"
        return output
    except Exception as e:
        return f"Error: {e}"

def _brain_check_kill_switch_impl() -> str:
    """Check Kill Switch status (MDR_010)."""
    try:
        brain = get_brain_path()
        status = commitment_ledger.check_kill_switch(brain)
        output = "## 🛑 Kill Switch Status (MDR_010)\n\n"
        output += f"**Action:** {status['action']}\n"
        output += f"**Message:** {status.get('message', 'N/A')}\n"
        if 'days_inactive' in status:
            output += f"**Days Inactive:** {status['days_inactive']}\n"
        return output
    except Exception as e:
        return f"Error: {e}"

def _brain_pause_notifications_impl() -> str:
    """Pause all PEFS notifications (Kill Switch activation)."""
    try:
        brain = get_brain_path()
        commitment_ledger.pause_notifications(brain)
        return "🛑 Notifications paused. Use brain_resume_notifications() to restart."
    except Exception as e:
        return f"Error: {e}"

def _brain_resume_notifications_impl() -> str:
    """Resume PEFS notifications after pause."""
    try:
        brain = get_brain_path()
        commitment_ledger.resume_notifications(brain)
        commitment_ledger.record_interaction(brain)
        return "✅ Notifications resumed. Interaction recorded."
    except Exception as e:
        return f"Error: {e}"

def _brain_record_feedback_impl(notification_type: str, score: int) -> str:
    """Record user feedback on a notification (MDR_010)."""
    try:
        brain = get_brain_path()
        commitment_ledger.record_feedback(brain, notification_type, score)
        if score >= 4:
            msg = "✅ Positive feedback recorded. Marked as high-impact."
        elif score >= 2:
            msg = "📝 Neutral feedback recorded."
        else:
            msg = "😔 Negative feedback recorded. Will try to improve."
        return msg
    except Exception as e:
        return f"Error: {e}"

def _brain_mark_high_impact_impl() -> str:
    """Manually mark a loop closure as high-impact (MDR_010)."""
    try:
        brain = get_brain_path()
        commitment_ledger.mark_high_impact_closure(brain)
        return "✅ Marked as high-impact closure. Value ratio updated."
    except Exception as e:
        return f"Error: {e}"
