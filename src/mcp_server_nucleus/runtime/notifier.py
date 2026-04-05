"""
Nucleus Notifier — unified notification channel.

Routes notifications through the ChannelRouter to all configured
channels (Telegram, Slack, Discord, WhatsApp, macOS).

Backward-compatible: Notifier.send() API is unchanged.
"""

import logging
import subprocess

logger = logging.getLogger("NucleusNotifier")


class Notifier:
    """Unified notification dispatcher.

    Delegates to ChannelRouter for multi-channel delivery while
    maintaining the original send(title, message, level) API.
    """

    def __init__(self, brain_path=None):
        self.brain_path = brain_path
        self._router = None

    def _get_router(self):
        if self._router is None:
            from .channels import get_channel_router
            self._router = get_channel_router(self.brain_path)
        return self._router

    def send(self, title: str, message: str, level: str = "info"):
        """Send notification to all available channels."""
        self.log(title, message, level)
        self.macos(title, message)
        if level in ("warning", "error", "critical"):
            self._get_router().notify(title, message, level)

    def macos(self, title: str, message: str) -> bool:
        """Send macOS notification via osascript."""
        try:
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
