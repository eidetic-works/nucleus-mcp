"""Skill Registry — Catalog of generated skills with metadata.

Append-only JSONL storage at .brain/skills/registry.jsonl.
Last entry per skill_id wins (same pattern as goals.jsonl).
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("nucleus.skill_registry")


class SkillRegistry:
    """Append-only catalog of extracted skills."""

    def __init__(self, brain_path: Path):
        self.brain_path = brain_path
        self.skills_dir = brain_path / "skills"
        self.generated_dir = self.skills_dir / "generated"
        self.registry_file = self.skills_dir / "registry.jsonl"
        # Auto-create dirs on init
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        self.generated_dir.mkdir(parents=True, exist_ok=True)

    def register(
        self,
        skill_id: str,
        name: str,
        version: str,
        score: float,
        skill_md_path: Path,
        source_turn_ids: List[str],
    ) -> dict:
        """Register or update a skill entry. Appends to registry.jsonl."""
        entry = {
            "skill_id": skill_id,
            "name": name,
            "version": version,
            "md_path": str(skill_md_path),
            "source_turns": source_turn_ids[:50],  # cap stored IDs
            "source_turn_count": len(source_turn_ids),
            "score": round(score, 3),
            "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "usage_count": 0,
            "success_count": 0,
            "installed": False,
        }
        with open(self.registry_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        logger.info("Registered skill %s (score=%.3f)", skill_id, score)
        return entry

    def list_skills(
        self,
        min_score: float = 0.0,
        installed_only: bool = False,
    ) -> List[dict]:
        """List registered skills. Deduplicates by skill_id (last entry wins)."""
        all_skills = self._load_all()
        results = list(all_skills.values())

        if min_score > 0:
            results = [s for s in results if s.get("score", 0) >= min_score]
        if installed_only:
            results = [s for s in results if s.get("installed")]

        results.sort(key=lambda s: s.get("score", 0), reverse=True)
        return results

    def get_skill(self, skill_id: str) -> Optional[dict]:
        """Get a single skill entry by ID."""
        all_skills = self._load_all()
        return all_skills.get(skill_id)

    def update_usage(self, skill_id: str, success: bool):
        """Increment usage_count (and success_count if success=True).

        Writes a new entry with updated counts (append-only, last wins).
        """
        skill = self.get_skill(skill_id)
        if not skill:
            logger.warning("Cannot update usage for unknown skill: %s", skill_id)
            return
        skill["usage_count"] = skill.get("usage_count", 0) + 1
        if success:
            skill["success_count"] = skill.get("success_count", 0) + 1
        with open(self.registry_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(skill, ensure_ascii=False) + "\n")

    def mark_installed(self, skill_id: str, installed: bool):
        """Update installed status."""
        skill = self.get_skill(skill_id)
        if not skill:
            logger.warning("Cannot mark unknown skill: %s", skill_id)
            return
        skill["installed"] = installed
        with open(self.registry_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(skill, ensure_ascii=False) + "\n")

    def _load_all(self) -> Dict[str, dict]:
        """Read registry.jsonl, return {skill_id: latest_entry}.

        Last entry per skill_id wins (append-only with overwrites).
        """
        if not self.registry_file.exists():
            return {}
        skills: Dict[str, dict] = {}
        with open(self.registry_file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    sid = entry.get("skill_id")
                    if sid:
                        skills[sid] = entry
                except json.JSONDecodeError:
                    continue
        return skills
