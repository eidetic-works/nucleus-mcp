"""Layer 0: Conversation Capture — streaming Claude Code JSONL → training archive.

Parses Claude Code session transcripts (.jsonl), extracts conversation pairs,
DPO signal from corrections, and reasoning chains from tool-use sequences.
All parsing is streaming (O(1) memory per line) to handle 100MB+ files.
"""

import hashlib
import json
import logging
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

from .common import get_brain_path

logger = logging.getLogger("nucleus.conversation_ops")

# ── Constants ──────────────────────────────────────────────────────────

WINDOW_SIZE = 20        # messages per conversation chunk
OVERLAP = 4             # overlap between sliding windows
MAX_CONTENT_LEN = 3000  # max chars per message (matches archive_pipeline)
MIN_CHUNK_SIZE = 4      # discard fragments smaller than this

# Event types worth extracting (everything else is noise)
_SIGNAL_TYPES = {"user", "assistant"}
_NOISE_TYPES = {"progress", "file-history-snapshot", "queue-operation", "last-prompt"}

# User messages containing these are meta/command output, not human intent
_META_MARKERS = {"<command-name>", "<local-command-stdout>", "<local-command-caveat>"}

# Secret patterns (reused from memory_pipeline)
_SECRET_PATTERNS = [
    (re.compile(r"(?:api[_-]?key|apikey)\s*[:=]\s*\S+", re.IGNORECASE), "API_KEY"),
    (re.compile(r"Bearer\s+[A-Za-z0-9\-._~+/]+=*", re.IGNORECASE), "BEARER"),
    (re.compile(r"(?:password|passwd|pwd)\s*[:=]\s*\S+", re.IGNORECASE), "PASSWORD"),
    (re.compile(r"(?:AWS_SECRET|aws_secret_access_key)\s*[:=]\s*\S+", re.IGNORECASE), "AWS_SECRET"),
    (re.compile(r"sk-[A-Za-z0-9]{20,}", re.IGNORECASE), "SECRET_KEY"),
    (re.compile(r"ghp_[A-Za-z0-9]{36,}", re.IGNORECASE), "GITHUB_PAT"),
    (re.compile(r"-----BEGIN (?:RSA |EC |DSA )?PRIVATE KEY-----"), "PEM_KEY"),
]

# Segment marker injected at compaction boundaries
_SEGMENT_MARKER = {"role": "__segment__", "content": ""}


# ── Streaming Parser ──────────────────────────────────────────────────

def _stream_parse_jsonl(filepath: Path) -> Iterator[Dict]:
    """Line-by-line JSONL generator. O(1) memory per line. Skips malformed."""
    with open(filepath, encoding="utf-8", errors="replace") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except (json.JSONDecodeError, ValueError):
                if line_num <= 5:
                    logger.debug("Skipping malformed line %d in %s", line_num, filepath.name)


def _is_signal_message(event: Dict) -> bool:
    """True if event is a user or assistant message worth extracting."""
    msg_type = event.get("type", "")
    if msg_type not in _SIGNAL_TYPES:
        return False
    if event.get("isSidechain"):
        return False
    if event.get("isMeta"):
        return False
    return True


def _extract_user_text(event: Dict) -> Optional[str]:
    """Extract human-readable text from a user event.

    Returns None for tool_result arrays, meta messages, and command output.
    """
    msg = event.get("message", {})
    content = msg.get("content", "")

    # String content = human text
    if isinstance(content, str):
        if not content.strip():
            return None
        # Skip meta markers (command output, slash commands)
        for marker in _META_MARKERS:
            if marker in content:
                return None
        return content[:MAX_CONTENT_LEN]

    # Array content = tool_results (echoed tool output, not human intent)
    if isinstance(content, list):
        return None

    return None


def _extract_assistant_text(event: Dict) -> Tuple[str, List[str], Optional[str]]:
    """Extract (text, tool_names, thinking) from assistant event.

    Returns ('', [], None) if no extractable content.
    """
    msg = event.get("message", {})
    content = msg.get("content", [])

    if isinstance(content, str):
        return (content[:MAX_CONTENT_LEN], [], None)

    if not isinstance(content, list):
        return ("", [], None)

    text_parts = []
    tool_names = []
    thinking_parts = []

    for block in content:
        btype = block.get("type", "")
        if btype == "text":
            text_parts.append(block.get("text", ""))
        elif btype == "tool_use":
            tool_names.append(block.get("name", "unknown"))
        elif btype == "thinking":
            thinking_parts.append(block.get("thinking", ""))

    text = "\n".join(t for t in text_parts if t)[:MAX_CONTENT_LEN]
    thinking = "\n".join(t for t in thinking_parts if t)[:MAX_CONTENT_LEN] if thinking_parts else None

    return (text, tool_names, thinking)


def _scan_and_redact(text: str) -> str:
    """Scan for secrets and replace with [REDACTED:{type}]."""
    result = text
    for pattern, label in _SECRET_PATTERNS:
        result = pattern.sub(f"[REDACTED:{label}]", result)
    return result


# ── Conversation Builder ──────────────────────────────────────────────

def _build_conversation_stream(filepath: Path) -> List[Dict]:
    """Stream-parse a JSONL file into a flat list of conversation messages.

    Each message: {"role": "user"|"assistant", "content": str, "tools": [...],
                   "thinking": str|None, "timestamp": str}

    Inserts segment markers at compaction boundaries.
    Memory: only extracted messages kept (~1MB for a 348MB file).
    """
    messages = []

    for event in _stream_parse_jsonl(filepath):
        # Compaction boundary = segment separator
        if event.get("type") == "system" and event.get("subtype") == "compact_boundary":
            if messages and messages[-1] != _SEGMENT_MARKER:
                messages.append(_SEGMENT_MARKER)
            continue

        if not _is_signal_message(event):
            continue

        ts = event.get("timestamp", "")
        msg_type = event.get("type", "")

        if msg_type == "user":
            text = _extract_user_text(event)
            if text:
                text = _scan_and_redact(text)
                messages.append({
                    "role": "user",
                    "content": text,
                    "tools": [],
                    "thinking": None,
                    "timestamp": ts,
                })

        elif msg_type == "assistant":
            text, tools, thinking = _extract_assistant_text(event)
            if text or tools:
                text = _scan_and_redact(text) if text else ""
                # Include tool markers in content for SFT context
                tool_marker = f"\n[Used: {', '.join(tools)}]" if tools else ""
                messages.append({
                    "role": "assistant",
                    "content": (text + tool_marker) if text else tool_marker.lstrip("\n"),
                    "tools": tools,
                    "thinking": _scan_and_redact(thinking) if thinking else None,
                    "timestamp": ts,
                })

    return messages


# ── Chunking ──────────────────────────────────────────────────────────

def _chunk_conversation(
    messages: List[Dict],
    window: int = WINDOW_SIZE,
    overlap: int = OVERLAP,
) -> List[List[Dict]]:
    """Sliding window chunker. Respects segment boundaries (compaction).

    Returns list of chunks, each a list of messages.
    Chunks with < MIN_CHUNK_SIZE messages are discarded.
    """
    # Split into segments at markers
    segments = []
    current = []
    for msg in messages:
        if msg.get("role") == "__segment__":
            if current:
                segments.append(current)
            current = []
        else:
            current.append(msg)
    if current:
        segments.append(current)

    # Window each segment independently
    chunks = []
    step = max(1, window - overlap)
    for segment in segments:
        for i in range(0, len(segment), step):
            chunk = segment[i:i + window]
            if len(chunk) >= MIN_CHUNK_SIZE:
                chunks.append(chunk)
    return chunks


# ── Training Extraction ───────────────────────────────────────────────

def _detect_corrections(messages: List[Dict]) -> List[Dict]:
    """Detect DPO-worthy corrections in the message stream.

    Pattern: user[i] starts with correction prefix → assistant[i-1] is rejected,
    assistant[i+1] is chosen, and user[i-2] (or the correction itself) is the prompt.
    """
    from .archive_pipeline import ArchivePipeline

    corrections = []
    # Build flat list without segment markers
    flat = [m for m in messages if m.get("role") != "__segment__"]

    for i, msg in enumerate(flat):
        if msg["role"] != "user":
            continue
        content = msg["content"].strip().lower()

        is_correction = False
        for prefix in ArchivePipeline.CORRECTION_PREFIXES:
            if content.startswith(prefix):
                is_correction = True
                break

        if not is_correction:
            continue

        # Find surrounding assistant messages
        prev_assistant = None
        for j in range(i - 1, -1, -1):
            if flat[j]["role"] == "assistant":
                prev_assistant = flat[j]
                break

        next_assistant = None
        for j in range(i + 1, len(flat)):
            if flat[j]["role"] == "assistant":
                next_assistant = flat[j]
                break

        if not prev_assistant or not next_assistant:
            continue

        # Find the original prompt (user message before the rejected response)
        prompt_msg = None
        if prev_assistant:
            prev_idx = flat.index(prev_assistant)
            for j in range(prev_idx - 1, -1, -1):
                if flat[j]["role"] == "user":
                    prompt_msg = flat[j]
                    break

        corrections.append({
            "prompt": (prompt_msg["content"] if prompt_msg else msg["content"])[:MAX_CONTENT_LEN],
            "chosen": next_assistant["content"][:MAX_CONTENT_LEN],
            "rejected": prev_assistant["content"][:MAX_CONTENT_LEN],
            "index": i,
        })

    return corrections


def _write_correction_to_rag(corr: Dict, session_id: str) -> None:
    """Write a correction as RAG-searchable markdown in .brain/corrections/.

    This closes the accountability loop: corrections from Layer 0 surface
    in future RAG queries, so TB can warn Claude not to repeat mistakes.
    """
    try:
        brain = get_brain_path()
        corrections_dir = brain / "corrections"
        corrections_dir.mkdir(parents=True, exist_ok=True)

        ts = datetime.now(timezone.utc)
        slug = f"{ts.strftime('%Y%m%d_%H%M%S')}_{session_id[:8]}"

        # Extract file paths from the correction content for searchability
        file_refs = set()
        for field in ("prompt", "chosen", "rejected"):
            text = corr.get(field, "")
            for token in text.split():
                if "/" in token and ("." in token or token.endswith("/")):
                    cleaned = token.strip("`,\"'()[]{}:")
                    if len(cleaned) > 3:
                        file_refs.add(cleaned)

        prompt_preview = corr["prompt"][:200].replace("\n", " ")
        rejected_preview = corr["rejected"][:400].replace("\n", " ")
        chosen_preview = corr["chosen"][:400].replace("\n", " ")

        md = f"""# Correction: {prompt_preview[:80]}

**Session:** {session_id[:12]}
**Date:** {ts.strftime('%Y-%m-%d %H:%M UTC')}
**Files:** {', '.join(sorted(file_refs)[:5]) if file_refs else 'unknown'}

## What was asked
{prompt_preview}

## What went wrong (rejected)
{rejected_preview}

## What was corrected to (chosen)
{chosen_preview}
"""
        out = corrections_dir / f"{slug}.md"
        out.write_text(md, encoding="utf-8")
        logger.debug("Correction written to RAG: %s", out.name)
    except Exception as e:
        logger.warning("Failed to write correction to RAG: %s", e)


def _extract_reasoning_chains(messages: List[Dict]) -> List[Dict]:
    """Extract multi-step reasoning chains from tool-use sequences.

    Pattern: assistant has thinking + tools → followed by more tool exchanges →
    ends with assistant text (final answer).
    """
    flat = [m for m in messages if m.get("role") != "__segment__"]
    chains = []
    i = 0

    while i < len(flat):
        msg = flat[i]

        # Look for assistant with thinking and tools (start of chain)
        if msg["role"] == "assistant" and msg.get("thinking") and msg.get("tools"):
            # Find the prompt (previous user message)
            prompt = ""
            for j in range(i - 1, -1, -1):
                if flat[j]["role"] == "user":
                    prompt = flat[j]["content"]
                    break

            if not prompt:
                i += 1
                continue

            steps = []
            k = i

            # Collect chain steps
            while k < len(flat):
                step_msg = flat[k]

                if step_msg["role"] == "assistant" and step_msg.get("tools"):
                    step = {
                        "thought": (step_msg.get("thinking") or "")[:1000],
                        "action": ", ".join(step_msg["tools"]),
                        "observation": "",
                    }
                    # Look for the tool result (next user message)
                    if k + 1 < len(flat) and flat[k + 1]["role"] == "user":
                        step["observation"] = flat[k + 1]["content"][:500]
                        k += 2
                    else:
                        k += 1
                    steps.append(step)

                elif step_msg["role"] == "assistant" and not step_msg.get("tools"):
                    # Final answer (assistant without tools)
                    if steps:
                        chains.append({
                            "prompt": prompt[:MAX_CONTENT_LEN],
                            "steps": steps,
                            "final_answer": step_msg["content"][:MAX_CONTENT_LEN],
                        })
                    k += 1
                    break
                else:
                    k += 1

            i = k
        else:
            i += 1

    return chains


# ── Cursor Management ─────────────────────────────────────────────────

def _cursor_path() -> Path:
    brain = get_brain_path()
    return brain / "training" / "conversation_cursor.json"


def _load_cursor() -> Dict:
    """Load conversation cursor state."""
    path = _cursor_path()
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, ValueError):
            return {"processed_sessions": {}, "last_scan": None, "total_sessions_processed": 0}
    return {"processed_sessions": {}, "last_scan": None, "total_sessions_processed": 0}


def _save_cursor(cursor: Dict):
    """Atomically write cursor state."""
    path = _cursor_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(cursor, indent=2, default=str), encoding="utf-8")
    tmp.replace(path)


def _session_needs_processing(session_id: str, filepath: Path, cursor: Dict) -> bool:
    """Check if a session needs (re)processing based on file size and mtime."""
    processed = cursor.get("processed_sessions", {})
    if session_id not in processed:
        return True
    entry = processed[session_id]
    current_size = filepath.stat().st_size
    return current_size > entry.get("file_size", 0)


# ── Transcript Discovery ─────────────────────────────────────────────

def _discover_transcripts() -> List[Tuple[str, Path]]:
    """Find all Claude Code JSONL transcript files.

    Returns list of (session_id, filepath) sorted by mtime (newest first).
    """
    results = []
    # Search all project directories under ~/.claude/projects/
    projects_dir = Path.home() / ".claude" / "projects"
    if not projects_dir.exists():
        return results

    for project_dir in projects_dir.iterdir():
        if not project_dir.is_dir():
            continue
        for f in project_dir.iterdir():
            if f.suffix == ".jsonl" and f.is_file() and f.stat().st_size > 100:
                session_id = f.stem
                results.append((session_id, f))

    # Sort by modification time, newest first
    results.sort(key=lambda x: x[1].stat().st_mtime, reverse=True)
    return results


# ── MCP Action Handlers ───────────────────────────────────────────────

def ingest_conversations(
    mode: str = "incremental",
    session_id: str = "",
    limit: int = 0,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Ingest Claude Code JSONL transcripts into the training archive.

    Modes:
      - "incremental": process sessions newer/larger than cursor (default)
      - "batch": process all unprocessed sessions
      - "single": process one session by session_id

    Returns: {sessions_processed, turns_created, preferences_found,
              chains_extracted, errors, duration_ms}
    """
    from .archive_pipeline import ArchivePipeline

    start = time.monotonic()
    cursor = _load_cursor()
    archive = ArchivePipeline()
    existing_hashes = archive._get_existing_hashes()

    totals = {
        "sessions_processed": 0,
        "turns_created": 0,
        "preferences_found": 0,
        "chains_extracted": 0,
        "errors": [],
    }

    # Discover transcripts
    if mode == "single" and session_id:
        transcripts = _discover_transcripts()
        transcripts = [(sid, fp) for sid, fp in transcripts if sid == session_id]
        if not transcripts:
            return {**totals, "errors": [f"Session {session_id} not found"]}
    else:
        transcripts = _discover_transcripts()

    processed_count = 0
    for sid, filepath in transcripts:
        # Incremental: skip already-processed
        if mode == "incremental" and not _session_needs_processing(sid, filepath, cursor):
            continue

        # Batch: skip already-processed (same check)
        if mode == "batch" and not _session_needs_processing(sid, filepath, cursor):
            continue

        if limit and processed_count >= limit:
            break

        try:
            result = _ingest_single_session(
                sid, filepath, archive, existing_hashes, dry_run=dry_run
            )
            totals["turns_created"] += result.get("turns_created", 0)
            totals["preferences_found"] += result.get("preferences_found", 0)
            totals["chains_extracted"] += result.get("chains_extracted", 0)
            totals["sessions_processed"] += 1

            # Update cursor
            if not dry_run:
                cursor["processed_sessions"][sid] = {
                    "file_size": filepath.stat().st_size,
                    "mtime": datetime.fromtimestamp(
                        filepath.stat().st_mtime, tz=timezone.utc
                    ).isoformat(),
                    "turns_extracted": result.get("turns_created", 0),
                    "prefs_extracted": result.get("preferences_found", 0),
                    "chains_extracted": result.get("chains_extracted", 0),
                }

            processed_count += 1
            logger.info(
                "Ingested %s: %d turns, %d prefs, %d chains",
                sid[:12], result.get("turns_created", 0),
                result.get("preferences_found", 0),
                result.get("chains_extracted", 0),
            )

        except Exception as e:
            totals["errors"].append(f"{sid[:12]}: {e}")
            logger.error("Failed to ingest %s: %s", sid[:12], e)

    # Save cursor
    if not dry_run:
        cursor["last_scan"] = datetime.now(timezone.utc).isoformat()
        cursor["total_sessions_processed"] = len(cursor.get("processed_sessions", {}))
        _save_cursor(cursor)

    totals["duration_ms"] = int((time.monotonic() - start) * 1000)
    return totals


def _ingest_single_session(
    session_id: str,
    filepath: Path,
    archive,
    existing_hashes: set,
    dry_run: bool = False,
) -> Dict[str, int]:
    """Ingest a single JSONL transcript file."""
    messages = _build_conversation_stream(filepath)
    if len(messages) < MIN_CHUNK_SIZE:
        return {"turns_created": 0, "preferences_found": 0, "chains_extracted": 0}

    chunks = _chunk_conversation(messages)
    corrections = _detect_corrections(messages)
    chains = _extract_reasoning_chains(messages)

    turns_created = 0
    prefs_found = 0
    chains_extracted = 0

    # Record conversation chunks as LoopTurns
    for idx, chunk in enumerate(chunks):
        # Build conversation pairs for ArchivePipeline
        conv = [
            {"role": m["role"], "content": m["content"],
             **({"tools": m["tools"]} if m.get("tools") else {})}
            for m in chunk
        ]

        first_user = next(
            (m["content"][:100] for m in chunk if m["role"] == "user"),
            "Claude Code session",
        )

        # Dedup by content hash
        content_sig = f"code:claude_code:{session_id}:{idx}"
        content_hash = hashlib.sha256(content_sig.encode()).hexdigest()[:16]
        if content_hash in existing_hashes:
            continue

        if dry_run:
            turns_created += 1
            existing_hashes.add(content_hash)
            continue

        # Collect tool names from chunk
        tools = []
        for m in chunk:
            tools.extend(m.get("tools", []))

        archive.record_turn(
            brother="code",
            intent=first_user,
            actions=[],
            tools_used=list(set(tools)),
            decisions=[],
            outcome=f"Claude Code session {session_id[:12]} chunk {idx + 1}/{len(chunks)} ({len(chunk)} messages)",
            signal_absorbed=[],
            signal_produced=[],
            confidence=0.8,
            context=f"Ingested from Claude Code session {session_id[:12]}",
            conversation=conv,
            metadata={
                "source": f"claude_code:{session_id}",
                "chunk_index": idx,
                "total_chunks": len(chunks),
            },
        )
        existing_hashes.add(content_hash)
        turns_created += 1

    # Record DPO preferences from corrections
    for corr in corrections:
        if dry_run:
            prefs_found += 1
            continue
        result = archive.record_preference(
            prompt=corr["prompt"],
            chosen=corr["chosen"],
            rejected=corr["rejected"],
            source="correction",
            metadata={"session_id": session_id, "source_type": "claude_code"},
        )
        if result:
            prefs_found += 1
            # Write RAG-searchable correction for accountability loop
            _write_correction_to_rag(corr, session_id)

    # Record reasoning chains
    for chain in chains:
        if dry_run:
            chains_extracted += 1
            continue
        result = archive.record_reasoning_chain(
            prompt=chain["prompt"],
            steps=chain["steps"],
            final_answer=chain["final_answer"],
            source="react_loop",
            metadata={"session_id": session_id, "source_type": "claude_code"},
        )
        if result:
            chains_extracted += 1

    return {
        "turns_created": turns_created,
        "preferences_found": prefs_found,
        "chains_extracted": chains_extracted,
    }


def search_conversations(
    query: str = "",
    limit: int = 20,
    session_id: str = "",
    date_from: str = "",
    date_to: str = "",
) -> Dict[str, Any]:
    """Search ingested conversations by keyword.

    Streams loop_turns.jsonl to avoid loading all into memory.
    Scores by keyword overlap.
    """
    if not query:
        return {"results": [], "total_matches": 0, "query": ""}

    brain = get_brain_path()
    turns_file = brain / "training" / "loop_turns.jsonl"
    if not turns_file.exists():
        return {"results": [], "total_matches": 0, "query": query}

    query_terms = set(query.lower().split())
    results = []

    with open(turns_file, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                turn = json.loads(line)
            except (json.JSONDecodeError, ValueError):
                continue

            # Filter by source type
            meta = turn.get("metadata", {})
            source = meta.get("source", "")
            if session_id and session_id not in source:
                continue

            # Filter by date
            ts = turn.get("timestamp", "")
            if date_from and ts < date_from:
                continue
            if date_to and ts > date_to:
                continue

            # Search in conversation content
            conv = turn.get("conversation", [])
            if not conv:
                continue

            conv_text = " ".join(m.get("content", "") for m in conv).lower()
            if not conv_text:
                continue

            # Score by keyword overlap
            conv_words = set(conv_text.split())
            overlap = query_terms & conv_words
            if not overlap:
                continue

            score = len(overlap) / len(query_terms)

            # Build snippet from first matching message
            snippet = ""
            for m in conv:
                content = m.get("content", "")
                if any(term in content.lower() for term in query_terms):
                    snippet = content[:200]
                    break

            results.append({
                "turn_id": turn.get("turn_id", ""),
                "timestamp": ts,
                "intent": turn.get("intent", "")[:100],
                "score": round(score, 2),
                "snippet": snippet,
                "session_id": source.replace("claude_code:", "")[:12] if "claude_code:" in source else "",
            })

    # Sort by score descending
    results.sort(key=lambda r: r["score"], reverse=True)
    total = len(results)
    results = results[:limit]

    return {"results": results, "total_matches": total, "query": query}


def list_conversations(
    limit: int = 50,
    offset: int = 0,
    sort: str = "recent",
) -> Dict[str, Any]:
    """List ingested conversation sessions with metadata from cursor."""
    cursor = _load_cursor()
    processed = cursor.get("processed_sessions", {})

    entries = []
    for sid, info in processed.items():
        entries.append({
            "session_id": sid[:12],
            "full_id": sid,
            "mtime": info.get("mtime", ""),
            "turns_extracted": info.get("turns_extracted", 0),
            "prefs_extracted": info.get("prefs_extracted", 0),
            "chains_extracted": info.get("chains_extracted", 0),
            "file_size_mb": round(info.get("file_size", 0) / (1024 * 1024), 1),
        })

    # Sort
    if sort == "recent":
        entries.sort(key=lambda e: e["mtime"], reverse=True)
    elif sort == "size":
        entries.sort(key=lambda e: e["file_size_mb"], reverse=True)
    elif sort == "turns":
        entries.sort(key=lambda e: e["turns_extracted"], reverse=True)

    total = len(entries)
    entries = entries[offset:offset + limit]

    return {"conversations": entries, "total": total, "offset": offset, "limit": limit}


def conversation_stats() -> Dict[str, Any]:
    """Aggregate statistics about the conversation corpus."""
    cursor = _load_cursor()
    processed = cursor.get("processed_sessions", {})

    # Count raw sessions available
    raw_transcripts = _discover_transcripts()
    total_raw_size = sum(fp.stat().st_size for _, fp in raw_transcripts)

    # Aggregate from cursor
    total_turns = sum(v.get("turns_extracted", 0) for v in processed.values())
    total_prefs = sum(v.get("prefs_extracted", 0) for v in processed.values())
    total_chains = sum(v.get("chains_extracted", 0) for v in processed.values())

    # Date range from cursor
    mtimes = [v.get("mtime", "") for v in processed.values() if v.get("mtime")]
    oldest = min(mtimes) if mtimes else None
    newest = max(mtimes) if mtimes else None

    return {
        "total_sessions_raw": len(raw_transcripts),
        "total_sessions_ingested": len(processed),
        "total_turns": total_turns,
        "total_preferences": total_prefs,
        "total_reasoning_chains": total_chains,
        "corpus_size_mb": round(total_raw_size / (1024 * 1024), 1),
        "oldest_session": oldest,
        "newest_session": newest,
        "last_scan": cursor.get("last_scan"),
    }
