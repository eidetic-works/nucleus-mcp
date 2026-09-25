"""Federation Operations — Federation engine MCP tool implementations.

Extracted from __init__.py (Phase 5 Federation Engine).
Contains:
- _get_federation_engine: Singleton for FederationEngine
- _brain_federation_status_impl
- _brain_federation_join_impl
- _brain_federation_leave_impl
- _brain_federation_peers_impl
- _brain_federation_sync_impl
- _brain_federation_route_impl
- _brain_federation_health_impl
"""

import asyncio
import enum
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from .common import get_brain_path
from .event_ops import _emit_event

logger = logging.getLogger("mcp_server_nucleus")


def _surface() -> str:
    """Resolve current surface from CC_SESSION_ROLE env var (per E3 spec)."""
    role = os.environ.get("CC_SESSION_ROLE", "").strip().lower()
    return role if role in ("main", "peer") else "unknown"


def _sanitize_to_primitives(obj: Any) -> Any:
    """Recursively coerce a value into JSON-primitive-safe types.

    Walks dicts/lists/tuples and converts non-serializable leaves to
    primitives: enums → ``.name``, ``Path`` → ``str``, ``datetime`` →
    isoformat, bytes → decoded str. Anything else that isn't already a
    JSON primitive is stringified as a last resort so ``json.dumps``
    never raises on federation status payloads.
    """
    if isinstance(obj, dict):
        return {str(k): _sanitize_to_primitives(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_sanitize_to_primitives(v) for v in obj]
    if isinstance(obj, enum.Enum):
        return obj.name
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, (bytes, bytearray)):
        try:
            return obj.decode("utf-8")
        except UnicodeDecodeError:
            return obj.hex()
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    try:
        return str(obj)
    except Exception:
        logger.debug("Swallowed exception in _sanitize_to_primitives", exc_info=True)
        return None


# ── Singleton ────────────────────────────────────────────────────
_federation_engine = None


def _get_federation_engine():
    """Get or create the federation engine singleton."""
    global _federation_engine
    if _federation_engine is None:
        try:
            from .federation import FederationEngine, FederationConfig
            brain_path = get_brain_path()
            config = FederationConfig(
                brain_id=f"brain_{brain_path.name}",
                region="default",
                brain_path=brain_path,
            )
            _federation_engine = FederationEngine(config)
        except ImportError:
            return None
        except Exception as e:
            logger.warning(f"Failed to initialize FederationEngine: {e}")
            return None
    return _federation_engine


# ── Implementations ──────────────────────────────────────────────

def _brain_federation_status_impl() -> str:
    """Internal implementation of federation status."""
    try:
        engine = _get_federation_engine()
        if engine is None:
            _emit_event("federation_status_failed", "nucleus_federation", {
                "action": "status",
                "reason": "engine_unavailable",
                "surface": _surface(),
            })
            return "❌ FederationEngine not available."

        status = engine.get_status()
        health = engine.get_health()
        
        # Format peer list
        peers = status.get("peers", {})
        peer_list = []
        for peer in engine.get_peers():
            icon = "🟢" if peer.is_online() else "🟡" if peer.status.name == "SUSPECT" else "🔴"
            peer_list.append(f"   {icon} {peer.peer_id} ({peer.region}) - {peer.latency_ms:.1f}ms")
        
        peer_display = "\n".join(peer_list) if peer_list else "   No peers discovered"
        
        warnings = health.get("warnings", [])
        warning_display = "\n".join(f"   ⚠️ {w}" for w in warnings) if warnings else "   None"
        
        _result = f"""🌐 FEDERATION STATUS
═══════════════════════════════════════

🧠 LOCAL BRAIN
   ID: {status['brain_id']}
   Region: {status['region']}
   Running: {'✅' if status['running'] else '❌'}

👑 CONSENSUS
   Leader: {status['leader_id'] or 'None'}
   Is Leader: {'✅' if status['is_leader'] else '❌'}
   Term: {status['term']}

🔗 PEERS ({peers.get('online', 0)}/{peers.get('total', 0)} online)
{peer_display}

📡 PARTITION STATUS
   Status: {status['partition_status']}
   Class A Enabled: {'✅' if status['class_a_enabled'] else '❌'}

💚 HEALTH
   Score: {health['score']:.0%}
   Healthy: {'✅' if health['healthy'] else '❌'}

⚠️ WARNINGS
{warning_display}

🔄 SYNC
   Merkle Root: {status['sync']['merkle_root'][:16]}...
   Vector Clock: {len(status['sync']['vector_clock'])} entries"""
        _emit_event("federation_status_succeeded", "nucleus_federation", {
            "action": "status",
            "brain_id": status.get("brain_id"),
            "running": status.get("running"),
            "is_leader": status.get("is_leader"),
            "peers_online": status.get("peers", {}).get("online", 0),
            "peers_total": status.get("peers", {}).get("total", 0),
            "health_score": health.get("score"),
            "surface": _surface(),
        })
        return _result

    except Exception as e:
        _emit_event("federation_status_failed", "nucleus_federation", {
            "action": "status",
            "error": str(e),
            "surface": _surface(),
        })
        return f"❌ Federation status error: {str(e)}"


def _brain_federation_status_json_impl() -> str:
    """Internal implementation of federation status as a JSON string.

    Returns a primitive-sanitized JSON payload (suitable for consumption
    by other modules such as ``pm_view_ops``). Emits ``_emit_event``
    telemetry on both success and failure paths and degrades gracefully
    to a safe standalone-mode payload when the ``FederationEngine`` is
    unavailable or raises.

    Contract (consumed by ``pm_view_ops._brain_pm_summary_impl``):
    - ``peers``: ``{"total": int, "online": int, "suspect": int}``
    - ``sovereign_mode``: bool — True when running with ≥1 peer
      (participating in federation consensus); False when standalone.
    """
    try:
        engine = _get_federation_engine()
        if engine is None:
            _emit_event("federation_status_json_failed", "nucleus_federation", {
                "action": "status_json",
                "reason": "engine_unavailable",
                "surface": _surface(),
            })
            return json.dumps({
                "available": False,
                "running": False,
                "sovereign_mode": False,
                "peers": {"total": 0, "online": 0, "suspect": 0},
                "reason": "engine_unavailable",
            })

        status = engine.get_status()
        peers_raw = status.get("peers", {})
        peers = peers_raw if isinstance(peers_raw, dict) else {}
        running = bool(status.get("running", False))
        peers_total = int(peers.get("total", 0) or 0)
        # Sovereign mode: participating in federation consensus
        # (engine running and at least one peer discovered).
        sovereign_mode = running and peers_total > 0

        payload = {
            "available": True,
            "brain_id": status.get("brain_id"),
            "region": status.get("region"),
            "running": running,
            "leader_id": status.get("leader_id"),
            "is_leader": bool(status.get("is_leader", False)),
            "term": status.get("term"),
            "partition_status": status.get("partition_status"),
            "class_a_enabled": bool(status.get("class_a_enabled", False)),
            "peers": {
                "total": peers_total,
                "online": int(peers.get("online", 0) or 0),
                "suspect": int(peers.get("suspect", 0) or 0),
            },
            "sovereign_mode": sovereign_mode,
            "sync": status.get("sync", {}),
            "metrics": status.get("metrics", {}),
        }

        sanitized = _sanitize_to_primitives(payload)

        _emit_event("federation_status_json_succeeded", "nucleus_federation", {
            "action": "status_json",
            "brain_id": sanitized.get("brain_id"),
            "running": sanitized.get("running"),
            "is_leader": sanitized.get("is_leader"),
            "peers_online": sanitized.get("peers", {}).get("online", 0),
            "peers_total": sanitized.get("peers", {}).get("total", 0),
            "sovereign_mode": sanitized.get("sovereign_mode"),
            "surface": _surface(),
        })
        return json.dumps(sanitized, indent=2, ensure_ascii=False)

    except Exception as e:
        _emit_event("federation_status_json_failed", "nucleus_federation", {
            "action": "status_json",
            "error": str(e),
            "surface": _surface(),
        })
        return json.dumps({
            "available": False,
            "running": False,
            "sovereign_mode": False,
            "peers": {"total": 0, "online": 0, "suspect": 0},
            "error": str(e),
        })


async def _brain_federation_join_impl(seed_peer: str) -> str:
    """Internal implementation of federation join."""
    try:
        engine = _get_federation_engine()
        if engine is None:
            _emit_event("federation_join_failed", "nucleus_federation", {
                "action": "join",
                "seed_peer": seed_peer,
                "reason": "engine_unavailable",
                "surface": _surface(),
            })
            return "❌ FederationEngine not available."

        # Start engine if not running
        if not engine.running:
            await engine.start()

        result = await engine.join(seed_peer)

        if result.get("success"):
            _emit_event("federation_join_succeeded", "nucleus_federation", {
                "action": "join",
                "seed_peer": seed_peer,
                "peers": result.get("peers", 0),
                "surface": _surface(),
            })
            return f"""✅ JOINED FEDERATION
   Seed Peer: {seed_peer}
   Total Peers: {result.get('peers', 0)}

💡 Federation engine is now active and syncing"""
        else:
            _emit_event("federation_join_failed", "nucleus_federation", {
                "action": "join",
                "seed_peer": seed_peer,
                "reason": "join_returned_failure",
                "error": result.get("error", "Unknown error"),
                "surface": _surface(),
            })
            return f"❌ Failed to join: {result.get('error', 'Unknown error')}"

    except Exception as e:
        _emit_event("federation_join_failed", "nucleus_federation", {
            "action": "join",
            "seed_peer": seed_peer,
            "error": str(e),
            "surface": _surface(),
        })
        return f"❌ Join error: {str(e)}"


async def _brain_federation_leave_impl() -> str:
    """Internal implementation of federation leave."""
    try:
        engine = _get_federation_engine()
        if engine is None:
            _emit_event("federation_leave_failed", "nucleus_federation", {
                "action": "leave",
                "reason": "engine_unavailable",
                "surface": _surface(),
            })
            return "❌ FederationEngine not available."

        result = await engine.leave()

        if result.get("success"):
            _emit_event("federation_leave_succeeded", "nucleus_federation", {
                "action": "leave",
                "surface": _surface(),
            })
            return """✅ LEFT FEDERATION

Federation engine stopped gracefully.
Local brain now operating in standalone mode."""
        else:
            _emit_event("federation_leave_failed", "nucleus_federation", {
                "action": "leave",
                "reason": "leave_returned_failure",
                "error": result.get("error", "Unknown error"),
                "surface": _surface(),
            })
            return f"❌ Failed to leave: {result.get('error', 'Unknown error')}"

    except Exception as e:
        _emit_event("federation_leave_failed", "nucleus_federation", {
            "action": "leave",
            "error": str(e),
            "surface": _surface(),
        })
        return f"❌ Leave error: {str(e)}"


def _brain_federation_peers_impl() -> str:
    """Internal implementation of federation peers list."""
    try:
        engine = _get_federation_engine()
        if engine is None:
            _emit_event("federation_peers_failed", "nucleus_federation", {
                "action": "peers",
                "reason": "engine_unavailable",
                "surface": _surface(),
            })
            return "❌ FederationEngine not available."

        peers = engine.get_peers()

        if not peers:
            _emit_event("federation_peers_succeeded", "nucleus_federation", {
                "action": "peers",
                "peer_count": 0,
                "surface": _surface(),
            })
            return """🔗 FEDERATION PEERS
═══════════════════════════════════════

No peers discovered.

💡 Use brain_federation_join(seed_peer) to connect to a federation."""
        
        lines = ["🔗 FEDERATION PEERS", "═══════════════════════════════════════", ""]
        
        for peer in peers:
            status_icon = {
                "ONLINE": "🟢",
                "SUSPECT": "🟡", 
                "OFFLINE": "🔴",
                "QUARANTINED": "⛔",
                "UNKNOWN": "❓",
            }.get(peer.status.name, "❓")
            
            trust_icon = {
                "OWNER": "👑",
                "ADMIN": "🛡️",
                "MEMBER": "👤",
                "GUEST": "👁️",
            }.get(peer.trust_level.name, "👤")
            
            lines.append(f"{status_icon} {peer.peer_id}")
            lines.append(f"   Address: {peer.address}")
            lines.append(f"   Region: {peer.region}")
            lines.append(f"   Trust: {trust_icon} {peer.trust_level.name}")
            lines.append(f"   Latency: {peer.latency_ms:.1f}ms")
            lines.append(f"   Load: {peer.load:.0%}")
            lines.append(f"   Capabilities: {', '.join(peer.capabilities) or 'None'}")
            lines.append("")

        _emit_event("federation_peers_succeeded", "nucleus_federation", {
            "action": "peers",
            "peer_count": len(peers),
            "surface": _surface(),
        })
        return "\n".join(lines)

    except Exception as e:
        _emit_event("federation_peers_failed", "nucleus_federation", {
            "action": "peers",
            "error": str(e),
            "surface": _surface(),
        })
        return f"❌ Peers error: {str(e)}"


async def _brain_federation_sync_impl() -> str:
    """Internal implementation of federation sync."""
    try:
        engine = _get_federation_engine()
        if engine is None:
            _emit_event("federation_sync_failed", "nucleus_federation", {
                "action": "sync",
                "reason": "engine_unavailable",
                "surface": _surface(),
            })
            return "❌ FederationEngine not available."

        if not engine.running:
            _emit_event("federation_sync_failed", "nucleus_federation", {
                "action": "sync",
                "reason": "engine_not_running",
                "surface": _surface(),
            })
            return "❌ Federation engine not running. Use brain_federation_join first."

        results = await engine.sync_now()

        if not results:
            _emit_event("federation_sync_completed", "nucleus_federation", {
                "action": "sync",
                "peers_synced": 0,
                "items_synced": 0,
                "conflicts_resolved": 0,
                "surface": _surface(),
            })
            return """🔄 SYNC COMPLETE

No peers to sync with."""
        
        lines = ["🔄 SYNC RESULTS", "═══════════════════════════════════════", ""]
        
        total_synced = 0
        total_conflicts = 0
        
        for result in results:
            icon = "✅" if result.success else "❌"
            lines.append(f"{icon} {result.peer_id}")
            lines.append(f"   Items synced: {result.items_synced}")
            lines.append(f"   Conflicts resolved: {result.conflicts_resolved}")
            lines.append(f"   Time: {result.sync_time_ms:.2f}ms")
            if result.error:
                lines.append(f"   Error: {result.error}")
            lines.append("")
            
            total_synced += result.items_synced
            total_conflicts += result.conflicts_resolved
        
        lines.append("📊 TOTALS")
        lines.append(f"   Peers synced: {len(results)}")
        lines.append(f"   Items synced: {total_synced}")
        lines.append(f"   Conflicts resolved: {total_conflicts}")

        _emit_event("federation_sync_completed", "nucleus_federation", {
            "action": "sync",
            "peers_synced": len(results),
            "items_synced": total_synced,
            "conflicts_resolved": total_conflicts,
            "successes": sum(1 for r in results if r.success),
            "failures": sum(1 for r in results if not r.success),
            "surface": _surface(),
        })
        return "\n".join(lines)

    except Exception as e:
        _emit_event("federation_sync_failed", "nucleus_federation", {
            "action": "sync",
            "error": str(e),
            "surface": _surface(),
        })
        return f"❌ Sync error: {str(e)}"


async def _brain_federation_route_impl(task_id: str, profile: str = "default") -> str:
    """Internal implementation of federation routing."""
    try:
        engine = _get_federation_engine()
        if engine is None:
            _emit_event("federation_route_failed", "nucleus_federation", {
                "action": "route",
                "task_id": task_id,
                "profile": profile,
                "reason": "engine_unavailable",
                "surface": _surface(),
            })
            return "❌ FederationEngine not available."

        # Get task from task store
        task = {"id": task_id}
        
        # Try to get full task details
        try:
            tasks_file = get_brain_path() / "ledger" / "tasks.json"
            if tasks_file.exists():
                with open(tasks_file, encoding='utf-8') as f:
                    tasks_data = json.load(f)
                for t in tasks_data.get("tasks", []):
                    if t.get("id") == task_id or t.get("description", "").startswith(task_id):
                        task = t
                        break
        except Exception:
            logger.debug("Swallowed exception in _brain_federation_route_impl", exc_info=True)
            pass
        
        decision = await engine.route_task(task, profile)

        _emit_event("federation_route_succeeded", "nucleus_federation", {
            "action": "route",
            "task_id": task_id,
            "profile": profile,
            "target_brain": decision.target_brain,
            "score": decision.score,
            "routing_time_ms": decision.routing_time_ms,
            "alternatives_count": len(decision.alternatives),
            "surface": _surface(),
        })
        return f"""🎯 ROUTING DECISION
═══════════════════════════════════════

📋 Task: {task_id}
📊 Profile: {profile}

🏆 TARGET
   Brain: {decision.target_brain}
   Score: {decision.score:.3f}

⏱️ ROUTING TIME
   {decision.routing_time_ms:.3f}ms

🔄 ALTERNATIVES
{chr(10).join(f'   {i+1}. {alt[0]} (score: {alt[1]:.3f})' for i, alt in enumerate(decision.alternatives[:3])) or '   None'}

💡 Task should be executed on {decision.target_brain}"""

    except Exception as e:
        _emit_event("federation_route_failed", "nucleus_federation", {
            "action": "route",
            "task_id": task_id,
            "profile": profile,
            "error": str(e),
            "surface": _surface(),
        })
        return f"❌ Routing error: {str(e)}"


def _brain_federation_health_impl() -> str:
    """Internal implementation of federation health."""
    try:
        engine = _get_federation_engine()
        if engine is None:
            _emit_event("federation_health_failed", "nucleus_federation", {
                "action": "health",
                "reason": "engine_unavailable",
                "surface": _surface(),
            })
            return "❌ FederationEngine not available."

        health = engine.get_health()
        metrics = engine.metrics
        
        # Health bar
        score = health["score"]
        bar_filled = int(score * 20)
        bar_empty = 20 - bar_filled
        health_bar = "█" * bar_filled + "░" * bar_empty
        
        # Status color
        if score >= 0.8:
            status = "🟢 HEALTHY"
        elif score >= 0.5:
            status = "🟡 DEGRADED"
        else:
            status = "🔴 CRITICAL"
        
        _emit_event("federation_health_succeeded", "nucleus_federation", {
            "action": "health",
            "score": score,
            "healthy": health.get("healthy"),
            "partition_status": health.get("partition_status"),
            "peers_online": health.get("peers_online"),
            "peers_total": health.get("peers_total"),
            "warnings_count": len(health.get("warnings", [])),
            "tasks_routed": metrics.tasks_routed,
            "sync_operations": metrics.sync_operations,
            "surface": _surface(),
        })
        return f"""💚 FEDERATION HEALTH
═══════════════════════════════════════

{status}
[{health_bar}] {score:.0%}

📊 PARTITION
   Status: {health['partition_status']}
   Peers Online: {health['peers_online']}/{health['peers_total']}
   Leader: {health['leader'] or 'None'}

📈 METRICS
   Tasks Routed: {metrics.tasks_routed}
   Avg Routing Time: {metrics.avg_routing_time_ms:.3f}ms
   Sync Operations: {metrics.sync_operations}
   Leader Changes: {metrics.raft_leader_changes}
   Partition Events: {metrics.partition_events}

⚠️ WARNINGS ({len(health['warnings'])})
{chr(10).join(f'   • {w}' for w in health['warnings']) or '   None'}"""

    except Exception as e:
        _emit_event("federation_health_failed", "nucleus_federation", {
            "action": "health",
            "error": str(e),
            "surface": _surface(),
        })
        return f"❌ Health error: {str(e)}"
