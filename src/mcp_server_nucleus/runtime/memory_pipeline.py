"""Memory Pipeline — ADUN Protocol (ADD/UPDATE/DELETE/NOOP).

MDR_014: Deterministic Engram State Machine.
Transforms the Nucleus memory system from append-only to a state-managed store.

Inspired by:
- Mem0: Explicit memory ops (ADD/UPDATE/DELETE/NOOP) with forgetting/decay.
- MemGPT/Letta: Memory editing via tool calling, not implicit prompt drift.

Soul Document Reference:
- "Engram writing/reading tools super critical hain, lekin abhi tak clearly nahi pata:
   Inko kab call karna hai, kaise long-term memory banaani hai bina system corrupt kiye."
   — NUCLEUS_FOUNDER_RANT_FEB19_PROBLEM_STATEMENT.md

Usage:
    pipeline = MemoryPipeline(brain_path)
    result = pipeline.process("PostgreSQL chosen for ACID compliance", context="Architecture", intensity=8)
    # result = {"op": "ADD", "key": "auto_arch_001", ...} or {"op": "NOOP", "reason": "Duplicate of ..."}
"""

import json
import logging
import re
import time
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("nucleus.memory_pipeline")


class EngramOp(str, Enum):
    """ADUN Operation Types."""
    ADD = "ADD"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    NOOP = "NOOP"


class MemoryPipeline:
    """
    Deterministic Engram State Machine (ADUN Protocol).

    Process flow:
    1. Extract: Normalize input into atomic candidate facts.
    2. Compare: Check candidates against existing ledger.
    3. Propose: Determine operation (ADD/UPDATE/DELETE/NOOP) per candidate.
    4. Commit: Execute the state changes and emit audit events.

    DT-1 Section 3 Answers (Questions 15-18):
    Q15: An engram is a versioned, typed, conflict-resolvable memory object written
         only through explicit operations (ADD/UPDATE/DELETE/NOOP) and retrieved
         by a scored policy — not by "LLM vibes."
    Q16: Write triggers: task completion, decision made, constraint discovered,
         pattern learned, error corrected.
    Q17: Read triggers: session start, task planning, conflict resolution,
         context injection before tool calls.
    Q18: Conflict resolution: newest-wins by default, intensity-wins for ties,
         human override for critical conflicts.
    """

    def __init__(self, brain_path: Optional[Path] = None):
        """Initialize the pipeline with a brain path."""
        if brain_path is None:
            from .common import get_brain_path
            brain_path = get_brain_path()

        self.brain_path = Path(brain_path)
        self.ledger_path = self.brain_path / "engrams" / "ledger.jsonl"
        self.history_path = self.brain_path / "engrams" / "history.jsonl"
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)

    # ── STEP 1: Extract Atoms ──────────────────────────────────────

    def extract_atoms(self, text: str) -> List[str]:
        """
        Break down complex input into atomic, self-contained statements.

        This is a deterministic extraction (no LLM needed for v0).
        Splits on sentence boundaries and filters noise.

        Args:
            text: Raw input text (e.g., a decision, learning, constraint).

        Returns:
            List of atomic fact strings.
        """
        if not text or not text.strip():
            return []

        # Split on common sentence boundaries
        # Handle: periods, semicolons, newlines, bullet points
        raw_parts = re.split(r'[.;]\s+|\n+|(?:^|\n)\s*[-*•]\s+', text.strip())

        atoms = []
        for part in raw_parts:
            cleaned = part.strip().rstrip('.')
            # Filter out noise: too short, too long, or just whitespace
            if len(cleaned) >= 10 and len(cleaned) <= 500:
                atoms.append(cleaned)

        # If no atoms extracted (text was a single statement), use the whole thing
        if not atoms and len(text.strip()) >= 10:
            atoms = [text.strip()]

        return atoms

    # ── STEP 2: Compare Against Existing Ledger ────────────────────

    def _load_active_engrams(self) -> List[Dict]:
        """Load all active (non-deleted) engrams from the ledger."""
        if not self.ledger_path.exists():
            return []

        engrams = []
        with open(self.ledger_path, "r") as f:
            for line in f:
                if line.strip():
                    try:
                        e = json.loads(line)
                        if not e.get("deleted", False):
                            engrams.append(e)
                    except json.JSONDecodeError:
                        continue
        return engrams

    def _find_similar(self, candidate: str, existing: List[Dict], threshold: float = 0.6) -> Optional[Dict]:
        """
        Find the most similar existing engram to a candidate atom.

        Uses keyword overlap scoring (v0 — no embeddings needed).

        Args:
            candidate: The candidate fact string.
            existing: List of existing engram dicts.
            threshold: Minimum similarity score to consider a match.

        Returns:
            The most similar engram dict, or None.
        """
        candidate_words = set(candidate.lower().split())
        # Remove common stop words for better matching
        stop_words = {"the", "a", "an", "is", "are", "was", "were", "be", "been",
                      "being", "have", "has", "had", "do", "does", "did", "will",
                      "would", "could", "should", "may", "might", "shall",
                      "for", "and", "but", "or", "nor", "not", "so", "yet",
                      "to", "of", "in", "on", "at", "by", "with", "from",
                      "this", "that", "it", "its", "we", "our", "their"}
        candidate_words -= stop_words

        if not candidate_words:
            return None

        best_match = None
        best_score = 0.0

        for engram in existing:
            value_words = set(engram.get("value", "").lower().split()) - stop_words
            key_words = set(engram.get("key", "").lower().replace("_", " ").split()) - stop_words

            combined = value_words | key_words

            if not combined:
                continue

            # Jaccard similarity
            intersection = candidate_words & combined
            union = candidate_words | combined
            score = len(intersection) / len(union) if union else 0

            if score > best_score and score >= threshold:
                best_score = score
                best_match = engram

        return best_match

    # ── STEP 3: Propose Operations ─────────────────────────────────

    def propose_ops(
        self,
        atoms: List[str],
        context: str = "Decision",
        intensity: int = 5,
        source_agent: str = "human",
    ) -> List[Dict]:
        """
        For each candidate atom, determine the ADUN operation.

        Rules:
        - Exact key match with same value → NOOP (duplicate)
        - Exact key match with different value → UPDATE (evolution)
        - High similarity match → UPDATE (refinement)
        - No match → ADD (new knowledge)

        Args:
            atoms: List of atomic fact strings.
            context: Category (Feature, Architecture, Brand, Strategy, Decision).
            intensity: 1-10 priority.
            source_agent: ID of the agent proposing.

        Returns:
            List of operation dicts with op type and metadata.
        """
        existing = self._load_active_engrams()
        operations = []

        for atom in atoms:
            # Check for exact key-value duplicate
            exact_match = None
            for e in existing:
                if e.get("value", "").strip().lower() == atom.strip().lower():
                    exact_match = e
                    break

            if exact_match:
                operations.append({
                    "op": EngramOp.NOOP,
                    "reason": f"Exact duplicate of engram '{exact_match['key']}'",
                    "existing_key": exact_match["key"],
                    "candidate": atom,
                })
                continue

            # Check for similar (potential UPDATE)
            similar = self._find_similar(atom, existing)
            if similar:
                operations.append({
                    "op": EngramOp.UPDATE,
                    "target_key": similar["key"],
                    "old_value": similar["value"],
                    "new_value": atom,
                    "context": context,
                    "intensity": max(intensity, similar.get("intensity", 5)),
                    "source_agent": source_agent,
                    "version": similar.get("version", 1) + 1,
                })
            else:
                # Generate a new key
                key = self._generate_key(atom, context)
                operations.append({
                    "op": EngramOp.ADD,
                    "key": key,
                    "value": atom,
                    "context": context,
                    "intensity": intensity,
                    "source_agent": source_agent,
                    "version": 1,
                })

        return operations

    def _generate_key(self, value: str, context: str) -> str:
        """Generate a deterministic key from value and context."""
        # Take first 3 meaningful words + context prefix + timestamp suffix
        words = [w.lower() for w in value.split()
                 if len(w) > 3 and w.lower() not in {"the", "this", "that", "with", "from"}]
        slug = "_".join(words[:3]) if words else "engram"
        prefix = context[:4].lower()
        suffix = str(int(time.time()))[-4:]
        return f"{prefix}_{slug}_{suffix}"

    # ── STEP 4: Commit Operations ──────────────────────────────────

    def commit_ops(self, operations: List[Dict]) -> Dict:
        """
        Execute the proposed operations against the ledger.

        Args:
            operations: List of operation dicts from propose_ops().

        Returns:
            Summary of committed operations.
        """
        results = {"added": 0, "updated": 0, "deleted": 0, "skipped": 0, "details": []}

        for op in operations:
            op_type = op["op"] if isinstance(op["op"], str) else op["op"].value

            if op_type == "NOOP":
                results["skipped"] += 1
                results["details"].append({"op": "NOOP", "reason": op.get("reason", "")})

            elif op_type == "ADD":
                engram = {
                    "key": op["key"],
                    "value": op["value"],
                    "context": op.get("context", "Decision"),
                    "intensity": op.get("intensity", 5),
                    "version": 1,
                    "source_agent": op.get("source_agent", "unknown"),
                    "op_type": "ADD",
                    "timestamp": datetime.now().isoformat(),
                    "deleted": False,
                    "signature": None,
                }
                self._append_to_ledger(engram)
                self._append_to_history(engram, "ADD")
                results["added"] += 1
                results["details"].append({"op": "ADD", "key": engram["key"]})

            elif op_type == "UPDATE":
                # Mark old version in history, write new version
                new_engram = {
                    "key": op["target_key"],
                    "value": op["new_value"],
                    "context": op.get("context", "Decision"),
                    "intensity": op.get("intensity", 5),
                    "version": op.get("version", 2),
                    "source_agent": op.get("source_agent", "unknown"),
                    "op_type": "UPDATE",
                    "timestamp": datetime.now().isoformat(),
                    "deleted": False,
                    "signature": None,
                }
                self._update_in_ledger(op["target_key"], new_engram)
                self._append_to_history(new_engram, "UPDATE")
                results["updated"] += 1
                results["details"].append({
                    "op": "UPDATE", "key": op["target_key"],
                    "version": op.get("version", 2)
                })

            elif op_type == "DELETE":
                self._delete_in_ledger(op.get("target_key", op.get("key", "")))
                self._append_to_history({"key": op.get("target_key", op.get("key", ""))}, "DELETE")
                results["deleted"] += 1
                results["details"].append({"op": "DELETE", "key": op.get("target_key", "")})

        return results

    def _append_to_ledger(self, engram: Dict):
        """Append a new engram to the ledger."""
        with open(self.ledger_path, "a") as f:
            f.write(json.dumps(engram) + "\n")

    def _update_in_ledger(self, key: str, new_engram: Dict):
        """Update an existing engram in the ledger (rewrite file)."""
        if not self.ledger_path.exists():
            self._append_to_ledger(new_engram)
            return

        lines = []
        updated = False
        with open(self.ledger_path, "r") as f:
            for line in f:
                if line.strip():
                    try:
                        e = json.loads(line)
                        if e.get("key") == key and not e.get("deleted", False):
                            lines.append(json.dumps(new_engram) + "\n")
                            updated = True
                        else:
                            lines.append(line)
                    except json.JSONDecodeError:
                        lines.append(line)

        if not updated:
            lines.append(json.dumps(new_engram) + "\n")

        with open(self.ledger_path, "w") as f:
            f.writelines(lines)

    def _delete_in_ledger(self, key: str):
        """Soft-delete an engram by marking it as deleted."""
        if not self.ledger_path.exists():
            return

        lines = []
        with open(self.ledger_path, "r") as f:
            for line in f:
                if line.strip():
                    try:
                        e = json.loads(line)
                        if e.get("key") == key:
                            e["deleted"] = True
                            e["deleted_at"] = datetime.now().isoformat()
                            lines.append(json.dumps(e) + "\n")
                        else:
                            lines.append(line)
                    except json.JSONDecodeError:
                        lines.append(line)

        with open(self.ledger_path, "w") as f:
            f.writelines(lines)

    def _append_to_history(self, engram: Dict, op_type: str):
        """Append an entry to the history log for audit-ability."""
        history_entry = {
            "key": engram.get("key", "unknown"),
            "op_type": op_type,
            "timestamp": datetime.now().isoformat(),
            "snapshot": engram,
        }
        with open(self.history_path, "a") as f:
            f.write(json.dumps(history_entry) + "\n")

    # ── HIGH-LEVEL API ─────────────────────────────────────────────

    def process(
        self,
        text: str,
        context: str = "Decision",
        intensity: int = 5,
        source_agent: str = "human",
        key: Optional[str] = None,
        operation: Optional[str] = None,
    ) -> Dict:
        """
        Full ADUN pipeline: Extract → Compare → Propose → Commit.

        This is the primary entry point for all engram writes.

        Args:
            text: The memory content to process.
            context: Category (Feature, Architecture, Brand, Strategy, Decision).
            intensity: 1-10 priority.
            source_agent: Who is writing (human, agent-id, etc.).
            key: Optional explicit key (bypasses auto-generation).
            operation: Optional explicit operation ('add', 'update', 'delete').
                      If set, bypasses the automatic comparison logic.

        Returns:
            Dict with operation results and audit trail.
        """
        # If explicit operation is forced (e.g., from a tool call)
        if operation and operation.lower() == "delete" and key:
            ops = [{"op": EngramOp.DELETE, "target_key": key}]
            result = self.commit_ops(ops)
            result["mode"] = "explicit_delete"
            return result

        # Step 1: Extract atoms
        atoms = self.extract_atoms(text)

        if not atoms:
            return {"op": "NOOP", "reason": "No extractable content", "skipped": 1}

        # If explicit key is given, use it for the first atom
        if key and atoms:
            # Check if this key already exists
            existing = self._load_active_engrams()
            existing_match = next((e for e in existing if e.get("key") == key), None)

            if existing_match:
                if operation and operation.lower() == "update":
                    ops = [{
                        "op": EngramOp.UPDATE,
                        "target_key": key,
                        "old_value": existing_match["value"],
                        "new_value": text,
                        "context": context,
                        "intensity": intensity,
                        "source_agent": source_agent,
                        "version": existing_match.get("version", 1) + 1,
                    }]
                else:
                    # Auto-detect: same key, different value → UPDATE
                    if existing_match["value"].strip().lower() != text.strip().lower():
                        ops = [{
                            "op": EngramOp.UPDATE,
                            "target_key": key,
                            "old_value": existing_match["value"],
                            "new_value": text,
                            "context": context,
                            "intensity": intensity,
                            "source_agent": source_agent,
                            "version": existing_match.get("version", 1) + 1,
                        }]
                    else:
                        ops = [{
                            "op": EngramOp.NOOP,
                            "reason": f"Exact duplicate of engram '{key}'",
                            "existing_key": key,
                            "candidate": text,
                        }]
            else:
                ops = [{
                    "op": EngramOp.ADD,
                    "key": key,
                    "value": text,
                    "context": context,
                    "intensity": intensity,
                    "source_agent": source_agent,
                    "version": 1,
                }]

            result = self.commit_ops(ops)
            result["mode"] = "explicit_key"
            result["atoms_extracted"] = len(atoms)
            return result

        # Step 2-3: Compare and propose
        ops = self.propose_ops(atoms, context, intensity, source_agent)

        # Step 4: Commit
        result = self.commit_ops(ops)
        result["mode"] = "auto_pipeline"
        result["atoms_extracted"] = len(atoms)
        return result
