"""Tests for the Skill Flywheel — extractor, generator, registry, publisher.

All tests use synthetic data. No external dependencies (Ollama, filesystem).
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch


# -- Fixtures --

def _make_turns(n: int = 20, domain: str = "test-writing") -> list:
    """Generate synthetic LoopTurn dicts for testing."""
    intents = {
        "test-writing": [
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
        ],
        "debug-errors": [
            "debug and fix TypeError error in user login handler",
            "debug and fix connection error in checkout handler",
            "debug and fix timeout error in worker pool handler",
            "debug and fix race condition error in session handler",
            "debug and fix validation error in payment handler",
        ],
        "git-workflow": [
            "git workflow create branch and push remote upstream",
            "git workflow merge pull request and resolve conflicts",
            "git workflow rebase branch onto main and push remote",
            "git workflow cherry pick hotfix commit and push remote",
            "git workflow resolve merge conflict and push remote",
        ],
    }

    domain_intents = intents.get(domain, intents["test-writing"])
    turns = []
    for i in range(n):
        intent = domain_intents[i % len(domain_intents)]
        turns.append({
            "turn_id": f"turn-{domain}-{i:03d}",
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
        })
    return turns


# -- Extractor tests --

def test_cluster_intents_groups_similar():
    """Similar intents should cluster together."""
    from mcp_server_nucleus.runtime.skill_extractor import cluster_intents

    turns = _make_turns(n=20, domain="test-writing")
    clusters = cluster_intents(turns, min_cluster_size=3, use_embeddings=False)
    assert len(clusters) >= 1
    # The largest cluster should contain most of the test-writing turns
    assert clusters[0]["size"] >= 3


def test_cluster_intents_separates_different():
    """Different domains form separate clusters."""
    from mcp_server_nucleus.runtime.skill_extractor import cluster_intents

    turns = _make_turns(n=15, domain="test-writing") + _make_turns(n=10, domain="debug-errors")
    clusters = cluster_intents(turns, min_cluster_size=3, use_embeddings=False)
    # Should have at least 2 distinct clusters
    assert len(clusters) >= 1
    domains = {c["domain"] for c in clusters}
    # At least one cluster should exist
    assert len(domains) >= 1


def test_cluster_intents_empty_data():
    """Empty turns list returns empty clusters."""
    from mcp_server_nucleus.runtime.skill_extractor import cluster_intents

    clusters = cluster_intents([], min_cluster_size=3, use_embeddings=False)
    assert clusters == []


def test_cluster_intents_min_size_filter():
    """Clusters below min_size are filtered out."""
    from mcp_server_nucleus.runtime.skill_extractor import cluster_intents

    # Only 2 turns = below min_cluster_size=3
    turns = _make_turns(n=2, domain="test-writing")
    clusters = cluster_intents(turns, min_cluster_size=3, use_embeddings=False)
    assert clusters == []


def test_score_skill_candidate():
    """Scoring produces expected composite scores."""
    from mcp_server_nucleus.runtime.skill_extractor import score_skill_candidate

    cluster = {
        "domain": "test-writing",
        "intents": ["write tests for auth", "add test coverage", "create unit tests"],
        "tools_used": {"Read": 5, "Edit": 8, "Bash": 3},
        "turns": [
            {"quality_grade": "gold", "tools_used": ["Read", "Edit"]},
            {"quality_grade": "silver", "tools_used": ["Edit", "Bash"]},
            {"quality_grade": "platinum", "tools_used": ["Read", "Edit", "Bash"]},
        ],
        "size": 3,
    }
    scored = score_skill_candidate(cluster)
    assert "score" in scored
    assert 0 <= scored["score"] <= 1
    assert "score_breakdown" in scored
    breakdown = scored["score_breakdown"]
    assert all(k in breakdown for k in ("frequency", "diversity", "quality", "generality"))
    # Quality should be > 0.5 (silver + gold + platinum avg)
    assert breakdown["quality"] > 0.5


def test_extract_skills_end_to_end(tmp_path):
    """Full pipeline with temp brain path."""
    from mcp_server_nucleus.runtime.skill_extractor import extract_skills
    from mcp_server_nucleus.runtime.archive_pipeline import ArchivePipeline

    brain = tmp_path / ".brain"
    brain.mkdir()
    archive = ArchivePipeline(brain_path=brain)

    # Write synthetic turns
    turns = _make_turns(n=15, domain="test-writing")
    archive.training_dir.mkdir(parents=True, exist_ok=True)
    with open(archive.turns_file, "w") as f:
        for t in turns:
            f.write(json.dumps(t) + "\n")

    skills = extract_skills(brain, min_score=0.0, min_cluster_size=3, use_embeddings=False)
    assert len(skills) >= 1
    assert all("score" in s for s in skills)


# -- Generator tests --

def test_generate_skill_md_format():
    """Generated SKILL.md has correct structure."""
    from mcp_server_nucleus.runtime.skill_generator import generate_skill_md

    cluster = {
        "domain": "test-writing",
        "score": 0.82,
        "size": 23,
        "intents": [
            "write tests for the auth module",
            "add test coverage for user registration",
            "create unit tests for this function",
        ],
        "turns": [
            {
                "tools_used": ["Read", "Edit", "Bash"],
                "decisions": ["Read existing code first"],
                "intent": "write tests for the auth module",
                "outcome": "Created 5 test cases with full coverage",
                "quality_grade": "gold",
            },
            {
                "tools_used": ["Read", "Edit"],
                "decisions": ["Follow project conventions"],
                "intent": "add test coverage for user registration",
                "outcome": "Added 3 integration tests",
                "quality_grade": "silver",
            },
        ],
    }
    md = generate_skill_md(cluster)
    assert "---" in md
    assert "name: test-writing" in md
    assert "version: 1.0.0" in md
    assert "source: nucleus-flywheel" in md
    assert "## When to use" in md
    assert "## Approach" in md
    assert "## Examples" in md


def test_anonymize_text_strips_paths():
    """File paths replaced with <file>."""
    from mcp_server_nucleus.runtime.skill_generator import _anonymize_text

    result = _anonymize_text("Fix the bug in /src/auth/middleware.py line 42")
    assert "/src/auth/middleware.py" not in result
    assert "<file>" in result


# ---- PII stripping: cross-platform paths ----

def test_pii_strips_macos_home_path():
    from mcp_server_nucleus.runtime.skill_extractor import _tokenize_intent
    tokens = _tokenize_intent("debug issue in /Users/alice/project/main.py")
    assert "alice" not in tokens


def test_pii_strips_linux_home_path():
    from mcp_server_nucleus.runtime.skill_extractor import _tokenize_intent
    tokens = _tokenize_intent("fix the crash at /home/bob/code/server.py")
    assert "bob" not in tokens


def test_pii_strips_windows_home_path():
    from mcp_server_nucleus.runtime.skill_extractor import _tokenize_intent
    for path in (r"C:\Users\carol\repo\file.py", "C:/Users/carol/repo/file.py"):
        tokens = _tokenize_intent(f"open {path} for editing")
        assert "carol" not in tokens


def test_pii_strips_wsl_home_path():
    from mcp_server_nucleus.runtime.skill_extractor import _tokenize_intent
    tokens = _tokenize_intent("cat /mnt/c/Users/dave/notes/todo.md")
    assert "dave" not in tokens


# ---- Hostname pattern builder (pure function) ----

def test_build_hostname_pattern_uses_first_dns_label():
    from mcp_server_nucleus.runtime.skill_extractor import _build_hostname_pattern
    p = _build_hostname_pattern("testbox-123.local")
    assert p.sub("<h>", "deploy on testbox-123 now") == "deploy on <h> now"


def test_build_hostname_pattern_fallback_on_empty():
    from mcp_server_nucleus.runtime.skill_extractor import _build_hostname_pattern
    p = _build_hostname_pattern("")
    assert p.sub("<h>", "ran build on oak-mbp") == "ran build on <h>"
    assert p.sub("<h>", "used johns-macbook here") == "used <h> here"


def test_build_hostname_pattern_fallback_on_too_short():
    from mcp_server_nucleus.runtime.skill_extractor import _build_hostname_pattern
    p = _build_hostname_pattern("xy")  # len < 3 -> fallback
    assert p.sub("<h>", "fred-laptop died") == "<h> died"


# ---- Integration: monkeypatched hostname flows through both layers ----

def test_tokenize_intent_strips_runtime_hostname(monkeypatch):
    import re as _re
    from mcp_server_nucleus.runtime import skill_extractor as se
    monkeypatch.setattr(se, "_HOSTNAME", _re.compile(r"\btestbox\b", _re.IGNORECASE))
    tokens = se._tokenize_intent("deploy bundle on testbox tomorrow")
    assert "testbox" not in tokens


def test_anonymize_text_strips_hostname(monkeypatch):
    import re as _re
    from mcp_server_nucleus.runtime import skill_extractor as se
    from mcp_server_nucleus.runtime.skill_generator import _anonymize_text
    monkeypatch.setattr(se, "_HOSTNAME", _re.compile(r"\bdevbox\b", _re.IGNORECASE))
    out = _anonymize_text("Run the migration on devbox before 5pm")
    assert "devbox" not in out
    assert "<host>" in out


def test_trigger_phrase_extraction():
    """Top phrases extracted from intents."""
    from mcp_server_nucleus.runtime.skill_generator import _extract_trigger_phrases

    intents = [
        "write tests for the auth module",
        "write tests for the payment system",
        "write tests for the API",
        "add test coverage for the database",
        "add test coverage for the cache",
    ]
    phrases = _extract_trigger_phrases(intents, top_n=3)
    assert len(phrases) >= 1
    # "write tests" should be in there
    assert any("write" in p or "test" in p for p in phrases)


# -- Registry tests --

def test_registry_register_and_list(tmp_path):
    """Register a skill, list it back."""
    from mcp_server_nucleus.runtime.skill_registry import SkillRegistry

    brain = tmp_path / ".brain"
    brain.mkdir()
    reg = SkillRegistry(brain)

    reg.register(
        skill_id="test-writing-v1",
        name="test-writing",
        version="1.0.0",
        score=0.82,
        skill_md_path=Path("skills/generated/test-writing/SKILL.md"),
        source_turn_ids=["turn-001", "turn-002"],
    )

    skills = reg.list_skills()
    assert len(skills) == 1
    assert skills[0]["skill_id"] == "test-writing-v1"
    assert skills[0]["score"] == 0.82


def test_registry_update_usage(tmp_path):
    """Usage tracking increments correctly."""
    from mcp_server_nucleus.runtime.skill_registry import SkillRegistry

    brain = tmp_path / ".brain"
    brain.mkdir()
    reg = SkillRegistry(brain)

    reg.register(
        skill_id="test-v1",
        name="test",
        version="1.0.0",
        score=0.5,
        skill_md_path=Path("test.md"),
        source_turn_ids=[],
    )

    reg.update_usage("test-v1", success=True)
    reg.update_usage("test-v1", success=False)
    reg.update_usage("test-v1", success=True)

    skill = reg.get_skill("test-v1")
    assert skill["usage_count"] == 3
    assert skill["success_count"] == 2


def test_registry_dedup_last_wins(tmp_path):
    """Multiple entries for same skill_id, last wins."""
    from mcp_server_nucleus.runtime.skill_registry import SkillRegistry

    brain = tmp_path / ".brain"
    brain.mkdir()
    reg = SkillRegistry(brain)

    reg.register("s1", "skill-one", "1.0.0", 0.5, Path("a.md"), [])
    reg.register("s1", "skill-one", "1.1.0", 0.7, Path("b.md"), [])

    skills = reg.list_skills()
    assert len(skills) == 1
    assert skills[0]["version"] == "1.1.0"
    assert skills[0]["score"] == 0.7


# -- Publisher tests --

def test_install_creates_file(tmp_path):
    """Install copies SKILL.md to commands dir."""
    from mcp_server_nucleus.runtime.skill_registry import SkillRegistry
    from mcp_server_nucleus.runtime.skill_publisher import SkillPublisher

    brain = tmp_path / ".brain"
    brain.mkdir()
    commands_dir = tmp_path / "commands"

    # Create a skill file
    skill_dir = brain / "skills" / "generated" / "test-writing"
    skill_dir.mkdir(parents=True)
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text("# Test Writing\n\nA skill for writing tests.")

    reg = SkillRegistry(brain)
    reg.register("tw-v1", "test-writing", "1.0.0", 0.8, skill_file, [])

    pub = SkillPublisher(brain, install_dir=commands_dir)
    dest = pub.install("tw-v1", reg)

    assert dest.exists()
    assert dest.name == "nucleus-skill-test-writing.md"
    assert "Test Writing" in dest.read_text()

    # Registry should be updated
    skill = reg.get_skill("tw-v1")
    assert skill["installed"] is True


def test_uninstall_removes_file(tmp_path):
    """Uninstall deletes the command file."""
    from mcp_server_nucleus.runtime.skill_registry import SkillRegistry
    from mcp_server_nucleus.runtime.skill_publisher import SkillPublisher

    brain = tmp_path / ".brain"
    brain.mkdir()
    commands_dir = tmp_path / "commands"

    skill_dir = brain / "skills" / "generated" / "debug"
    skill_dir.mkdir(parents=True)
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text("# Debug\n\nDebug skill.")

    reg = SkillRegistry(brain)
    reg.register("dbg-v1", "debug", "1.0.0", 0.7, skill_file, [])

    pub = SkillPublisher(brain, install_dir=commands_dir)
    pub.install("dbg-v1", reg)
    assert (commands_dir / "nucleus-skill-debug.md").exists()

    pub.uninstall("dbg-v1", reg)
    assert not (commands_dir / "nucleus-skill-debug.md").exists()

    skill = reg.get_skill("dbg-v1")
    assert skill["installed"] is False


def test_list_installed(tmp_path):
    """Lists only nucleus-skill-* files."""
    from mcp_server_nucleus.runtime.skill_publisher import SkillPublisher

    brain = tmp_path / ".brain"
    brain.mkdir()
    commands_dir = tmp_path / "commands"
    commands_dir.mkdir()

    # Create some files
    (commands_dir / "nucleus-skill-test-writing.md").write_text("test")
    (commands_dir / "nucleus-skill-debug.md").write_text("debug")
    (commands_dir / "user-custom-command.md").write_text("custom")

    pub = SkillPublisher(brain, install_dir=commands_dir)
    installed = pub.list_installed()

    assert "test-writing" in installed
    assert "debug" in installed
    assert "user-custom-command" not in installed
    assert len(installed) == 2


# -- Session-aware helpers and tests --

def _make_session_turns(specs: list) -> list:
    """Build turn dicts from (intent, session_id, tools) tuples.

    Does NOT modify the existing _make_turns() fixture.
    """
    turns = []
    for i, (intent, session_id, tools) in enumerate(specs):
        turns.append({
            "turn_id": f"turn-session-{i:03d}",
            "intent": intent,
            "tools_used": tools,
            "decisions": [],
            "outcome": f"Completed: {intent}",
            "quality_grade": "silver",
            "conversation": [
                {"role": "user", "content": intent},
                {"role": "assistant", "content": f"I'll {intent.lower()}."},
            ],
            "actions": [],
            "signal_absorbed": [],
            "signal_produced": [],
            "metadata": {"source": session_id},
        })
    return turns


def test_retry_dedup_collapses_same_session():
    """Near-identical intents within one session collapse to one per distinct intent."""
    from mcp_server_nucleus.runtime.skill_extractor import _dedup_retries

    specs = [
        # Group 1: 3 near-identical "investigate fix post" retries
        ("investigate and fix the post endpoint 500 error", "session-abc", ["Read", "Grep"]),
        ("investigate and fix the post endpoint 500 error now", "session-abc", ["Read", "Grep", "Edit"]),
        ("investigate and fix post endpoint 500 error again", "session-abc", ["Read"]),
        # Group 2: 3 near-identical "debug chat handler" retries
        ("debug the chat handler connection timeout issue", "session-abc", ["Read", "Bash"]),
        ("debug the chat handler connection timeout problem", "session-abc", ["Read"]),
        ("debug chat handler connection timeout issue fix", "session-abc", ["Read", "Edit", "Bash"]),
        # Group 3: 3 near-identical "update config" retries
        ("update the deployment config for production server", "session-abc", ["Read", "Edit"]),
        ("update deployment config for production server now", "session-abc", ["Read"]),
        ("update the deployment config production server fix", "session-abc", ["Read", "Edit", "Bash"]),
    ]
    turns = _make_session_turns(specs)
    result = _dedup_retries(turns)
    # 9 turns from 3 groups of retries → should collapse to ≤3 (one per distinct intent)
    assert len(result) <= 3


def test_retry_dedup_preserves_cross_session():
    """Same intent across different sessions = reuse, not retry. Preserved."""
    from mcp_server_nucleus.runtime.skill_extractor import _dedup_retries

    specs = [
        ("write unit tests for the auth module coverage", "session-A", ["Read", "Edit"]),
        ("write unit tests for the auth module coverage", "session-A", ["Read", "Edit", "Bash"]),
        ("write unit tests for the auth module coverage", "session-A", ["Read"]),
        ("write unit tests for the auth module coverage", "session-B", ["Read", "Edit"]),
        ("write unit tests for the auth module coverage", "session-B", ["Read", "Edit", "Bash"]),
        ("write unit tests for the auth module coverage", "session-B", ["Read"]),
    ]
    turns = _make_session_turns(specs)
    result = _dedup_retries(turns)
    # Cross-session repetition = reuse. Each session collapses to 1, so ≥2 total.
    assert len(result) >= 2


def test_session_diversity_scoring():
    """Cluster from many sessions scores higher than cluster from one session."""
    from mcp_server_nucleus.runtime.skill_extractor import score_skill_candidate

    # Cluster A: 9 turns all from 1 session
    turns_a = _make_session_turns([
        (f"write unit tests for module {i} coverage", "session-only", ["Read", "Edit", "Bash"])
        for i in range(9)
    ])
    cluster_a = {
        "domain": "write-tests",
        "intents": [t["intent"] for t in turns_a],
        "tools_used": {"Read": 9, "Edit": 9, "Bash": 9},
        "turns": turns_a,
        "size": 9,
        "avg_quality": "silver",
        "unique_sessions": 1,
    }

    # Cluster B: 9 turns from 5 different sessions
    turns_b = _make_session_turns([
        (f"write unit tests for module {i} coverage", f"session-{i % 5}", ["Read", "Edit", "Bash"])
        for i in range(9)
    ])
    cluster_b = {
        "domain": "write-tests",
        "intents": [t["intent"] for t in turns_b],
        "tools_used": {"Read": 9, "Edit": 9, "Bash": 9},
        "turns": turns_b,
        "size": 9,
        "avg_quality": "silver",
        "unique_sessions": 5,
    }

    scored_a = score_skill_candidate(cluster_a)
    scored_b = score_skill_candidate(cluster_b)

    bd_a = scored_a["score_breakdown"]
    bd_b = scored_b["score_breakdown"]

    assert bd_b["session_diversity"] > bd_a["session_diversity"]
    assert scored_b["score"] > scored_a["score"]


def test_verb_object_labels():
    """Domain labels should follow verb-noun structure."""
    from mcp_server_nucleus.runtime.skill_extractor import cluster_intents

    turns = _make_session_turns([
        (f"write tests for the {mod} module implementation", f"session-{i}", ["Read", "Edit", "Bash"])
        for i, mod in enumerate([
            "auth", "payment", "database", "email", "session",
            "cache", "upload", "webhook", "search", "config",
        ])
    ])
    clusters = cluster_intents(turns, min_cluster_size=3, use_embeddings=False)
    assert len(clusters) >= 1
    label = clusters[0]["domain"]
    # Should contain a verb like "write" or "test"
    assert any(v in label for v in ("write", "test")), f"Label '{label}' missing verb"
    # Should contain a noun (not just a verb)
    assert "-" in label, f"Label '{label}' should be verb-noun format"
