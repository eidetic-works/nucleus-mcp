"""
Nucleus Notification Channels — multi-channel messaging integrations.

Supports Telegram, Slack, Discord, and WhatsApp via a unified
ChannelRouter that replaces scattered notification code.
"""

from .base import NotificationChannel, ChannelRouter, get_channel_router

__all__ = ["NotificationChannel", "ChannelRouter", "get_channel_router"]
