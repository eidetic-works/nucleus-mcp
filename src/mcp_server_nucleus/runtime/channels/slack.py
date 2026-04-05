"""Slack incoming webhook notification channel."""

import json
import logging
import os
import urllib.request
from typing import Any, Dict

from .base import NotificationChannel

logger = logging.getLogger("nucleus.channels.slack")


class SlackChannel(NotificationChannel):
    """Send notifications via Slack incoming webhook.

    Requires:
        SLACK_WEBHOOK_URL — Incoming webhook URL from Slack app settings
        (e.g. https://hooks.slack.com/services/T.../B.../xxx)
    """

    def __init__(self, webhook_url: str = None):
        self._webhook_url = webhook_url

    @property
    def name(self) -> str:
        return "slack"

    @property
    def display_name(self) -> str:
        return "Slack Webhook"

    def _get_webhook_url(self) -> str:
        if self._webhook_url:
            return self._webhook_url
        try:
            from ..secrets import get_secret
            url = get_secret("SLACK_WEBHOOK_URL")
            if url:
                return url
        except ImportError:
            pass
        return os.environ.get("SLACK_WEBHOOK_URL", "")

    def is_configured(self) -> bool:
        return bool(self._get_webhook_url())

    def send(self, title: str, message: str, level: str = "info") -> bool:
        url = self._get_webhook_url()
        if not url:
            return False

        emoji = {"critical": ":rotating_light:", "error": ":x:", "warning": ":warning:", "info": ":information_source:"}.get(level, ":bell:")
        color = {"critical": "#FF0000", "error": "#CC0000", "warning": "#FFA500", "info": "#36A2EB"}.get(level, "#808080")

        payload = {
            "attachments": [
                {
                    "color": color,
                    "blocks": [
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"{emoji} *{title}*\n{message}",
                            },
                        },
                        {
                            "type": "context",
                            "elements": [
                                {
                                    "type": "mrkdwn",
                                    "text": f"Nucleus Agent OS | {level.upper()}",
                                }
                            ],
                        },
                    ],
                }
            ]
        }

        try:
            data = json.dumps(payload).encode()
            req = urllib.request.Request(url, data=data, method="POST")
            req.add_header("Content-Type", "application/json")
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status == 200
        except Exception as e:
            logger.debug(f"Slack send failed: {e}")
            return False

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        url = self._get_webhook_url()
        if url:
            # Mask the webhook URL for display (show only last 8 chars)
            d["webhook_url"] = f"...{url[-8:]}" if len(url) > 8 else "***"
        return d
