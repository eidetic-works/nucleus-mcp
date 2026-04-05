"""
Channel abstraction and routing for Nucleus notifications.

NotificationChannel is the ABC. ChannelRouter fans out messages
to all configured channels based on severity routing rules.
"""

import json
import logging
import threading
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("nucleus.channels")

# Default routing: which channels get which severity levels
DEFAULT_ROUTING = {
    "critical": "__all__",
    "error": "__all__",
    "warning": "__all__",
    "info": "__all__",
}


class NotificationChannel(ABC):
    """Abstract base for notification channels (Telegram, Slack, etc.)."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Channel identifier (e.g. 'telegram', 'slack')."""
        ...

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable name (e.g. 'Telegram Bot')."""
        ...

    @abstractmethod
    def send(self, title: str, message: str, level: str = "info") -> bool:
        """Send a notification. Returns True on success."""
        ...

    @abstractmethod
    def is_configured(self) -> bool:
        """Check whether credentials/config are present."""
        ...

    def test(self) -> bool:
        """Send a test message to verify the channel works."""
        return self.send(
            "Nucleus Test",
            "This is a test notification from Nucleus Agent OS.",
            level="info",
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize channel config (no secrets)."""
        return {
            "type": self.name,
            "display_name": self.display_name,
            "configured": self.is_configured(),
        }


class ChannelRouter:
    """Routes notifications to configured channels based on severity.

    Usage:
        router = get_channel_router(brain_path)
        router.notify("Deploy failed", "Error in production", level="critical")
    """

    def __init__(self, brain_path: Optional[Path] = None):
        self.brain_path = brain_path
        self._channels: Dict[str, NotificationChannel] = {}
        self._routing: Dict[str, Any] = dict(DEFAULT_ROUTING)
        self._lock = threading.Lock()

    def register(self, channel: NotificationChannel) -> None:
        """Register a channel. Replaces existing channel with same name."""
        with self._lock:
            self._channels[channel.name] = channel

    def unregister(self, name: str) -> bool:
        """Remove a channel by name."""
        with self._lock:
            return self._channels.pop(name, None) is not None

    def get_channel(self, name: str) -> Optional[NotificationChannel]:
        return self._channels.get(name)

    def list_channels(self) -> List[Dict[str, Any]]:
        """List all registered channels with their status."""
        return [ch.to_dict() for ch in self._channels.values()]

    def notify(self, title: str, message: str, level: str = "info") -> Dict[str, bool]:
        """Send notification to all channels matching the severity routing.

        Returns dict of {channel_name: success_bool}.
        """
        results = {}
        target_channels = self._resolve_targets(level)

        for ch_name in target_channels:
            ch = self._channels.get(ch_name)
            if ch and ch.is_configured():
                try:
                    results[ch_name] = ch.send(title, message, level)
                except Exception as e:
                    logger.error(f"Channel {ch_name} failed: {e}")
                    results[ch_name] = False

        return results

    def _resolve_targets(self, level: str) -> List[str]:
        """Determine which channels should receive a message at this level."""
        rule = self._routing.get(level, self._routing.get("info", "__all__"))
        if rule == "__all__":
            return list(self._channels.keys())
        if isinstance(rule, list):
            return rule
        return list(self._channels.keys())

    def set_routing(self, level: str, channels: List[str]) -> None:
        """Configure which channels receive messages at a given severity."""
        self._routing[level] = channels

    # ── Persistence ──────────────────────────────────────────────

    def load_from_brain(self, brain_path: Optional[Path] = None) -> None:
        """Load channel config from .brain/channels/config.json."""
        bp = brain_path or self.brain_path
        if not bp:
            return
        config_file = Path(bp) / "channels" / "config.json"
        if not config_file.exists():
            return
        try:
            data = json.loads(config_file.read_text(encoding="utf-8"))
            if "routing" in data and isinstance(data["routing"], dict):
                self._routing.update(data["routing"])
            for ch_conf in data.get("channels", []):
                self._load_channel_from_config(ch_conf)
        except Exception as e:
            logger.error(f"Failed to load channel config: {e}")

    def save_to_brain(self, brain_path: Optional[Path] = None) -> None:
        """Persist channel config to .brain/channels/config.json."""
        bp = brain_path or self.brain_path
        if not bp:
            return
        config_dir = Path(bp) / "channels"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / "config.json"

        data = {
            "channels": [],
            "routing": self._routing,
        }
        for ch in self._channels.values():
            data["channels"].append(ch.to_dict())

        config_file.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def _load_channel_from_config(self, conf: Dict[str, Any]) -> None:
        """Instantiate and register a channel from saved config."""
        ch_type = conf.get("type")
        if not ch_type:
            return
        # Lazy imports to avoid circular deps
        if ch_type == "telegram":
            from .telegram import TelegramChannel
            self.register(TelegramChannel())
        elif ch_type == "slack":
            from .slack import SlackChannel
            self.register(SlackChannel(webhook_url=conf.get("webhook_url")))
        elif ch_type == "discord":
            from .discord import DiscordChannel
            self.register(DiscordChannel(webhook_url=conf.get("webhook_url")))
        elif ch_type == "whatsapp":
            from .whatsapp import WhatsAppChannel
            self.register(WhatsAppChannel())

    # ── Auto-discovery ───────────────────────────────────────────

    def auto_discover(self) -> int:
        """Detect channels from environment variables. Returns count found."""
        count = 0

        # Telegram
        from .telegram import TelegramChannel
        tg = TelegramChannel()
        if tg.is_configured():
            self.register(tg)
            count += 1

        # Slack
        from .slack import SlackChannel
        sl = SlackChannel()
        if sl.is_configured():
            self.register(sl)
            count += 1

        # Discord
        from .discord import DiscordChannel
        dc = DiscordChannel()
        if dc.is_configured():
            self.register(dc)
            count += 1

        # WhatsApp
        from .whatsapp import WhatsAppChannel
        wa = WhatsAppChannel()
        if wa.is_configured():
            self.register(wa)
            count += 1

        return count


# ── Singleton ────────────────────────────────────────────────────

_router_instance: Optional[ChannelRouter] = None
_router_lock = threading.Lock()


def get_channel_router(brain_path: Optional[Path] = None) -> ChannelRouter:
    """Get or create the singleton ChannelRouter.

    On first call, auto-discovers channels from env vars and loads
    config from .brain/channels/config.json if brain_path is provided.
    """
    global _router_instance
    with _router_lock:
        if _router_instance is None:
            _router_instance = ChannelRouter(brain_path)
            _router_instance.auto_discover()
            if brain_path:
                _router_instance.load_from_brain(brain_path)
        return _router_instance
