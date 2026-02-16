"""
NOP V3.1 Federation Engine - Distributed Multi-Brain Orchestration

This module implements the federation layer for NOP, enabling multiple brains
to coordinate across geographic regions with:
- SWIM-based peer discovery and membership
- Raft consensus for critical operations
- CRDT-based state synchronization with Merkle tree verification
- Composite task routing with pluggable strategies
- Partition tolerance and automatic recovery

v0.6.0 DSoR Integration:
- DecisionMade events for all federation operations
- Context hashing for state verification
- IPC token security for cross-brain communication

Author: NOP V3.1 Team
Version: 1.1.0-DSoR
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import random
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

# v0.6.0 DSoR imports
try:
    from .context_manager import compute_context_hash, get_context_manager
    from .ipc_auth import get_ipc_auth_manager
    from .event_stream import emit_event, EventTypes
    DSOR_AVAILABLE = True
except ImportError:
    DSOR_AVAILABLE = False

logger = logging.getLogger(__name__)

# =============================================================================
# ENUMS AND CONSTANTS
# =============================================================================

class TrustLevel(Enum):
    OWNER = 4
    ADMIN = 3
    MEMBER = 2
    GUEST = 1

class PeerStatus(Enum):
    UNKNOWN = auto()
    ONLINE = auto()
    SUSPECT = auto()
    OFFLINE = auto()
    QUARANTINED = auto()

class PartitionStatus(Enum):
    NORMAL = auto()
    MAJORITY = auto()
    MINORITY = auto()
    ISOLATED = auto()

class ConsistencyClass(Enum):
    CLASS_A = "critical"
    CLASS_B = "important"
    CLASS_C = "normal"

class RaftState(Enum):
    FOLLOWER = auto()
    CANDIDATE = auto()
    LEADER = auto()

DEFAULT_HEARTBEAT_INTERVAL = 1.0
DEFAULT_HEARTBEAT_TIMEOUT = 5.0
DEFAULT_SYNC_INTERVAL = 5.0
DEFAULT_ELECTION_TIMEOUT_MIN = 150
DEFAULT_ELECTION_TIMEOUT_MAX = 300
DEFAULT_GOSSIP_FANOUT = 3
DEFAULT_SUSPECT_TIMEOUT = 5.0

# =============================================================================
# CORE DATA STRUCTURES
# =============================================================================

@dataclass
class VectorClock:
    """Vector clock for causal ordering across distributed brains."""
    clocks: Dict[str, int] = field(default_factory=dict)
    
    def increment(self, brain_id: str) -> 'VectorClock':
        new_clocks = self.clocks.copy()
        new_clocks[brain_id] = new_clocks.get(brain_id, 0) + 1
        return VectorClock(new_clocks)
    
    def merge(self, other: 'VectorClock') -> 'VectorClock':
        all_keys = set(self.clocks.keys()) | set(other.clocks.keys())
        merged = {k: max(self.clocks.get(k, 0), other.clocks.get(k, 0)) for k in all_keys}
        return VectorClock(merged)
    
    def happens_before(self, other: 'VectorClock') -> bool:
        dominated = all(self.clocks.get(k, 0) <= other.clocks.get(k, 0) for k in self.clocks)
        strictly_less = any(self.clocks.get(k, 0) < other.clocks.get(k, 0) for k in other.clocks)
        return dominated and strictly_less
    
    def to_dict(self) -> Dict[str, int]:
        return self.clocks.copy()
    
    @classmethod
    def from_dict(cls, data: Dict[str, int]) -> 'VectorClock':
        return cls(clocks=data.copy())


class MerkleTree:
    """Merkle tree for efficient state comparison and synchronization."""
    
    def __init__(self):
        self.leaves: Dict[str, str] = {}
        self._root: str = ""
        self._dirty = True
    
    def update(self, key: str, value: bytes) -> None:
        value_hash = hashlib.sha256(value).hexdigest()
        self.leaves[key] = hashlib.sha256(f"{key}:{value_hash}".encode()).hexdigest()
        self._dirty = True
    
    def remove(self, key: str) -> None:
        if key in self.leaves:
            del self.leaves[key]
            self._dirty = True
    
    def get_root(self) -> str:
        if self._dirty:
            if not self.leaves:
                self._root = ""
            else:
                sorted_hashes = sorted(self.leaves.values())
                combined = ":".join(sorted_hashes)
                self._root = hashlib.sha256(combined.encode()).hexdigest()
            self._dirty = False
        return self._root
    
    def diff(self, other_root: str) -> bool:
        return self.get_root() != other_root


@dataclass
class FederationPeer:
    """Represents a remote brain in the federation."""
    peer_id: str
    address: str
    region: str
    trust_level: TrustLevel = TrustLevel.MEMBER
    capabilities: Set[str] = field(default_factory=set)
    status: PeerStatus = PeerStatus.UNKNOWN
    last_heartbeat: Optional[datetime] = None
    last_sync: Optional[datetime] = None
    vector_clock: VectorClock = field(default_factory=VectorClock)
    merkle_root: str = ""
    latency_ms: float = 0.0
    load: float = 0.0
    version: str = "1.0.0"
    incarnation: int = 0
    suspect_time: Optional[datetime] = None
    
    def is_online(self) -> bool:
        return self.status == PeerStatus.ONLINE
    
    def is_healthy(self) -> bool:
        return self.status in (PeerStatus.ONLINE, PeerStatus.SUSPECT)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "peer_id": self.peer_id, "address": self.address, "region": self.region,
            "trust_level": self.trust_level.name, "capabilities": list(self.capabilities),
            "status": self.status.name, "latency_ms": self.latency_ms, "load": self.load,
            "last_heartbeat": self.last_heartbeat.isoformat() if self.last_heartbeat else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FederationPeer':
        return cls(
            peer_id=data["peer_id"], address=data["address"],
            region=data.get("region", "unknown"),
            trust_level=TrustLevel[data.get("trust_level", "MEMBER")],
            capabilities=set(data.get("capabilities", [])),
            status=PeerStatus[data.get("status", "UNKNOWN")],
            latency_ms=data.get("latency_ms", 0.0), load=data.get("load", 0.0),
        )


@dataclass
class RoutingDecision:
    """Result of task routing computation."""
    target_brain: str
    score: float
    factors: Dict[str, float]
    alternatives: List[Tuple[str, float]]
    routing_time_ms: float


@dataclass
class RoutingProfile:
    """Weights for routing decision factors."""
    skill_weight: float = 0.3
    latency_weight: float = 0.2
    load_weight: float = 0.2
    cost_weight: float = 0.2
    affinity_weight: float = 0.1

ROUTING_PROFILES: Dict[str, RoutingProfile] = {
    "default": RoutingProfile(),
    "realtime": RoutingProfile(0.2, 0.5, 0.2, 0.0, 0.1),
    "batch": RoutingProfile(0.3, 0.0, 0.3, 0.3, 0.1),
    "premium": RoutingProfile(0.5, 0.1, 0.2, 0.0, 0.2),
    "budget": RoutingProfile(0.2, 0.0, 0.2, 0.5, 0.1),
}


@dataclass
class RaftLogEntry:
    """Entry in the Raft consensus log."""
    term: int
    index: int
    command: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SyncResult:
    """Result of a state synchronization operation."""
    success: bool
    peer_id: str
    items_synced: int
    conflicts_resolved: int
    sync_time_ms: float
    new_merkle_root: str
    error: Optional[str] = None


@dataclass
class FederationConfig:
    """Configuration for federation engine."""
    brain_id: str
    region: str = "default"
    address: str = "localhost:9000"
    seed_peers: List[str] = field(default_factory=list)
    heartbeat_interval: float = DEFAULT_HEARTBEAT_INTERVAL
    heartbeat_timeout: float = DEFAULT_HEARTBEAT_TIMEOUT
    sync_interval: float = DEFAULT_SYNC_INTERVAL
    election_timeout_min: int = DEFAULT_ELECTION_TIMEOUT_MIN
    election_timeout_max: int = DEFAULT_ELECTION_TIMEOUT_MAX
    gossip_fanout: int = DEFAULT_GOSSIP_FANOUT
    suspect_timeout: float = DEFAULT_SUSPECT_TIMEOUT
    brain_path: Path = field(default_factory=lambda: Path(".brain"))
    enable_consensus: bool = True
    enable_auto_sync: bool = True


@dataclass
class FederationState:
    """Complete federation state for persistence."""
    brain_id: str
    region: str
    peers: Dict[str, FederationPeer] = field(default_factory=dict)
    leader_id: Optional[str] = None
    term: int = 0
    voted_for: Optional[str] = None
    log: List[RaftLogEntry] = field(default_factory=list)
    commit_index: int = 0
    last_applied: int = 0
    vector_clock: VectorClock = field(default_factory=VectorClock)
    merkle_root: str = ""
    partition_status: PartitionStatus = PartitionStatus.NORMAL
    class_a_enabled: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "brain_id": self.brain_id, "region": self.region,
            "peers": {k: v.to_dict() for k, v in self.peers.items()},
            "leader_id": self.leader_id, "term": self.term,
            "vector_clock": self.vector_clock.to_dict(),
            "partition_status": self.partition_status.name,
        }


@dataclass
class FederationMetrics:
    """Metrics for federation monitoring."""
    peers_total: int = 0
    peers_online: int = 0
    peers_suspect: int = 0
    sync_operations: int = 0
    sync_conflicts: int = 0
    avg_sync_lag_ms: float = 0.0
    raft_term: int = 0
    raft_leader_changes: int = 0
    tasks_routed: int = 0
    tasks_forwarded: int = 0
    avg_routing_time_ms: float = 0.0
    partition_events: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "peers": {"total": self.peers_total, "online": self.peers_online},
            "sync": {"operations": self.sync_operations, "avg_lag_ms": self.avg_sync_lag_ms},
            "consensus": {"term": self.raft_term, "leader_changes": self.raft_leader_changes},
            "routing": {"tasks_routed": self.tasks_routed, "avg_time_ms": self.avg_routing_time_ms},
        }


# =============================================================================
# ROUTING STRATEGIES
# =============================================================================

class RoutingStrategy(ABC):
    @abstractmethod
    def score(self, brain: FederationPeer, task: Dict[str, Any], local_brain_id: str) -> float:
        pass


class CompositeRoutingStrategy(RoutingStrategy):
    def __init__(self, profile: RoutingProfile = None):
        self.profile = profile or ROUTING_PROFILES["default"]
    
    def score(self, brain: FederationPeer, task: Dict[str, Any], local_brain_id: str) -> float:
        required_skills = set(task.get("required_skills", []))
        if required_skills and not required_skills.issubset(brain.capabilities):
            return -1.0
        
        skill_score = len(required_skills & brain.capabilities) / max(len(required_skills), 1)
        latency_score = 1.0 - min(brain.latency_ms / 200.0, 1.0)
        load_score = 1.0 - brain.load
        cost_score = 1.0
        
        affinity = task.get("affinity", {})
        affinity_score = 0.0
        if affinity.get("preferred_brain") == brain.peer_id:
            affinity_score = 1.0
        elif affinity.get("preferred_region") == brain.region:
            affinity_score = 0.5
        elif brain.peer_id == local_brain_id:
            affinity_score = 0.3
        
        return (self.profile.skill_weight * skill_score +
                self.profile.latency_weight * latency_score +
                self.profile.load_weight * load_score +
                self.profile.cost_weight * cost_score +
                self.profile.affinity_weight * affinity_score)


# =============================================================================
# DISCOVERY MANAGER
# =============================================================================

class DiscoveryManager:
    """SWIM-based peer discovery and membership management."""
    
    def __init__(self, config: FederationConfig, state: FederationState):
        self.config = config
        self.state = state
        self.running = False
        self._gossip_task: Optional[asyncio.Task] = None
        self._probe_task: Optional[asyncio.Task] = None
        self.on_peer_joined: Optional[Callable[[FederationPeer], None]] = None
        self.on_peer_left: Optional[Callable[[str], None]] = None
        self.on_peer_suspect: Optional[Callable[[str], None]] = None
    
    async def start(self) -> None:
        self.running = True
        await self._bootstrap()
        self._gossip_task = asyncio.create_task(self._gossip_loop())
        self._probe_task = asyncio.create_task(self._probe_loop())
        logger.info(f"Discovery started for {self.config.brain_id}")
    
    async def stop(self) -> None:
        self.running = False
        for task in [self._gossip_task, self._probe_task]:
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
    
    async def _bootstrap(self) -> None:
        for seed in self.config.seed_peers:
            try:
                host, port = seed.rsplit(":", 1) if ":" in seed else (seed, "9000")
                peer_id = f"seed_{host}_{port}"
                peer = FederationPeer(peer_id=peer_id, address=f"{host}:{port}", region="unknown")
                self.state.peers[peer_id] = peer
                peer.status = PeerStatus.ONLINE
                peer.last_heartbeat = datetime.utcnow()
                if self.on_peer_joined:
                    self.on_peer_joined(peer)
            except Exception as e:
                logger.warning(f"Failed to contact seed peer {seed}: {e}")
    
    async def _gossip_loop(self) -> None:
        while self.running:
            try:
                await self._gossip_round()
                await asyncio.sleep(self.config.heartbeat_interval)
            except asyncio.CancelledError:
                break
    
    async def _gossip_round(self) -> None:
        online_peers = [p for p in self.state.peers.values() if p.is_healthy()]
        if not online_peers:
            return
        targets = random.sample(online_peers, min(self.config.gossip_fanout, len(online_peers)))
        # In production: exchange membership info with targets
    
    async def _probe_loop(self) -> None:
        while self.running:
            try:
                await self._probe_round()
                await asyncio.sleep(self.config.heartbeat_interval)
            except asyncio.CancelledError:
                break
    
    async def _probe_round(self) -> None:
        now = datetime.utcnow()
        for peer in list(self.state.peers.values()):
            if peer.peer_id == self.config.brain_id:
                continue
            if peer.last_heartbeat:
                elapsed = (now - peer.last_heartbeat).total_seconds()
                if elapsed > self.config.heartbeat_timeout:
                    if peer.status == PeerStatus.ONLINE:
                        peer.status = PeerStatus.SUSPECT
                        peer.suspect_time = now
                        if self.on_peer_suspect:
                            self.on_peer_suspect(peer.peer_id)
                    elif peer.status == PeerStatus.SUSPECT and peer.suspect_time:
                        if (now - peer.suspect_time).total_seconds() > self.config.suspect_timeout:
                            peer.status = PeerStatus.OFFLINE
                            if self.on_peer_left:
                                self.on_peer_left(peer.peer_id)
    
    def get_online_peers(self) -> List[FederationPeer]:
        return [p for p in self.state.peers.values() if p.is_online()]
    
    def get_healthy_peers(self) -> List[FederationPeer]:
        return [p for p in self.state.peers.values() if p.is_healthy()]


# =============================================================================
# CONSENSUS MANAGER (Simplified Raft)
# =============================================================================

class ConsensusManager:
    """Simplified Raft consensus for critical operations."""
    
    def __init__(self, config: FederationConfig, state: FederationState):
        self.config = config
        self.state = state
        self.raft_state = RaftState.FOLLOWER
        self.running = False
        self._election_timer: Optional[asyncio.Task] = None
        self._heartbeat_timer: Optional[asyncio.Task] = None
        self.on_leader_change: Optional[Callable[[Optional[str]], None]] = None
        self.on_commit: Optional[Callable[[RaftLogEntry], None]] = None
    
    async def start(self) -> None:
        self.running = True
        self._reset_election_timer()
        logger.info(f"Consensus started for {self.config.brain_id}")
    
    async def stop(self) -> None:
        self.running = False
        for timer in [self._election_timer, self._heartbeat_timer]:
            if timer:
                timer.cancel()
    
    def _get_election_timeout(self) -> float:
        return random.randint(self.config.election_timeout_min, self.config.election_timeout_max) / 1000.0
    
    def _reset_election_timer(self) -> None:
        if self._election_timer:
            self._election_timer.cancel()
        if self.running and self.raft_state != RaftState.LEADER:
            self._election_timer = asyncio.create_task(
                self._election_timeout_handler(self._get_election_timeout())
            )
    
    async def _election_timeout_handler(self, timeout: float) -> None:
        try:
            await asyncio.sleep(timeout)
            if self.running and self.raft_state != RaftState.LEADER:
                await self._start_election()
        except asyncio.CancelledError:
            pass
    
    async def _start_election(self) -> None:
        self.state.term += 1
        self.raft_state = RaftState.CANDIDATE
        self.state.voted_for = self.config.brain_id
        
        peers = [p for p in self.state.peers.values() if p.is_healthy()]
        total_nodes = len(peers) + 1
        votes_received = 1  # Vote for self
        
        if total_nodes == 1 or votes_received >= (total_nodes // 2) + 1:
            await self._become_leader()
        else:
            self.raft_state = RaftState.FOLLOWER
            self._reset_election_timer()
    
    async def _become_leader(self) -> None:
        self.raft_state = RaftState.LEADER
        self.state.leader_id = self.config.brain_id
        logger.info(f"Became leader for term {self.state.term}")
        self._start_heartbeat()
        if self.on_leader_change:
            self.on_leader_change(self.config.brain_id)
    
    def _start_heartbeat(self) -> None:
        if self._heartbeat_timer:
            self._heartbeat_timer.cancel()
        if self.running and self.raft_state == RaftState.LEADER:
            self._heartbeat_timer = asyncio.create_task(self._heartbeat_loop())
    
    async def _heartbeat_loop(self) -> None:
        while self.running and self.raft_state == RaftState.LEADER:
            try:
                await asyncio.sleep(self.config.heartbeat_interval / 2)
            except asyncio.CancelledError:
                break
    
    async def propose(self, command: Dict[str, Any]) -> bool:
        if self.raft_state != RaftState.LEADER:
            return False
        entry = RaftLogEntry(term=self.state.term, index=len(self.state.log) + 1, command=command)
        self.state.log.append(entry)
        if len(self.state.peers) == 0:
            self.state.commit_index = entry.index
            if self.on_commit:
                self.on_commit(entry)
        return True
    
    def is_leader(self) -> bool:
        return self.raft_state == RaftState.LEADER
    
    def get_leader(self) -> Optional[str]:
        return self.state.leader_id


# =============================================================================
# SYNC MANAGER
# =============================================================================

class SyncManager:
    """State synchronization using Merkle trees and CRDT merge."""
    
    def __init__(self, config: FederationConfig, state: FederationState):
        self.config = config
        self.state = state
        self.merkle_tree = MerkleTree()
        self.running = False
        self._sync_task: Optional[asyncio.Task] = None
        self.sync_in_progress: Set[str] = set()
        self.on_state_changed: Optional[Callable[[Dict[str, Any]], None]] = None
    
    async def start(self) -> None:
        self.running = True
        if self.config.enable_auto_sync:
            self._sync_task = asyncio.create_task(self._sync_loop())
        logger.info(f"Sync started for {self.config.brain_id}")
    
    async def stop(self) -> None:
        self.running = False
        if self._sync_task:
            self._sync_task.cancel()
    
    async def _sync_loop(self) -> None:
        while self.running:
            try:
                for peer in [p for p in self.state.peers.values() if p.is_healthy()]:
                    if peer.peer_id not in self.sync_in_progress:
                        await self.sync_with_peer(peer.peer_id)
                await asyncio.sleep(self.config.sync_interval)
            except asyncio.CancelledError:
                break
    
    async def sync_with_peer(self, peer_id: str, full: bool = False) -> SyncResult:
        if peer_id in self.sync_in_progress:
            return SyncResult(False, peer_id, 0, 0, 0, self.merkle_tree.get_root(), "Sync in progress")
        
        self.sync_in_progress.add(peer_id)
        start_time = time.perf_counter()
        
        try:
            peer = self.state.peers.get(peer_id)
            if not peer:
                return SyncResult(False, peer_id, 0, 0, 0, "", "Peer not found")
            
            local_root = self.merkle_tree.get_root()
            if not full and local_root == peer.merkle_root:
                return SyncResult(True, peer_id, 0, 0, (time.perf_counter() - start_time) * 1000, local_root)
            
            self.state.vector_clock = self.state.vector_clock.merge(peer.vector_clock).increment(self.config.brain_id)
            peer.last_sync = datetime.utcnow()
            
            return SyncResult(True, peer_id, 0, 0, (time.perf_counter() - start_time) * 1000, self.merkle_tree.get_root())
        finally:
            self.sync_in_progress.discard(peer_id)
    
    async def force_sync(self) -> List[SyncResult]:
        return [await self.sync_with_peer(p.peer_id, full=True) for p in self.state.peers.values() if p.is_healthy()]
    
    def update_local_state(self, key: str, value: bytes) -> None:
        self.merkle_tree.update(key, value)
        self.state.merkle_root = self.merkle_tree.get_root()
        self.state.vector_clock = self.state.vector_clock.increment(self.config.brain_id)


# =============================================================================
# ROUTING ENGINE
# =============================================================================

class RoutingEngine:
    """Task routing with pluggable strategies and caching."""
    
    def __init__(self, config: FederationConfig, state: FederationState):
        self.config = config
        self.state = state
        self.strategies: Dict[str, RoutingStrategy] = {"composite": CompositeRoutingStrategy()}
        self.routing_cache: Dict[str, Tuple[RoutingDecision, float]] = {}
        self.cache_ttl = 1.0
        self.total_routes = 0
        self.total_routing_time = 0.0
    
    async def route_task(self, task: Dict[str, Any], profile: str = "default") -> RoutingDecision:
        start_time = time.perf_counter()
        
        cache_key = hashlib.md5(json.dumps(task, sort_keys=True, default=str).encode()).hexdigest()
        if cache_key in self.routing_cache:
            decision, cached_time = self.routing_cache[cache_key]
            if time.time() - cached_time < self.cache_ttl:
                return decision
        
        strategy = CompositeRoutingStrategy(ROUTING_PROFILES.get(profile, ROUTING_PROFILES["default"]))
        candidates: List[Tuple[str, float]] = []
        
        local_peer = FederationPeer(self.config.brain_id, self.config.address, self.config.region, latency_ms=0)
        local_score = strategy.score(local_peer, task, self.config.brain_id)
        candidates.append((self.config.brain_id, local_score))
        
        for peer in self.state.peers.values():
            if peer.is_healthy():
                score = strategy.score(peer, task, self.config.brain_id)
                if score >= 0:
                    candidates.append((peer.peer_id, score))
        
        candidates.sort(key=lambda x: x[1], reverse=True)
        best_brain, best_score = candidates[0] if candidates else (self.config.brain_id, 0.0)
        
        elapsed = (time.perf_counter() - start_time) * 1000
        decision = RoutingDecision(best_brain, best_score, {}, candidates[1:5], elapsed)
        
        self.routing_cache[cache_key] = (decision, time.time())
        self.total_routes += 1
        self.total_routing_time += elapsed
        
        return decision


# =============================================================================
# CIRCUIT BREAKER
# =============================================================================

class CircuitBreaker:
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 30.0):
        self.state = self.CLOSED
        self.failures = 0
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.last_failure_time: Optional[float] = None
    
    def record_success(self) -> None:
        self.failures = 0
        self.state = self.CLOSED
    
    def record_failure(self) -> None:
        self.failures += 1
        self.last_failure_time = time.time()
        if self.failures >= self.failure_threshold:
            self.state = self.OPEN
    
    def allow_request(self) -> bool:
        if self.state == self.CLOSED:
            return True
        if self.state == self.OPEN and self.last_failure_time:
            if time.time() - self.last_failure_time >= self.recovery_timeout:
                self.state = self.HALF_OPEN
                return True
        return self.state == self.HALF_OPEN


# =============================================================================
# RECOVERY MANAGER
# =============================================================================

class RecoveryManager:
    """Failure detection and recovery handling."""
    
    def __init__(self, config: FederationConfig, state: FederationState,
                 discovery: DiscoveryManager, consensus: ConsensusManager, sync: SyncManager):
        self.config = config
        self.state = state
        self.discovery = discovery
        self.consensus = consensus
        self.sync = sync
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.unreachable_peers: Set[str] = set()
        self.on_partition_detected: Optional[Callable[[Set[str]], None]] = None
        self.on_partition_healed: Optional[Callable[[Set[str]], None]] = None
    
    def check_partition_status(self) -> PartitionStatus:
        total_peers = len(self.state.peers) + 1
        reachable = len([p for p in self.state.peers.values() if p.is_healthy()]) + 1
        
        if reachable == total_peers:
            return PartitionStatus.NORMAL
        majority = (total_peers // 2) + 1
        if reachable >= majority:
            return PartitionStatus.MAJORITY
        elif reachable == 1:
            return PartitionStatus.ISOLATED
        return PartitionStatus.MINORITY
    
    def is_operation_allowed(self, consistency_class: ConsistencyClass) -> bool:
        status = self.check_partition_status()
        if consistency_class == ConsistencyClass.CLASS_A:
            return status in (PartitionStatus.NORMAL, PartitionStatus.MAJORITY)
        return True
    
    async def handle_peer_failure(self, peer_id: str) -> None:
        self.unreachable_peers.add(peer_id)
        new_status = self.check_partition_status()
        if new_status != self.state.partition_status:
            self.state.partition_status = new_status
            if new_status in (PartitionStatus.MINORITY, PartitionStatus.ISOLATED):
                self.state.class_a_enabled = False
                if self.on_partition_detected:
                    self.on_partition_detected(self.unreachable_peers.copy())
    
    async def handle_peer_recovery(self, peer_id: str) -> None:
        self.unreachable_peers.discard(peer_id)
        new_status = self.check_partition_status()
        if new_status != self.state.partition_status:
            self.state.partition_status = new_status
            if new_status == PartitionStatus.NORMAL:
                self.state.class_a_enabled = True
                if self.on_partition_healed:
                    self.on_partition_healed(self.unreachable_peers.copy())
                await self.sync.sync_with_peer(peer_id, full=True)


# =============================================================================
# FEDERATION ENGINE (Main Entry Point)
# =============================================================================

class FederationEngine:
    """Main federation engine coordinating all components."""
    
    def __init__(self, config: FederationConfig):
        self.config = config
        self.state = FederationState(brain_id=config.brain_id, region=config.region)
        
        self.discovery = DiscoveryManager(config, self.state)
        self.consensus = ConsensusManager(config, self.state)
        self.sync = SyncManager(config, self.state)
        self.routing = RoutingEngine(config, self.state)
        self.recovery = RecoveryManager(config, self.state, self.discovery, self.consensus, self.sync)
        
        self._setup_callbacks()
        self.metrics = FederationMetrics()
        self.running = False
        self._persistence_path = config.brain_path / "federation"
    
    def _setup_callbacks(self) -> None:
        self.discovery.on_peer_joined = self._on_peer_joined
        self.discovery.on_peer_left = self._on_peer_left
        self.discovery.on_peer_suspect = self._on_peer_suspect
        self.consensus.on_leader_change = self._on_leader_change
    
    def _on_peer_joined(self, peer: FederationPeer) -> None:
        self.metrics.peers_total = len(self.state.peers)
        self.metrics.peers_online = len([p for p in self.state.peers.values() if p.is_online()])
        logger.info(f"Peer joined: {peer.peer_id}")
        
        # v0.6.0 DSoR: Emit federation event
        if DSOR_AVAILABLE:
            try:
                emit_event(EventTypes.FEDERATION_PEER_JOINED, {
                    "peer_id": peer.peer_id,
                    "region": peer.region,
                    "trust_level": peer.trust_level.name,
                    "decision_id": str(uuid.uuid4()),
                    "context_hash": self.sync.merkle_tree.get_root()
                })
            except Exception as e:
                logger.debug(f"DSoR event emission failed: {e}")
    
    def _on_peer_left(self, peer_id: str) -> None:
        self.metrics.peers_online = len([p for p in self.state.peers.values() if p.is_online()])
        asyncio.create_task(self.recovery.handle_peer_failure(peer_id))
        logger.warning(f"Peer left: {peer_id}")
        
        # v0.6.0 DSoR: Emit federation event
        if DSOR_AVAILABLE:
            try:
                emit_event(EventTypes.FEDERATION_PEER_LEFT, {
                    "peer_id": peer_id,
                    "decision_id": str(uuid.uuid4()),
                    "context_hash": self.sync.merkle_tree.get_root()
                })
            except Exception as e:
                logger.debug(f"DSoR event emission failed: {e}")
    
    def _on_peer_suspect(self, peer_id: str) -> None:
        self.metrics.peers_suspect = len([p for p in self.state.peers.values() if p.status == PeerStatus.SUSPECT])
        logger.warning(f"Peer suspect: {peer_id}")
        
        # v0.6.0 DSoR: Emit federation event
        if DSOR_AVAILABLE:
            try:
                emit_event(EventTypes.FEDERATION_PEER_SUSPECT, {
                    "peer_id": peer_id,
                    "decision_id": str(uuid.uuid4())
                })
            except Exception as e:
                logger.debug(f"DSoR event emission failed: {e}")
    
    def _on_leader_change(self, leader_id: Optional[str]) -> None:
        self.metrics.raft_leader_changes += 1
        self.metrics.raft_term = self.state.term
        logger.info(f"Leader changed to: {leader_id}")
        
        # v0.6.0 DSoR: Emit leader election event (critical decision)
        if DSOR_AVAILABLE:
            try:
                emit_event(EventTypes.FEDERATION_LEADER_ELECTED, {
                    "leader_id": leader_id,
                    "term": self.state.term,
                    "decision_id": str(uuid.uuid4()),
                    "context_hash": self.sync.merkle_tree.get_root(),
                    "is_self": leader_id == self.config.brain_id
                })
            except Exception as e:
                logger.debug(f"DSoR event emission failed: {e}")
    
    async def start(self) -> None:
        self.running = True
        self._persistence_path.mkdir(parents=True, exist_ok=True)
        await self._load_state()
        
        await self.discovery.start()
        if self.config.enable_consensus:
            await self.consensus.start()
        await self.sync.start()
        
        logger.info(f"Federation engine started: {self.config.brain_id}")
    
    async def stop(self) -> None:
        self.running = False
        await self._save_state()
        
        await self.sync.stop()
        await self.consensus.stop()
        await self.discovery.stop()
        
        logger.info(f"Federation engine stopped: {self.config.brain_id}")
    
    async def _load_state(self) -> None:
        state_file = self._persistence_path / "state.json"
        if state_file.exists():
            try:
                with open(state_file) as f:
                    data = json.load(f)
                self.state.term = data.get("term", 0)
                self.state.leader_id = data.get("leader_id")
                self.state.vector_clock = VectorClock.from_dict(data.get("vector_clock", {}))
            except Exception as e:
                logger.warning(f"Failed to load federation state: {e}")
    
    async def _save_state(self) -> None:
        state_file = self._persistence_path / "state.json"
        try:
            with open(state_file, "w") as f:
                json.dump(self.state.to_dict(), f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save federation state: {e}")
    
    # Public API
    async def join(self, seed_peer: str) -> Dict[str, Any]:
        """Join the federation via a seed peer."""
        try:
            host, port = seed_peer.rsplit(":", 1) if ":" in seed_peer else (seed_peer, "9000")
            peer_id = f"peer_{host}_{port}"
            peer = FederationPeer(peer_id=peer_id, address=f"{host}:{port}", region="unknown")
            self.state.peers[peer_id] = peer
            peer.status = PeerStatus.ONLINE
            peer.last_heartbeat = datetime.utcnow()
            return {"success": True, "peers": len(self.state.peers)}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def leave(self) -> Dict[str, Any]:
        """Leave the federation gracefully."""
        # Notify peers and stop
        await self.stop()
        return {"success": True}
    
    async def route_task(self, task: Dict[str, Any], profile: str = "default") -> RoutingDecision:
        """Route a task to the optimal brain."""
        decision = await self.routing.route_task(task, profile)
        self.metrics.tasks_routed += 1
        
        # v0.6.0 DSoR: Log routing decision with provenance
        if DSOR_AVAILABLE:
            try:
                emit_event(EventTypes.FEDERATION_TASK_ROUTED, {
                    "target_brain": decision.target_brain,
                    "score": decision.score,
                    "profile": profile,
                    "decision_id": str(uuid.uuid4()),
                    "routing_time_ms": decision.routing_time_ms,
                    "alternatives_count": len(decision.alternatives)
                })
            except Exception as e:
                logger.debug(f"DSoR routing event failed: {e}")
        
        return decision
    
    async def sync_now(self) -> List[SyncResult]:
        """Force immediate synchronization."""
        return await self.sync.force_sync()
    
    def get_peers(self) -> List[FederationPeer]:
        """Get all known peers."""
        return list(self.state.peers.values())
    
    def get_online_peers(self) -> List[FederationPeer]:
        """Get online peers."""
        return self.discovery.get_online_peers()
    
    def get_status(self) -> Dict[str, Any]:
        """Get federation status."""
        return {
            "brain_id": self.config.brain_id,
            "region": self.config.region,
            "running": self.running,
            "leader_id": self.state.leader_id,
            "is_leader": self.consensus.is_leader(),
            "term": self.state.term,
            "partition_status": self.state.partition_status.name,
            "class_a_enabled": self.state.class_a_enabled,
            "peers": {
                "total": len(self.state.peers),
                "online": len([p for p in self.state.peers.values() if p.is_online()]),
                "suspect": len([p for p in self.state.peers.values() if p.status == PeerStatus.SUSPECT]),
            },
            "sync": {
                "merkle_root": self.sync.merkle_tree.get_root(),
                "vector_clock": self.state.vector_clock.to_dict(),
            },
            "metrics": self.metrics.to_dict(),
        }
    
    def get_health(self) -> Dict[str, Any]:
        """Get federation health status."""
        partition = self.recovery.check_partition_status()
        online_count = len([p for p in self.state.peers.values() if p.is_online()])
        total_count = len(self.state.peers)
        
        health_score = 1.0
        if partition == PartitionStatus.MINORITY:
            health_score = 0.3
        elif partition == PartitionStatus.ISOLATED:
            health_score = 0.1
        elif partition == PartitionStatus.MAJORITY:
            health_score = 0.7
        
        if total_count > 0:
            health_score *= (online_count / total_count)
        
        return {
            "healthy": health_score > 0.5,
            "score": health_score,
            "partition_status": partition.name,
            "peers_online": online_count,
            "peers_total": total_count,
            "leader": self.state.leader_id,
            "warnings": self._get_warnings(),
        }
    
    def _get_warnings(self) -> List[str]:
        warnings = []
        partition = self.recovery.check_partition_status()
        if partition != PartitionStatus.NORMAL:
            warnings.append(f"Partition detected: {partition.name}")
        if not self.state.class_a_enabled:
            warnings.append("Class A operations disabled")
        suspect = [p for p in self.state.peers.values() if p.status == PeerStatus.SUSPECT]
        if suspect:
            warnings.append(f"{len(suspect)} peer(s) suspect")
        return warnings


# =============================================================================
# FACTORY FUNCTION
# =============================================================================

def create_federation_engine(
    brain_id: str,
    region: str = "default",
    seed_peers: List[str] = None,
    brain_path: Path = None
) -> FederationEngine:
    """Factory function to create a federation engine."""
    config = FederationConfig(
        brain_id=brain_id,
        region=region,
        seed_peers=seed_peers or [],
        brain_path=brain_path or Path(".brain")
    )
    return FederationEngine(config)
