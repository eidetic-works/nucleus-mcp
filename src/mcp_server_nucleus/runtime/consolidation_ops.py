"""
Consolidation Operations - Brain artifact archival, redundancy detection, merge proposals,
and task garbage collection.

Extracted from __init__.py monolith (v1.0.7 decomposition).
"""

import json
import time
import logging
from typing import Dict, List
from pathlib import Path

from .common import get_brain_path
from .event_ops import _emit_event

logger = logging.getLogger("nucleus.consolidation")


def _get_archive_path() -> Path:
    """Get the path to the archive directory."""
    brain = get_brain_path()
    archive_path = brain / "archive"
    archive_path.mkdir(parents=True, exist_ok=True)
    return archive_path


def _archive_resolved_files() -> Dict:
    """Archive all .resolved.* backup files to archive/resolved/.
    
    These are version snapshot files created by Antigravity when editing.
    Moving them clears visual clutter while preserving file history.
    
    Returns:
        Dict with moved count, archive path, and list of moved files
    """
    try:
        brain = get_brain_path()
        archive_dir = _get_archive_path() / "resolved"
        archive_dir.mkdir(parents=True, exist_ok=True)
        
        moved_files = []
        skipped_files = []
        
        # Find all .resolved.* files (pattern: *.resolved or *.resolved.N)
        for f in brain.glob("*.resolved*"):
            if f.is_file():
                try:
                    dest = archive_dir / f.name
                    # Handle duplicate names in archive
                    if dest.exists():
                        base = f.stem
                        suffix = f.suffix
                        counter = 1
                        while dest.exists():
                            dest = archive_dir / f"{base}.dup{counter}{suffix}"
                            counter += 1
                    
                    f.rename(dest)
                    moved_files.append(f.name)
                except Exception as e:
                    skipped_files.append({"file": f.name, "error": str(e)})
        
        # Also check for metadata.json files (Antigravity auto-generated)
        for f in brain.glob("*.metadata.json"):
            if f.is_file():
                try:
                    dest = archive_dir / f.name
                    if dest.exists():
                        base = f.stem
                        suffix = f.suffix
                        counter = 1
                        while dest.exists():
                            dest = archive_dir / f"{base}.dup{counter}{suffix}"
                            counter += 1
                    
                    f.rename(dest)
                    moved_files.append(f.name)
                except Exception as e:
                    skipped_files.append({"file": f.name, "error": str(e)})
        
        # Log the consolidation event
        if moved_files:
            _emit_event(
                "brain_consolidated",
                "BRAIN_CONSOLIDATION",
                {
                    "tier": 1,
                    "action": "archive_resolved",
                    "files_moved": len(moved_files),
                    "archive_path": str(archive_dir)
                },
                f"Archived {len(moved_files)} resolved/metadata files"
            )
        
        return {
            "success": True,
            "files_moved": len(moved_files),
            "files_skipped": len(skipped_files),
            "archive_path": str(archive_dir),
            "moved_files": moved_files[:20],  # Limit output size
            "skipped_files": skipped_files,
            "message": f"Archived {len(moved_files)} files to {archive_dir}"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def _detect_redundant_artifacts() -> Dict:
    """Detect potentially redundant artifacts based on filename patterns.
    
    Looks for:
    1. Versioned duplicates (file.md vs FILE_V0_4_0.md)
    2. Related synthesis docs (SYNTHESIS_PART1, SYNTHESIS_PART2, etc.)
    3. Stale files (not modified in 30+ days, no references)
    
    Returns:
        Dict with categorized redundancy findings
    """
    try:
        brain = get_brain_path()
        
        findings = {
            "versioned_duplicates": [],
            "related_series": [],
            "stale_files": [],
            "archive_candidates": []
        }
        
        all_files = list(brain.glob("*.md"))
        
        # 1. Detect versioned duplicates
        # e.g., implementation_plan.md vs IMPLEMENTATION_PLAN_V0_4_0.md
        version_patterns = ["_v0", "_v1", "_v2", "_v3", "_v4", "_v5"]
        processed = set()
        
        for f in all_files:
            stem = f.stem.lower()
            
            # Skip if already processed
            if f.name in processed:
                continue
                
            # Check for versioned variant
            for vp in version_patterns:
                if vp in stem:
                    # This IS the versioned file, find the unversioned
                    base_name = stem.split(vp)[0].replace("_", "").strip()
                    
                    # Look for potential match
                    for other_f in all_files:
                        other_stem = other_f.stem.lower().replace("_", "")
                        if other_f != f and base_name in other_stem and vp not in other_f.stem.lower():
                            findings["versioned_duplicates"].append({
                                "old": other_f.name,
                                "new": f.name,
                                "reason": "Versioned file likely supersedes unversioned",
                                "suggestion": "Archive old, keep new"
                            })
                            processed.add(other_f.name)
                            processed.add(f.name)
                            break
        
        # 2. Detect related series (SYNTHESIS_PART1, SYNTHESIS_PART2, etc.)
        series_patterns = {
            "SYNTHESIS_PART": [],
            "RAW_MONOLOGUE_PART": [],
            "DESIGN_": [],
        }
        
        for f in all_files:
            for pattern in series_patterns:
                if pattern in f.stem:
                    series_patterns[pattern].append(f.name)
        
        for pattern, files in series_patterns.items():
            if len(files) > 2:
                findings["related_series"].append({
                    "pattern": pattern,
                    "files": files[:5],  # Limit to first 5
                    "count": len(files),
                    "reason": f"{len(files)} related files in series",
                    "suggestion": f"Consider consolidating into single {pattern.replace('_', '')}ALL.md"
                })
        
        # 3. Detect stale files (30+ days old)
        thirty_days_ago = time.time() - (30 * 24 * 60 * 60)
        
        for f in all_files:
            if f.stat().st_mtime < thirty_days_ago:
                # Skip key preserved files
                preserved = ["NORTH_STAR", "task", "README", "PROTOCOL"]
                if any(p in f.stem for p in preserved):
                    continue
                    
                findings["stale_files"].append({
                    "file": f.name,
                    "last_modified": time.strftime("%Y-%m-%d", time.localtime(f.stat().st_mtime)),
                    "reason": "Not modified in 30+ days",
                    "suggestion": "Review for archiving"
                })
        
        # 4. Archive candidates (temp files, completed work)
        archive_keywords = ["_exploration", "_proposal", "_draft", "_temp", "_old"]
        for f in all_files:
            stem = f.stem.lower()
            for kw in archive_keywords:
                if kw in stem:
                    findings["archive_candidates"].append({
                        "file": f.name,
                        "keyword": kw,
                        "reason": f"Contains '{kw}' suggesting temporary nature",
                        "suggestion": "Move to archive/"
                    })
                    break
        
        return {
            "success": True,
            "total_files_scanned": len(all_files),
            "findings": findings,
            "summary": {
                "versioned_duplicates": len(findings["versioned_duplicates"]),
                "related_series": len(findings["related_series"]),
                "stale_files": len(findings["stale_files"]),
                "archive_candidates": len(findings["archive_candidates"])
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def _generate_merge_proposals() -> Dict:
    """Generate human-readable merge proposal document.
    
    Runs detection and formats results as actionable proposals.
    Does NOT execute any merges - proposals only.
    
    Returns:
        Dict with proposal_text and structured data
    """
    try:
        detection_result = _detect_redundant_artifacts()
        
        if not detection_result.get("success"):
            return detection_result
        
        findings = detection_result.get("findings", {})
        summary = detection_result.get("summary", {})
        
        # Generate markdown proposal
        today = time.strftime("%Y-%m-%d")
        lines = [
            "# Brain Consolidation Proposals",
            "",
            f"> **Generated:** {today}  ",
            "> **Status:** Awaiting human review  ",
            "> **Action:** None taken - proposals only",
            "",
            "---",
            "",
        ]
        
        # Summary
        total_proposals = sum(summary.values())
        lines.append("## Summary")
        lines.append("")
        lines.append("| Category | Count |")
        lines.append("|:---------|:------|")
        lines.append(f"| Versioned Duplicates | {summary.get('versioned_duplicates', 0)} |")
        lines.append(f"| Related Series | {summary.get('related_series', 0)} |")
        lines.append(f"| Stale Files (30+ days) | {summary.get('stale_files', 0)} |")
        lines.append(f"| Archive Candidates | {summary.get('archive_candidates', 0)} |")
        lines.append(f"| **Total Proposals** | **{total_proposals}** |")
        lines.append("")
        
        if total_proposals == 0:
            lines.append("✅ **Brain is clean!** No consolidation needed.")
            return {
                "success": True,
                "total_proposals": 0,
                "proposal_text": "\n".join(lines),
                "findings": findings
            }
        
        lines.append("---")
        lines.append("")
        
        # Versioned duplicates section
        if findings.get("versioned_duplicates"):
            lines.append("## Versioned Duplicates")
            lines.append("")
            lines.append("These files appear to have old/new versions. Consider archiving the old one.")
            lines.append("")
            for i, dup in enumerate(findings["versioned_duplicates"], 1):
                lines.append(f"### {i}. {dup['old']}")
                lines.append(f"- **Old:** `{dup['old']}`")
                lines.append(f"- **New:** `{dup['new']}`")
                lines.append(f"- **Reason:** {dup['reason']}")
                lines.append(f"- **Suggestion:** {dup['suggestion']}")
                lines.append("")
        
        # Related series section
        if findings.get("related_series"):
            lines.append("## Related File Series")
            lines.append("")
            lines.append("These files form related series that could potentially be consolidated.")
            lines.append("")
            for i, series in enumerate(findings["related_series"], 1):
                lines.append(f"### {i}. {series['pattern']}* ({series['count']} files)")
                lines.append(f"- **Pattern:** `{series['pattern']}*`")
                lines.append(f"- **Files:** {', '.join(['`' + f + '`' for f in series['files']])}")
                if series['count'] > 5:
                    lines.append(f"  - ... and {series['count'] - 5} more")
                lines.append(f"- **Suggestion:** {series['suggestion']}")
                lines.append("")
        
        # Stale files section
        if findings.get("stale_files"):
            lines.append("## Stale Files (30+ Days Old)")
            lines.append("")
            lines.append("These files haven't been modified in 30+ days. Review if still relevant.")
            lines.append("")
            for i, stale in enumerate(findings["stale_files"][:10], 1):  # Limit to 10
                lines.append(f"{i}. `{stale['file']}` - Last modified: {stale['last_modified']}")
            if len(findings["stale_files"]) > 10:
                lines.append(f"   ... and {len(findings['stale_files']) - 10} more")
            lines.append("")
        
        # Archive candidates section
        if findings.get("archive_candidates"):
            lines.append("## Archive Candidates")
            lines.append("")
            lines.append("These files contain keywords suggesting they're temporary work.")
            lines.append("")
            for i, cand in enumerate(findings["archive_candidates"][:10], 1):
                lines.append(f"{i}. `{cand['file']}` - Contains '{cand['keyword']}'")
            if len(findings["archive_candidates"]) > 10:
                lines.append(f"   ... and {len(findings['archive_candidates']) - 10} more")
            lines.append("")
        
        # Next steps section
        lines.append("---")
        lines.append("")
        lines.append("## Next Steps")
        lines.append("")
        lines.append("1. Review proposals above")
        lines.append("2. To archive files, run: `nucleus consolidate archive`")
        lines.append("3. To manually move files: `mv file.md .brain/archive/`")
        lines.append("4. Tier 3 (Execute Merges) coming soon...")
        lines.append("")
        
        proposal_text = "\n".join(lines)
        
        # Log event
        _emit_event(
            "merge_proposals_generated",
            "BRAIN_CONSOLIDATION",
            {
                "tier": 2,
                "total_proposals": total_proposals,
                "categories": summary
            },
            f"Generated {total_proposals} consolidation proposals"
        )
        
        return {
            "success": True,
            "total_proposals": total_proposals,
            "proposal_text": proposal_text,
            "findings": findings,
            "summary": summary
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def _garbage_collect_tasks(
    max_age_hours: int = 72,
    dry_run: bool = False
) -> Dict:
    """Archive stale tasks that have had no activity for max_age_hours.
    
    Targets:
    - PENDING tasks with no update in 72+ hours
    - Auto-generated tasks (id starts with 'auto_')
    - Duplicate descriptions (keeps newest)
    
    Does NOT touch:
    - IN_PROGRESS tasks (someone is working on them)
    - DONE tasks (historical record)
    - Tasks updated within the window
    
    Args:
        max_age_hours: Hours of inactivity before a task is considered stale (default 72)
        dry_run: If True, report what would be archived without doing it
    
    Returns:
        Dict with archived count, kept count, and details
    """
    try:
        brain = get_brain_path()
        tasks_file = brain / "ledger" / "tasks.json"
        
        if not tasks_file.exists():
            return {"success": True, "archived": 0, "kept": 0, "message": "No tasks.json found"}
        
        with open(tasks_file, "r") as f:
            raw = json.load(f)
        
        # Handle both list and object formats
        if isinstance(raw, list):
            tasks = raw
        elif isinstance(raw, dict) and "tasks" in raw:
            tasks = raw["tasks"]
        else:
            tasks = []
        
        if not tasks:
            return {"success": True, "archived": 0, "kept": 0, "message": "No tasks to process"}
        
        cutoff = time.time() - (max_age_hours * 3600)
        cutoff_iso = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(cutoff))
        
        keep = []
        archive = []
        dedup_seen = {}
        
        for task in tasks:
            if not isinstance(task, dict):
                continue
            
            task_id = task.get("id", "")
            status = task.get("status", "").upper()
            description = task.get("description", "")
            updated_at = task.get("updated_at", task.get("created_at", ""))
            
            # Never archive IN_PROGRESS or DONE tasks
            if status in ("IN_PROGRESS", "DONE", "COMPLETED"):
                keep.append(task)
                continue
            
            # Check for auto-generated noise (auto_* IDs)
            is_auto = task_id.startswith("auto_")
            
            # Check staleness by comparing updated_at string
            is_stale = False
            if updated_at and updated_at < cutoff_iso:
                is_stale = True
            
            # Check for duplicate descriptions (keep newest)
            desc_key = description.strip().lower()[:100]
            if desc_key in dedup_seen:
                # This is a duplicate — archive the older one
                existing_updated = dedup_seen[desc_key].get("updated_at", "")
                if updated_at > existing_updated:
                    # Current is newer, archive the old one
                    archive.append(dedup_seen[desc_key])
                    dedup_seen[desc_key] = task
                else:
                    # Current is older, archive it
                    archive.append(task)
                    continue
            else:
                dedup_seen[desc_key] = task
            
            # Archive if stale OR auto-generated
            if is_stale or is_auto:
                archive.append(task)
                if desc_key in dedup_seen and dedup_seen[desc_key] is task:
                    del dedup_seen[desc_key]
            else:
                keep.append(task)
        
        # Add remaining dedup survivors to keep
        for desc_key, task in dedup_seen.items():
            if task not in keep and task not in archive:
                keep.append(task)
        
        if not dry_run and archive:
            # Save archived tasks to archive/tasks_archived_YYYYMMDD.jsonl
            archive_dir = _get_archive_path() / "tasks"
            archive_dir.mkdir(parents=True, exist_ok=True)
            archive_file = archive_dir / f"tasks_archived_{time.strftime('%Y%m%d_%H%M%S')}.jsonl"
            
            with open(archive_file, "w") as f:
                for task in archive:
                    f.write(json.dumps(task) + "\n")
            
            # Write back the kept tasks
            if isinstance(raw, dict) and "tasks" in raw:
                raw["tasks"] = keep
                with open(tasks_file, "w") as f:
                    json.dump(raw, f, indent=2)
            else:
                with open(tasks_file, "w") as f:
                    json.dump(keep, f, indent=2)
            
            _emit_event(
                "tasks_garbage_collected",
                "BRAIN_CONSOLIDATION",
                {
                    "archived": len(archive),
                    "kept": len(keep),
                    "max_age_hours": max_age_hours,
                    "archive_file": str(archive_file)
                },
                f"Garbage collected {len(archive)} stale tasks, kept {len(keep)}"
            )
        
        # Categorize archived tasks for reporting
        auto_count = sum(1 for t in archive if t.get("id", "").startswith("auto_"))
        stale_count = len(archive) - auto_count
        
        return {
            "success": True,
            "archived": len(archive),
            "kept": len(keep),
            "dry_run": dry_run,
            "breakdown": {
                "auto_generated": auto_count,
                "stale": stale_count
            },
            "sample_archived": [
                {"id": t.get("id"), "description": t.get("description", "")[:60]}
                for t in archive[:10]
            ],
            "message": f"{'Would archive' if dry_run else 'Archived'} {len(archive)} tasks, kept {len(keep)}"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
