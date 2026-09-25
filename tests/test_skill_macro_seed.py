"""Tests for the allowlist-gated macro-seed loop (skill_allowlist + skill_friction)."""
import json
import tempfile
import unittest
import datetime as dt
from pathlib import Path

from mcp_server_nucleus.runtime.skill_allowlist import (
    load_allowlist,
    match_allowlist,
)
from mcp_server_nucleus.runtime.skill_friction import (
    is_macro_cluster,
    compute_friction,
    record_friction,
    check_kill_gate,
)

PATTERNS = [
    {"id": "relays", "match": "check relays"},
    {"id": "report", "match": "report back to cowork"},
]


class TestAllowlist(unittest.TestCase):
    def test_match_on_intent(self):
        c = {"domain": "relays", "intents": ["check relays and continue", "check realys"]}
        self.assertEqual(match_allowlist(c, PATTERNS), "relays")

    def test_match_on_domain(self):
        c = {"domain": "report-cowork", "intents": ["report back to cowork now"]}
        self.assertEqual(match_allowlist(c, PATTERNS), "report")

    def test_no_match_returns_none(self):
        c = {"domain": "whatever", "intents": ["what do you recommend"]}
        self.assertIsNone(match_allowlist(c, PATTERNS))

    def test_empty_patterns_returns_none(self):
        c = {"domain": "relays", "intents": ["check relays and continue"]}
        self.assertIsNone(match_allowlist(c, []))

    def test_no_cross_boundary_match(self):
        # needle "check relays" must NOT match across domain<->intent boundary
        c = {"domain": "check", "intents": ["relays now", "later"]}
        self.assertIsNone(match_allowlist(c, [{"id": "x", "match": "check relays"}]))

    def test_short_needle_skipped(self):
        c = {"domain": "do-stuff", "intents": ["do the thing"]}
        self.assertIsNone(match_allowlist(c, [{"id": "x", "match": "do"}]))

    def test_empty_id_skipped(self):
        c = {"domain": "relays", "intents": ["check relays and continue"]}
        self.assertIsNone(match_allowlist(c, [{"id": "", "match": "check relays"}]))

    def test_load_missing_returns_empty(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(load_allowlist(Path(d)), [])

    def test_load_reads_patterns(self):
        with tempfile.TemporaryDirectory() as d:
            brain = Path(d)
            (brain / "skills").mkdir(parents=True)
            (brain / "skills" / "allowlist.json").write_text(
                json.dumps({"version": 1, "patterns": PATTERNS}), encoding="utf-8"
            )
            self.assertEqual(len(load_allowlist(brain)), 2)

    def test_load_malformed_returns_empty(self):
        with tempfile.TemporaryDirectory() as d:
            brain = Path(d)
            (brain / "skills").mkdir(parents=True)
            (brain / "skills" / "allowlist.json").write_text("{not json", encoding="utf-8")
            self.assertEqual(load_allowlist(brain), [])


class TestMacroDetection(unittest.TestCase):
    def _cluster(self, intents, grade, size):
        return {
            "intents": intents,
            "turns": [{"quality_grade": grade} for _ in range(size)],
            "size": size,
        }

    def test_command_like_high_quality_is_macro(self):
        c = self._cluster(["check relays and continue"] * 3, "gold", 3)
        self.assertTrue(is_macro_cluster(c))

    def test_low_quality_is_not_macro(self):
        c = self._cluster(["check relays and continue"] * 3, "copper", 3)
        self.assertFalse(is_macro_cluster(c))

    def test_long_nonimperative_filler_is_not_macro(self):
        long_q = "what do you think about the overall architecture and the design choices the team made here"
        c = self._cluster([long_q] * 3, "gold", 3)
        self.assertFalse(is_macro_cluster(c))

    def test_too_few_intents_is_not_macro(self):
        c = self._cluster(["check relays"] * 2, "gold", 2)
        self.assertFalse(is_macro_cluster(c))


class TestFriction(unittest.TestCase):
    def test_compute_sums_size_minus_one(self):
        macro_a = {"intents": ["check relays"] * 3, "turns": [{"quality_grade": "gold"}] * 14, "size": 14}
        macro_b = {"intents": ["fire relay to tb"] * 3, "turns": [{"quality_grade": "gold"}] * 9, "size": 9}
        filler = {"intents": ["what do you recommend overall about the whole architecture design"] * 3,
                  "turns": [{"quality_grade": "copper"}] * 18, "size": 18}
        m = compute_friction([macro_a, macro_b, filler], total_turns=1000)
        self.assertEqual(m["macro_clusters"], 2)
        self.assertEqual(m["addressable_pastes"], 13 + 8)
        self.assertEqual(m["friction_pct"], round(100 * 21 / 1000, 2))

    def test_record_and_kill_gate(self):
        with tempfile.TemporaryDirectory() as d:
            brain = Path(d)
            old = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=20)).isoformat()
            now = dt.datetime.now(dt.timezone.utc).isoformat()
            # no drop across a >14d window => kill flagged
            record_friction(brain, {"addressable_pastes": 100, "macro_clusters": 5}, ts=old)
            record_friction(brain, {"addressable_pastes": 98, "macro_clusters": 5}, ts=now)
            flag = check_kill_gate(brain, window_days=14, drop_target=0.30)
            self.assertIsNotNone(flag)
            self.assertTrue(flag["kill_recommended"])

    def test_kill_gate_not_flagged_on_good_drop(self):
        with tempfile.TemporaryDirectory() as d:
            brain = Path(d)
            old = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=20)).isoformat()
            now = dt.datetime.now(dt.timezone.utc).isoformat()
            record_friction(brain, {"addressable_pastes": 100}, ts=old)
            record_friction(brain, {"addressable_pastes": 50}, ts=now)  # 50% drop
            self.assertIsNone(check_kill_gate(brain, window_days=14, drop_target=0.30))

    def test_kill_gate_insufficient_history(self):
        with tempfile.TemporaryDirectory() as d:
            brain = Path(d)
            record_friction(brain, {"addressable_pastes": 100})
            self.assertIsNone(check_kill_gate(brain))

    def test_kill_gate_base_zero_returns_none(self):
        # ramping loop (no baseline friction) must NOT be flagged for kill
        with tempfile.TemporaryDirectory() as d:
            brain = Path(d)
            old = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=20)).isoformat()
            now = dt.datetime.now(dt.timezone.utc).isoformat()
            record_friction(brain, {"addressable_pastes": 0}, ts=old)
            record_friction(brain, {"addressable_pastes": 0}, ts=now)
            self.assertIsNone(check_kill_gate(brain))

    def test_compute_omits_pct_without_total(self):
        macro = {"intents": ["check relays"] * 3, "turns": [{"quality_grade": "gold"}] * 4, "size": 4}
        m = compute_friction([macro])  # no total_turns
        self.assertNotIn("friction_pct", m)
        self.assertEqual(m["addressable_pastes"], 3)


class TestJobWiring(unittest.TestCase):
    def test_job_invokes_kill_gate(self):
        """cc-peer HIGH finding: prove check_kill_gate is actually called by the job."""
        import asyncio
        from unittest.mock import patch, MagicMock
        with tempfile.TemporaryDirectory() as d:
            brain = Path(d)
            fake = {"domain": "relays", "score": 0.6, "turn_ids": [],
                    "intents": ["check relays"] * 3,
                    "turns": [{"quality_grade": "gold"}] * 3, "size": 3}
            with patch("mcp_server_nucleus.runtime.common.get_brain_path", return_value=brain), \
                 patch("mcp_server_nucleus.runtime.skill_extractor.extract_skills", return_value=[fake]), \
                 patch("mcp_server_nucleus.runtime.skill_generator.generate_skill_md", return_value="md"), \
                 patch("mcp_server_nucleus.runtime.skill_registry.SkillRegistry", MagicMock()), \
                 patch("mcp_server_nucleus.runtime.skill_publisher.SkillPublisher", MagicMock()), \
                 patch("mcp_server_nucleus.runtime.skill_friction.check_kill_gate",
                       return_value=None) as mock_gate:
                from mcp_server_nucleus.runtime.jobs.skill_extract_job import run_skill_extract
                res = asyncio.run(run_skill_extract())
                self.assertTrue(res["ok"])
                mock_gate.assert_called_once()


if __name__ == "__main__":
    unittest.main()
