"""Telegram Bot API notification channel."""

import json
import logging
import os
import urllib.error
import urllib.request

from .base import NotificationChannel

logger = logging.getLogger("nucleus.channels.telegram")


class TelegramChannel(NotificationChannel):
    """Send notifications via Telegram Bot API.

    Requires:
        TELEGRAM_BOT_TOKEN — Bot token from @BotFather
        TELEGRAM_CHAT_ID   — Target chat/group/channel ID
    """

    def __init__(self, token: str = None, chat_id: str = None):
        self._token = token
        self._chat_id = chat_id

    @property
    def name(self) -> str:
        return "telegram"

    @property
    def display_name(self) -> str:
        return "Telegram Bot"

    def _get_token(self) -> str:
        if self._token:
            return self._token
        try:
            from ..secrets import get_telegram_token
            return get_telegram_token()
        except ImportError:
            return os.environ.get("TELEGRAM_BOT_TOKEN", "")

    def _get_chat_id(self) -> str:
        if self._chat_id:
            return self._chat_id
        try:
            from ..secrets import get_telegram_chat_id
            return get_telegram_chat_id()
        except ImportError:
            return os.environ.get("TELEGRAM_CHAT_ID", "")

    def is_configured(self) -> bool:
        return bool(self._get_token() and self._get_chat_id())

    def send(self, title: str, message: str, level: str = "info") -> bool:
        token = self._get_token()
        chat_id = self._get_chat_id()
        if not token or not chat_id:
            return False

        emoji = {"critical": "🚨", "error": "❌", "warning": "⚠️", "info": "ℹ️"}.get(level, "📢")
        text = f"{emoji} *{title}*\n{message}"

        try:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            payload = json.dumps({
                "chat_id": chat_id,
                "text": text[:4096],
                "parse_mode": "Markdown",
            }).encode()
            req = urllib.request.Request(url, data=payload, method="POST")
            req.add_header("Content-Type", "application/json")
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status == 200
        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = e.read(200).decode("utf-8", errors="replace")
            except Exception:
                pass
            logger.warning(
                "Telegram send failed: HTTP %s for title=%r body=%r",
                e.code, title[:60], body,
            )
            return False
        except Exception as e:
            logger.debug(f"Telegram send failed: {e}")
            return False
