"""Daily daemon job that runs the skill extraction pipeline automatically."""

import asyncio
import logging

logger = logging.getLogger("NucleusJobs.skill_extract")


async def run_skill_extract() -> dict:
    """Run skill extraction from accumulated conversation turns.

    Pipeline: extract -> generate -> register -> auto-install (ALLOWLIST-gated).
    Runs daily after conversation_ingest_job has processed new sessions.

    Install gate: the raw frequency-scorer mis-ranks conversational filler as
    high-value, so autonomous install is gated on an operator-approved allowlist
    (<brain>/skills/allowlist.json) — NOT on score >= 0.7. Non-allowlisted
    candidates are still registered + surfaced, never auto-installed. A paste-
    friction snapshot is recorded each run for the kill-gate. See
    skill_allowlist.py / skill_friction.py.
    """
    try:
        from ..common import get_brain_path
        from ..skill_extractor import extract_skills
        from ..skill_generator import generate_skill_md
        from ..skill_registry import SkillRegistry
        from ..skill_publisher import SkillPublisher
        from ..skill_allowlist import load_allowlist, match_allowlist
        from ..skill_friction import compute_friction, record_friction, check_kill_gate

        brain_path = get_brain_path()
        allowlist = load_allowlist(brain_path)
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

            # Auto-install ONLY allowlisted recurring macros. Everything else is
            # registered + surfaced but never auto-applied (blind scorer is not
            # trustworthy). Log every decision — no silent skips.
            matched = match_allowlist(cluster, allowlist)
            if matched:
                try:
                    pub.install(skill_id, reg)
                    installed += 1
                    logger.info("auto-installed %s (allowlist match: %s)", skill_id, matched)
                except Exception as e:
                    logger.warning("Auto-install failed for %s: %s", skill_id, e)
            else:
                logger.info(
                    "surface-only %s (no allowlist match; score=%.2f) — registered, not installed",
                    skill_id, cluster.get("score", 0),
                )

        # Record paste-friction snapshot, then EVALUATE the kill-gate so the
        # loop self-flags if it isn't reducing friction (no orphan loop).
        kill_flag = None
        try:
            metric = compute_friction(candidates)
            record_friction(brain_path, metric)
            kill_flag = check_kill_gate(brain_path)
            if kill_flag:
                logger.warning(
                    "MACRO-LOOP KILL-GATE TRIPPED: friction not dropping "
                    "(baseline=%s current=%s drop=%.0f%% < target=%.0f%% over %dd) "
                    "— recommend disabling skill_extract or revisiting the allowlist.",
                    kill_flag["baseline"], kill_flag["current"],
                    kill_flag["drop"] * 100, kill_flag["target"] * 100,
                    kill_flag["window_days"],
                )
        except Exception as e:
            logger.warning("friction snapshot/kill-gate failed: %s", e)

        logger.info(
            "Skill extraction: %d candidates, %d generated, %d auto-installed (allowlist)",
            len(candidates), generated, installed,
        )
        result = {
            "ok": True,
            "extracted": len(candidates),
            "generated": generated,
            "installed": installed,
        }
        if kill_flag:
            result["kill_gate"] = kill_flag
        return result

    except Exception as e:
        logger.error("Skill extraction failed: %s", e)
        return {"ok": False, "error": str(e)}
