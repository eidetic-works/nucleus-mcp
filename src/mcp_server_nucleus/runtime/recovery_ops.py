"""
Nucleus Runtime - Recovery Operations
======================================
Universal session recovery workflow for frozen/bloated conversations.
Antigravity-specific helpers; sibling modules cover other IDEs.
"""

import json
import os
import shutil
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import re

from .common import get_brain_path


def _get_antigravity_brain_path() -> Optional[Path]:
    """Get Antigravity brain path if it exists."""
    home = Path.home()
    ag_brain = home / ".gemini" / "antigravity" / "brain"
    if ag_brain.exists():
        return ag_brain
    return None


def _detect_bloated_conversations(threshold_mb: int = 50, file_count_threshold: int = 1000) -> List[Dict[str, Any]]:
    """Detect bloated conversation directories in Antigravity brain.
    
    Args:
        threshold_mb: Size threshold in MB for .pb files
        file_count_threshold: Max file count before flagging as bloated
        
    Returns:
        List of dicts with conversation_id, bloat_type, size_mb, file_count
    """
    ag_brain = _get_antigravity_brain_path()
    if not ag_brain:
        return []
    
    bloated = []
    threshold_bytes = threshold_mb * 1024 * 1024
    
    for conv_dir in ag_brain.iterdir():
        if not conv_dir.is_dir():
            continue
        
        conversation_id = conv_dir.name
        bloat_info = {
            "conversation_id": conversation_id,
            "path": str(conv_dir),
            "bloat_types": [],
            "total_size_mb": 0,
            "file_count": 0,
            "pb_files": []
        }
        
        # Count files and check for large .pb files
        file_count = 0
        total_size = 0
        for item in conv_dir.rglob("*"):
            if item.is_file():
                file_count += 1
                file_size = item.stat().st_size
                total_size += file_size
                
                if item.suffix == ".pb" and file_size > threshold_bytes:
                    bloat_info["pb_files"].append({
                        "name": item.name,
                        "size_mb": round(file_size / (1024 * 1024), 2)
                    })
        
        bloat_info["file_count"] = file_count
        bloat_info["total_size_mb"] = round(total_size / (1024 * 1024), 2)
        
        # Determine bloat types
        if bloat_info["pb_files"]:
            bloat_info["bloat_types"].append("large_protobuf")
        if file_count > file_count_threshold:
            bloat_info["bloat_types"].append("excessive_files")
        
        if bloat_info["bloat_types"]:
            bloated.append(bloat_info)
    
    return bloated


def _extract_conversation_context(conversation_id: str) -> Dict[str, Any]:
    """Extract context from a conversation for inheritance package.
    
    Args:
        conversation_id: UUID of the conversation to extract
        
    Returns:
        Dict with extracted context (tasks, verification, playbook, handoffs)
    """
    ag_brain = _get_antigravity_brain_path()
    if not ag_brain:
        return {"success": False, "error": "Antigravity brain not found"}
    
    conv_dir = ag_brain / conversation_id
    if not conv_dir.exists():
        return {"success": False, "error": f"Conversation {conversation_id} not found"}
    
    context = {
        "conversation_id": conversation_id,
        "extracted_at": datetime.now(timezone.utc).isoformat(),
        "artifacts": {}
    }
    
    # Extract key artifacts
    artifacts_to_extract = [
        "task.md.resolved",
        "task.md",
        "verification_tracker.md",
        "manual_testing_playbook.md",
        "handoffs.jsonl",
        "implementation_plan.md"
    ]
    
    for artifact in artifacts_to_extract:
        artifact_path = conv_dir / artifact
        if artifact_path.exists():
            try:
                content = artifact_path.read_text(encoding="utf-8")
                context["artifacts"][artifact] = {
                    "content": content,
                    "size_bytes": len(content),
                    "lines": len(content.splitlines())
                }
            except Exception as e:
                context["artifacts"][artifact] = {
                    "error": str(e)
                }
    
    context["success"] = True
    return context


def _quarantine_bloated_files(conversation_id: str, create_checksums: bool = True) -> Dict[str, Any]:
    """Move bloated files to quarantine directory with checksums.
    
    Args:
        conversation_id: UUID of the conversation to quarantine
        create_checksums: Whether to create SHA256 checksums for reversibility
        
    Returns:
        Dict with quarantine status and file list
    """
    ag_brain = _get_antigravity_brain_path()
    if not ag_brain:
        return {"success": False, "error": "Antigravity brain not found"}
    
    conv_dir = ag_brain / conversation_id
    if not conv_dir.exists():
        return {"success": False, "error": f"Conversation {conversation_id} not found"}
    
    brain = get_brain_path()
    quarantine_dir = brain / "quarantine" / conversation_id
    quarantine_dir.mkdir(parents=True, exist_ok=True)
    
    quarantined_files = []
    checksums = {}
    
    # Quarantine .pb files and large files
    for item in conv_dir.rglob("*"):
        if not item.is_file():
            continue
        
        # Quarantine .pb files or files >10MB
        if item.suffix == ".pb" or item.stat().st_size > 10 * 1024 * 1024:
            rel_path = item.relative_to(conv_dir)
            dest = quarantine_dir / rel_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            
            # Create checksum if requested
            if create_checksums:
                with open(item, "rb") as f:
                    file_hash = hashlib.sha256(f.read()).hexdigest()
                    checksums[str(rel_path)] = file_hash
            
            # Move file
            shutil.move(str(item), str(dest))
            quarantined_files.append({
                "original": str(item),
                "quarantine": str(dest),
                "size_mb": round(item.stat().st_size / (1024 * 1024), 2)
            })
    
    # Save checksums
    if create_checksums and checksums:
        checksum_file = quarantine_dir / "checksums.json"
        with open(checksum_file, "w", encoding="utf-8") as f:
            json.dump(checksums, f, indent=2)
    
    return {
        "success": True,
        "conversation_id": conversation_id,
        "quarantine_path": str(quarantine_dir),
        "files_quarantined": len(quarantined_files),
        "quarantined_files": quarantined_files,
        "checksums_created": len(checksums)
    }


def _generate_inheritance_package(conversation_id: str, context: Dict[str, Any]) -> str:
    """Generate markdown inheritance package from extracted context.
    
    Args:
        conversation_id: UUID of the source conversation
        context: Extracted context dict from _extract_conversation_context
        
    Returns:
        Markdown string for inheritance package
    """
    package = f"""# Antigravity Context Inheritance Package

**Source Conversation**: `{conversation_id}`
**Extracted**: {context.get('extracted_at', 'Unknown')}

## Extracted Artifacts

"""
    
    artifacts = context.get("artifacts", {})
    
    # Task state
    if "task.md.resolved" in artifacts or "task.md" in artifacts:
        task_key = "task.md.resolved" if "task.md.resolved" in artifacts else "task.md"
        task_content = artifacts[task_key].get("content", "")
        package += f"""### Current Task State
```markdown
{task_content}
```

"""
    
    # Verification tracker
    if "verification_tracker.md" in artifacts:
        tracker_content = artifacts["verification_tracker.md"].get("content", "")
        # Extract first 100 lines for summary
        tracker_lines = tracker_content.splitlines()[:100]
        package += f"""### Verification Progress
```markdown
{chr(10).join(tracker_lines)}
... (truncated, see full file in conversation dir)
```

"""
    
    # Manual testing playbook
    if "manual_testing_playbook.md" in artifacts:
        playbook_content = artifacts["manual_testing_playbook.md"].get("content", "")
        # Extract first 50 lines for summary
        playbook_lines = playbook_content.splitlines()[:50]
        package += f"""### Manual Testing Playbook
```markdown
{chr(10).join(playbook_lines)}
... (truncated, see full file in conversation dir)
```

"""
    
    # Handoffs
    if "handoffs.jsonl" in artifacts:
        handoffs_content = artifacts["handoffs.jsonl"].get("content", "")
        handoff_count = len(handoffs_content.splitlines())
        package += f"""### Session Handoffs
- Total handoffs: {handoff_count}
- See full handoffs log in conversation dir

"""
    
    package += f"""## Recovery Instructions

1. Load this package as context in fresh session
2. Verify UI responsiveness
3. Update test script paths if needed
4. Resume work from task state above

## Source Artifacts Location
`{_get_antigravity_brain_path() / conversation_id if _get_antigravity_brain_path() else 'N/A'}`
"""
    
    return package


def _generate_bootstrap_session(conversation_id: str, inheritance_package: str) -> Dict[str, Any]:
    """Generate fresh session directory with bootstrap context.
    
    Args:
        conversation_id: Source conversation UUID
        inheritance_package: Markdown inheritance package content
        
    Returns:
        Dict with new session ID and bootstrap info
    """
    ag_brain = _get_antigravity_brain_path()
    if not ag_brain:
        return {"success": False, "error": "Antigravity brain not found"}
    
    # Generate new session UUID
    import uuid
    new_session_id = str(uuid.uuid4())
    new_session_dir = ag_brain / new_session_id
    new_session_dir.mkdir(parents=True, exist_ok=True)
    
    # Write bootstrap context
    bootstrap_file = new_session_dir / "BOOTSTRAP_CONTEXT.md"
    bootstrap_file.write_text(inheritance_package, encoding="utf-8")
    
    # Create minimal task.md from inheritance package
    task_md = new_session_dir / "task.md"
    task_md.write_text(f"""# Recovered Session from {conversation_id}

See BOOTSTRAP_CONTEXT.md for full inherited context.

## Recovery Tasks
- [ ] Verify context inheritance
- [ ] Update test script paths if needed
- [ ] Resume work from inherited task state
""", encoding="utf-8")
    
    # Create implementation plan
    impl_plan = new_session_dir / "implementation_plan.md"
    impl_plan.write_text(f"""# Implementation Plan - Recovered Session

**Source**: Conversation `{conversation_id}`
**Recovery Date**: {datetime.now(timezone.utc).isoformat()}

## Context Inheritance
- Bootstrap context loaded from BOOTSTRAP_CONTEXT.md
- Original artifacts preserved in source conversation dir
- Test script paths may need updating to new session ID

## Next Steps
1. Review BOOTSTRAP_CONTEXT.md for full context
2. Update any hardcoded paths in test scripts
3. Resume work from inherited task state
""", encoding="utf-8")
    
    return {
        "success": True,
        "new_session_id": new_session_id,
        "session_path": str(new_session_dir),
        "bootstrap_file": str(bootstrap_file),
        "bootstrap_prompt": f"Fresh session created. Load context from: {bootstrap_file}"
    }


def _rewrite_test_paths(old_conversation_id: str, new_session_id: str, dry_run: bool = False) -> Dict[str, Any]:
    """Rewrite hardcoded conversation paths in test scripts.
    
    Args:
        old_conversation_id: Old conversation UUID to replace
        new_session_id: New session UUID to use
        dry_run: If True, only report changes without applying
        
    Returns:
        Dict with rewrite status and file list
    """
    brain = get_brain_path()
    test_dirs = [
        brain.parent / "mcp-server-nucleus" / "tests",
        brain.parent / "nucleus-mcp" / "tests"
    ]
    
    rewrites = []
    pattern = re.compile(re.escape(old_conversation_id))
    
    for test_dir in test_dirs:
        if not test_dir.exists():
            continue
        
        for py_file in test_dir.glob("*.py"):
            try:
                content = py_file.read_text(encoding="utf-8")
                if old_conversation_id in content:
                    new_content = pattern.sub(new_session_id, content)
                    
                    if not dry_run:
                        py_file.write_text(new_content, encoding="utf-8")
                    
                    rewrites.append({
                        "file": str(py_file),
                        "occurrences": content.count(old_conversation_id),
                        "applied": not dry_run
                    })
            except Exception as e:
                rewrites.append({
                    "file": str(py_file),
                    "error": str(e)
                })
    
    return {
        "success": True,
        "dry_run": dry_run,
        "files_rewritten": len([r for r in rewrites if r.get("applied", False)]),
        "rewrites": rewrites
    }


def _recover_conversation_auto(conversation_id: str) -> Dict[str, Any]:
    """One-shot automatic recovery workflow.
    
    Args:
        conversation_id: UUID of conversation to recover
        
    Returns:
        Dict with full recovery status
    """
    results = {
        "conversation_id": conversation_id,
        "steps": {}
    }
    
    # Step 1: Extract context
    context = _extract_conversation_context(conversation_id)
    results["steps"]["extract"] = context
    if not context.get("success"):
        return results
    
    # Step 2: Generate inheritance package
    package = _generate_inheritance_package(conversation_id, context)
    results["steps"]["package"] = {"success": True, "size": len(package)}
    
    # Step 3: Quarantine bloat
    quarantine = _quarantine_bloated_files(conversation_id)
    results["steps"]["quarantine"] = quarantine
    
    # Step 4: Bootstrap fresh session
    bootstrap = _generate_bootstrap_session(conversation_id, package)
    results["steps"]["bootstrap"] = bootstrap
    if not bootstrap.get("success"):
        return results
    
    # Step 5: Rewrite test paths
    new_session_id = bootstrap["new_session_id"]
    rewrite = _rewrite_test_paths(conversation_id, new_session_id, dry_run=False)
    results["steps"]["rewrite"] = rewrite
    
    results["success"] = True
    results["new_session_id"] = new_session_id
    results["bootstrap_prompt"] = bootstrap["bootstrap_prompt"]
    
    return results
