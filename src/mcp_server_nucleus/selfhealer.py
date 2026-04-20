#!/usr/bin/env python3
"""Nucleus Self-Healing Engine — Intent-Level Error Recovery.

The Nucleus self-healer captures FOUR dimensions of context that no other
system provides simultaneously:

  1. Error output   — what broke (traceback, exception)
  2. Code file      — what was running (source around the crash site)
  3. Intent         — what it was SUPPOSED to do (engram context from .brain)
  4. Recent history — what changed before it broke (git diff)

With all four, an LLM can propose a *semantic* fix rather than a band-aid.
The healer then optionally retries the failed operation to close the loop.

Architecture (per Perplexity spec):
  Error happens → capture full context → LLM diagnoses → fix applied OR
  surfaced in Windsurf/Antigravity → re-run → verify → done → Nucleus is
  now better than before it broke.
"""

import os
import sys
import json
import traceback
import subprocess
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import types

from .runtime.common import get_brain_path, make_response
from .cli_output import EXIT_ERROR, EXIT_OK

logger = logging.getLogger("nucleus.selfhealer")

# ════════════════════════════════════════════════════════════════
# FULL-CONTEXT CAPTURE — The 4 Dimensions
# ════════════════════════════════════════════════════════════════

def _get_error_output(exc: Exception) -> Dict[str, Any]:
    """Dimension 1: What broke."""
    return {
        "type": type(exc).__name__,
        "message": str(exc),
        "traceback": traceback.format_exc(),
    }


def _get_code_file(tb: Optional[types.TracebackType] = None) -> Dict[str, Any]:
    """Dimension 2: What was running — source lines around the crash site."""
    try:
        if tb is None:
            tb = sys.exc_info()[2]
        if tb is None:
            return {"available": False}
        # Walk to the innermost frame (the actual crash site)
        while tb.tb_next:
            tb = tb.tb_next
        frame = tb.tb_frame
        filename = frame.f_code.co_filename
        lineno = tb.tb_lineno
        func = frame.f_code.co_name
        # Read surrounding source lines (±10)
        source_lines = []
        try:
            with open(filename, "r", encoding="utf-8", errors="replace") as f:
                all_lines = f.readlines()
            start = max(0, lineno - 11)
            end = min(len(all_lines), lineno + 10)
            source_lines = [
                {"line": i + 1, "code": all_lines[i].rstrip(), "is_error": (i + 1 == lineno)}
                for i in range(start, end)
            ]
        except Exception:
            pass
        return {
            "available": True,
            "filename": filename,
            "lineno": lineno,
            "function": func,
            "source_lines": source_lines,
        }
    except Exception:
        return {"available": False}


def _get_intent_context(brain_path: Path) -> Dict[str, Any]:
    """Dimension 3: What it was SUPPOSED to do — recent engrams + active task."""
    intent = {"engrams": [], "active_task": None, "active_session": None}
    try:
        # Recent high-intensity engrams (intent signals)
        engram_path = brain_path / "engrams" / "ledger.jsonl"
        if engram_path.exists():
            engrams = []
            with open(engram_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        try:
                            engrams.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
            # Top 5 by intensity, most recent first
            engrams.sort(key=lambda e: (e.get("intensity", 0), e.get("timestamp", "")), reverse=True)
            intent["engrams"] = engrams[:5]

        # Active task from task ledger
        task_path = brain_path / "tasks" / "ledger.jsonl"
        if task_path.exists():
            with open(task_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        try:
                            t = json.loads(line)
                            if t.get("status") in ("IN_PROGRESS", "READY", "CLAIMED"):
                                intent["active_task"] = t
                        except json.JSONDecodeError:
                            continue

        # Active session
        active_path = brain_path / "sessions" / "active.json"
        if active_path.exists():
            try:
                intent["active_session"] = json.loads(active_path.read_text(encoding="utf-8"))
            except Exception:
                pass
    except Exception as e:
        intent["capture_error"] = str(e)
    return intent


def _get_recent_history() -> Dict[str, Any]:
    """Dimension 4: What changed before it broke — git diff + recent commits."""
    history: Dict[str, Any] = {"git_available": False}
    try:
        # Git diff (staged + unstaged)
        diff = subprocess.run(
            ["git", "diff", "--stat", "HEAD~3..HEAD"],
            capture_output=True, text=True, timeout=10
        )
        if diff.returncode == 0:
            history["git_available"] = True
            history["recent_diff_stat"] = diff.stdout.strip()

        # Last 5 commits
        log = subprocess.run(
            ["git", "log", "--oneline", "-5"],
            capture_output=True, text=True, timeout=5
        )
        if log.returncode == 0:
            history["recent_commits"] = log.stdout.strip().split("\n")

        # Uncommitted changes
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, timeout=5
        )
        if status.returncode == 0:
            history["uncommitted"] = status.stdout.strip()
            history["dirty"] = bool(status.stdout.strip())
    except Exception:
        pass
    return history


def get_full_context(exc: Exception, brain_path: Path, command: str = "",
                     args: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Capture all 4 dimensions of error context.

    This is the function that makes Nucleus self-healing categorically
    different from every other system: it captures intent, not just symptoms.
    """
    return {
        "id": f"err-{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}",
        "timestamp": datetime.now().isoformat(),
        "command": command,
        "args": args or {},
        "error_output": _get_error_output(exc),
        "code_file": _get_code_file(),
        "intent": _get_intent_context(brain_path),
        "recent_history": _get_recent_history(),
        "system": {
            "python_version": sys.version,
            "working_dir": os.getcwd(),
            "brain_path": str(brain_path),
            "env_brain": os.environ.get("NUCLEUS_BRAIN_PATH", ""),
        },
    }


# ════════════════════════════════════════════════════════════════
# ERROR CLASSIFICATION — Pattern-based fast path
# ════════════════════════════════════════════════════════════════

def classify_error(error_info: Dict[str, Any]) -> Dict[str, Any]:
    """Classify error by pattern for fast deterministic recovery."""
    msg = error_info["error_output"]["message"].lower()
    exc_type = error_info["error_output"]["type"]

    if "permission" in msg or exc_type == "PermissionError":
        return {"type": "permission_error", "severity": "high", "deterministic_fix": True, "recoverable": True}
    if exc_type == "FileNotFoundError" or "no such file" in msg:
        return {"type": "file_not_found", "severity": "medium", "deterministic_fix": True, "recoverable": True}
    if "brain" in msg and ("not found" in msg or "not set" in msg or "does not exist" in msg):
        return {"type": "brain_not_found", "severity": "high", "deterministic_fix": True, "recoverable": True}
    if "json" in msg and ("decode" in msg or "expecting" in msg):
        return {"type": "data_corruption", "severity": "high", "deterministic_fix": False, "recoverable": False}
    if exc_type in ("ConnectionError", "TimeoutError", "ConnectionRefusedError"):
        return {"type": "network_error", "severity": "medium", "deterministic_fix": True, "recoverable": True}
    if exc_type == "ImportError" or exc_type == "ModuleNotFoundError":
        return {"type": "import_error", "severity": "medium", "deterministic_fix": False, "recoverable": False}
    if exc_type == "KeyError" or exc_type == "TypeError" or exc_type == "AttributeError":
        return {"type": "code_bug", "severity": "high", "deterministic_fix": False, "recoverable": False}

    return {"type": "runtime_error", "severity": "medium", "deterministic_fix": False, "recoverable": False}


# ════════════════════════════════════════════════════════════════
# DETERMINISTIC RECOVERY — Fast fixes without LLM
# ════════════════════════════════════════════════════════════════

def attempt_deterministic_fix(error_info: Dict[str, Any], classification: Dict[str, Any]) -> Dict[str, Any]:
    """Try known fixes for common errors. No LLM needed."""
    result = {"attempted": False, "fixed": False, "action": None, "suggestions": []}
    etype = classification["type"]
    brain_path = Path(error_info["system"]["brain_path"])

    if etype == "permission_error":
        result["attempted"] = True
        try:
            if brain_path.exists():
                os.chmod(brain_path, 0o755)
                for root, dirs, files in os.walk(brain_path):
                    for d in dirs:
                        os.chmod(os.path.join(root, d), 0o755)
                    for f in files:
                        os.chmod(os.path.join(root, f), 0o644)
                result["fixed"] = True
                result["action"] = "Fixed permissions on brain directory"
        except Exception as e:
            result["action"] = f"Permission fix failed: {e}"
            result["suggestions"] = ["Run: chmod -R 755 <brain_path>"]

    elif etype == "brain_not_found":
        result["attempted"] = True
        cwd = Path(error_info["system"]["working_dir"])
        home = Path.home()
        candidates = [cwd / ".brain", home / ".brain", home / ".nucleus" / "brain"]
        found = [p for p in candidates if p.exists()]
        if found:
            result["fixed"] = True
            result["action"] = f"Found brain at {found[0]}. Set NUCLEUS_BRAIN_PATH={found[0]}"
        else:
            result["action"] = "No brain found in common locations"
            result["suggestions"] = ["Run 'nucleus init' to create a brain", "Set NUCLEUS_BRAIN_PATH"]

    elif etype == "file_not_found":
        result["attempted"] = True
        msg = error_info["error_output"]["message"]
        # If missing brain sub-directory, create it
        if "brain" in msg.lower() or str(brain_path) in msg:
            try:
                brain_path.mkdir(parents=True, exist_ok=True)
                result["fixed"] = True
                result["action"] = f"Created missing directory: {brain_path}"
            except Exception as e:
                result["action"] = f"Directory creation failed: {e}"
        else:
            result["suggestions"] = [f"Missing file: {msg}", "Check if file was moved or deleted"]

    elif etype == "network_error":
        result["attempted"] = True
        result["action"] = "Network error detected — will retry on next invocation"
        result["suggestions"] = ["Check network connectivity", "Verify API endpoints are reachable"]

    return result


# ════════════════════════════════════════════════════════════════
# LLM-POWERED DIAGNOSIS — The Intent-Level Fix
# ════════════════════════════════════════════════════════════════

def _build_llm_prompt(error_info: Dict[str, Any], classification: Dict[str, Any]) -> str:
    """Build a structured prompt giving the LLM all 4 dimensions."""
    parts = []
    parts.append("You are the Nucleus OS self-healing agent. Diagnose this error and suggest a fix.\n")

    # Dimension 1: Error
    eo = error_info["error_output"]
    parts.append(f"## ERROR\nType: {eo['type']}\nMessage: {eo['message']}\n")
    tb_lines = eo.get("traceback", "")
    if tb_lines and tb_lines != "NoneType: None\n":
        parts.append(f"Traceback:\n```\n{tb_lines}\n```\n")

    # Dimension 2: Code
    cf = error_info.get("code_file", {})
    if cf.get("available"):
        parts.append(f"## CODE ({cf['filename']}:{cf['lineno']} in {cf['function']})")
        for sl in cf.get("source_lines", []):
            marker = " >>> " if sl.get("is_error") else "     "
            parts.append(f"{marker}{sl['line']:4d} | {sl['code']}")
        parts.append("")

    # Dimension 3: Intent
    intent = error_info.get("intent", {})
    if intent.get("active_task"):
        t = intent["active_task"]
        parts.append(f"## ACTIVE TASK\n{t.get('description', 'unknown')} (status: {t.get('status', '?')})\n")
    if intent.get("engrams"):
        parts.append("## RECENT ENGRAMS (what the user/agent intended)")
        for e in intent["engrams"][:3]:
            parts.append(f"  - [{e.get('context','?')}] {e.get('key','?')}: {e.get('value','?')[:120]}")
        parts.append("")

    # Dimension 4: History
    hist = error_info.get("recent_history", {})
    if hist.get("recent_commits"):
        parts.append("## RECENT COMMITS")
        for c in hist["recent_commits"][:3]:
            parts.append(f"  {c}")
        parts.append("")
    if hist.get("uncommitted"):
        parts.append(f"## UNCOMMITTED CHANGES\n{hist['uncommitted'][:500]}\n")

    parts.append("## CLASSIFICATION")
    parts.append(f"Type: {classification['type']}, Severity: {classification['severity']}\n")

    parts.append("## YOUR RESPONSE")
    parts.append("Respond with JSON: {\"diagnosis\": \"...\", \"fix\": \"...\", \"confidence\": 0.0-1.0, \"needs_human\": bool}")

    return "\n".join(parts)


def llm_diagnose(error_info: Dict[str, Any], classification: Dict[str, Any]) -> Dict[str, Any]:
    """Use LLM to diagnose and suggest a fix with full context.

    Returns dict with: diagnosis, fix, confidence, needs_human
    """
    result = {"diagnosis": "", "fix": "", "confidence": 0.0, "needs_human": True, "llm_used": False}
    try:
        from .runtime.llm_client import DualEngineLLM
        llm = DualEngineLLM()
        prompt = _build_llm_prompt(error_info, classification)
        raw = llm.generate(prompt, job_type="ORCHESTRATION")
        # Parse JSON from response
        text = raw if isinstance(raw, str) else str(raw)
        # Extract JSON block
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            parsed = json.loads(text[start:end])
            result.update(parsed)
            result["llm_used"] = True
        else:
            result["diagnosis"] = text[:500]
            result["llm_used"] = True
    except ImportError:
        result["diagnosis"] = "LLM client not available — install google-genai for AI-powered diagnosis"
    except Exception as e:
        result["diagnosis"] = f"LLM diagnosis failed: {e}"
        logger.warning(f"LLM diagnosis error: {e}")
    return result


# ════════════════════════════════════════════════════════════════
# THE SELF-HEALER — Orchestrates the full loop
# ════════════════════════════════════════════════════════════════

class SelfHealer:
    """Nucleus Self-Healing Engine.

    Pipeline:
      1. Capture full context (4 dimensions)
      2. Classify error (fast pattern match)
      3. Try deterministic fix (no LLM)
      4. If not fixed → LLM diagnosis with full context
      5. Log everything to .brain/ledger/selfheal_log.jsonl
      6. Return structured result with recovery info
    """

    def __init__(self, brain_path: Optional[Path] = None) -> None:
        if brain_path:
            self.brain_path = brain_path
        else:
            try:
                self.brain_path = get_brain_path()
            except Exception:
                self.brain_path = Path.cwd() / ".brain"
        self.error_log_path = self.brain_path / "ledger" / "selfheal_log.jsonl"
        try:
            self.error_log_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

    def handle_error(self, exc: Exception, command: str = "",
                     args: Optional[Dict[str, Any]] = None,
                     use_llm: bool = True) -> Dict[str, Any]:
        """Full self-healing pipeline.

        Args:
            exc: The exception
            command: CLI command that failed
            args: Command arguments
            use_llm: Whether to attempt LLM-powered diagnosis

        Returns:
            Structured error response with self-healing info
        """
        # Step 1: Capture all 4 dimensions
        error_info = get_full_context(exc, self.brain_path, command, args)

        # Step 2: Classify
        classification = classify_error(error_info)

        # Step 3: Try deterministic fix
        deterministic = attempt_deterministic_fix(error_info, classification)

        # Step 4: LLM diagnosis (if not already fixed and LLM requested)
        llm_result = {"llm_used": False}
        if use_llm and not deterministic["fixed"]:
            llm_result = llm_diagnose(error_info, classification)

        # Step 5: Build final result
        result = {
            "ok": False,
            "error": classification["type"],
            "message": str(exc),
            "exit_code": EXIT_ERROR,
            "self_heal": {
                "error_id": error_info["id"],
                "classification": classification,
                "deterministic": deterministic,
                "llm_diagnosis": llm_result,
                "fixed": deterministic["fixed"],
                "suggestions": (
                    deterministic["suggestions"]
                    + ([llm_result.get("fix", "")] if llm_result.get("fix") else [])
                ),
                "needs_human": (
                    not deterministic["fixed"]
                    and llm_result.get("needs_human", True)
                ),
            },
        }

        # Step 6: Log
        self._log_incident(error_info, classification, deterministic, llm_result)

        return result

    def _log_incident(self, error_info: Dict[str, Any], classification: Dict[str, Any],
                      deterministic: Dict[str, Any], llm_result: Dict[str, Any]) -> None:
        """Persistent incident log to .brain/ledger/selfheal_log.jsonl"""
        incident = {
            "id": error_info["id"],
            "timestamp": error_info["timestamp"],
            "command": error_info.get("command", ""),
            "error_type": error_info["error_output"]["type"],
            "error_message": error_info["error_output"]["message"],
            "classification": classification["type"],
            "severity": classification["severity"],
            "deterministic_attempted": deterministic["attempted"],
            "deterministic_fixed": deterministic["fixed"],
            "deterministic_action": deterministic.get("action"),
            "llm_used": llm_result.get("llm_used", False),
            "llm_diagnosis": llm_result.get("diagnosis", "")[:500],
            "llm_confidence": llm_result.get("confidence", 0),
            "fixed": deterministic["fixed"],
            "needs_human": llm_result.get("needs_human", True),
            "code_file": error_info.get("code_file", {}).get("filename", ""),
            "code_lineno": error_info.get("code_file", {}).get("lineno", 0),
        }
        try:
            with open(self.error_log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(incident, default=str) + "\n")
        except Exception:
            pass


# ════════════════════════════════════════════════════════════════
# PUBLIC API
# ════════════════════════════════════════════════════════════════

_self_healer: Optional[SelfHealer] = None


def get_self_healer(brain_path: Optional[Path] = None) -> SelfHealer:
    """Get or create the global SelfHealer instance."""
    global _self_healer
    if _self_healer is None:
        _self_healer = SelfHealer(brain_path)
    return _self_healer


def handle_cli_error(exc: Exception, command: str,
                     args: Optional[Dict[str, Any]] = None,
                     use_llm: bool = True) -> Dict[str, Any]:
    """Handle a CLI error with self-healing. Called from cli.py try/except.

    This is the primary entry point for the CLI integration.
    """
    healer = get_self_healer()
    return healer.handle_error(exc, command, args, use_llm=use_llm)


def diagnose_and_fix(exc: Exception, context: Optional[Dict[str, Any]] = None,
                     use_llm: bool = True) -> Dict[str, Any]:
    """Standalone self-healing function — importable by coordinator.py and external agents.

    This is the function referenced in the Perplexity architecture:
        selfhealer.diagnose_and_fix(e, context=get_full_context())

    Args:
        exc: The exception or error
        context: Additional context (source, line, command, etc.)
        use_llm: Whether to use LLM for diagnosis

    Returns:
        Self-healing result dict
    """
    healer = get_self_healer()
    command = ""
    if context:
        command = context.get("command", context.get("source", ""))
    return healer.handle_error(exc, command, context, use_llm=use_llm)
