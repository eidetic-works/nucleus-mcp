from typing import List
from .capabilities.proof_system import ProofSystem
import json

def _get_proof_system():
    return ProofSystem()

def _brain_generate_proof_impl(
    feature_id: str, 
    thinking: str, 
    deployed_url: str, 
    files_changed: List[str], 
    risk_level: str, 
    rollback_time: str
) -> str:
    """Implement brain_generate_proof."""
    try:
        sys = _get_proof_system()
        args = {
            "feature_id": feature_id,
            "thinking": thinking,
            "deployed_url": deployed_url,
            "files_changed": files_changed,
            "risk_level": risk_level,
            "rollback_time": rollback_time
        }
        result = sys._generate_proof(args)
        return json.dumps(result) if isinstance(result, dict) else str(result)
    except Exception as e:
        return f"Error generating proof: {e}"

def _brain_get_proof_impl(feature_id: str) -> str:
    """Implement brain_get_proof."""
    try:
        sys = _get_proof_system()
        return sys._get_proof(feature_id)
    except Exception as e:
        return f"Error getting proof: {e}"

def _brain_list_proofs_impl() -> List[str]:
    """Implement brain_list_proofs."""
    try:
        sys = _get_proof_system()
        return sys._list_proofs() # Returns List[str] filenames
    except Exception:
        return []
