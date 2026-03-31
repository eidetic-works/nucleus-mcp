"""
Nucleus Notifier — unified notification channel.

Routes to Telegram + macOS notifications. Replaces scattered osascript and
Telegram calls throughout the codebase.
"""

import logging
import os
import subprocess
from typing import Optional

logger = logging.getLogger("NucleusNotifier")


class Notifier:
    """Unified notification dispatcher."""

    def __init__(self, brain_path=None):
        self.brain_path = brain_path
        self._telegram_token = os.environ.get("TELEGRAM_BOT_TOKEN")
        self._telegram_chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    def send(self, title: str, message: str, level: str = "info"):
        """Send notification to all available channels."""
        self.log(title, message, level)
        self.macos(title, message)
        if level in ("warning", "error", "critical"):
            self.telegram(f"[{level.upper()}] {title}\n{message}")

    def telegram(self, message: str) -> bool:
        """Send via Telegram bot. Returns True on success."""
        if not self._telegram_token or not self._telegram_chat_id:
            return False
        try:
            import urllib.request
            import urllib.parse
            url = (
                f"https://api.telegram.org/bot{self._telegram_token}"
                f"/sendMessage"
            )
            data = urllib.parse.urlencode({
                "chat_id": self._telegram_chat_id,
                "text": message[:4096],
                "parse_mode": "Markdown",
            }).encode()
            req = urllib.request.Request(url, data=data, method="POST")
            urllib.request.urlopen(req, timeout=10)
            return True
        except Exception as e:
            logger.debug(f"Telegram send failed: {e}")
            return False

    def macos(self, title: str, message: str) -> bool:
        """Send macOS notification via osascript."""
        try:
            # Escape quotes to prevent osascript injection
            safe_title = title.replace('"', '\\"').replace("'", "\\'")
            safe_msg = message.replace('"', '\\"').replace("'", "\\'")
            subprocess.run(
                ["osascript", "-e",
                 f'display notification "{safe_msg}" with title "Nucleus" subtitle "{safe_title}"'],
                timeout=5, capture_output=True,
            )
            return True
        except Exception:
            return False

    def log(self, title: str, message: str, level: str = "info"):
        """Always log."""
        log_fn = getattr(logger, level, logger.info)
        log_fn(f"[{title}] {message}")
