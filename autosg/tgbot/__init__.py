"""
Implements interactions with Telegram bot server.
"""
from .tgbot import init_tg, on_startup, on_shutdown
from .handlers.notifications import notify_on_enter


__all__ = ['init_tg', 'on_startup', 'on_shutdown', 'notify_on_enter']
