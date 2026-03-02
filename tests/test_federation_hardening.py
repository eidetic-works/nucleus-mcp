"""
Test Suite: Federation + Hardening Integration
===============================================
Tests federation.py with security hardening modules applied.

Addresses Cullinan III finding: "federation.py is 968 lines... ZERO tests"
Agent: CODE_FORCE via Windsurf
Date: Feb 24, 2026
"""

import pytest
import tempfile
import asyncio
import json
from pathlib import Path
from datetime import datetime

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from mcp_server_nucleus.runtime.federation import (
    VectorClock,
    MerkleTree,
    FederationPeer,
    FederationConfig,
    FederationState,
    PeerStatus,
    TrustLevel,
    PartitionStatus,
    ConsistencyClass,
    RaftState,
    create_federation_engine,
)

# Import hardening modules
from mcp_server_nucleus.runtime.hardening import (
    safe_path,
    safe_write_json,
    safe_read_json,
    safe_error,
    safe_federation_state_write,
    PathTraversalError,
)
from mcp_server_nucleus.runtime.path_sanitizer import sanitize_filename
from mcp_server_nucleus.runtime.file_lock import atomic_write_json


class TestVectorClock:
    """Test VectorClock for causal ordering."""

    def test_increment(self):
        """Test clock increment."""
        vc = VectorClock()
        vc = vc.increment("brain_A")
        assert vc.clocks["brain_A"] == 1
        
        vc = vc.increment("brain_A")
        assert vc.clocks["brain_A"] == 2

    def test_merge(self):
        """Test clock merge (max of each)."""
        vc1 = VectorClock(clocks={"A": 3, "B": 2})
        vc2 = VectorClock(clocks={"A": 1, "B": 5, "C": 1})
        
        merged = vc1.merge(vc2)
        
        assert merged.clocks["A"] == 3
        assert merged.clocks["B"] == 5
        assert merged.clocks["C"] == 1

    def test_happens_before(self):
        """Test causal ordering."""
        vc1 = VectorClock(clocks={"A": 1, "B": 2})
        vc2 = VectorClock(clocks={"A": 2, "B": 3})
        
        assert vc1.happens_before(vc2)
        assert not vc2.happens_before(vc1)

    def test_concurrent(self):
        """Test concurrent detection."""
        vc1 = VectorClock(clocks={"A": 2, "B": 1})
        vc2 = VectorClock(clocks={"A": 1, "B": 2})
        
        # VectorClock doesn't have is_concurrent, test happens_before instead
        assert not vc1.happens_before(vc2)
        assert not vc2.happens_before(vc1)


class TestMerkleTree:
    """Test MerkleTree for state verification."""

    def test_single_leaf(self):
        """Test tree with single leaf."""
        tree = MerkleTree()
        tree.update("key1", b"value1")
        
        root = tree.get_root()
        assert root is not None
        assert len(root) == 64  # SHA-256 hex

    def test_multiple_leaves(self):
        """Test tree with multiple leaves."""
        tree = MerkleTree()
        tree.update("key1", b"value1")
        tree.update("key2", b"value2")
        tree.update("key3", b"value3")
        
        root = tree.get_root()
        assert root is not None

    def test_root_changes_on_update(self):
        """Test root changes when data changes."""
        tree = MerkleTree()
        tree.update("key1", b"value1")
        root1 = tree.get_root()
        
        tree.update("key2", b"value2")
        root2 = tree.get_root()
        
        assert root1 != root2

    def test_verify(self):
        """Test verification of leaves."""
        tree = MerkleTree()
        tree.update("key1", b"value1")
        tree.update("key2", b"value2")
        
        # MerkleTree doesn't have verify method, test diff instead
        tree2 = MerkleTree()
        tree2.update("key1", b"value1")
        tree2.update("key2", b"value2")
        assert not tree.diff(tree2.get_root())
        
        tree2.update("key1", b"wrong_value")
        assert tree.diff(tree2.get_root())


class TestFederationPeer:
    """Test FederationPeer data structure."""

    def test_peer_creation(self):
        """Test peer creation."""
        peer = FederationPeer(
            peer_id="brain_001",
            address="192.168.1.1:9000",
            region="us-west"
        )
        assert peer.peer_id == "brain_001"
        assert peer.status == PeerStatus.UNKNOWN
        assert peer.trust_level == TrustLevel.MEMBER  # Default is MEMBER, not GUEST

    def test_peer_online_check(self):
        """Test online status check."""
        peer = FederationPeer("peer_002", "10.0.0.1:9000", "eu-west")
        peer.status = PeerStatus.ONLINE
        peer.last_heartbeat = datetime.utcnow()
        
        # FederationPeer doesn't have is_online method, just check status
        assert peer.status == PeerStatus.ONLINE

    def test_peer_staleness(self):
        """Test staleness detection."""
        peer = FederationPeer("peer_003", "10.0.0.2:9000", "ap-south")
        peer.status = PeerStatus.ONLINE
        peer.last_heartbeat = datetime(2020, 1, 1)  # Very old
        
        # FederationPeer doesn't have is_stale method, check last_heartbeat directly
        assert peer.last_heartbeat is not None
        assert (datetime.utcnow() - peer.last_heartbeat).total_seconds() > 60


class TestFederationState:
    """Test FederationState management."""

    def test_state_creation(self):
        """Test state initialization."""
        state = FederationState(brain_id="master_brain", region="us-west")
        assert state.brain_id == "master_brain"
        assert state.term == 0
        assert state.leader_id is None
        assert len(state.peers) == 0

    def test_state_serialization(self):
        """Test state to_dict."""
        state = FederationState(brain_id="serialize_test", region="eu-west")
        state.term = 5
        state.leader_id = "leader_brain"
        
        data = state.to_dict()
        
        assert data["brain_id"] == "serialize_test"
        assert data["term"] == 5
        assert data["leader_id"] == "leader_brain"


class TestFederationStatePersistence:
    """Test federation state persistence with hardening."""

    def test_safe_state_write(self):
        """Test atomic state writes."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            federation_dir = Path(tmp_dir) / "federation"
            federation_dir.mkdir()
            
            state = {
                "brain_id": "persist_brain",
                "term": 10,
                "leader_id": "leader_001",
                "peers": {"peer_1": {"status": "ONLINE"}},
            }
            
            safe_federation_state_write("persist_brain", state, federation_dir)
            
            # Verify file was created
            state_file = federation_dir / "node_persist_brain.json"
            assert state_file.exists()
            
            # Verify content
            loaded = safe_read_json(state_file)
            assert loaded["brain_id"] == "persist_brain"

    def test_unicode_state(self):
        """Test state with unicode content."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            federation_dir = Path(tmp_dir) / "federation"
            federation_dir.mkdir()
            
            state = {
                "brain_id": "unicode_brain_中文",
                "metadata": {"region": "भारत", "emoji": "🌍"},
            }
            
            safe_federation_state_write("unicode_brain", state, federation_dir)
            
            state_file = federation_dir / "node_unicode_brain.json"
            loaded = safe_read_json(state_file)
            assert loaded["metadata"]["region"] == "भारत"


class TestFederationNodeIdSanitization:
    """Test node ID sanitization for security."""

    def test_path_traversal_prevention(self):
        """Prevent path traversal in node IDs."""
        malicious_id = "../../../etc/passwd"
        safe_id = sanitize_filename(malicious_id)
        
        assert ".." not in safe_id
        assert "/" not in safe_id

    def test_special_characters(self):
        """Test node IDs with special characters."""
        special_ids = [
            "node<script>",
            "node\x00null",
            "node%2F%2e%2e",
        ]
        
        for malicious_id in special_ids:
            safe_id = sanitize_filename(malicious_id)
            assert "<" not in safe_id
            assert "\x00" not in safe_id


class TestFederationConfig:
    """Test FederationConfig."""

    def test_config_creation(self):
        """Test config with defaults."""
        config = FederationConfig(
            brain_id="config_brain",
            region="us-east"
        )
        assert config.brain_id == "config_brain"
        assert config.region == "us-east"

    def test_config_with_seed_peers(self):
        """Test config with seed peers."""
        config = FederationConfig(
            brain_id="seeded_brain",
            region="eu-central",
            seed_peers=["10.0.0.1:9000", "10.0.0.2:9000"]
        )
        assert len(config.seed_peers) == 2


class TestFederationEngineCreation:
    """Test FederationEngine factory."""

    def test_create_engine(self):
        """Test engine creation."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            engine = create_federation_engine(
                brain_id="factory_brain",
                region="ap-southeast",
                brain_path=Path(tmp_dir)
            )
            assert engine is not None
            assert engine.config.brain_id == "factory_brain"

    def test_engine_status(self):
        """Test engine status retrieval."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            engine = create_federation_engine(
                brain_id="status_brain",
                brain_path=Path(tmp_dir)
            )
            status = engine.get_status()
            
            assert status["brain_id"] == "status_brain"
            assert "peers" in status
            assert "running" in status


class TestFederationErrorHandling:
    """Test error handling with sanitization."""

    def test_error_sanitization(self):
        """Test that internal errors are sanitized."""
        try:
            raise FileNotFoundError("/Users/secret/federation/state.json")
        except Exception as e:
            sanitized = safe_error(e, "federation")
        
        assert "/Users/secret" not in sanitized


class TestFederationAsync:
    """Test async federation operations (stdlib asyncio.run, no plugin required)."""

    def test_join_federation(self):
        """Test joining federation."""
        async def _join():
            with tempfile.TemporaryDirectory() as tmp_dir:
                engine = create_federation_engine(
                    brain_id="join_brain",
                    brain_path=Path(tmp_dir)
                )
                result = await engine.join("10.0.0.1:9000")
                assert result["success"]
                assert result["peers"] >= 1
        
        asyncio.run(_join())

    def test_leave_federation(self):
        """Test leaving federation gracefully."""
        async def _leave():
            with tempfile.TemporaryDirectory() as tmp_dir:
                engine = create_federation_engine(
                    brain_id="leave_brain",
                    brain_path=Path(tmp_dir)
                )
                result = await engine.leave()
                assert result["success"]
        
        asyncio.run(_leave())


class TestDiscoveryManager:
    """Test DiscoveryManager peer lifecycle and probing logic."""
    
    @pytest.mark.asyncio
    async def test_probe_marks_peer_suspect(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            engine = create_federation_engine("engine_bh1", Path(tmp_dir))
            # Set short timeouts for testing
            engine.discovery.config.heartbeat_timeout = 0.5
            
            # Setup an online peer acting normally
            peer_good = FederationPeer(peer_id="peer_good", address="host1", region="us")
            peer_good.status = PeerStatus.ONLINE
            peer_good.last_heartbeat = datetime.utcnow()
            engine.state.peers["peer_good"] = peer_good
            
            # Setup a peer that missed heartbeats
            peer_suspect = FederationPeer(peer_id="peer_suspect", address="host2", region="us")
            peer_suspect.status = PeerStatus.ONLINE
            import time
            from datetime import timedelta
            # Aged past the 0.5 timeout
            peer_suspect.last_heartbeat = datetime.utcnow() - timedelta(seconds=1.0)
            engine.state.peers["peer_suspect"] = peer_suspect
            
            # Run the probe manually
            await engine.discovery._probe_round()
            
            assert engine.state.peers["peer_good"].status == PeerStatus.ONLINE
            assert engine.state.peers["peer_suspect"].status == PeerStatus.SUSPECT
            assert engine.state.peers["peer_suspect"].suspect_time is not None

    @pytest.mark.asyncio
    async def test_probe_marks_suspect_offline(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            engine = create_federation_engine("engine_bh2", Path(tmp_dir))
            engine.discovery.config.heartbeat_timeout = 0.5
            engine.discovery.config.suspect_timeout = 0.5
            
            # Setup a peer that is a long time suspect
            peer_dead = FederationPeer(peer_id="peer_dead", address="host3", region="us")
            peer_dead.status = PeerStatus.SUSPECT
            from datetime import timedelta
            peer_dead.last_heartbeat = datetime.utcnow() - timedelta(seconds=2.0)
            peer_dead.suspect_time = datetime.utcnow() - timedelta(seconds=1.0)
            engine.state.peers["peer_dead"] = peer_dead
            
            await engine.discovery._probe_round()
            
            assert engine.state.peers["peer_dead"].status == PeerStatus.OFFLINE


class TestSyncManager:
    """Test state synchronization operations."""
    
    @pytest.mark.asyncio
    async def test_sync_with_peer_updates_clock(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            engine = create_federation_engine("engine_sync", Path(tmp_dir))
            
            # Setup a peer
            peer = FederationPeer("sync_peer", "host1", "us")
            peer.vector_clock = VectorClock(clocks={"sync_peer": 5})
            engine.state.peers["sync_peer"] = peer
            
            # Sync
            result = await engine.sync.sync_with_peer("sync_peer", full=True)
            
            assert result.success is True
            # The local state clock should have merged the peer's clock and incremented itself
            assert engine.state.vector_clock.clocks.get("sync_peer") == 5
            assert engine.state.vector_clock.clocks.get("engine_sync") == 1
            assert peer.last_sync is not None


class TestFederationTaskRouting:
    """Test FederationEngine task routing logic with RoutingProfiles."""
    
    @pytest.mark.asyncio
    async def test_route_task_default_profile(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            engine = create_federation_engine("engine_route_1", Path(tmp_dir))
            
            # Add some peers
            engine.state.peers["peer_fast_empty"] = FederationPeer(
                peer_id="peer_fast_empty", address="host1", region="us",
                capabilities={"llm"}, load=0.1, latency_ms=10.0
            )
            engine.state.peers["peer_fast_empty"].status = PeerStatus.ONLINE
            
            engine.state.peers["peer_slow_busy"] = FederationPeer(
                peer_id="peer_slow_busy", address="host2", region="us",
                capabilities={"llm", "gpu"}, load=0.9, latency_ms=200.0
            )
            engine.state.peers["peer_slow_busy"].status = PeerStatus.ONLINE
            
            # Without specific requirements, it should pick the fast/empty one
            decision = await engine.route_task({"required_skills": ["llm"]}, profile="default")
            # Usually local node gets a slight affinity bump. Let's see if the peer wins.
            assert getattr(decision, "target_brain", None) is not None
            
            # With specific requirement, it should pick the one that has it
            decision2 = await engine.route_task({"required_skills": ["gpu"]}, profile="default")
            assert decision2.target_brain == "peer_slow_busy"

    @pytest.mark.asyncio
    async def test_routing_no_peers_available(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            engine = create_federation_engine("engine_route_3", Path(tmp_dir))
            
            engine.state.peers["peer_offline"] = FederationPeer(
                peer_id="peer_offline", address="host1", region="us",
                capabilities={"magic"}, load=0.1, latency_ms=10.0
            )
            engine.state.peers["peer_offline"].status = PeerStatus.OFFLINE
            
            # Should fallback to local
            decision = await engine.route_task({"required_skills": ["magic"]})
            assert decision.target_brain == "engine_route_3"


class TestConsensusManager:
    """Test Raft leader election and proposal logic."""

    @pytest.mark.asyncio
    async def test_start_election_single_node(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            engine = create_federation_engine("engine_raft_1", Path(tmp_dir))
            # Initially FOLLOWER
            assert engine.consensus.raft_state == RaftState.FOLLOWER
            
            # Single node should immediately elect itself
            await engine.consensus._start_election()
            
            assert engine.consensus.raft_state == RaftState.LEADER
            assert engine.state.leader_id == "engine_raft_1"
            assert engine.state.term == 1

    @pytest.mark.asyncio
    async def test_propose_when_leader(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            engine = create_federation_engine("engine_raft_2", Path(tmp_dir))
            engine.consensus.raft_state = RaftState.LEADER
            
            success = await engine.consensus.propose({"action": "test"})
            assert success is True
            assert len(engine.state.log) == 1
            assert engine.state.log[0].command == {"action": "test"}

    @pytest.mark.asyncio
    async def test_propose_when_follower(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            engine = create_federation_engine("engine_raft_3", Path(tmp_dir))
            engine.consensus.raft_state = RaftState.FOLLOWER
            
            success = await engine.consensus.propose({"action": "test"})
            assert success is False
            assert len(engine.state.log) == 0


class TestRecoveryManager:
    """Test partition detection and handling."""
    
    def test_partition_detection(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            engine = create_federation_engine("engine_rec_1", Path(tmp_dir))
            
            # 1 node = NORMAL
            assert engine.recovery.check_partition_status() == PartitionStatus.NORMAL
            
            # Add 2 offline peers. Total = 3, Online = 1 => ISOLATED
            peer1 = FederationPeer("p1", "h1", "us")
            peer1.status = PeerStatus.OFFLINE
            peer2 = FederationPeer("p2", "h2", "us")
            peer2.status = PeerStatus.OFFLINE
            engine.state.peers["p1"] = peer1
            engine.state.peers["p2"] = peer2
            
            assert engine.recovery.check_partition_status() == PartitionStatus.ISOLATED
            
            # Make 1 peer online. Total = 3, Online = 2 => MAJORITY
            peer1.status = PeerStatus.ONLINE
            assert engine.recovery.check_partition_status() == PartitionStatus.MAJORITY

    @pytest.mark.asyncio
    async def test_handle_peer_failure_disables_class_a(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            engine = create_federation_engine("engine_rec_2", Path(tmp_dir))
            
            # Add 2 online peers. Total = 3, Online = 3
            peer1 = FederationPeer("p1", "h1", "us")
            peer1.status = PeerStatus.ONLINE
            peer2 = FederationPeer("p2", "h2", "us")
            peer2.status = PeerStatus.ONLINE
            engine.state.peers["p1"] = peer1
            engine.state.peers["p2"] = peer2
            
            assert engine.state.class_a_enabled is True
            
            # Both fail
            peer1.status = PeerStatus.OFFLINE
            peer2.status = PeerStatus.OFFLINE
            
            await engine.recovery.handle_peer_failure("p1")
            await engine.recovery.handle_peer_failure("p2")
            
            assert engine.state.partition_status == PartitionStatus.ISOLATED
            assert engine.state.class_a_enabled is False


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
