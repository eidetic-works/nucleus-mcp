"""Skill pipeline integration test — full flow from extraction to installation.

Tests the end-to-end pipeline:
  synthetic turns → extract_skills() → generate_skill_md() → SkillRegistry → SkillPublisher

All I/O uses tmp_path. No Ollama (keyword fallback only).
"""

import json
import pytest
from pathlib import Path


def _synthetic_turns(n: int = 20) -> list:
    """Generate synthetic conversation turns that cluster well."""
    intents = [
        "write unit tests for auth module coverage",
        "write unit tests for payment module coverage",
        "write unit tests for database module coverage",
        "write unit tests for email module coverage",
        "write unit tests for session module coverage",
        "write unit tests for cache module coverage",
        "write unit tests for upload module coverage",
        "write unit tests for webhook module coverage",
        "write unit tests for search module coverage",
        "write unit tests for config module coverage",
        "write unit tests for scheduler module coverage",
        "write unit tests for logging module coverage",
        "write unit tests for validation module coverage",
        "write unit tests for middleware module coverage",
        "write unit tests for notification module coverage",
        "write unit tests for rate limiting module coverage",
        "write unit tests for error handling module coverage",
        "write unit tests for file parser module coverage",
        "write unit tests for API endpoint module coverage",
        "write unit tests for registration module coverage",
    ]
    turns = []
    for i in range(n):
        intent = intents[i % len(intents)]
        turns.append({
            "turn_id": f"turn-pipe-{i:03d}",
            "intent": intent,
            "tools_used": ["Read", "Edit", "Bash"],
            "decisions": ["Read existing code first", "Follow project conventions"],
            "outcome": f"Completed: {intent}",
            "quality_grade": ["copper", "silver", "gold", "platinum"][i % 4],
            "conversation": [
                {"role": "user", "content": intent},
                {"role": "assistant", "content": f"I'll {intent.lower()}."},
            ],
            "actions": [f"action_{i}"],
            "signal_absorbed": [],
            "signal_produced": [],
            "metadata": {"source": f"session-{i % 3}"},
        })
    return turns


@pytest.fixture
def brain_with_turns(tmp_path):
    """Create a .brain dir seeded with synthetic turn data."""
    brain = tmp_path / ".brain"
    brain.mkdir(exist_ok=True)
    training_dir = brain / "training"
    training_dir.mkdir()
    turns_file = training_dir / "loop_turns.jsonl"
    with open(turns_file, "w") as f:
        for t in _synthetic_turns(20):
            f.write(json.dumps(t) + "\n")
    return brain


class TestSkillPipelineEndToEnd:
    """Full pipeline: extract → generate → register → install."""

    def test_extract_cluster_generate_register_install(self, brain_with_turns, tmp_path):
        """The full pipeline should produce an installed SKILL.md file."""
        from mcp_server_nucleus.runtime.skill_extractor import extract_skills
        from mcp_server_nucleus.runtime.skill_generator import generate_skill_md
        from mcp_server_nucleus.runtime.skill_registry import SkillRegistry
        from mcp_server_nucleus.runtime.skill_publisher import SkillPublisher

        brain = brain_with_turns

        # Step 1: Extract skills (keyword fallback, no Ollama)
        candidates = extract_skills(
            brain, min_score=0.0, min_cluster_size=3, use_embeddings=False,
        )
        assert len(candidates) >= 1, "Should extract at least 1 skill cluster"
        top = candidates[0]
        assert top["size"] >= 3
        assert "domain" in top
        assert "score" in top

        # Step 2: Generate SKILL.md
        md_content = generate_skill_md(top)
        assert "---" in md_content
        assert "name:" in md_content
        assert "## When to use" in md_content
        assert "## Approach" in md_content

        # Step 3: Register in registry
        reg = SkillRegistry(brain)
        domain = top["domain"]
        skill_id = f"{domain}-v1"

        skill_dir = reg.generated_dir / domain
        skill_dir.mkdir(parents=True, exist_ok=True)
        md_path = skill_dir / "SKILL.md"
        md_path.write_text(md_content, encoding="utf-8")

        entry = reg.register(
            skill_id=skill_id,
            name=domain,
            version="1.0.0",
            score=top["score"],
            skill_md_path=md_path,
            source_turn_ids=top.get("turn_ids", []),
        )
        assert entry["skill_id"] == skill_id
        assert entry["installed"] is False

        # Verify it's listed
        listed = reg.list_skills()
        assert len(listed) == 1
        assert listed[0]["skill_id"] == skill_id

        # Step 4: Install to a temp commands directory
        commands_dir = tmp_path / "commands"
        pub = SkillPublisher(brain, install_dir=commands_dir)
        dest = pub.install(skill_id, reg)

        assert dest.exists()
        assert dest.name.startswith("nucleus-skill-")
        installed_content = dest.read_text()
        assert "## When to use" in installed_content
        assert "## Approach" in installed_content

        # Registry should reflect installed=True
        skill = reg.get_skill(skill_id)
        assert skill["installed"] is True

    def test_extract_with_no_data_returns_empty(self, tmp_path):
        """extract_skills with empty brain returns no candidates."""
        from mcp_server_nucleus.runtime.skill_extractor import extract_skills

        brain = tmp_path / ".brain"
        brain.mkdir(exist_ok=True)
        (brain / "training").mkdir(exist_ok=True)

        candidates = extract_skills(
            brain, min_score=0.0, min_cluster_size=3, use_embeddings=False,
        )
        assert candidates == []

    def test_uninstall_after_install(self, brain_with_turns, tmp_path):
        """Install then uninstall should leave no trace in commands dir."""
        from mcp_server_nucleus.runtime.skill_extractor import extract_skills
        from mcp_server_nucleus.runtime.skill_generator import generate_skill_md
        from mcp_server_nucleus.runtime.skill_registry import SkillRegistry
        from mcp_server_nucleus.runtime.skill_publisher import SkillPublisher

        brain = brain_with_turns
        candidates = extract_skills(
            brain, min_score=0.0, min_cluster_size=3, use_embeddings=False,
        )
        assert len(candidates) >= 1

        top = candidates[0]
        md_content = generate_skill_md(top)
        reg = SkillRegistry(brain)
        domain = top["domain"]
        skill_id = f"{domain}-v1"

        skill_dir = reg.generated_dir / domain
        skill_dir.mkdir(parents=True, exist_ok=True)
        md_path = skill_dir / "SKILL.md"
        md_path.write_text(md_content, encoding="utf-8")
        reg.register(skill_id, domain, "1.0.0", top["score"], md_path, [])

        commands_dir = tmp_path / "commands"
        pub = SkillPublisher(brain, install_dir=commands_dir)
        dest = pub.install(skill_id, reg)
        assert dest.exists()

        pub.uninstall(skill_id, reg)
        assert not dest.exists()
        assert reg.get_skill(skill_id)["installed"] is False

    def test_registry_tracks_usage(self, brain_with_turns):
        """Usage tracking increments correctly across the pipeline."""
        from mcp_server_nucleus.runtime.skill_registry import SkillRegistry

        brain = brain_with_turns
        reg = SkillRegistry(brain)
        reg.register("s1", "test-skill", "1.0.0", 0.8, Path("fake.md"), [])

        reg.update_usage("s1", success=True)
        reg.update_usage("s1", success=True)
        reg.update_usage("s1", success=False)

        skill = reg.get_skill("s1")
        assert skill["usage_count"] == 3
        assert skill["success_count"] == 2
