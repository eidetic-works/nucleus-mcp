"""Feedback channel — allows other agents to report bugs/enhancements.

Other agents using the autonomous lane can submit feedback (bugs, enhancement
requests, observations) without modifying the nucleus codebase. Feedback is
stored in a shared location that the nucleus team reviews.

Feedback is NOT relayed to the nucleus team's brain — it's stored in a
designated feedback directory that the nucleus team polls. This maintains
strict isolation while enabling communication.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


class FeedbackStore:
    """Stores feedback from other agents using the autonomous lane.

    Feedback is stored in a JSON file at a configurable path. The nucleus
    team reviews this file periodically.
    """

    def __init__(self, feedback_path: Path):
        self.feedback_path = Path(feedback_path)
        self.feedback_path.parent.mkdir(parents=True, exist_ok=True)

    def submit(
        self,
        feedback_type: str,
        subject: str,
        body: str,
        reporter: str = "anonymous",
        repo: str = "",
        lane_config: Optional[dict] = None,
    ) -> Dict[str, Any]:
        """Submit a feedback item.

        Args:
            feedback_type: "bug", "enhancement", "observation", or "question".
            subject: Short summary.
            body: Detailed description.
            reporter: Agent/project reporting the feedback.
            repo: The repo where the feedback was observed.
            lane_config: Optional lane config snapshot for context.

        Returns:
            The stored feedback item with ID and timestamp.
        """
        item = {
            "id": f"feedback_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}",
            "type": feedback_type,
            "subject": subject,
            "body": body,
            "reporter": reporter,
            "repo": repo,
            "lane_config": lane_config,
            "status": "open",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        items = self._load_all()
        items.append(item)
        self._save_all(items)

        return item

    def list_all(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all feedback items, optionally filtered by status."""
        items = self._load_all()
        if status:
            items = [i for i in items if i.get("status") == status]
        return items

    def update_status(self, feedback_id: str, status: str, resolution: str = "") -> Optional[Dict[str, Any]]:
        """Update the status of a feedback item."""
        items = self._load_all()
        for item in items:
            if item["id"] == feedback_id:
                item["status"] = status
                if resolution:
                    item["resolution"] = resolution
                item["updated_at"] = datetime.now(timezone.utc).isoformat()
                self._save_all(items)
                return item
        return None

    def _load_all(self) -> List[Dict[str, Any]]:
        if self.feedback_path.exists():
            return json.loads(self.feedback_path.read_text())
        return []

    def _save_all(self, items: List[Dict[str, Any]]) -> None:
        from .atomic_write import atomic_write
        atomic_write(self.feedback_path, json.dumps(items, indent=2, default=str))


def submit_feedback(
    feedback_type: str,
    subject: str,
    body: str,
    reporter: str = "anonymous",
    repo: str = "",
    feedback_path: Optional[Path] = None,
    github_repo: str = "",
) -> Dict[str, Any]:
    """Convenience function to submit feedback.

    By default, feedback is stored in the project's own brain directory
    under .brain/feedback/lane_feedback.json AND a GitHub issue is created
    so the nucleus team can see it cross-machine.

    Issue routing:
        - Set NUCLEUS_LANE_FEEDBACK_REPO to override (e.g. for internal users
          who have access to the private repo).
        - Default: public repo (eidetic-works/nucleus-mcp) — works for anyone.
        - Internal users: set NUCLEUS_LANE_FEEDBACK_REPO=eidetic-works/mcp-server-nucleus
          to route to the private repo.

    Set NUCLEUS_LANE_FEEDBACK_GITHUB=0 to disable GitHub issue creation
    (e.g. for air-gapped environments or testing).
    """
    if feedback_path is None:
        brain = Path(os.environ.get("NUCLEUS_BRAIN_PATH", ".brain"))
        feedback_path = brain / "feedback" / "lane_feedback.json"

    store = FeedbackStore(feedback_path)
    item = store.submit(
        feedback_type=feedback_type,
        subject=subject,
        body=body,
        reporter=reporter,
        repo=repo,
    )

    # Also create a GitHub issue for cross-machine visibility
    github_enabled = os.environ.get("NUCLEUS_LANE_FEEDBACK_GITHUB", "1") != "0"
    if github_enabled:
        # Resolve target repo: env override > parameter > default public
        target_repo = (
            os.environ.get("NUCLEUS_LANE_FEEDBACK_REPO", "")
            or github_repo
            or "eidetic-works/nucleus-mcp"  # public repo — works for anyone
        )
        try:
            item["github_issue"] = _create_github_issue(
                target_repo, feedback_type, subject, body, reporter, repo, item["id"]
            )
            store.update_status(item["id"], "open")  # refresh stored item
        except Exception as exc:
            item["github_issue_error"] = str(exc)

    return item


def _create_github_issue(
    repo: str,
    feedback_type: str,
    subject: str,
    body: str,
    reporter: str,
    source_repo: str,
    feedback_id: str,
) -> Dict[str, Any]:
    """Create a GitHub issue for the feedback. Requires gh CLI installed and auth'd."""
    import subprocess

    label_map = {
        "bug": "lane-feedback,bug",
        "enhancement": "lane-feedback,enhancement",
        "observation": "lane-feedback",
        "question": "lane-feedback,question",
    }
    labels = label_map.get(feedback_type, "lane-feedback")

    title = f"[lane-feedback] [{feedback_type}] {subject}"
    issue_body = (
        f"## Lane Feedback\n\n"
        f"**Type:** {feedback_type}\n"
        f"**Reporter:** {reporter}\n"
        f"**Source repo:** {source_repo}\n"
        f"**Feedback ID:** {feedback_id}\n\n"
        f"---\n\n"
        f"{body}\n\n"
        f"---\n"
        f"_Auto-generated by `nucleus lane feedback`_"
    )

    result = subprocess.run(
        [
            "gh", "issue", "create",
            "--repo", repo,
            "--title", title,
            "--body", issue_body,
            "--label", labels,
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )

    if result.returncode != 0:
        raise RuntimeError(f"gh issue create failed: {result.stderr.strip()}")

    issue_url = result.stdout.strip()
    return {"url": issue_url, "repo": repo}
