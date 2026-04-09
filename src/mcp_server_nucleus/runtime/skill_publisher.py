"""Skill Publisher — Install/uninstall generated skills into Claude Code.

Copies SKILL.md files to ~/.claude/commands/nucleus-skill-{name}.md
where Claude Code auto-discovers them as custom slash commands.

The `nucleus-skill-` prefix groups all flywheel-generated skills together
and avoids conflicts with user-created commands.
"""

import logging
import shutil
from pathlib import Path
from typing import Dict, List

from .skill_registry import SkillRegistry

logger = logging.getLogger("nucleus.skill_publisher")

CLAUDE_COMMANDS_DIR = Path.home() / ".claude" / "commands"
SKILL_PREFIX = "nucleus-skill-"  # Prefix for nucleus-generated commands


class SkillPublisher:
    """Install/uninstall generated skills into Claude Code's command system."""

    def __init__(self, brain_path: Path, install_dir: Path = None):
        self.brain_path = brain_path
        self.install_dir = install_dir or CLAUDE_COMMANDS_DIR

    def install(self, skill_id: str, registry: SkillRegistry) -> Path:
        """Install a skill as a Claude Code custom command.

        Copies SKILL.md to ~/.claude/commands/nucleus-skill-{name}.md.
        Updates registry installed=True.
        Creates install_dir if needed.
        """
        skill = registry.get_skill(skill_id)
        if not skill:
            raise ValueError(f"Unknown skill: {skill_id}")

        md_path = Path(skill["md_path"])
        if not md_path.is_absolute():
            md_path = self.brain_path / md_path

        if not md_path.exists():
            raise FileNotFoundError(f"Skill file not found: {md_path}")

        self.install_dir.mkdir(parents=True, exist_ok=True)
        dest = self.install_dir / f"{SKILL_PREFIX}{skill['name']}.md"
        shutil.copy2(md_path, dest)

        registry.mark_installed(skill_id, True)
        logger.info("Installed %s -> %s", skill_id, dest)
        return dest

    def uninstall(self, skill_id: str, registry: SkillRegistry):
        """Remove a skill from Claude Code. Updates registry installed=False."""
        skill = registry.get_skill(skill_id)
        if not skill:
            raise ValueError(f"Unknown skill: {skill_id}")

        dest = self.install_dir / f"{SKILL_PREFIX}{skill['name']}.md"
        if dest.exists():
            dest.unlink()
            logger.info("Uninstalled %s (removed %s)", skill_id, dest)
        else:
            logger.warning("Skill file not found for uninstall: %s", dest)

        registry.mark_installed(skill_id, False)

    def list_installed(self) -> List[str]:
        """List nucleus-skill-* files in Claude Code commands dir."""
        if not self.install_dir.exists():
            return []
        return [
            f.stem.replace(SKILL_PREFIX, "", 1)
            for f in self.install_dir.glob(f"{SKILL_PREFIX}*.md")
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
