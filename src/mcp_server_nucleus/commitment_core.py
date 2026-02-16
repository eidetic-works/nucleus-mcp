import logging
from typing import Dict
from . import commitment_ledger
from . import get_brain_path, _emit_event

logger = logging.getLogger(__name__)


def _scan_commitments() -> Dict:
    """
    Scan artifacts for commitments (checklists, TODOs, drafts, decisions).
    Returns scan results with commitment count.
    """
    import subprocess
    
    try:
        brain = get_brain_path()
        artifacts_path = brain / "artifacts"
        
        # Scan for checklist items
        try:
            result = subprocess.run(
                ["rg", r"- \[ \]", str(artifacts_path), "--type", "md", "-n"],
                capture_output=True,
                text=True
            )
            
            if result.stdout:
                for line in result.stdout.strip().split('\n'):
                    if not line:
                        continue
                    
                    # Parse: file:line:content
                    parts = line.split(':', 2)
                    if len(parts) == 3:
                        file_path, line_num, content = parts
                        description = content.strip().replace('- [ ]', '').strip()
                        
                        # Check if already in ledger
                        ledger = commitment_ledger.load_ledger(brain)
                        existing = any(
                            c["source_file"] == file_path and 
                            c["source_line"] == int(line_num) and 
                            c["status"] == "open"
                            for c in ledger["commitments"]
                        )
                        
                        if not existing:
                            commitment_ledger.add_commitment(
                                brain, file_path, int(line_num), 
                                description, "checklist_item"
                            )
        except Exception as e:
            logger.warning(f"Checklist scan failed: {e}")
        
        # Update ages for all commitments
        ledger = commitment_ledger.update_commitment_ages(brain)
        
        # Emit event
        _emit_event(
            "commitment_scan_complete",
            "commitment_ledger",
            {
                "total_open": ledger["stats"]["total_open"],
                "red_tier": ledger["stats"]["red_tier"]
            },
            description=f"Scanned artifacts, found {ledger['stats']['total_open']} open commitments"
        )
        
        return {
            "success": True,
            "stats": ledger["stats"],
            "last_scan": ledger["last_scan"]
        }
    except Exception as e:
        return {" error": str(e)}

def _list_commitments(tier: str = None) -> Dict:
    """List all open commitments, optionally filtered by tier."""
    try:
        brain = get_brain_path()
        commitments = commitment_ledger.get_open_commitments(brain, tier)
        
        return {
            "success": True,
            "commitments": commitments,
            "count": len(commitments)
        }
    except Exception as e:
        return {"error": str(e)}

def _close_commitment(comm_id: str, method: str) -> Dict:
    """Close a commitment with specified method."""
    try:
        brain = get_brain_path()
        commitment = commitment_ledger.close_commitment(brain, comm_id, method)
        
        # Emit event
        _emit_event(
            "commitment_closed",
            "user",
            {
                "commitment_id": comm_id,
                "method": method,
                "description": commitment["description"]
            },
            description=f"Closed commitment: {commitment['description']}"
        )
        
        return {
            "success": True,
            "commitment": commitment
        }
    except Exception as e:
        return {"error": str(e)}

def _get_commitment_health() -> Dict:
    """Get commitment health summary for Satellite View."""
    try:
        brain = get_brain_path()
        ledger = commitment_ledger.load_ledger(brain)
        
        stats = ledger.get("stats", {})
        total = stats.get("total_open", 0)
        green = stats.get("green_tier", 0)
        yellow = stats.get("yellow_tier", 0)
        red = stats.get("red_tier", 0)
        
        # Determine health status
        if red > 0:
            health = "🔴 NEEDS ATTENTION"
        elif yellow > 2:
            health = "🟡 WATCH"
        else:
            health = "🟢 HEALTHY"
        
        return {
            "total_open": total,
            "green": green,
            "yellow": yellow,
            "red": red,
            "health_status": health,
            "last_scan": ledger.get("last_scan")
        }
    except Exception as e:
        return {"error": str(e)}
