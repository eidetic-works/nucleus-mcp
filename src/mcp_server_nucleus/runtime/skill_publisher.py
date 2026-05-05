"""Skill Publisher — Install/uninstall generated skills into Claude Code's Skills feature.

Writes to ~/.claude/skills/<name>/SKILL.md (the Skills auto-discovery path),
not ~/.claude/commands/ (which is the slash-command path — different feature).

Discovered empirically via .brain/research/2026-04-28_tier_architecture/03_skill_activation_telemetry.md:
auto-generated skills shipped to ~/.claude/commands/ never auto-activate as Skills.
CC's Skills feature reads ~/.claude/skills/<name>/SKILL.md (directory per skill).
"""

import logging
import shutil
from pathlib import Path
from typing import Dict, List

from .skill_registry import SkillRegistry

logger = logging.getLogger("nucleus.skill_publisher")

CLAUDE_SKILLS_DIR = Path.home() / ".claude" / "skills"


class SkillPublisher:
    """Install/uninstall generated skills into Claude Code's Skills feature."""

    def __init__(self, brain_path: Path, install_dir: Path = None):
        self.brain_path = brain_path
        self.install_dir = install_dir or CLAUDE_SKILLS_DIR

    def install(self, skill_id: str, registry: SkillRegistry) -> Path:
        """Install a skill so CC auto-discovers it.

        Copies SKILL.md to <install_dir>/<name>/SKILL.md.
        Updates registry installed=True.
        Creates the per-skill directory if needed.
        """
        skill = registry.get_skill(skill_id)
        if not skill:
            raise ValueError(f"Unknown skill: {skill_id}")

        md_path = Path(skill["md_path"])
        if not md_path.is_absolute():
            md_path = self.brain_path / md_path

        if not md_path.exists():
            raise FileNotFoundError(f"Skill file not found: {md_path}")

        skill_dir = self.install_dir / skill["name"]
        skill_dir.mkdir(parents=True, exist_ok=True)
        dest = skill_dir / "SKILL.md"
        shutil.copy2(md_path, dest)

        registry.mark_installed(skill_id, True)
        logger.info("Installed %s -> %s", skill_id, dest)

        # Coord-event capture (Phase B). Best-effort; never breaks install flow.
        try:
            from . import coord_events as _ce
            _ce.emit(
                event_type="skill_picked",
                agent="skill_publisher",
                session_id=skill_id,
                context_summary=f"installed {skill['name']} -> {dest}",
                chosen_option=skill_id,
                tags=["install"],
            )
        except Exception:
            pass

        return dest

    def uninstall(self, skill_id: str, registry: SkillRegistry):
        """Remove a skill from Claude Code. Updates registry installed=False.

        Removes <install_dir>/<name>/SKILL.md and the per-skill directory
        if it becomes empty.
        """
        skill = registry.get_skill(skill_id)
        if not skill:
            raise ValueError(f"Unknown skill: {skill_id}")

        skill_dir = self.install_dir / skill["name"]
        dest = skill_dir / "SKILL.md"
        if dest.exists():
            dest.unlink()
            logger.info("Uninstalled %s (removed %s)", skill_id, dest)
        else:
            logger.warning("Skill file not found for uninstall: %s", dest)

        if skill_dir.exists() and not any(skill_dir.iterdir()):
            skill_dir.rmdir()

        registry.mark_installed(skill_id, False)

    def list_installed(self) -> List[str]:
        """List skill names installed under install_dir.

        A skill is considered installed if <install_dir>/<name>/SKILL.md exists.
        """
        if not self.install_dir.exists():
            return []
        return [
            d.name
            for d in self.install_dir.iterdir()
            if d.is_dir() and (d / "SKILL.md").exists()
        ]

    def install_batch(
        self,
        skill_ids: List[str],
        registry: SkillRegistry,
    ) -> Dict[str, list]:
        """Install multiple skills. Returns {installed: [...], failed: [...]}."""
        installed = []
        failed = []
        for sid in skill_ids:
            try:
                self.install(sid, registry)
                installed.append(sid)
            except Exception as e:
                failed.append({"skill_id": sid, "error": str(e)})
                logger.warning("Failed to install %s: %s", sid, e)
        return {"installed": installed, "failed": failed}
