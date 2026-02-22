"""Checkpoint Operations — Pause/Resume for long-running tasks.

Extracted from __init__.py (NOP V3.1 Checkpoint Tools).
Contains:
- _brain_checkpoint_task_impl
- _brain_resume_from_checkpoint_impl
- _brain_generate_handoff_summary_impl
"""

from typing import List


def _lazy(name):
    import mcp_server_nucleus as m
    return getattr(m, name)


def _brain_checkpoint_task_impl(
    task_id: str,
    step: int = None,
    progress_percent: float = None,
    context: str = None,
    artifacts: List[str] = None,
    resumable: bool = True
) -> str:
    """Internal implementation of brain_checkpoint_task - directly callable."""
    try:
        get_orch = _lazy("get_orch")
        orch = get_orch()
        
        checkpoint_data = {
            "step": step,
            "progress_percent": progress_percent,
            "context": context,
            "artifacts": artifacts or [],
            "resumable": resumable
        }
        
        # Remove None values
        checkpoint_data = {k: v for k, v in checkpoint_data.items() if v is not None}
        
        result = orch.checkpoint_task(task_id, checkpoint_data)
        
        if result.get("success"):
            output = f"✅ Checkpoint saved for task {task_id}\n"
            output += f"   Step: {step or 'N/A'}\n"
            output += f"   Progress: {progress_percent or 'N/A'}%\n"
            output += f"   Resumable: {resumable}\n"
            if artifacts:
                output += f"   Artifacts: {len(artifacts)} files\n"
            output += f"\n💡 To resume: brain_resume_from_checkpoint('{task_id}')"
            return output
        else:
            return f"❌ Checkpoint failed: {result.get('error')}"
            
    except Exception as e:
        return f"❌ Checkpoint error: {str(e)}"


def _brain_resume_from_checkpoint_impl(task_id: str) -> str:
    """Internal implementation of brain_resume_from_checkpoint - directly callable."""
    try:
        get_orch = _lazy("get_orch")
        orch = get_orch()
        result = orch.resume_from_checkpoint(task_id)
        
        if result.get("success"):
            checkpoint = result.get("checkpoint", {})
            data = checkpoint.get("data", {})
            context_summary = result.get("context_summary")
            
            output = f"📋 Resume Instructions for {task_id}\n"
            output += "=" * 50 + "\n\n"
            
            output += "## Checkpoint Data\n"
            output += f"   Last checkpoint: {checkpoint.get('last_checkpoint_at', 'N/A')}\n"
            output += f"   Step: {data.get('step', 'N/A')}\n"
            output += f"   Progress: {data.get('progress_percent', 'N/A')}%\n"
            output += f"   Resumable: {data.get('resumable', True)}\n"
            
            if data.get("context"):
                output += f"\n## Context\n{data.get('context')}\n"
            
            if data.get("artifacts"):
                output += "\n## Artifacts Created\n"
                for a in data["artifacts"]:
                    output += f"   - {a}\n"
            
            if context_summary:
                output += f"\n## Previous Summary\n{context_summary.get('summary', 'N/A')}\n"
                if context_summary.get("key_decisions"):
                    output += "\n## Key Decisions\n"
                    for d in context_summary["key_decisions"]:
                        output += f"   - {d}\n"
            
            output += f"\n{result.get('resume_instructions', '')}"
            return output
        else:
            return f"❌ Resume failed: {result.get('error')}"
            
    except Exception as e:
        return f"❌ Resume error: {str(e)}"


def _brain_generate_handoff_summary_impl(
    task_id: str,
    summary: str,
    key_decisions: List[str] = None,
    handoff_notes: str = ""
) -> str:
    """Internal implementation of brain_generate_handoff_summary - directly callable."""
    try:
        get_orch = _lazy("get_orch")
        orch = get_orch()
        result = orch.generate_context_summary(
            task_id, summary, key_decisions or [], handoff_notes
        )
        
        if result.get("success"):
            output = f"✅ Handoff summary generated for {task_id}\n"
            output += f"   Summary length: {len(summary)} chars\n"
            output += f"   Key decisions: {len(key_decisions or [])} items\n"
            if handoff_notes:
                output += f"   Handoff notes: {len(handoff_notes)} chars\n"
            return output
        else:
            return f"❌ Summary generation failed: {result.get('error')}"
            
    except Exception as e:
        return f"❌ Summary error: {str(e)}"
