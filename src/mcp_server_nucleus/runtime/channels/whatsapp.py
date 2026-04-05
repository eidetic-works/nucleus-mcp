"""WhatsApp Cloud API notification channel.

Uses Meta's WhatsApp Business Cloud API to send template-based
messages. Requires a Meta Business account with WhatsApp integration.
"""

import json
import logging
import os
import urllib.request

from .base import NotificationChannel

logger = logging.getLogger("nucleus.channels.whatsapp")

# WhatsApp Cloud API base URL
GRAPH_API_BASE = "https://graph.facebook.com/v21.0"


class WhatsAppChannel(NotificationChannel):
    """Send notifications via WhatsApp Cloud API.

    Requires:
        WHATSAPP_TOKEN    — Permanent access token from Meta Business
        WHATSAPP_PHONE_ID — Phone number ID from WhatsApp Business settings
        WHATSAPP_TO       — Recipient phone number (E.164 format, e.g. +1234567890)
    """

    def __init__(self, token: str = None, phone_id: str = None, to_number: str = None):
        self._token = token
        self._phone_id = phone_id
        self._to_number = to_number

    @property
    def name(self) -> str:
        return "whatsapp"

    @property
    def display_name(self) -> str:
        return "WhatsApp Cloud API"

    def _get_token(self) -> str:
        if self._token:
            return self._token
        try:
            from ..secrets import get_secret
            t = get_secret("WHATSAPP_TOKEN")
            if t:
                return t
        except ImportError:
            pass
        return os.environ.get("WHATSAPP_TOKEN", "")

    def _get_phone_id(self) -> str:
        if self._phone_id:
            return self._phone_id
        return os.environ.get("WHATSAPP_PHONE_ID", "")

    def _get_to_number(self) -> str:
        if self._to_number:
            return self._to_number
        return os.environ.get("WHATSAPP_TO", "")

    def is_configured(self) -> bool:
        return bool(self._get_token() and self._get_phone_id() and self._get_to_number())

    def send(self, title: str, message: str, level: str = "info") -> bool:
        token = self._get_token()
        phone_id = self._get_phone_id()
        to_number = self._get_to_number()
        if not (token and phone_id and to_number):
            return False

        emoji = {"critical": "🚨", "error": "❌", "warning": "⚠️", "info": "ℹ️"}.get(level, "📢")
        text = f"{emoji} *{title}*\n\n{message}"

        # WhatsApp Cloud API text message format
        payload = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "text",
            "text": {
                "preview_url": False,
                "body": text[:4096],
            },
        }

        try:
            url = f"{GRAPH_API_BASE}/{phone_id}/messages"
            data = json.dumps(payload).encode()
            req = urllib.request.Request(url, data=data, method="POST")
            req.add_header("Content-Type", "application/json")
            req.add_header("Authorization", f"Bearer {token}")
            with urllib.request.urlopen(req, timeout=15) as resp:
                return resp.status == 200
        except Exception as e:
            logger.debug(f"WhatsApp send failed: {e}")
            return False
