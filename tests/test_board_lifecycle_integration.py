"""End-to-end post → claim → resolve lifecycle, plus atomic-claim race + TTL archival."""

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

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


class TestFullLifecycle:
    def test_post_claim_resolve_cycle(self, brain):
        from mcp_server_nucleus.runtime.board_ops import (
            claim,
            list_posts,
            post,
            resolve,
        )

        # POST
        p = post(
            subject="lifecycle smoke",
            body={"summary": "smoke"},
            tags=["tribal-knowledge:misc"],
            from_role="main",
        )
        bid = p["board_id"]
        opens = list_posts(status="open")
        assert len(opens) == 1
        assert opens[0]["board_id"] == bid

        # CLAIM
        c = claim(board_id=bid, claimer_role="peer")
        assert c["ok"] is True
        claimeds = list_posts(status="claimed")
        assert len(claimeds) == 1
        assert claimeds[0]["claimed_by"] == "peer"

        # RESOLVE
        r = resolve(
            board_id=bid, resolution="fixed via X", resolver_role="peer"
        )
        assert r["ok"] is True
        resolveds = list_posts(status="resolved")
        assert len(resolveds) == 1
        assert resolveds[0]["resolved_by"] == "peer"
        assert resolveds[0]["resolution"] == "fixed via X"

        # No orphans
        all_files = list((brain / "relay" / "board").glob("*.json"))
        assert len(all_files) == 1


class TestAtomicClaimRace:
    def test_two_claims_one_wins(self, brain):
        """Sequential is sufficient — atomicity = mkdir(exist_ok=False)."""
        from mcp_server_nucleus.runtime.board_ops import claim, post

        p = post(
            subject="race",
            body={},
            tags=["tribal-knowledge:r2"],
            from_role="main",
        )
        bid = p["board_id"]
        winners = []
        losers = []
        for role in ("peer", "cc-tb", "op-assistant"):
            r = claim(board_id=bid, claimer_role=role)
            (winners if r["ok"] else losers).append(r)
        assert len(winners) == 1
        assert len(losers) == 2
        assert winners[0]["claimer_role"] == "peer"
        for L in losers:
            assert L["error"] == "already_claimed"
            assert L["already_claimed_by"] == "peer"


class TestTTLArchival:
    def _backdate(self, path: Path, days: int) -> None:
        data = json.loads(path.read_text())
        old = datetime.now(timezone.utc) - timedelta(days=days)
        data["created_at"] = old.replace(microsecond=0).isoformat().replace(
            "+00:00", "Z"
        )
        path.write_text(json.dumps(data, indent=2, sort_keys=True))

    def test_stale_open_post_archived_on_next_post(self, brain):
        from mcp_server_nucleus.runtime.board_ops import list_posts, post

        p1 = post(
            subject="stale",
            body={},
            tags=["tribal-knowledge:misc"],
            from_role="main",
        )
        stale_path = Path(p1["file_path"])
        self._backdate(stale_path, days=10)  # > 7d TTL

        # Trigger sweep via any new post.
        post(
            subject="fresh",
            body={},
            tags=["tribal-knowledge:misc"],
            from_role="main",
        )

        opens = list_posts(status="open")
        # Only the fresh one should remain.
        assert len(opens) == 1
        assert opens[0]["subject"] == "fresh"

        archive_files = list(
            (brain / "relay" / "board" / "_archive").glob("*.json")
        )
        assert len(archive_files) == 1
        archived = json.loads(archive_files[0].read_text())
        assert archived["board_id"] == p1["board_id"]

    def test_resolved_kept_until_30d(self, brain):
        from mcp_server_nucleus.runtime.board_ops import (
            claim,
            list_posts,
            post,
            resolve,
        )

        p = post(
            subject="recent",
            body={},
            tags=["tribal-knowledge:misc"],
            from_role="main",
        )
        bid = p["board_id"]
        claim(board_id=bid, claimer_role="peer")
        resolve(board_id=bid, resolution="ok", resolver_role="peer")
        self._backdate(Path(p["file_path"]).parent / list(
            (brain / "relay" / "board").glob("*resolved*.json")
        )[0].name, days=10)
        # Sweep via new post — resolved < 30d should NOT archive.
        post(
            subject="trigger",
            body={},
            tags=["tribal-knowledge:misc"],
            from_role="main",
        )
        resolved = list_posts(status="resolved")
        assert len(resolved) == 1


class TestReactivationIntegration:
    def test_archived_in_same_domain_surfaces_on_new_post(self, brain):
        from mcp_server_nucleus.runtime.board_ops import (
            claim,
            list_posts,
            post,
            resolve,
        )

        # Cycle 1: post, claim, resolve, then backdate + sweep so it archives.
        p1 = post(
            subject="cycle1",
            body={"summary": "first"},
            tags=["tribal-knowledge:r2"],
            from_role="main",
        )
        bid1 = p1["board_id"]
        claim(board_id=bid1, claimer_role="peer")
        resolve(board_id=bid1, resolution="done1", resolver_role="peer")

        # Backdate resolved post >30d so the next mutating call archives it.
        resolved_path = next(
            (brain / "relay" / "board").glob("*resolved*.json")
        )
        data = json.loads(resolved_path.read_text())
        old = datetime.now(timezone.utc) - timedelta(days=40)
        data["created_at"] = old.replace(microsecond=0).isoformat().replace(
            "+00:00", "Z"
        )
        resolved_path.write_text(json.dumps(data, indent=2, sort_keys=True))

        # Cycle 2: new post in same domain — should surface bid1 as related.
        p2 = post(
            subject="cycle2",
            body={"summary": "second"},
            tags=["tribal-knowledge:r2"],
            from_role="main",
        )
        assert p2["related_archived_count"] >= 1
        data2 = json.loads(Path(p2["file_path"]).read_text())
        assert bid1 in data2["body"]["related_archived_items"]
