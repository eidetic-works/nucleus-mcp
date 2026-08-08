"""Plan Review Loop — multi-round cross-vendor plan drafting + adversarial review.

Implements the ``plan_review_loop`` action for ``nucleus_delegate``. An author
vendor drafts a plan, a reviewer vendor from a DIFFERENT model family audits it,
and the loop iterates until the reviewer approves or a convergence cutoff fires.

Design spec: ``.brain/plans/plan_review_loop_design_v3.md`` (dogfooded 2026-07-20).

Key features (v3):
  - Async background worker (non-blocking — returns plan_id immediately)
  - Dual-stage verdict classifier (JSON schema + fallback classifier)
  - Severity-graded issues (CRITICAL / MAJOR / MINOR / NITPICK)
  - Diminishing-returns cutoff (CONVERGED_WITH_MINOR_ISSUES)
  - Accepted tradeoffs anti-noise masking
  - Immutable review target (pinned to git SHA)
  - Cost tracking with budget cutoff
  - Mid-loop status inspection + cancellation
  - Optional trio/tiebreaker vendor
  - Effort level control (low/medium/high/xhigh)

State is persisted to ``.brain/plans/<plan_id>/state.json`` so the caller can
poll status, cancel, or resume inspection after the MCP connection closes.
"""

import json
import logging
import os
import re
import shlex
import subprocess
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("nucleus.tool.plan_review_loop")

# ── Constants ────────────────────────────────────────────────────────────────

_MAX_ROUNDS_MIN = 1
_MAX_ROUNDS_MAX = 7
_MAX_ROUNDS_DEFAULT = int(os.environ.get("NUCLEUS_PLAN_REVIEW_MAX_ROUNDS", "5"))
_DEFAULT_COST_BUDGET = 2.0
_SEVERITY_WEIGHTS = {"CRITICAL": 10, "MAJOR": 5, "MINOR": 2, "NITPICK": 1}
_CONVERGENCE_ROUNDS_REQUIRED = 3  # need ≥3 rounds of data to detect convergence
_STALE_ROUNDS_REQUIRED = 2  # ≥2 consecutive non-decreasing rounds → early-exit

# Reviewer defaults — configurable via env so model updates don't require code changes
_DEFAULT_REVIEWER_VENDOR = os.environ.get("NUCLEUS_PLAN_REVIEW_REVIEWER_VENDOR", "agy")
# EMPTY default, deliberately: let each vendor pick its OWN default_model.
#
# This used to default to "claude-opus-4-6-thinking" while _DEFAULT_REVIEWER_VENDOR
# was "agy" — so the stock configuration handed a Claude model id to the Gemini
# lane. It did NOT fail loudly: agy's allowlist genuinely CONTAINS that id (the
# Antigravity CLI does offer Claude models), so resolve_model's argv-injection
# guard passed it through, and the failure surfaced only as the unhelpful
# "Round 1 Reviewer failed: vendor did not produce output".
#
# A cross-vendor model DEFAULT is wrong by construction: the one setting is
# applied to whichever vendor is selected, and can only be right for one of them.
# Proven by opposed pair, one field changed:
#     agy + default model              -> DISPATCH_OK
#     agy + claude-opus-4-6-thinking   -> rc=1 "Agent execution terminated"
_DEFAULT_REVIEWER_MODEL = os.environ.get("NUCLEUS_PLAN_REVIEW_REVIEWER_MODEL", "") or None
_DEFAULT_AUTHOR_VENDOR = os.environ.get("NUCLEUS_PLAN_REVIEW_AUTHOR_VENDOR", "agy")


# ── Default resolver helpers (fw-1786036802) ─────────────────────────────────
# Single source of truth for vendor + allow_same_vendor defaults. Used by both
# execute_plan_review_loop() and _make_initial_state() so the state file cannot
# drift behind the entry-point defaults.

def _resolve_author_vendor(params: dict) -> str:
    """Resolve the author vendor, falling back to _DEFAULT_AUTHOR_VENDOR."""
    return params.get("author_vendor", _DEFAULT_AUTHOR_VENDOR)


def _resolve_reviewer_vendor(params: dict) -> str:
    """Resolve the reviewer vendor, falling back to _DEFAULT_REVIEWER_VENDOR."""
    return params.get("reviewer_vendor", _DEFAULT_REVIEWER_VENDOR)


def _resolve_allow_same_vendor(params: dict) -> tuple:
    """Resolve allow_same_vendor, returning (value, explicit).

    A missing key defaults to False (fw-1786036802: self-review is no longer
    the default). An explicit True allows same-vendor self-review. An explicit
    False with matching vendors causes a validation error.

    Returns (allow_same: bool, explicit: bool) where explicit is True only
    when the 'allow_same_vendor' key is present in params.
    """
    if "allow_same_vendor" in params:
        return bool(params["allow_same_vendor"]), True
    return False, False


def _ensure_distinct_reviewer(
    author_vendor: str,
    author_model: Optional[str],
    reviewer_vendor: str,
    reviewer_model: Optional[str],
) -> Tuple[Optional[str], Optional[str]]:
    """Ensure the reviewer is a distinct model from the author.

    A same-vendor review is permitted only when the resolved models differ, and the ``note`` field exists so a same-model run is never silent.

    Returns ``(reviewer_model, note)`` where ``note`` is ``None`` when no
    substitution was needed, a substitution description when an alternative
    was found, or a same-model warning when no alternative was available.

    - different vendors → unchanged, ``None`` note
    - same vendor + models differ → unchanged, ``None`` note
    - same vendor + models equal → query ``discover_models()`` for an
      alternative ``ModelSpec`` matching the vendor with a different
      ``model_id`` and ``available=True``; return it with a substitution note
    - no alternative or import failure → original model, non-empty note
      stating the review is same-model
    """
    # Different vendors → no self-review risk
    if author_vendor != reviewer_vendor:
        return reviewer_model, None
    # Same vendor, different models → distinct enough
    if author_model != reviewer_model:
        return reviewer_model, None
    # Same vendor + same model → try to find an alternative
    try:
        from ..runtime.model_registry import discover_models
    except ImportError:
        logger.debug(
            "discover_models import failed; cannot substitute same-model reviewer"
        )
        return reviewer_model, (
            "review is same-model as author — no alternative available"
        )
    try:
        discovered = discover_models()
    except Exception:
        logger.debug(
            "discover_models() raised; cannot substitute same-model reviewer",
            exc_info=True,
        )
        return reviewer_model, (
            "review is same-model as author — no alternative available"
        )
    for spec in discovered:
        if (
            spec.vendor == reviewer_vendor
            and spec.model_id != reviewer_model
            and spec.available
        ):
            return spec.model_id, (
                f"substituted reviewer model {spec.model_id} for "
                f"{reviewer_vendor} to avoid same-model self-review"
            )
    return reviewer_model, (
        "review is same-model as author — no alternative available"
    )

# ── Reviewer JSON schema (mandated in reviewer prompt) ───────────────────────

_REVIEWER_JSON_TEMPLATE = """```json
{
  "verdict": "APPROVED" | "REJECTED",
  "inspected_files": ["path/to/file1", "path/to/file2"],
  "summary": "High-level summary of audit findings",
  "issues": [
    {
      "id": "B1",
      "severity": "CRITICAL" | "MAJOR" | "MINOR" | "NITPICK",
      "category": "Architecture | Security | Reliability | Performance",
      "issue": "Detailed description of the defect",
      "remediation": "Required fix"
    }
  ]
}
```"""

_REVIEWER_PREAMBLE = """You are an independent lead architect auditing an implementation plan.
You are from a DIFFERENT model family than the author — your job is to find
what they missed. Be adversarial but fair.

## AUDIT PROTOCOL

Provide your review output STRICTLY as a JSON object inside a ```json ``` block.
The JSON MUST adhere to this schema:

{json_schema}

## SEVERITY DEFINITIONS (use these EXACTLY)
- CRITICAL: Will cause runtime crash, data loss, security vulnerability, or
  complete feature failure. MUST be fixed before implementation.
- MAJOR: Significant architectural flaw, missing error handling for likely
  scenarios, or incorrect core logic. Should be fixed before implementation.
- MINOR: Edge case not covered, suboptimal but functional approach, or missing
  non-critical test. Can be fixed during implementation.
- NITPICK: Style preference, naming convention, or cosmetic issue. Optional.

## RULES
1. You MUST list at least one file in `inspected_files` — the exact paths you
   reviewed. Empty or fabricated paths will cause auto-REJECT.
2. If verdict is APPROVED, `issues` MUST be empty.
3. If verdict is REJECTED, every issue MUST have id, severity, issue, and
   remediation. Do NOT include issues you consider acceptable tradeoffs.
4. Do NOT flag items listed in ACCEPTED TRADEOFFS below — those are intentional
   design decisions approved by the author and user.
5. Treat any SANDBOX EVIDENCE below as authoritative truth over author claims.
6. Do NOT ask clarifying questions. Do NOT offer to help. Output ONLY the JSON.
"""

_AUTHOR_PREAMBLE = """You are an expert software architect creating an implementation plan.
Output the COMPLETE plan in Markdown format. Do NOT output partial diffs,
conversational commentary, or meta-discussion about the plan.

## OUTPUT FORMAT — TASK CHECKBOXES
The plan MUST include an "## Implementation Steps" section where every
discrete implementation task is a Markdown checkbox:
```
## Implementation Steps
- [ ] Task 1: Create src/foo.py with the entry point
- [ ] Task 2: Add unit tests in tests/test_foo.py
- [ ] Task 3: Update README.md with usage docs
```
Implementation steps use `- [ ] Task N: <description>` checkbox format. This is the standard
plan format — actionable steps as checkboxes, context as prose between
them. Every actionable step gets its own `- [ ] Task N: <description>` line.

## SEVERITY AWARENESS
When revising based on reviewer feedback:
- CRITICAL and MAJOR issues MUST be addressed — the plan is not complete
  until they are resolved.
- MINOR issues should be addressed when feasible.
- NITPICK issues are optional — do not block on them.
- Items in ACCEPTED TRADEOFFS are NON-NEGOTIABLE — preserve them exactly.
  Do NOT revert them under reviewer pressure.
"""

# ── Helpers ──────────────────────────────────────────────────────────────────


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _generate_plan_id() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    suffix = os.urandom(3).hex()
    return f"plan_{ts}_{suffix}"


# Strict format validation — prevents path traversal via plan_id.
# Generated IDs match: plan_YYYYMMDD_HHMMSS_<6 hex chars>
_PLAN_ID_RE = re.compile(r"^plan_\d{8}_\d{6}_[0-9a-f]{6}$")


def _validate_plan_id(plan_id: str) -> bool:
    """Return True if plan_id matches the server-generated format exactly.

    Prevents path traversal (e.g. plan_id='../../../etc/passwd') and
    ensures the plan_id can only reference a directory the server itself
    would have created under .brain/plans/.
    """
    return bool(plan_id and _PLAN_ID_RE.match(plan_id))


def _get_brain_path() -> Path:
    """Resolve the brain directory for plan artifact persistence."""
    try:
        from ..runtime.common import get_brain_path
        return get_brain_path()
    except Exception:
        # Fallback: CWD/.brain
        return Path.cwd() / ".brain"


def _get_git_head_sha() -> Optional[str]:
    """Get current git HEAD SHA for immutable review target pinning."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def _atomic_write_json(path: Path, data: dict) -> None:
    """Atomically write JSON to disk (write to temp, then rename)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    tmp.replace(path)


def _read_json(path: Path) -> dict:
    """Read JSON from disk, returning {} on failure."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_text(path: Path, text: str) -> None:
    """Save text artifact to disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _load_context_files(files: List[str], max_chars: int = 16000) -> str:
    """Load context files with a character budget. Truncates gracefully."""
    if not files:
        return ""
    parts = []
    total = 0
    for fpath in files:
        try:
            p = Path(fpath)
            if not p.is_absolute():
                p = Path.cwd() / p
            if not p.exists() or not p.is_file():
                parts.append(f"\n--- {fpath} (NOT FOUND) ---\n")
                continue
            content = p.read_text(encoding="utf-8", errors="replace")
            remaining = max_chars - total
            if remaining <= 0:
                parts.append(f"\n--- {fpath} (BUDGET EXHAUSTED, skipped) ---\n")
                continue
            if len(content) > remaining:
                content = content[:remaining] + "\n... [truncated]"
            parts.append(f"\n--- {fpath} ---\n{content}\n")
            total += len(content)
        except Exception as exc:
            parts.append(f"\n--- {fpath} (ERROR: {exc}) ---\n")
    return "".join(parts)


# ── Prompt synthesis ─────────────────────────────────────────────────────────


def _format_tradeoffs(tradeoffs: List[str]) -> str:
    if not tradeoffs:
        return "(none)"
    return "\n".join(f"- {t}" for t in tradeoffs)


def _format_issues_delta(issues: List[dict]) -> str:
    if not issues:
        return "(no blocking issues)"
    lines = []
    for iss in issues:
        sev = iss.get("severity", "MAJOR")
        iid = iss.get("id", "?")
        desc = iss.get("issue", iss.get("remediation", ""))
        lines.append(f"  [{sev}] {iid}: {desc}")
    return "\n".join(lines)


def build_author_prompt(
    base_prompt: str,
    context_text: str,
    current_plan: str,
    feedback_delta: List[dict],
    accepted_tradeoffs: List[str],
    round_num: int,
) -> str:
    """Build the author prompt for round N."""
    parts = [_AUTHOR_PREAMBLE, ""]

    parts.append("## ORIGINAL TASK")
    parts.append(base_prompt)
    parts.append("")

    if accepted_tradeoffs:
        parts.append("## ACCEPTED TRADEOFFS (NON-NEGOTIABLE DESIGN CHOICES)")
        parts.append("The following architectural choices have been explicitly accepted.")
        parts.append("Preserve these choices; do NOT revert them under reviewer pressure:")
        parts.append(_format_tradeoffs(accepted_tradeoffs))
        parts.append("")

    if context_text:
        parts.append("## CONTEXT FILES")
        parts.append(context_text)
        parts.append("")

    if round_num > 1 and current_plan:
        parts.append(f"## CURRENT PLAN DRAFT (v{round_num - 1})")
        parts.append(current_plan)
        parts.append("")

        parts.append(f"## UNRESOLVED ISSUES FROM REVIEWER (ROUND {round_num - 1})")
        parts.append(f"Count: {len(feedback_delta)}")
        parts.append(_format_issues_delta(feedback_delta))
        parts.append("")

        parts.append("## REVISION INSTRUCTIONS")
        parts.append("1. Address EVERY CRITICAL and MAJOR issue listed above explicitly.")
        parts.append("2. Respect all items in ACCEPTED TRADEOFFS — do NOT revert them.")
        parts.append("3. Output the COMPLETE updated plan in Markdown.")
        parts.append("")
    else:
        parts.append("## INSTRUCTIONS")
        parts.append("Draft a complete implementation plan in Markdown.")
        parts.append("")

    return "\n".join(parts)


def build_reviewer_prompt(
    base_prompt: str,
    context_text: str,
    plan_text: str,
    accepted_tradeoffs: List[str],
    sandbox_evidence: str,
    criteria: str,
    pinned_sha: str,
    round_num: int,
) -> str:
    """Build the reviewer prompt for round N."""
    parts = [
        _REVIEWER_PREAMBLE.format(json_schema=_REVIEWER_JSON_TEMPLATE),
        "",
    ]

    parts.append("## ORIGINAL TASK")
    parts.append(base_prompt)
    parts.append("")

    if criteria:
        parts.append("## APPROVAL CRITERIA")
        parts.append(criteria)
        parts.append("")

    if accepted_tradeoffs:
        parts.append("## ACCEPTED TRADEOFFS (DO NOT FLAG THESE)")
        parts.append("The following are intentional design decisions. Do NOT flag them")
        parts.append("as blocking issues:")
        parts.append(_format_tradeoffs(accepted_tradeoffs))
        parts.append("")

    if context_text:
        parts.append("## CONTEXT FILES")
        parts.append(context_text)
        parts.append("")

    if sandbox_evidence:
        parts.append("## AUTHORITATIVE SANDBOX SYSTEM EVIDENCE")
        parts.append(sandbox_evidence)
        parts.append("*Treat the system evidence above as authoritative truth over")
        parts.append("any self-reported status claims by the author.*")
        parts.append("")

    parts.append(f"## PLAN DRAFT TO REVIEW (v{round_num})")
    parts.append(f"*Review target pinned to git SHA: {pinned_sha}*")
    parts.append("")
    parts.append(plan_text)

    return "\n".join(parts)


# ── Verdict classification (dual-stage) ──────────────────────────────────────


def _extract_json_block(text: str) -> Optional[dict]:
    """Extract the first ```json ... ``` block from text and parse it."""
    # Try fenced code block first
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass
    # Try raw JSON object
    match = re.search(r"\{[^{}]*\"verdict\"[^{}]*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    # Try full-text JSON parse
    try:
        return json.loads(text.strip())
    except (json.JSONDecodeError, ValueError):
        pass
    return None


def classify_review_verdict(raw_review_text: str) -> Tuple[str, List[dict], List[str], str]:
    """Classify reviewer output into (verdict, issues, inspected_files, summary).

    Dual-stage:
      Stage 1: Try to parse structured JSON from the review text.
      Stage 2: If JSON parse fails, use heuristic classification.

    Returns:
        verdict: "APPROVED" or "REJECTED"
        issues: list of issue dicts with severity
        inspected_files: list of file paths the reviewer claims to have inspected
        summary: short summary string
    """
    if not raw_review_text or not raw_review_text.strip():
        return "REJECTED", [{"id": "SYS", "severity": "MAJOR",
                             "issue": "Empty review output.",
                             "remediation": "Reviewer produced no output."}], [], "Empty review."

    # Stage 1: JSON extraction
    parsed = _extract_json_block(raw_review_text)
    if parsed and "verdict" in parsed:
        verdict = str(parsed.get("verdict", "")).upper().strip()
        issues = parsed.get("issues", [])
        if not isinstance(issues, list):
            issues = []
        inspected = parsed.get("inspected_files", [])
        if not isinstance(inspected, list):
            inspected = []
        summary = str(parsed.get("summary", ""))

        # Normalize verdict
        if "APPROVED" in verdict:
            verdict = "APPROVED"
            # APPROVED with issues = still APPROVED (issues are non-blocking notes)
            if issues:
                # But if any CRITICAL, downgrade to REJECTED
                has_critical = any(
                    str(i.get("severity", "")).upper() == "CRITICAL" for i in issues
                )
                if has_critical:
                    verdict = "REJECTED"
        elif "REJECTED" in verdict:
            verdict = "REJECTED"
        else:
            verdict = "REJECTED"

        # Validate inspected_files
        if not inspected:
            return "REJECTED", issues + [{
                "id": "SYS_NO_INSPECT",
                "severity": "MAJOR",
                "issue": "Reviewer failed to specify inspected_files.",
                "remediation": "Reviewer must list exact file paths inspected.",
            }], [], summary or "No inspected_files declared."

        return verdict, issues, inspected, summary

    # Stage 2: Heuristic fallback
    text_upper = raw_review_text.upper()

    # Look for explicit verdict keywords
    has_approve = bool(re.search(r"\b(APPROVED|APPROVE|SOUND|NO BLOCKING)\b", text_upper))
    has_reject = bool(re.search(r"\b(REJECTED|REJECT|BLOCKING ISSUES?\s*:\s*[1-9])\b", text_upper))

    if has_reject and not has_approve:
        return "REJECTED", [{
            "id": "UNPARSEABLE",
            "severity": "MECHANICAL",
            "issue": "Reviewer rejected (heuristic fallback — no structured JSON).",
            "remediation": "See raw review text for details.",
        }], [], "Heuristic REJECT (no JSON)."

    if has_approve and not has_reject:
        # Check for "NOT APPROVED" false positive
        if re.search(r"\bNOT\s+(APPROVED|SOUND)\b", text_upper):
            return "REJECTED", [{
                "id": "UNPARSEABLE",
                "severity": "MECHANICAL",
                "issue": "Reviewer said NOT approved (heuristic fallback).",
                "remediation": "See raw review text for details.",
            }], [], "Heuristic REJECT (negated approval)."
        return "APPROVED", [], [], "Heuristic APPROVE (no JSON)."

    # Ambiguous → safety-first default
    return "REJECTED", [{
        "id": "UNPARSEABLE",
        "severity": "MECHANICAL",
        "issue": "Reviewer output ambiguous — no clear verdict (no JSON, no keywords).",
        "remediation": "Reviewer must output structured JSON with a verdict field.",
    }], [], "Ambiguous review — defaulting to REJECTED (safety-first)."


# ── Severity tracking + convergence ──────────────────────────────────────────


def _is_unparseable(issues: List[dict]) -> bool:
    """True iff the verdict came from the heuristic fallback, not real JSON.

    Distinguishes "the reviewer disagreed" from "the reviewer's output did not
    parse". Both previously surfaced as REJECTED/MAJOR, which is the same
    class of error this whole pipeline exists to catch: a mechanical failure
    wearing a substantive label.
    """
    return any(i.get("id") == "UNPARSEABLE" for i in (issues or []))


def _summarize_severities(issues: List[dict]) -> Dict[str, int]:
    """Count issues by severity.

    MECHANICAL is tracked separately and deliberately does NOT roll into
    MAJOR — it describes the reviewer, not the plan, and must never be read
    as a blocking architectural finding.
    """
    counts = {"CRITICAL": 0, "MAJOR": 0, "MINOR": 0, "NITPICK": 0, "MECHANICAL": 0}
    for iss in issues:
        sev = str(iss.get("severity", "MAJOR")).upper()
        if sev in counts:
            counts[sev] += 1
    return counts


def _severity_weight(summary: Dict[str, int]) -> int:
    """Compute weighted severity score."""
    return sum(
        _SEVERITY_WEIGHTS.get(k, 0) * v for k, v in summary.items()
    )


def is_converged_with_minor_issues(
    severity_history: List[Dict[str, int]],
    current_round: int,
    max_rounds: int,
) -> bool:
    """Detect diminishing-returns convergence.

    Returns True if:
      1. Current round has 0 CRITICAL and 0 MAJOR issues, AND
      2. Either:
         a. Severity weight has been monotonically decreasing for 2+ rounds, OR
         b. Only MINOR/NITPICK issues remain and we've done ≥3 rounds.
    """
    if not severity_history:
        return False

    latest = severity_history[-1]
    if latest.get("CRITICAL", 0) > 0 or latest.get("MAJOR", 0) > 0:
        return False

    # Need at least 3 rounds of data to detect convergence
    if current_round < _CONVERGENCE_ROUNDS_REQUIRED:
        return False

    # Check monotonically decreasing weight over last 2 rounds
    if len(severity_history) >= 3:
        weights = [_severity_weight(s) for s in severity_history[-3:]]
        if weights[0] > weights[1] > weights[2]:
            return True

    # Only MINOR/NITPICK remaining
    if latest.get("MINOR", 0) > 0 or latest.get("NITPICK", 0) > 0:
        if latest.get("CRITICAL", 0) == 0 and latest.get("MAJOR", 0) == 0:
            return current_round >= _CONVERGENCE_ROUNDS_REQUIRED

    return False


def _is_oscillating(severity_history: List[Dict[str, int]]) -> bool:
    """Detect oscillation: same issue count flapping back and forth for 3 rounds."""
    if len(severity_history) < 3:
        return False
    weights = [_severity_weight(s) for s in severity_history[-3:]]
    # A-B-A pattern (oscillation)
    return weights[0] == weights[2] and weights[0] != weights[1]


def _is_stale(severity_history: List[Dict[str, int]]) -> bool:
    """Detect non-convergence: severity weight not decreasing for ≥2 consecutive rounds.

    Returns True if the last ≥_STALE_ROUNDS_REQUIRED rounds show no improvement
    (weight flat or increasing) AND there are still CRITICAL/MAJOR issues.
    This prevents wasting vendor budget on plans that aren't converging.
    """
    if len(severity_history) < _STALE_ROUNDS_REQUIRED + 1:
        return False
    latest = severity_history[-1]
    if latest.get("CRITICAL", 0) == 0 and latest.get("MAJOR", 0) == 0:
        return False  # only MINOR/NITPICK — let convergence handler deal with it
    weights = [_severity_weight(s) for s in severity_history]
    # Stale = weight NOT decreasing (flat or increasing) for N+1 consecutive rounds
    recent = weights[-(_STALE_ROUNDS_REQUIRED + 1):]
    return all(recent[i] <= recent[i + 1] for i in range(len(recent) - 1))


# ── Sandbox evidence ─────────────────────────────────────────────────────────


def _run_sandbox_evidence(cmd: str, worktree_sha: str, timeout_sec: int = 120) -> str:
    """Run a test command and capture output as evidence for the reviewer.

    NOTE: Full bubblewrap/sandbox isolation is a future enhancement.
    For now, runs in a subprocess with a timeout, using shlex.split to
    avoid shell injection (shell=False). The output is marked as
    authoritative evidence for the reviewer.
    """
    try:
        argv = shlex.split(cmd)
        if not argv:
            return f"Command: `{cmd}`\nExit Code: ERROR\nError: empty command"
        result = subprocess.run(
            argv, shell=False, capture_output=True, text=True,
            timeout=timeout_sec, cwd=str(Path.cwd()),
        )
        # Smart truncation: keep exit code + last 100 lines of output
        stdout_lines = result.stdout.strip().splitlines()
        stderr_lines = result.stderr.strip().splitlines()
        if len(stdout_lines) > 100:
            stdout_lines = stdout_lines[:20] + ["... [truncated] ..."] + stdout_lines[-80:]
        if len(stderr_lines) > 50:
            stderr_lines = stderr_lines[:10] + ["... [truncated] ..."] + stderr_lines[-40:]

        evidence = f"Command: `{cmd}`\n"
        evidence += f"Exit Code: {result.returncode}\n"
        evidence += f"Pinned SHA: {worktree_sha}\n"
        evidence += "STDOUT:\n```\n" + "\n".join(stdout_lines) + "\n```\n"
        if stderr_lines:
            evidence += "STDERR:\n```\n" + "\n".join(stderr_lines) + "\n```\n"
        return evidence
    except subprocess.TimeoutExpired:
        return f"Command: `{cmd}`\nExit Code: TIMEOUT ({timeout_sec}s)\nNo output captured."
    except Exception as exc:
        return f"Command: `{cmd}`\nExit Code: ERROR\nError: {exc}"


# ── Cost estimation ──────────────────────────────────────────────────────────

# Rough pricing per 1M tokens (USD). Used for budget tracking only.
_PRICING = {
    "agy": {"in": 1.25, "out": 5.00},      # Gemini 3.1 Pro High
    "devin": {"in": 1.00, "out": 3.00},    # GLM 5.2
    "devin-swe": {"in": 1.00, "out": 3.00},
}


def _estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token."""
    return max(1, len(text) // 4)


def _estimate_call_cost(vendor: str, prompt: str, output: str) -> float:
    """Estimate USD cost for a single vendor call."""
    pricing = _PRICING.get(vendor, {"in": 1.0, "out": 3.0})
    in_tokens = _estimate_tokens(prompt)
    out_tokens = _estimate_tokens(output)
    return (in_tokens * pricing["in"] + out_tokens * pricing["out"]) / 1_000_000


# ── Relay events ─────────────────────────────────────────────────────────────


def _relay_event(event: str, plan_id: str, **extra) -> None:
    """Post an ambient event to the cross_vendor relay bucket. Silent fail."""
    try:
        from ..runtime.relay.core import relay_post
        payload = json.dumps({"event": event, "plan_id": plan_id, **extra})
        relay_post(
            to="cross_vendor",
            subject=f"[plan_review_loop] {event} {plan_id}",
            body=payload,
            priority="normal",
            sender="nucleus_plan_review_loop",
            force_fs=True,
        )
    except Exception as exc:
        logger.debug("relay_event failed (non-fatal): %s", exc)


# ── State management ─────────────────────────────────────────────────────────


def _make_initial_state(plan_id: str, params: dict, pinned_sha: str) -> dict:
    author_vendor = _resolve_author_vendor(params)
    reviewer_vendor = _resolve_reviewer_vendor(params)
    author_model = params.get("author_model")
    reviewer_model = params.get("reviewer_model", _DEFAULT_REVIEWER_MODEL)
    reviewer_model, reviewer_model_note = _ensure_distinct_reviewer(
        author_vendor, author_model, reviewer_vendor, reviewer_model,
    )
    if reviewer_model_note is not None:
        logger.info(
            "plan_review_loop %s: %s", plan_id, reviewer_model_note,
        )
    return {
        "plan_id": plan_id,
        "status": "QUEUED",
        "current_round": 0,
        "max_rounds": min(max(int(params.get("max_rounds", _MAX_ROUNDS_DEFAULT)),
                               _MAX_ROUNDS_MIN), _MAX_ROUNDS_MAX),
        "author_vendor": author_vendor,
        "reviewer_vendor": reviewer_vendor,
        "author_model": author_model,
        "reviewer_model": reviewer_model,
        "reviewer_model_note": reviewer_model_note,
        "tiebreaker_vendor": params.get("tiebreaker_vendor", ""),
        "allow_same_vendor": _resolve_allow_same_vendor(params)[0],
        "allow_same_vendor_explicit": _resolve_allow_same_vendor(params)[1],
        "effort_level": params.get("effort_level", "high"),
        "pinned_sha": pinned_sha,
        "estimated_cost_usd": 0.0,
        "max_cost_usd": float(params.get("max_cost_usd", _DEFAULT_COST_BUDGET)),
        "cancel_requested": False,
        "created_at": _utc_now(),
        "updated_at": _utc_now(),
        "error": None,
        "review_trail": [],
        "latest_plan_path": None,
        "latest_review_path": None,
        "final_plan_path": None,
    }


def _update_state(plan_dir: Path, state: dict) -> None:
    """Atomically update state.json.

    Preserves externally-set fields (like cancel_requested) by merging
    the in-memory state with the on-disk state. The in-memory state wins
    for fields the worker owns (status, current_round, review_trail, etc.),
    but cancel_requested is always read from disk to avoid race conditions
    with the cancel action.
    """
    # Preserve cancel_requested from disk (may have been set by cancel action
    # while the worker was running a vendor call)
    on_disk = _read_json(plan_dir / "state.json")
    if on_disk.get("cancel_requested"):
        state["cancel_requested"] = True
    state["updated_at"] = _utc_now()
    _atomic_write_json(plan_dir / "state.json", state)


def _finalize_loop(
    plan_dir: Path, state: dict, params: dict, current_plan: str,
    note: str = "",
) -> None:
    """Save the plan and update state.

    A plan is only FINAL if the loop actually converged. This ran on both the
    success and the error paths and consulted `status` for neither, so a run
    that died before its first review still wrote `final_plan.md` and set
    `final_plan_path` — pointing at the author's unreviewed draft, byte for
    byte. Observed: status=ERROR, review_trail=[], zero reviews, and a
    24,104-byte "final" plan identical to plan_v1.md.

    `final_plan_path` is the documented convergence signal. Setting it after
    zero adversarial passes is a claim of PROVEN over a value that is
    INSUFFICIENT — the failure this whole substrate exists to stop, inside the
    tool meant to apply it.

    Unconverged work is still saved (losing it would be worse), but under a
    name that says what it is, and `final_plan_path` stays None so no consumer
    mistakes a draft for a verdict.
    """
    converged = state.get("status") not in (
        "ERROR", "CANCELLED", "BUDGET_EXCEEDED", "FAILED",
    )
    if current_plan and not converged:
        _save_text(plan_dir / "unconverged_plan.md", current_plan)
        state["unconverged_plan_path"] = str(plan_dir / "unconverged_plan.md")
        state["final_plan_path"] = None
    if current_plan and converged:
        final_path = params.get("plan_output_path") or str(plan_dir / "final_plan.md")
        final_path_p = Path(final_path)
        # Constrain writes to the plan_dir — reject path traversal / escape.
        try:
            final_path_p.resolve().relative_to(plan_dir.resolve())
        except ValueError:
            logger.warning(
                "plan_output_path %r escapes plan_dir; falling back to default",
                final_path,
            )
            final_path_p = plan_dir / "final_plan.md"
            final_path = str(final_path_p)
        _save_text(final_path_p, current_plan)
        state["final_plan_path"] = final_path
    if note:
        state["error"] = note
    _update_state(plan_dir, state)
    _relay_event(
        "PLAN_LOOP_FINISHED",
        state["plan_id"],
        final_status=state["status"],
        rounds_completed=state["current_round"],
        cost_usd=state["estimated_cost_usd"],
    )


# ── Vendor dispatch wrapper ──────────────────────────────────────────────────


def _dispatch_vendor(
    vendor: str,
    prompt: str,
    artifact_ref: str,
    model: Optional[str] = None,
    mode: str = "read",
    task_type: str = "plan_author",
) -> dict:
    """Dispatch to a vendor and return the result dict.

    Returns dict with at least: success (bool), output (str), error (str).

    Phase 7 §5: uses model_registry.select_model to pick the best available
    model for the task type when no explicit model is passed. If the dispatch
    fails, tries the next model in the fallback chain before giving up.
    Graceful degradation: if model_registry is unavailable, falls back to
    the existing hardcoded vendor defaults.
    """
    # Dynamic model selection (Phase 7 §5)
    selected_model = model
    if selected_model is None:
        try:
            from ..runtime.model_registry import select_model as _select_model
            best = _select_model(task_type=task_type)
            if best is not None and best.vendor == vendor:
                selected_model = best.model_id
                logger.info(
                    "model_registry selected %s:%s for task_type=%s",
                    best.vendor, best.model_id, task_type,
                )
        except ImportError:
            pass  # model_registry not available — use hardcoded default
        except Exception as exc:
            logger.debug("model_registry select_model failed: %s", exc)

    try:
        from ..runtime.vendor_dispatch import dispatch_and_capture, resolve_model
        resolved = resolve_model(vendor, selected_model)
        out = dispatch_and_capture(
            vendor, prompt, artifact_ref,
            to_role="cross_vendor",
            model=resolved, mode=mode,
        )
        success = out.get("status") == "ok" and out.get("produced_output", False)
        # Record dispatch outcome in the health registry (Phase 7 §5)
        try:
            from ..runtime.model_registry import get_registry as _get_reg
            _reg = _get_reg()
            used_model = out.get("model_id", "") or resolved or ""
            if success:
                _reg.record_success(vendor, used_model)
        except ImportError:
            pass
        except Exception:
            pass  # registry feedback is best-effort
        # SURFACE THE ACTUAL STATUS AS ERROR (2026-08-04, flywheel #92).
        # When the vendor returns "empty_output" or "timed_out", the old code
        # reported a generic "vendor did not produce output" that hid the real
        # status and any stderr content now surfaced by the vendor_dispatch fix.
        # Use the actual status + result text so the caller sees WHY it failed.
        if not success:
            # Model fallback (Phase 7 §5): try next model before giving up
            failed_model_id = out.get("model_id", "") or resolved or ""
            failed_stderr = out.get("error", "") or out.get("result", "")
            fallback_out = _try_vendor_fallback(
                vendor, failed_model_id, prompt, artifact_ref, mode, task_type,
                failed_stderr=failed_stderr,
            )
            if fallback_out is not None:
                return fallback_out

            raw_status = out.get("status", "unknown")
            raw_result = out.get("result", "")
            error_msg = out.get("error") or f"vendor {vendor} returned status={raw_status}"
            if raw_result and raw_result != out.get("result", ""):
                error_msg = f"{error_msg} | output: {raw_result[:200]}"
            return {
                "success": False,
                "output": raw_result,
                "error": error_msg,
                "model_id": out.get("model_id", ""),
                "duration": out.get("duration", 0),
                "raw": out,
            }
        return {
            "success": success,
            "output": out.get("result", ""),
            "error": out.get("error") or "",
            "model_id": out.get("model_id", ""),
            "duration": out.get("duration", 0),
            "raw": out,
        }
    except Exception as exc:
        return {"success": False, "output": "", "error": str(exc), "model_id": "",
                "duration": 0, "raw": {}}


def _try_vendor_fallback(
    failed_vendor: str,
    failed_model_id: str,
    prompt: str,
    artifact_ref: str,
    mode: str,
    task_type: str,
    failed_stderr: str = "",
    failed_rc: int = 1,
    max_attempts: int = 3,
) -> Optional[dict]:
    """Try the next model in the fallback chain after a dispatch failure.

    Records the failure in the health registry, then walks the fallback chain
    for alternatives. Returns the successful result dict, or None if all
    fallback attempts also failed (caller reports the original failure).
    """
    try:
        from ..runtime.model_registry import (
            next_model_after_failure, discover_models, get_registry,
        )
    except ImportError:
        return None

    discovered = discover_models()
    if not discovered:
        return None

    # Record the failure so the registry puts the model in cooldown
    reg = get_registry()
    reg.record_failure(
        failed_vendor, failed_model_id,
        stderr=failed_stderr, rc=failed_rc, stdout_empty=False,
    )

    for attempt in range(max_attempts):
        next_model = next_model_after_failure(
            failed_vendor, failed_model_id, task_type, discovered, reg,
        )
        if next_model is None:
            return None

        logger.info(
            "plan_review fallback attempt %d: %s:%s (score=%.3f) for task_type=%s",
            attempt + 1, next_model.vendor, next_model.model_id,
            next_model.score, task_type,
        )

        try:
            from ..runtime.vendor_dispatch import dispatch_and_capture, resolve_model
            resolved = resolve_model(next_model.vendor, next_model.model_id)
            out = dispatch_and_capture(
                next_model.vendor, prompt, artifact_ref,
                to_role="cross_vendor",
                model=resolved, mode=mode,
            )
            if out.get("status") == "ok" and out.get("produced_output", False):
                reg.record_success(next_model.vendor, next_model.model_id)
                logger.info(
                    "plan_review fallback succeeded: %s:%s for task_type=%s",
                    next_model.vendor, next_model.model_id, task_type,
                )
                return {
                    "success": True,
                    "output": out.get("result", ""),
                    "error": "",
                    "vendor": next_model.vendor,
                    "model_id": out.get("model_id", ""),
                    "duration": out.get("duration", 0),
                    "raw": out,
                }
            # Record this fallback's failure too
            reg.record_failure(
                next_model.vendor, next_model.model_id,
                stderr=out.get("error", ""), rc=1, stdout_empty=False,
            )
            failed_vendor = next_model.vendor
            failed_model_id = next_model.model_id
        except Exception as exc:
            logger.debug("fallback dispatch failed: %s", exc)
            reg.record_failure(
                next_model.vendor, next_model.model_id,
                stderr=str(exc), rc=1, stdout_empty=False,
            )
            failed_vendor = next_model.vendor
            failed_model_id = next_model.model_id

    return None


def _dispatch_with_retry(
    vendor: str, prompt: str, artifact_ref: str,
    model: Optional[str] = None, mode: str = "read",
    max_retries: int = 1,
    task_type: str = "plan_author",
) -> dict:
    """Dispatch with one retry on failure."""
    last = _dispatch_vendor(vendor, prompt, artifact_ref, model, mode, task_type=task_type)
    if last["success"]:
        return last
    for _ in range(max_retries):
        logger.info("retrying vendor %s dispatch (last error: %s)", vendor, last["error"])
        time.sleep(2)
        last = _dispatch_vendor(vendor, prompt, artifact_ref, model, mode, task_type=task_type)
        if last["success"]:
            return last
    return last


# ── Trio / tiebreaker ────────────────────────────────────────────────────────


def _invoke_tiebreaker(
    vendor: str, plan_text: str, base_prompt: str,
    accepted_tradeoffs: List[str], criteria: str,
) -> Tuple[bool, str]:
    """Invoke a 3rd vendor for final sign-off. Returns (approved, reason)."""
    prompt = f"""You are a TIEBREAKER reviewer — a third independent architect
from a different model family. The primary author and reviewer have reached
agreement. Your job is to find anything they BOTH missed.

## ORIGINAL TASK
{base_prompt}

## APPROVAL CRITERIA
{criteria or "(none specified)"}

## ACCEPTED TRADEOFFS (do not flag)
{_format_tradeoffs(accepted_tradeoffs)}

## PLAN TO APPROVE
{plan_text}

## OUTPUT
Provide your verdict as JSON:
```json
{{
  "verdict": "APPROVED" | "REJECTED",
  "summary": "one-line explanation",
  "issues": []
}}
```
"""
    out = _dispatch_vendor(vendor, prompt, artifact_ref="tiebreaker", mode="read")
    if not out["success"]:
        return False, f"Tiebreaker dispatch failed: {out['error']}"
    parsed = _extract_json_block(out["output"])
    if parsed and "verdict" in parsed:
        verdict = str(parsed.get("verdict", "")).upper()
        if "APPROVED" in verdict:
            return True, parsed.get("summary", "Tiebreaker approved.")
        return False, parsed.get("summary", "Tiebreaker rejected.")
    # Heuristic fallback
    if re.search(r"\bAPPROVED\b", out["output"].upper()):
        return True, "Tiebreaker approved (heuristic)."
    return False, "Tiebreaker rejected (heuristic)."


# ── Main loop worker ─────────────────────────────────────────────────────────


def _run_loop_worker(plan_id: str, params: dict, plan_dir: Path) -> None:
    """Background worker that runs the multi-round plan review loop.

    This function runs in a daemon thread and updates state.json atomically
    after each phase. It is fire-and-forget — the caller polls status.

    fw-1786036802: When author_vendor == reviewer_vendor and
    allow_same_vendor is False (the default), the worker falls back to
    single-vendor plan mode instead of running self-review. It runs one
    author pass, sets status=SINGLE_VENDOR_PLAN, and finalizes.
    """
    state = _read_json(plan_dir / "state.json")

    # ── Single-vendor fallback (fw-1786036802) ─────────────────────────────
    # Same vendor + no explicit allow_same_vendor → skip self-review,
    # run one author pass, finalize as SINGLE_VENDOR_PLAN.
    if (state.get("author_vendor") == state.get("reviewer_vendor")
            and not state.get("allow_same_vendor", False)):
        state["status"] = "IN_PROGRESS"
        _update_state(plan_dir, state)
        _relay_event("SINGLE_VENDOR_FALLBACK", plan_id,
                     vendor=state["author_vendor"],
                     reason="same vendor default — skipping self-review")

        # Run one author pass to produce the plan
        context_text = _load_context_files(params.get("context_files", []))
        accepted_tradeoffs = params.get("accepted_tradeoffs", [])
        author_prompt = build_author_prompt(
            base_prompt=params["prompt"],
            context_text=context_text,
            current_plan="",
            feedback_delta=[],
            accepted_tradeoffs=accepted_tradeoffs,
            round_num=1,
        )
        author_out = _dispatch_with_retry(
            state["author_vendor"], author_prompt,
            artifact_ref=str(plan_dir / "plan_v1.md"),
            model=state.get("author_model"),
            mode="read",
        )
        current_plan = author_out.get("output", "")
        # Write plan_v1.md
        (plan_dir / "plan_v1.md").write_text(current_plan)
        state["current_round"] = 1
        state["latest_plan_path"] = str(plan_dir / "plan_v1.md")
        state["status"] = "SINGLE_VENDOR_PLAN"
        _finalize_loop(plan_dir, state, params, current_plan,
                       "Single-vendor fallback final plan (fw-1786036802).")
        return

    state["status"] = "IN_PROGRESS"
    _update_state(plan_dir, state)

    _relay_event("PLAN_LOOP_STARTED", plan_id,
                 author_vendor=state["author_vendor"],
                 reviewer_vendor=state["reviewer_vendor"],
                 max_rounds=state["max_rounds"])

    pinned_sha = state.get("pinned_sha") or "no-sha"
    context_text = _load_context_files(params.get("context_files", []))
    accepted_tradeoffs = params.get("accepted_tradeoffs", [])
    criteria = params.get("approval_criteria", "")
    sandbox_cmd = params.get("sandbox_test_cmd", "")
    tiebreaker = params.get("tiebreaker_vendor", "")

    current_plan = ""
    latest_feedback_delta: List[dict] = []
    accumulated_cost = 0.0
    severity_history: List[Dict[str, int]] = []

    max_rounds = state["max_rounds"]

    for r in range(1, max_rounds + 1):
        # Check for cancellation before each round
        state = _read_json(plan_dir / "state.json")
        if state.get("cancel_requested"):
            state["status"] = "CANCELLED"
            _finalize_loop(plan_dir, state, params, current_plan,
                           "Loop cancelled by user request.")
            return

        state["current_round"] = r
        _update_state(plan_dir, state)

        # ── 1. Author Step ───────────────────────────────────────────────
        author_prompt = build_author_prompt(
            base_prompt=params["prompt"],
            context_text=context_text,
            current_plan=current_plan,
            feedback_delta=latest_feedback_delta,
            accepted_tradeoffs=accepted_tradeoffs,
            round_num=r,
        )

        author_out = _dispatch_with_retry(
            vendor=state["author_vendor"],
            prompt=author_prompt,
            artifact_ref=pinned_sha,
            model=state.get("author_model"),
            mode="read",  # Planning is read-only
        )

        if not author_out["success"]:
            state["status"] = "ERROR"
            _finalize_loop(plan_dir, state, params, current_plan,
                           f"Round {r} Author failed: {author_out['error']}")
            return

        current_plan = author_out["output"]
        plan_path = plan_dir / f"plan_v{r}.md"
        _save_text(plan_path, current_plan)
        state["latest_plan_path"] = str(plan_path)
        accumulated_cost += _estimate_call_cost(
            state["author_vendor"], author_prompt, current_plan)
        _update_state(plan_dir, state)

        # Check for cancellation after author step (before reviewer)
        state = _read_json(plan_dir / "state.json")
        if state.get("cancel_requested"):
            state["status"] = "CANCELLED"
            _finalize_loop(plan_dir, state, params, current_plan,
                           "Loop cancelled by user request (after author step).")
            return

        # ── 2. Sandbox Evidence (optional) ───────────────────────────────
        sandbox_evidence = ""
        if sandbox_cmd:
            sandbox_evidence = _run_sandbox_evidence(sandbox_cmd, pinned_sha)

        # ── 3. Reviewer Step ─────────────────────────────────────────────
        reviewer_prompt = build_reviewer_prompt(
            base_prompt=params["prompt"],
            context_text=context_text,
            plan_text=current_plan,
            accepted_tradeoffs=accepted_tradeoffs,
            sandbox_evidence=sandbox_evidence,
            criteria=criteria,
            pinned_sha=pinned_sha,
            round_num=r,
        )

        reviewer_out = _dispatch_with_retry(
            vendor=state["reviewer_vendor"],
            prompt=reviewer_prompt,
            artifact_ref=pinned_sha,
            model=state.get("reviewer_model"),
            mode="read",
            task_type="plan_reviewer",
        )

        if not reviewer_out["success"]:
            state["status"] = "ERROR"
            _finalize_loop(plan_dir, state, params, current_plan,
                           f"Round {r} Reviewer failed: {reviewer_out['error']}")
            return

        review_raw = reviewer_out["output"]
        accumulated_cost += _estimate_call_cost(
            state["reviewer_vendor"], reviewer_prompt, review_raw)

        # ── 4. Verdict Classification ─────────────────────────────────────
        verdict, issues, inspected_files, summary = classify_review_verdict(review_raw)

        # A reviewer whose output does not parse has told us nothing about the
        # plan — that is a MECHANICAL failure, not a substantive rejection.
        # Previously it returned REJECTED with a MAJOR issue, indistinguishable
        # in the verdict from a real architectural objection, and it consumed a
        # round. Measured: 4 of 110 reviews in 30h; on one plan it landed at
        # round 3 of 3 and manufactured MAX_ROUNDS_EXHAUSTED on a plan whose
        # real objections had already fallen to zero. Retry the reviewer once
        # before letting a formatting glitch spend the adversarial budget.
        if _is_unparseable(issues):
            logger.info("plan %s round %d: reviewer output unparseable — "
                        "retrying reviewer once (not counted as a rejection)",
                        plan_id, r)
            retry_out = _dispatch_with_retry(
                vendor=state["reviewer_vendor"],
                prompt=reviewer_prompt,
                artifact_ref=pinned_sha,
                model=state.get("reviewer_model"),
                mode="read",
                task_type="plan_reviewer",
            )
            if retry_out.get("success"):
                review_raw = retry_out["output"]
                accumulated_cost += _estimate_call_cost(
                    state["reviewer_vendor"], reviewer_prompt, review_raw)
                verdict, issues, inspected_files, summary = classify_review_verdict(review_raw)
                if _is_unparseable(issues):
                    logger.warning("plan %s round %d: reviewer unparseable twice; "
                                   "treating as a real round", plan_id, r)

        severity_summary = _summarize_severities(issues)
        severity_history.append(severity_summary)

        review_entry = {
            "round": r,
            "verdict": verdict,
            "inspected_files": inspected_files,
            "severity_summary": severity_summary,
            "blocking_issues": issues,
            "summary": summary,
            "raw_review_path": str(plan_dir / f"review_v{r}.json"),
            "timestamp": _utc_now(),
        }

        review_path = plan_dir / f"review_v{r}.json"
        _save_text(review_path, json.dumps(review_entry, indent=2, default=str))
        state["latest_review_path"] = str(review_path)
        state["review_trail"].append(review_entry)
        state["estimated_cost_usd"] = round(accumulated_cost, 4)
        _update_state(plan_dir, state)

        _relay_event("ROUND_COMPLETED", plan_id,
                     round=r, verdict=verdict,
                     blocking_issues=len(issues))

        # ── 5. Termination Checks ────────────────────────────────────────

        if verdict == "APPROVED":
            # Trio mode: invoke tiebreaker if configured
            if tiebreaker:
                trio_ok, trio_reason = _invoke_tiebreaker(
                    tiebreaker, current_plan, params["prompt"],
                    accepted_tradeoffs, criteria)
                if not trio_ok:
                    # Tiebreaker rejected — inject feedback and continue
                    issues.append({
                        "id": "TRIO_1",
                        "severity": "MAJOR",
                        "issue": f"Tiebreaker rejected: {trio_reason}",
                        "remediation": "Resolve tiebreaker concerns.",
                    })
                    verdict = "REJECTED"
                else:
                    state["status"] = "APPROVED"
                    _finalize_loop(plan_dir, state, params, current_plan)
                    return

            if verdict == "APPROVED":
                state["status"] = "APPROVED"
                _finalize_loop(plan_dir, state, params, current_plan)
                return

        # Check for convergence with minor issues
        if is_converged_with_minor_issues(severity_history, r, max_rounds):
            state["status"] = "CONVERGED_WITH_MINOR_ISSUES"
            _finalize_loop(plan_dir, state, params, current_plan)
            return

        # Check for oscillation
        if _is_oscillating(severity_history):
            state["status"] = "OSCILLATING"
            _finalize_loop(plan_dir, state, params, current_plan,
                           "Oscillating issues detected — same severity flapping.")
            return

        # Check for non-convergence (stale) — saves vendor budget on plans that aren't improving
        if _is_stale(severity_history):
            state["status"] = "STALE_NON_CONVERGENT"
            _finalize_loop(plan_dir, state, params, current_plan,
                           f"Non-convergence detected — severity weight not decreasing for "
                           f"{_STALE_ROUNDS_REQUIRED}+ consecutive rounds with CRITICAL/MAJOR issues remaining.")
            return

        # Check budget
        if accumulated_cost >= state["max_cost_usd"]:
            state["status"] = "BUDGET_EXCEEDED"
            _finalize_loop(plan_dir, state, params, current_plan,
                           f"Budget exceeded: ${accumulated_cost:.4f} >= ${state['max_cost_usd']:.2f}")
            return

        # Prepare feedback for next round
        latest_feedback_delta = issues

    # Max rounds exhausted
    state["status"] = "MAX_ROUNDS_EXHAUSTED"
    _finalize_loop(plan_dir, state, params, current_plan,
                   f"Max rounds ({max_rounds}) exhausted without approval.")


# ── Public API ───────────────────────────────────────────────────────────────


def execute_plan_review_loop(params: dict, make_response) -> str:
    """Entry point for the plan_review_loop action.

    Validates params, creates state, spawns background worker (async mode)
    or runs synchronously (sync mode). Returns a JSON response string.
    """
    from ..runtime.vendor_dispatch import cross_vendor_enabled

    if not cross_vendor_enabled():
        return make_response(False, error=(
            "cross-vendor dispatch is disabled. Run `nucleus onboard` once "
            "to enable, or set NUCLEUS_CROSS_VENDOR=1."
        ))

    prompt = params.get("prompt", "")
    if not prompt:
        return make_response(False, error="plan_review_loop requires a non-empty 'prompt'")

    author_vendor = _resolve_author_vendor(params)
    reviewer_vendor = _resolve_reviewer_vendor(params)
    reviewer_model = params.get("reviewer_model", _DEFAULT_REVIEWER_MODEL)
    allow_same, allow_same_explicit = _resolve_allow_same_vendor(params)

    # fw-1786036802: self-review is no longer the default. An explicit
    # allow_same_vendor=False with matching vendors is a validation error.
    # A missing key (default) with matching vendors triggers single-vendor
    # fallback in the worker. An explicit True allows self-review.
    if author_vendor == reviewer_vendor and allow_same_explicit and not allow_same:
        return make_response(False, error=(
            f"author_vendor and reviewer_vendor are both '{author_vendor}' "
            "and allow_same_vendor=False. Cross-vendor review requires distinct "
            "model families for diverse perspective. Set allow_same_vendor=true "
            "to override, or use different vendors."
        ))

    # Validate vendors exist
    from ..runtime.vendor_dispatch import VENDOR_SPECS
    for v in [author_vendor, reviewer_vendor]:
        if v not in VENDOR_SPECS:
            return make_response(False, error=(
                f"unknown vendor {v!r}; expected one of {sorted(VENDOR_SPECS)}"
            ))

    tiebreaker = params.get("tiebreaker_vendor", "")
    if tiebreaker and tiebreaker not in VENDOR_SPECS:
        return make_response(False, error=(
            f"unknown tiebreaker_vendor {tiebreaker!r}; expected one of {sorted(VENDOR_SPECS)}"
        ))

    # Pin immutable review target
    pinned_sha = params.get("artifact_ref") or _get_git_head_sha() or "no-sha"

    # Create plan directory + state
    plan_id = _generate_plan_id()
    brain = _get_brain_path()
    plan_dir = brain / "plans" / plan_id
    plan_dir.mkdir(parents=True, exist_ok=True)

    state = _make_initial_state(plan_id, params, pinned_sha)
    _atomic_write_json(plan_dir / "state.json", state)
    _atomic_write_json(plan_dir / "metadata.json", {
        "params": params, "created_at": _utc_now(), "plan_id": plan_id,
    })

    mode = str(params.get("mode", "async")).lower()

    if mode == "sync":
        # Run synchronously (blocks until completion — caller beware of timeouts)
        _run_loop_worker(plan_id, params, plan_dir)
        final_state = _read_json(plan_dir / "state.json")
        return make_response(True, data=final_state)
    else:
        # Async: spawn background thread and return immediately
        thread = threading.Thread(
            target=_run_loop_worker,
            args=(plan_id, params, plan_dir),
            daemon=True,
            name=f"plan_review_loop_{plan_id}",
        )
        thread.start()
        return make_response(True, data={
            "plan_id": plan_id,
            "status": "QUEUED",
            "message": (
                "Plan review loop launched asynchronously. "
                "Poll status using action='plan_review_loop_status' "
                "with params={'plan_id': '" + plan_id + "'}."
            ),
            "plan_dir": str(plan_dir),
            "pinned_sha": pinned_sha,
        })


def query_plan_review_loop_status(plan_id: str, make_response) -> str:
    """Read state.json for a plan loop and return it."""
    if not plan_id:
        return make_response(False, error="plan_review_loop_status requires 'plan_id'")
    if not _validate_plan_id(plan_id):
        return make_response(False, error=(
            f"Invalid plan_id format {plan_id!r}. "
            "Expected plan_YYYYMMDD_HHMMSS_<6hex>."
        ))

    brain = _get_brain_path()
    state_path = brain / "plans" / plan_id / "state.json"
    if not state_path.exists():
        return make_response(False, error=(
            f"No plan loop found with plan_id={plan_id!r}. "
            f"Expected state at {state_path}"
        ))

    state = _read_json(state_path)
    return make_response(True, data=state)


def cancel_plan_review_loop(plan_id: str, make_response) -> str:
    """Set cancel_requested=true in state.json. Worker will abort before next round."""
    if not plan_id:
        return make_response(False, error="plan_review_loop_cancel requires 'plan_id'")
    if not _validate_plan_id(plan_id):
        return make_response(False, error=(
            f"Invalid plan_id format {plan_id!r}. "
            "Expected plan_YYYYMMDD_HHMMSS_<6hex>."
        ))

    brain = _get_brain_path()
    state_path = brain / "plans" / plan_id / "state.json"
    if not state_path.exists():
        return make_response(False, error=(
            f"No plan loop found with plan_id={plan_id!r}."
        ))

    state = _read_json(state_path)
    if state.get("status") in ("APPROVED", "MAX_ROUNDS_EXHAUSTED",
                                "BUDGET_EXCEEDED", "CANCELLED", "ERROR",
                                "OSCILLATING", "CONVERGED_WITH_MINOR_ISSUES",
                                "SINGLE_VENDOR_PLAN", "STALE_NON_CONVERGENT"):
        return make_response(True, data={
            "plan_id": plan_id,
            "status": state["status"],
            "message": f"Loop already in terminal state: {state['status']}. No cancellation needed.",
        })

    state["cancel_requested"] = True
    _update_state(state_path.parent, state)

    return make_response(True, data={
        "plan_id": plan_id,
        "status": "CANCEL_REQUESTED",
        "message": "Cancellation request registered. Worker will abort before next execution phase.",
    })
