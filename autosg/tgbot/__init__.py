"""
Implements interactions with Telegram bot server.
"""
from .tgbot import init_tg, on_startup, on_shutdown


__all__ = ['init_tg', 'on_startup', 'on_shutdown']
