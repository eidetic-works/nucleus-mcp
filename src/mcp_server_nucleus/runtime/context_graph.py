"""Context Graph — Engram Relationship Mapping.

Builds a lightweight in-memory graph of engram relationships based on:
1. Shared context categories (Feature, Architecture, Brand, Strategy, Decision)
2. Key prefix clustering (e.g., fusion_capture_*, phase3_*)
3. Temporal proximity (engrams written within N seconds of each other)
4. Value similarity (shared keywords between engram values)

The graph is computed on-demand from the engram ledger (no separate persistence).
This keeps it consistent with the source of truth and avoids stale state.

Usage:
    from mcp_server_nucleus.runtime.context_graph import build_context_graph
    graph = build_context_graph()
"""

import json
import re
from collections import defaultdict
from datetime import datetime
from typing import Dict, Any, List, Optional, Set, Tuple

from .common import get_brain_path, make_response


# ── Configuration ─────────────────────────────────────────────
MAX_ENGRAMS = 500          # Safety cap on engrams to process
TEMPORAL_WINDOW_SECS = 60  # Engrams within 60s are temporally linked
MIN_KEYWORD_OVERLAP = 2    # Minimum shared keywords for value similarity
STOP_WORDS = frozenset({
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "need", "must", "to", "of",
    "in", "for", "on", "with", "at", "by", "from", "as", "into", "about",
    "and", "or", "but", "not", "no", "if", "then", "than", "that", "this",
    "it", "its", "all", "each", "every", "both", "few", "more", "most",
    "other", "some", "such", "only", "own", "so", "up", "out", "now",
})


def _extract_keywords(text: str) -> Set[str]:
    """Extract meaningful keywords from text, removing stop words."""
    words = re.findall(r'[a-zA-Z]{3,}', text.lower())
    return {w for w in words if w not in STOP_WORDS}


def _get_key_prefix(key: str) -> str:
    """Extract prefix from an engram key (e.g., 'fusion_capture_20260301' → 'fusion_capture')."""
    # Remove trailing timestamps/numbers
    cleaned = re.sub(r'_?\d{8,}$', '', key)
    cleaned = re.sub(r'_?\d+$', '', cleaned)
    return cleaned if cleaned else key


def _parse_timestamp(ts_str: str) -> Optional[float]:
    """Parse ISO timestamp to epoch seconds."""
    try:
        dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        return dt.timestamp()
    except (ValueError, TypeError):
        return None


def _load_engrams() -> List[Dict]:
    """Load engrams from ledger with safety cap."""
    brain = get_brain_path()
    ledger = brain / "engrams" / "ledger.jsonl"
    if not ledger.exists():
        return []

    engrams = []
    with open(ledger, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    engrams.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

    # Sort by timestamp (most recent first) and cap
    engrams.sort(key=lambda e: e.get("timestamp", ""), reverse=True)
    return engrams[:MAX_ENGRAMS]


def build_context_graph(
    include_edges: bool = True,
    min_intensity: int = 1,
) -> Dict[str, Any]:
    """Build the context graph from the engram ledger.

    Args:
        include_edges: Whether to include edge list (can be large).
        min_intensity: Minimum engram intensity to include.

    Returns:
        Dict with nodes, edges, clusters, and statistics.
    """
    engrams = _load_engrams()

    # Filter by intensity
    engrams = [e for e in engrams if e.get("intensity", 5) >= min_intensity]

    if not engrams:
        return {
            "nodes": [],
            "edges": [],
            "clusters": {},
            "stats": {"node_count": 0, "edge_count": 0, "unique_pairs": 0, "cluster_count": 0, "edge_types": {}, "contexts": {}, "avg_intensity": 0, "density": 0},
        }

    # ── Build nodes ───────────────────────────────────────────
    nodes = []
    key_to_idx: Dict[str, int] = {}
    for i, e in enumerate(engrams):
        key = e.get("key", f"unknown_{i}")
        key_to_idx[key] = i
        nodes.append({
            "id": key,
            "context": e.get("context", "Unknown"),
            "intensity": e.get("intensity", 5),
            "prefix": _get_key_prefix(key),
            "keywords": list(_extract_keywords(e.get("value", "")))[:20],
            "timestamp": e.get("timestamp", ""),
        })

    # ── Build edges ───────────────────────────────────────────
    edges: List[Dict[str, Any]] = []
    edge_set: Set[Tuple[str, str, str]] = set()

    def _add_edge(a: str, b: str, rel_type: str, weight: float = 1.0):
        pair = (*sorted([a, b]), rel_type)
        if pair not in edge_set and a != b:
            edge_set.add(pair)
            edges.append({"source": a, "target": b, "type": rel_type, "weight": weight})

    for i, n1 in enumerate(nodes):
        for j, n2 in enumerate(nodes):
            if j <= i:
                continue

            # 1. Same context → context edge
            if n1["context"] == n2["context"]:
                _add_edge(n1["id"], n2["id"], "context", 0.5)

            # 2. Same key prefix → prefix edge (stronger)
            if n1["prefix"] == n2["prefix"] and n1["prefix"] != n1["id"]:
                _add_edge(n1["id"], n2["id"], "prefix", 0.8)

            # 3. Temporal proximity
            ts1 = _parse_timestamp(n1["timestamp"])
            ts2 = _parse_timestamp(n2["timestamp"])
            if ts1 and ts2 and abs(ts1 - ts2) <= TEMPORAL_WINDOW_SECS:
                _add_edge(n1["id"], n2["id"], "temporal", 0.6)

            # 4. Keyword overlap
            kw1 = set(n1["keywords"])
            kw2 = set(n2["keywords"])
            overlap = kw1 & kw2
            if len(overlap) >= MIN_KEYWORD_OVERLAP:
                weight = min(len(overlap) / 10.0, 1.0)
                _add_edge(n1["id"], n2["id"], "semantic", weight)

    # ── Build clusters ────────────────────────────────────────
    # Cluster by context
    context_clusters: Dict[str, List[str]] = defaultdict(list)
    for n in nodes:
        context_clusters[n["context"]].append(n["id"])

    # Cluster by prefix
    prefix_clusters: Dict[str, List[str]] = defaultdict(list)
    for n in nodes:
        if n["prefix"] != n["id"]:  # Only meaningful prefixes
            prefix_clusters[n["prefix"]].append(n["id"])

    # Remove single-item prefix clusters
    prefix_clusters = {k: v for k, v in prefix_clusters.items() if len(v) > 1}

    clusters = {
        "by_context": dict(context_clusters),
        "by_prefix": dict(prefix_clusters),
    }

    # ── Statistics ─────────────────────────────────────────────
    edge_type_counts = defaultdict(int)
    for e in edges:
        edge_type_counts[e["type"]] += 1

    # Unique node pairs (ignoring edge type) for density calculation
    unique_pairs = len({tuple(sorted([e["source"], e["target"]])) for e in edges})
    max_pairs = len(nodes) * (len(nodes) - 1) // 2

    stats = {
        "node_count": len(nodes),
        "edge_count": len(edges),
        "unique_pairs": unique_pairs,
        "cluster_count": len(context_clusters) + len(prefix_clusters),
        "edge_types": dict(edge_type_counts),
        "contexts": {k: len(v) for k, v in context_clusters.items()},
        "avg_intensity": round(sum(n["intensity"] for n in nodes) / max(len(nodes), 1), 1),
        "density": round(unique_pairs / max(max_pairs, 1), 4),
    }

    result = {
        "nodes": [{"id": n["id"], "context": n["context"], "intensity": n["intensity"]} for n in nodes],
        "clusters": clusters,
        "stats": stats,
    }

    if include_edges:
        result["edges"] = edges

    return result


def render_ascii_graph(max_nodes: int = 30, min_intensity: int = 1) -> str:
    """Render the context graph as an ASCII art visualization.

    Shows clusters, top nodes by intensity, and edge connections.

    Args:
        max_nodes: Maximum number of nodes to display.
        min_intensity: Minimum intensity filter.

    Returns:
        Multi-line ASCII string suitable for terminal output.
    """
    graph = build_context_graph(include_edges=True, min_intensity=min_intensity)
    nodes = graph["nodes"][:max_nodes]
    edges = graph.get("edges", [])
    stats = graph["stats"]
    clusters = graph["clusters"]

    lines: List[str] = []
    lines.append("╔══════════════════════════════════════════════════════════╗")
    lines.append("║           NUCLEUS ENGRAM CONTEXT GRAPH                  ║")
    lines.append("╠══════════════════════════════════════════════════════════╣")
    lines.append(f"║  Nodes: {stats['node_count']:<6}  Edges: {stats['edge_count']:<6}  Density: {stats['density']:<8} ║")
    lines.append(f"║  Unique pairs: {stats['unique_pairs']:<4}  Clusters: {stats['cluster_count']:<4}                  ║")
    lines.append("╠══════════════════════════════════════════════════════════╣")

    # Context clusters
    if clusters.get("by_context"):
        lines.append("║  CLUSTERS BY CONTEXT:                                    ║")
        for ctx, members in clusters["by_context"].items():
            count = len(members)
            bar = "█" * min(count, 30)
            lines.append(f"║    {ctx:<14} ({count:>3}) {bar:<30}   ║")
        lines.append("║                                                          ║")

    # Prefix clusters
    if clusters.get("by_prefix"):
        lines.append("║  CLUSTERS BY PREFIX:                                     ║")
        for prefix, members in list(clusters["by_prefix"].items())[:8]:
            lines.append(f"║    {prefix[:20]:<20} → {len(members)} engrams                   ║")
        lines.append("║                                                          ║")

    # Top nodes by intensity
    sorted_nodes = sorted(nodes, key=lambda n: n["intensity"], reverse=True)[:15]
    if sorted_nodes:
        lines.append("║  TOP ENGRAMS (by intensity):                             ║")
        for n in sorted_nodes:
            intensity_bar = "●" * n["intensity"] + "○" * (10 - n["intensity"])
            label = n["id"][:28]
            lines.append(f"║    {label:<28} [{intensity_bar}] {n['context'][:8]:<8}║")
        lines.append("║                                                          ║")

    # Edge type distribution
    edge_types = stats.get("edge_types", {})
    if edge_types:
        lines.append("║  EDGE TYPES:                                             ║")
        for etype, count in sorted(edge_types.items(), key=lambda x: x[1], reverse=True):
            bar = "─" * min(count * 2, 30)
            lines.append(f"║    {etype:<12} {count:>4}  {bar:<30}    ║")

    lines.append("╚══════════════════════════════════════════════════════════╝")
    return "\n".join(lines)


def get_engram_neighbors(key: str, max_depth: int = 1) -> Dict[str, Any]:
    """Get the neighborhood of a specific engram in the context graph.

    Args:
        key: The engram key to find neighbors for.
        max_depth: How many hops to traverse (1 = direct neighbors only).

    Returns:
        Dict with the target node, its neighbors, and connecting edges.
    """
    graph = build_context_graph(include_edges=True)

    # Find the target node
    target = None
    for n in graph["nodes"]:
        if n["id"] == key:
            target = n
            break

    if not target:
        return {"error": f"Engram '{key}' not found in graph", "node_count": graph["stats"]["node_count"]}

    # BFS to find neighbors within max_depth
    visited = {key}
    frontier = {key}
    neighbor_edges = []

    for _ in range(max_depth):
        next_frontier = set()
        for edge in graph.get("edges", []):
            src, tgt = edge["source"], edge["target"]
            if src in frontier and tgt not in visited:
                next_frontier.add(tgt)
                neighbor_edges.append(edge)
            elif tgt in frontier and src not in visited:
                next_frontier.add(src)
                neighbor_edges.append(edge)
        visited.update(next_frontier)
        frontier = next_frontier

    neighbor_nodes = [n for n in graph["nodes"] if n["id"] in visited and n["id"] != key]

    return {
        "target": target,
        "neighbors": neighbor_nodes,
        "edges": neighbor_edges,
        "neighbor_count": len(neighbor_nodes),
        "depth": max_depth,
    }
