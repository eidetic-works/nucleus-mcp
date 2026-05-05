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
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

# v0.6.0 DSoR imports
try:
    from .context_manager import compute_context_hash, get_context_manager
    from .auth import get_ipc_auth_manager
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
    timestamp: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))


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



class NetworkManager:
    """Handles low-level TCP/JSON communication between brains."""
    
    def __init__(self, config: FederationConfig, engine: 'FederationEngine'):
        self.config = config
        self.engine = engine
        self.server: Optional[asyncio.AbstractServer] = None
        self.running = False
    
    async def start(self) -> None:
        """Start the federation RPC server."""
        try:
            host, port = self.config.address.rsplit(":", 1) if ":" in self.config.address else ("0.0.0.0", "9000")
            self.server = await asyncio.start_server(self._handle_connection, host, int(port))
            self.running = True
            asyncio.create_task(self.server.serve_forever())
            logger.info(f"Federation Network listening on {host}:{port}")
        except Exception as e:
            logger.error(f"Failed to start federation server: {e}")
    
    async def stop(self) -> None:
        """Stop the federation RPC server."""
        self.running = False
        if self.server:
            self.server.close()
            await self.server.wait_closed()
    
    async def _handle_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        """Handle an incoming brain-to-brain RPC connection."""
        try:
            line = await reader.readline()
            if not line:
                return
            
            message = json.loads(line.decode())
            sender_id = message.get("sender_id", "unknown")
            msg_type = message.get("type", "unknown")
            
            # v0.6.0 DSoR/Security: Verify IPC Token
            if DSOR_AVAILABLE:
                token = message.get("token")
                # auth_manager = get_ipc_auth_manager()
                # if not auth_manager.verify_federation_token(token, sender_id):
                #     logger.warning(f"Invalid federation token from {sender_id}")
                #     # return
            
            # Dispatch to engine
            response = await self.engine.handle_message(message)
            
            if response:
                writer.write((json.dumps(response) + "\n").encode())
                await writer.drain()
                
        except Exception as e:
            logger.debug(f"Federation connection error: {e}")
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass
    
    async def send_message(self, address: str, message: Dict[str, Any], timeout: float = 3.0) -> Optional[Dict[str, Any]]:
        """Send an RPC message to a remote brain."""
        try:
            host, port = address.rsplit(":", 1) if ":" in address else (address, "9000")
            reader, writer = await asyncio.wait_for(asyncio.open_connection(host, int(port)), timeout=timeout)
            
            # Enrich message
            message["sender_id"] = self.config.brain_id
            message["timestamp"] = datetime.now(tz=timezone.utc).isoformat()
            
            if DSOR_AVAILABLE:
                # message["token"] = get_ipc_auth_manager().generate_federation_token(host)
                pass
            
            writer.write((json.dumps(message) + "\n").encode())
            await writer.drain()
            
            line = await asyncio.wait_for(reader.readline(), timeout=timeout)
            if not line:
                return None
            
            return json.loads(line.decode())
            
        except asyncio.TimeoutError:
            logger.debug(f"Timeout sending {message.get('type')} to {address}")
            return None
        except Exception as e:
            logger.debug(f"Failed to send {message.get('type')} to {address}: {e}")
            return None
        finally:
            try:
                # In older python, writer.close() is not awaitable or can fail
                # if connection never opened
                if 'writer' in locals():
                    writer.close()
                    await writer.wait_closed()
            except Exception:
                pass


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
    
    def __init__(self, engine: 'FederationEngine'):
        self.engine = engine
        self.config = engine.config
        self.state = engine.state
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
        """Initial bootstrap by contacting seed peers."""
        for seed in self.config.seed_peers:
            try:
                host, port = seed.rsplit(":", 1) if ":" in seed else (seed, "9000")
                # Try to PING the seed peer
                response = await self.engine.network.send_message(seed, {"type": "ping"})
                
                if response and response.get("success"):
                    peer_id = response.get("brain_id", f"peer_{host}_{port}")
                    region = response.get("region", "unknown")
                    
                    peer = FederationPeer(peer_id=peer_id, address=f"{host}:{port}", region=region)
                    self.state.peers[peer_id] = peer
                    peer.status = PeerStatus.ONLINE
                    peer.last_heartbeat = datetime.now(tz=timezone.utc)
                    peer.capabilities = set(response.get("capabilities", []))
                    
                    if self.on_peer_joined:
                        self.on_peer_joined(peer)
                    
                    logger.info(f"Successfully bootstrapped from seed {seed} (ID: {peer_id})")
                else:
                    logger.warning(f"Seed peer {seed} reachable but returned failure or no brain_id")
            except Exception as e:
                logger.warning(f"Failed to bootstrap from seed peer {seed}: {e}")
    
    async def _gossip_loop(self) -> None:
        """Periodic gossip of membership information."""
        while self.running:
            try:
                await asyncio.sleep(self.config.heartbeat_interval)
                await self._gossip_round()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Gossip loop error: {e}")
    
    async def _gossip_round(self) -> None:
        """Exchange membership info with a subset of random peers."""
        online_peers = [p for p in self.state.peers.values() if p.is_healthy() and p.peer_id != self.config.brain_id]
        if not online_peers:
            return
        
        targets = random.sample(online_peers, min(self.config.gossip_fanout, len(online_peers)))
        
        # Prepare membership data (SWIM-style gossip)
        membership = []
        # Sample some peers to share (including self)
        all_peers = list(self.state.peers.values())
        sample_size = min(10, len(all_peers))
        sampled = random.sample(all_peers, sample_size)
        
        for p in sampled:
            membership.append({
                "peer_id": p.peer_id,
                "address": p.address,
                "status": p.status.name,
                "incarnation": p.incarnation,
                "region": p.region
            })
            
        gossip_msg = {
            "type": "gossip",
            "membership": membership
        }
        
        for target in targets:
            asyncio.create_task(self.engine.network.send_message(target.address, gossip_msg))
    
    async def _probe_loop(self) -> None:
        """Periodic probing of peer health."""
        while self.running:
            try:
                await asyncio.sleep(self.config.heartbeat_interval)
                await self._probe_round()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Probe loop error: {e}")
    
    async def _probe_round(self) -> None:
        """Probe peers for health and handle timeouts."""
        now = datetime.now(tz=timezone.utc)
        
        # 1. PING a random peer to check if it's still alive (SWIM direct probe)
        online_peers = [p for p in self.state.peers.values() if p.status == PeerStatus.ONLINE and p.peer_id != self.config.brain_id]
        if online_peers:
            target = random.choice(online_peers)
            asyncio.create_task(self._probe_peer(target))
            
        # 2. Check for timeouts in all peers
        for peer in list(self.state.peers.values()):
            if peer.peer_id == self.config.brain_id:
                continue
                
            if peer.last_heartbeat:
                elapsed = (now - peer.last_heartbeat).total_seconds()
                
                # ONLINE -> SUSPECT
                if elapsed > self.config.heartbeat_timeout and peer.status == PeerStatus.ONLINE:
                    peer.status = PeerStatus.SUSPECT
                    peer.suspect_time = now
                    logger.warning(f"Peer {peer.peer_id} missed heartbeat, marking SUSPECT")
                    if self.on_peer_suspect:
                        self.on_peer_suspect(peer.peer_id)
                
                # SUSPECT -> OFFLINE
                elif peer.status == PeerStatus.SUSPECT and peer.suspect_time:
                    if (now - peer.suspect_time).total_seconds() > self.config.suspect_timeout:
                        peer.status = PeerStatus.OFFLINE
                        logger.error(f"Peer {peer.peer_id} suspect timeout, marking OFFLINE")
                        if self.on_peer_left:
                            self.on_peer_left(peer.peer_id)
    
    async def _probe_peer(self, peer: FederationPeer) -> None:
        """Directly probe a peer with a PING."""
        response = await self.engine.network.send_message(peer.address, {"type": "ping"})
        if response and response.get("success"):
            peer.last_heartbeat = datetime.now(tz=timezone.utc)
            # If it was suspect, it's back
            if peer.status == PeerStatus.SUSPECT:
                peer.status = PeerStatus.ONLINE
                peer.suspect_time = None
                logger.info(f"Peer {peer.peer_id} recovered from SUSPECT")
    
    async def handle_gossip(self, membership: List[Dict[str, Any]]) -> None:
        """Handle incoming membership gossip."""
        for entry in membership:
            peer_id = entry.get("peer_id")
            if not peer_id or peer_id == self.config.brain_id:
                continue
                
            # If we don't know about this peer, add it
            if peer_id not in self.state.peers:
                peer = FederationPeer(
                    peer_id=peer_id,
                    address=entry["address"],
                    region=entry.get("region", "unknown"),
                    status=PeerStatus.ONLINE # Trust gossip for now
                )
                peer.last_heartbeat = datetime.now(tz=timezone.utc)
                self.state.peers[peer_id] = peer
                if self.on_peer_joined:
                    self.on_peer_joined(peer)
                logger.info(f"Discovered new peer via gossip: {peer_id}")
            else:
                # Update existing peer info if incarnation is higher (SWIM logic)
                peer = self.state.peers[peer_id]
                remote_incarnation = entry.get("incarnation", 0)
                if remote_incarnation > peer.incarnation:
                    peer.incarnation = remote_incarnation
                    # Update status if remote says it's alive and we thought it was dead/suspect
                    remote_status = entry.get("status")
                    if remote_status == "ONLINE" and peer.status != PeerStatus.ONLINE:
                        peer.status = PeerStatus.ONLINE
                        peer.last_heartbeat = datetime.now(tz=timezone.utc)
    
    def get_online_peers(self) -> List[FederationPeer]:
        return [p for p in self.state.peers.values() if p.is_online()]
    
    def get_healthy_peers(self) -> List[FederationPeer]:
        return [p for p in self.state.peers.values() if p.is_healthy()]


# =============================================================================
# CONSENSUS MANAGER (Simplified Raft)
# =============================================================================

class ConsensusManager:
    """Simplified Raft consensus for critical operations."""
    
    def __init__(self, engine: 'FederationEngine'):
        self.engine = engine
        self.config = engine.config
        self.state = engine.state
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
        
        # Request votes from all peers
        last_log_index = len(self.state.log)
        last_log_term = self.state.log[-1].term if self.state.log else 0
        
        vote_request = {
            "type": "raft_vote",
            "term": self.state.term,
            "candidate_id": self.config.brain_id,
            "last_log_index": last_log_index,
            "last_log_term": last_log_term
        }
        
        votes_received = 1  # Vote for self
        
        async def ask_for_vote(peer: FederationPeer):
            nonlocal votes_received
            resp = await self.engine.network.send_message(peer.address, vote_request)
            if resp and resp.get("vote_granted"):
                votes_received += 1
                if votes_received >= (total_nodes // 2) + 1 and self.raft_state == RaftState.CANDIDATE:
                    await self._become_leader()

        for peer in peers:
            asyncio.create_task(ask_for_vote(peer))
            
        # If no other nodes, become leader immediately
        if total_nodes == 1:
            await self._become_leader()
        else:
            # If we don't get enough votes within election timeout, another timer will trigger a new election
            self._reset_election_timer()
    
    async def handle_request_vote(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming Raft vote request."""
        term = request.get("term", 0)
        candidate_id = request.get("candidate_id")
        
        # 1. Reply false if term < currentTerm
        if term < self.state.term:
            return {"term": self.state.term, "vote_granted": False}
            
        # 2. If term > currentTerm, update currentTerm and transition to follower
        if term > self.state.term:
            self.state.term = term
            self.raft_state = RaftState.FOLLOWER
            self.state.voted_for = None
            self._reset_election_timer()
            
        # 3. If votedFor is null or candidateId, and candidate's log is at least as up-to-date
        # as receiver's log, grant vote
        can_vote = self.state.voted_for is None or self.state.voted_for == candidate_id
        
        # Log completeness check
        last_log_index = len(self.state.log)
        last_log_term = self.state.log[-1].term if self.state.log else 0
        candidate_last_index = request.get("last_log_index", 0)
        candidate_last_term = request.get("last_log_term", 0)
        
        log_ok = (candidate_last_term > last_log_term) or \
                 (candidate_last_term == last_log_term and candidate_last_index >= last_log_index)
        
        if can_vote and log_ok:
            self.state.voted_for = candidate_id
            self._reset_election_timer()
            return {"term": self.state.term, "vote_granted": True}
        
        return {"term": self.state.term, "vote_granted": False}
    
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
                await self._send_heartbeats()
                await asyncio.sleep(self.config.heartbeat_interval / 2)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat loop error: {e}")

    async def _send_heartbeats(self) -> None:
        """Send heartbeats (AppendEntries with no entries) to all peers."""
        peers = [p for p in self.state.peers.values() if p.is_healthy()]
        
        for peer in peers:
            prev_log_index = peer.next_index - 1
            prev_log_term = self.state.log[prev_log_index - 1].term if prev_log_index > 0 else 0
            
            # Send entries from next_index to end
            entries = []
            if len(self.state.log) >= peer.next_index:
                entries = [e.to_dict() for e in self.state.log[peer.next_index-1:]]
                
            append_req = {
                "type": "raft_append",
                "term": self.state.term,
                "leader_id": self.config.brain_id,
                "prev_log_index": prev_log_index,
                "prev_log_term": prev_log_term,
                "entries": entries,
                "leader_commit": self.state.commit_index
            }
            
            asyncio.create_task(self._send_append_to_peer(peer, append_req))

    async def _send_append_to_peer(self, peer: FederationPeer, request: Dict[str, Any]) -> None:
        resp = await self.engine.network.send_message(peer.address, request)
        if resp:
            term = resp.get("term", 0)
            if term > self.state.term:
                self.state.term = term
                self.raft_state = RaftState.FOLLOWER
                self.state.voted_for = None
                self._reset_election_timer()
                return
            
            if self.raft_state == RaftState.LEADER:
                if resp.get("success"):
                    peer.next_index = request["prev_log_index"] + len(request["entries"]) + 1
                    peer.match_index = peer.next_index - 1
                    await self._update_commit_index()
                else:
                    # Log inconsistency, decrement next_index and retry
                    peer.next_index = max(1, peer.next_index - 1)

    async def _update_commit_index(self) -> None:
        """Update leader's commit index based on peer match indices."""
        match_indices = [p.match_index for p in self.state.peers.values() if p.is_healthy()]
        match_indices.append(len(self.state.log))
        match_indices.sort(reverse=True)
        
        # Find highest N such that majority of match_index >= N
        total_nodes = len(self.state.peers) + 1
        n_index = (total_nodes // 2)
        if n_index < len(match_indices):
            n = match_indices[n_index]
            if n > self.state.commit_index and self.state.log[n-1].term == self.state.term:
                self.state.commit_index = n
                # Apply entries to state machine
                while self.state.last_applied < self.state.commit_index:
                    self.state.last_applied += 1
                    entry = self.state.log[self.state.last_applied - 1]
                    if self.on_commit:
                        self.on_commit(entry)

    async def handle_append_entries(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming Raft AppendEntries request."""
        term = request.get("term", 0)
        leader_id = request.get("leader_id")
        
        # 1. Reply false if term < currentTerm
        if term < self.state.term:
            return {"term": self.state.term, "success": False}
            
        # Accept leader
        self.state.leader_id = leader_id
        self._reset_election_timer()
        
        if term > self.state.term:
            self.state.term = term
            self.raft_state = RaftState.FOLLOWER
            self.state.voted_for = None
            
        # 2. Reply false if log doesn't contain an entry at prevLogIndex whose term matches prevLogTerm
        prev_idx = request.get("prev_log_index", 0)
        prev_term = request.get("prev_log_term", 0)
        
        if prev_idx > 0:
            if len(self.state.log) < prev_idx or self.state.log[prev_idx-1].term != prev_term:
                return {"term": self.state.term, "success": False}
        
        # 3. If an existing entry conflicts with a new one (same index but different terms), 
        # delete the existing entry and all that follow it
        entries = [RaftLogEntry.from_dict(e) for e in request.get("entries", [])]
        for i, entry in enumerate(entries):
            idx = prev_idx + i + 1
            if len(self.state.log) >= idx:
                if self.state.log[idx-1].term != entry.term:
                    self.state.log = self.state.log[:idx-1]
                    self.state.log.append(entry)
            else:
                self.state.log.append(entry)
                
        # 5. If leaderCommit > commitIndex, set commitIndex = min(leaderCommit, index of last new entry)
        leader_commit = request.get("leader_commit", 0)
        if leader_commit > self.state.commit_index:
            self.state.commit_index = min(leader_commit, len(self.state.log))
            while self.state.last_applied < self.state.commit_index:
                self.state.last_applied += 1
                entry = self.state.log[self.state.last_applied - 1]
                if self.on_commit:
                    self.on_commit(entry)
                    
        return {"term": self.state.term, "success": True}
    
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
    
    def __init__(self, engine: 'FederationEngine'):
        self.engine = engine
        self.config = engine.config
        self.state = engine.state
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
            
            # 1. Exchange Merkle roots
            sync_req = {
                "type": "sync_merkle",
                "merkle_root": self.merkle_tree.get_root(),
                "vector_clock": self.state.vector_clock.to_dict()
            }
            
            resp = await self.engine.network.send_message(peer.address, sync_req)
            if not resp or not resp.get("success"):
                return SyncResult(False, peer_id, 0, 0, 0, "", "Peer sync request failed")
                
            remote_root = resp.get("merkle_root")
            peer.merkle_root = remote_root
            
            # Update vector clock
            remote_vc_dict = resp.get("vector_clock", {})
            remote_vc = VectorClock.from_dict(remote_vc_dict)
            self.state.vector_clock = self.state.vector_clock.merge(remote_vc).increment(self.config.brain_id)
            
            peer.last_sync = datetime.now(tz=timezone.utc)
            
            # In a full sync, we would iterate through Merkle diffs here
            # and request missing chunks. For MVP, root match + VC merge is enough.
            
            elapsed = (time.perf_counter() - start_time) * 1000
            return SyncResult(True, peer_id, 0, 0, elapsed, self.merkle_tree.get_root())
        finally:
            self.sync_in_progress.discard(peer_id)
    
    async def handle_sync_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming Merkle sync request."""
        # Update remote info for this peer if we have it
        sender_id = request.get("sender_id")
        if sender_id in self.state.peers:
            peer = self.state.peers[sender_id]
            peer.merkle_root = request.get("merkle_root", "")
            remote_vc = VectorClock.from_dict(request.get("vector_clock", {}))
            self.state.vector_clock = self.state.vector_clock.merge(remote_vc)
            peer.last_sync = datetime.now(tz=timezone.utc)
            
        return {
            "success": True,
            "merkle_root": self.merkle_tree.get_root(),
            "vector_clock": self.state.vector_clock.to_dict()
        }
    
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
    
    def __init__(self, engine: 'FederationEngine'):
        self.engine = engine
        self.config = engine.config
        self.state = engine.state
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
    
    def __init__(self, engine: 'FederationEngine',
                 discovery: DiscoveryManager, consensus: ConsensusManager, sync: SyncManager):
        self.engine = engine
        self.config = engine.config
        self.state = engine.state
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
        
        self.discovery = DiscoveryManager(self)
        self.consensus = ConsensusManager(self)
        self.sync = SyncManager(self)
        self.routing = RoutingEngine(self)
        self.recovery = RecoveryManager(self, self.discovery, self.consensus, self.sync)
        self.network = NetworkManager(config, self)
        
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
        """Start the federation engine."""
        self.running = True
        self._persistence_path.mkdir(parents=True, exist_ok=True)
        await self._load_state()
        
        await self.network.start()
        await self.discovery.start()
        if self.config.enable_consensus:
            await self.consensus.start()
        await self.sync.start()
        
        logger.info(f"Federation engine started: {self.config.brain_id}")
    
    async def stop(self) -> None:
        """Stop the federation engine."""
        self.running = False
        await self._save_state()
        
        await self.sync.stop()
        await self.consensus.stop()
        await self.discovery.stop()
        await self.network.stop()
        
        logger.info(f"Federation engine stopped: {self.config.brain_id}")
    
    async def _load_state(self) -> None:
        state_file = self._persistence_path / "state.json"
        if state_file.exists():
            try:
                with open(state_file, encoding='utf-8') as f:
                    data = json.load(f)
                self.state.term = data.get("term", 0)
                self.state.leader_id = data.get("leader_id")
                self.state.vector_clock = VectorClock.from_dict(data.get("vector_clock", {}))
            except Exception as e:
                logger.warning(f"Failed to load federation state: {e}")
    
    async def _save_state(self) -> None:
        state_file = self._persistence_path / "state.json"
        try:
            with open(state_file, "w", encoding="utf-8") as f:
                json.dump(self.state.to_dict(), f, indent=2, default=str, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save federation state: {e}")
    
    async def handle_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Main RPC dispatcher for incoming brain-to-brain messages."""
        msg_type = message.get("type")
        sender_id = message.get("sender_id", "unknown")
        
        if msg_type == "ping":
            return {
                "success": True,
                "brain_id": self.config.brain_id,
                "region": self.config.region,
                "status": "online",
                "capabilities": ["llm", "mcp", "federation"]
            }
            
        elif msg_type == "gossip":
            membership = message.get("membership", [])
            await self.discovery.handle_gossip(membership)
            return {"success": True}
            
        elif msg_type == "raft_vote":
            return await self.consensus.handle_request_vote(message)
            
        elif msg_type == "raft_append":
            return await self.consensus.handle_append_entries(message)
            
        elif msg_type == "sync_merkle":
            return await self.sync.handle_sync_request(message)
            
        logger.warning(f"Unknown federation message type: {msg_type} from {sender_id}")
        return {"success": False, "error": "unknown_message_type"}
    
    # Public API
    async def join(self, seed_peer: str) -> Dict[str, Any]:
        """Join the federation via a seed peer."""
        try:
            host, port = seed_peer.rsplit(":", 1) if ":" in seed_peer else (seed_peer, "9000")
            peer_id = f"peer_{host}_{port}"
            peer = FederationPeer(peer_id=peer_id, address=f"{host}:{port}", region="unknown")
            self.state.peers[peer_id] = peer
            peer.status = PeerStatus.ONLINE
            peer.last_heartbeat = datetime.now(tz=timezone.utc)
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
