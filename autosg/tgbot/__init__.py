"""
Implements interactions with Telegram bot server.
"""

from .handlers.notifications import notify_on_enter
from .tgbot import init_tg, on_shutdown, on_startup

__all__ = ["init_tg", "on_startup", "on_shutdown", "notify_on_enter"]
