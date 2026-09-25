"""Tests for `nucleus_board(action='post')` — `runtime/board_ops.py::post`.

Covers:
- Mandatory tagging validator (rejects bare; accepts tribal-knowledge OR priority:blocker)
- Filename + board_id shape
- from_role auto-fill from CC_SESSION_ROLE
- Re-activation trigger surfaces archived items
- Secret carve-out notice
"""

import json
import os
from datetime import datetime, timedelta, timezone

import pytest


@pytest.fixture
def brain(tmp_path):
    b = tmp_path / ".brain"
    (b / "relay" / "board").mkdir(parents=True)
    os.environ["NUCLEUS_BRAIN_PATH"] = str(b)
    yield b
    os.environ.pop("NUCLEUS_BRAIN_PATH", None)
    os.environ.pop("NUCLEAR_BRAIN_PATH", None)
    os.environ.pop("CC_SESSION_ROLE", None)


class TestMandatoryTagging:
    def test_rejects_bare_post_no_tags(self, brain):
        from mcp_server_nucleus.runtime.board_ops import post

        with pytest.raises(ValueError, match="at least one tag"):
            post(subject="x", body={"summary": "s"}, tags=[])

    def test_rejects_irrelevant_tags(self, brain):
        from mcp_server_nucleus.runtime.board_ops import post

        with pytest.raises(ValueError, match="tribal-knowledge"):
            post(subject="x", body={"summary": "s"}, tags=["random:tag", "color:red"])

    def test_accepts_tribal_knowledge_tag(self, brain):
        from mcp_server_nucleus.runtime.board_ops import post

        result = post(
            subject="ok", body={"summary": "s"}, tags=["tribal-knowledge:r2"]
        )
        assert result["ok"] is True
        assert result["board_id"].startswith("board_")

    def test_accepts_priority_blocker_alone(self, brain):
        from mcp_server_nucleus.runtime.board_ops import post

        result = post(
            subject="urgent", body={"summary": "s"}, tags=["priority:blocker"]
        )
        assert result["ok"] is True

    def test_error_message_is_actionable(self, brain):
        from mcp_server_nucleus.runtime.board_ops import post

        with pytest.raises(ValueError) as exc:
            post(subject="x", body={"summary": "s"}, tags=["foo"])
        msg = str(exc.value)
        assert "tribal-knowledge" in msg
        assert "priority:blocker" in msg


class TestFileShape:
    def test_writes_file_to_board_dir(self, brain):
        from mcp_server_nucleus.runtime.board_ops import post

        result = post(
            subject="R2 creds in CC Voice",
            body={"summary": "doc"},
            tags=["tribal-knowledge:cloudflare-r2"],
        )
        from pathlib import Path

        p = Path(result["file_path"])
        assert p.exists()
        assert p.parent == brain / "relay" / "board"
        data = json.loads(p.read_text())
        assert data["board_id"] == result["board_id"]
        assert data["status"] == "open"
        assert data["from_role"] == "main"
        assert "r2-creds" in p.name or "r2" in p.name

    def test_filename_sanitized(self, brain):
        from mcp_server_nucleus.runtime.board_ops import post

        result = post(
            subject="Subject With / Slashes & Special!! chars",
            body={"summary": "s"},
            tags=["tribal-knowledge:misc"],
        )
        from pathlib import Path

        p = Path(result["file_path"])
        # Only [a-z0-9-] in the slug portion of the filename.
        slug = p.stem.split("_open_", 1)[-1]
        import re

        assert re.fullmatch(r"[a-z0-9-]+", slug), f"bad slug: {slug}"


class TestRoleAutofill:
    def test_explicit_from_role_wins(self, brain):
        from mcp_server_nucleus.runtime.board_ops import post

        os.environ["CC_SESSION_ROLE"] = "peer"
        result = post(
            subject="x",
            body={},
            tags=["tribal-knowledge:misc"],
            from_role="cc-tb",
        )
        from pathlib import Path

        data = json.loads(Path(result["file_path"]).read_text())
        assert data["from_role"] == "cc-tb"

    def test_env_var_fills_when_arg_missing(self, brain):
        from mcp_server_nucleus.runtime.board_ops import post

        os.environ["CC_SESSION_ROLE"] = "peer"
        result = post(
            subject="x", body={}, tags=["tribal-knowledge:misc"]
        )
        from pathlib import Path

        data = json.loads(Path(result["file_path"]).read_text())
        assert data["from_role"] == "peer"

    def test_default_main_when_neither(self, brain):
        from mcp_server_nucleus.runtime.board_ops import post

        os.environ.pop("CC_SESSION_ROLE", None)
        result = post(subject="x", body={}, tags=["tribal-knowledge:misc"])
        from pathlib import Path

        data = json.loads(Path(result["file_path"]).read_text())
        assert data["from_role"] == "main"


class TestReactivationTrigger:
    def test_surfaces_archived_in_same_domain(self, brain):
        from mcp_server_nucleus.runtime import board_ops

        # Drop an archived post directly into _archive/ with matching domain.
        archive = brain / "relay" / "board" / "_archive"
        archive.mkdir(parents=True, exist_ok=True)
        old = {
            "board_id": "board_20250101T000000Z_deadbeef",
            "schema_version": 1,
            "from_role": "main",
            "subject": "older",
            "body": {"summary": "old"},
            "tags": ["tribal-knowledge:cloudflare-r2"],
            "priority": "normal",
            "status": "resolved",
            "created_at": "2025-01-01T00:00:00Z",
        }
        (archive / "20250101T000000Z_main_resolved_older.json").write_text(
            json.dumps(old)
        )

        result = board_ops.post(
            subject="new question",
            body={"summary": "s"},
            tags=["tribal-knowledge:cloudflare-r2"],
        )
        assert result["related_archived_count"] == 1
        from pathlib import Path

        data = json.loads(Path(result["file_path"]).read_text())
        assert "board_20250101T000000Z_deadbeef" in data["body"][
            "related_archived_items"
        ]

    def test_no_related_when_no_archive(self, brain):
        from mcp_server_nucleus.runtime.board_ops import post

        result = post(
            subject="x", body={"summary": "s"}, tags=["tribal-knowledge:novel-domain"]
        )
        assert result["related_archived_count"] == 0


class TestSecretCarveout:
    def test_secret_tag_adds_notice(self, brain):
        from mcp_server_nucleus.runtime.board_ops import post

        result = post(
            subject="creds rotation",
            body={"summary": "need new R2 token"},
            tags=["tribal-knowledge:secrets-handling", "secret-required"],
        )
        from pathlib import Path

        data = json.loads(Path(result["file_path"]).read_text())
        assert "operator-keyboard only" in data["body"]["secret_notice"]
        assert "do NOT transmit" in data["body"]["secret_notice"]
