"""Skills tool — MCP interface for the Skill Flywheel.

Exposes skill operations (list, extract, install, status) so AI agents
can discover, manage, and invoke skills during sessions.

Follows the same dispatch() facade pattern as tools/archive.py.
"""

import json

from ._dispatch import dispatch


def register(mcp, helpers):
    """Register the nucleus_skills facade tool with the MCP server."""
    make_response = helpers["make_response"]

    def _h_list(min_score=0.0, installed_only=False):
        from ..runtime.skill_registry import SkillRegistry
        from ..runtime.common import get_brain_path

        reg = SkillRegistry(get_brain_path())
        skills = reg.list_skills(
            min_score=float(min_score),
            installed_only=bool(installed_only),
        )
        return make_response(True, data={"skills": skills, "count": len(skills)})

    def _h_extract(min_score=0.5, min_cluster=3):
        from ..runtime.skill_extractor import extract_skills
        from ..runtime.skill_generator import generate_skill_md
        from ..runtime.skill_registry import SkillRegistry
        from ..runtime.common import get_brain_path

        brain_path = get_brain_path()
        candidates = extract_skills(
            brain_path,
            min_score=float(min_score),
            min_cluster_size=int(min_cluster),
            use_embeddings=True,
        )

        reg = SkillRegistry(brain_path)
        generated = []
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
            generated.append(skill_id)

        return make_response(True, data={
            "extracted": len(candidates),
            "generated": generated,
            "message": f"Extracted {len(candidates)} skills",
        })

    def _h_install(skill_id=None, all=False, min_score=0.7):
        from ..runtime.skill_registry import SkillRegistry
        from ..runtime.skill_publisher import SkillPublisher
        from ..runtime.common import get_brain_path

        brain_path = get_brain_path()
        reg = SkillRegistry(brain_path)
        pub = SkillPublisher(brain_path)

        if all or not skill_id:
            skills = reg.list_skills(min_score=float(min_score))
            ids = [s["skill_id"] for s in skills]
            result = pub.install_batch(ids, reg)
            return make_response(True, data=result)
        else:
            path = pub.install(skill_id, reg)
            return make_response(True, data={
                "installed": skill_id,
                "path": str(path),
            })

    def _h_status():
        """Summary: total skills, installed count, top skills by score."""
        from ..runtime.skill_registry import SkillRegistry
        from ..runtime.skill_publisher import SkillPublisher
        from ..runtime.common import get_brain_path

        brain_path = get_brain_path()
        reg = SkillRegistry(brain_path)
        pub = SkillPublisher(brain_path)

        all_skills = reg.list_skills()
        installed = pub.list_installed()

        top_skills = [
            {"id": s["skill_id"], "score": s["score"], "installed": s.get("installed", False)}
            for s in all_skills[:10]
        ]

        return make_response(True, data={
            "total_skills": len(all_skills),
            "installed_count": len(installed),
            "top_skills": top_skills,
        })

    ACTION_MAP = {
        "list": _h_list,
        "extract": _h_extract,
        "install": _h_install,
        "status": _h_status,
    }

    @mcp.tool()
    def nucleus_skills(action: str = "", params: dict = None) -> str:
        """Skill Flywheel — auto-extracted skills from conversation history.

        Actions: list, extract, install, status"""
        return dispatch(action, params or {}, ACTION_MAP, "nucleus_skills")

    return [("nucleus_skills", nucleus_skills)]
