"""Daily daemon job that runs the skill extraction pipeline automatically."""

import asyncio
import logging

logger = logging.getLogger("NucleusJobs.skill_extract")


async def run_skill_extract() -> dict:
    """Run skill extraction from accumulated conversation turns.

    Pipeline: extract -> generate -> register -> auto-install (score >= 0.7).
    Runs daily after conversation_ingest_job has processed new sessions.
    """
    try:
        from ..common import get_brain_path
        from ..skill_extractor import extract_skills
        from ..skill_generator import generate_skill_md
        from ..skill_registry import SkillRegistry
        from ..skill_publisher import SkillPublisher

        brain_path = get_brain_path()
        candidates = await asyncio.to_thread(
            extract_skills, brain_path,
            min_score=0.5, min_cluster_size=3, use_embeddings=True,
        )

        if not candidates:
            logger.info("No skill candidates found.")
            return {"ok": True, "extracted": 0, "installed": 0}

        reg = SkillRegistry(brain_path)
        pub = SkillPublisher(brain_path)
        generated = 0
        installed = 0

        for cluster in candidates:
            domain = cluster["domain"]
            skill_id = f"{domain}-v1"
            md_content = generate_skill_md(cluster)

            # Write SKILL.md
            skill_dir = reg.generated_dir / domain
            skill_dir.mkdir(parents=True, exist_ok=True)
            md_path = skill_dir / "SKILL.md"
            md_path.write_text(md_content, encoding="utf-8")

            reg.register(
                skill_id=skill_id,
                name=domain,
                version="1.0.0",
                score=cluster.get("score", 0),
                skill_md_path=md_path,
                source_turn_ids=cluster.get("turn_ids", []),
            )
            generated += 1

            # Auto-install high-scoring skills
            if cluster.get("score", 0) >= 0.7:
                try:
                    pub.install(skill_id, reg)
                    installed += 1
                except Exception as e:
                    logger.warning("Auto-install failed for %s: %s", skill_id, e)

        logger.info(
            "Skill extraction: %d candidates, %d generated, %d auto-installed",
            len(candidates), generated, installed,
        )
        return {"ok": True, "extracted": len(candidates), "generated": generated, "installed": installed}

    except Exception as e:
        logger.error("Skill extraction failed: %s", e)
        return {"ok": False, "error": str(e)}
