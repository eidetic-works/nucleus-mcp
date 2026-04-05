"""Discord webhook notification channel."""

import json
import logging
import os
import urllib.request
from typing import Any, Dict

from .base import NotificationChannel

logger = logging.getLogger("nucleus.channels.discord")


class DiscordChannel(NotificationChannel):
    """Send notifications via Discord webhook.

    Requires:
        DISCORD_WEBHOOK_URL — Webhook URL from Discord channel settings
        (e.g. https://discord.com/api/webhooks/1234567890/abcdef...)
    """

    def __init__(self, webhook_url: str = None):
        self._webhook_url = webhook_url

    @property
    def name(self) -> str:
        return "discord"

    @property
    def display_name(self) -> str:
        return "Discord Webhook"

    def _get_webhook_url(self) -> str:
        if self._webhook_url:
            return self._webhook_url
        try:
            from ..secrets import get_secret
            url = get_secret("DISCORD_WEBHOOK_URL")
            if url:
                return url
        except ImportError:
            pass
        return os.environ.get("DISCORD_WEBHOOK_URL", "")

    def is_configured(self) -> bool:
        return bool(self._get_webhook_url())

    def send(self, title: str, message: str, level: str = "info") -> bool:
        url = self._get_webhook_url()
        if not url:
            return False

        color = {
            "critical": 0xFF0000,
            "error": 0xCC0000,
            "warning": 0xFFA500,
            "info": 0x36A2EB,
        }.get(level, 0x808080)

        payload = {
            "embeds": [
                {
                    "title": title,
                    "description": message[:4096],
                    "color": color,
                    "footer": {
                        "text": f"Nucleus Agent OS | {level.upper()}",
                    },
                }
            ]
        }

        try:
            data = json.dumps(payload).encode()
            req = urllib.request.Request(url, data=data, method="POST")
            req.add_header("Content-Type", "application/json")
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status in (200, 204)
        except Exception as e:
            logger.debug(f"Discord send failed: {e}")
            return False

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        url = self._get_webhook_url()
        if url:
            d["webhook_url"] = f"...{url[-8:]}" if len(url) > 8 else "***"
        return d
