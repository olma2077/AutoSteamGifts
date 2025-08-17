"""Implements interaction with Telegram bot server"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from aiogram import Bot, Dispatcher
from dotenv import load_dotenv

from autosg import config

from .file_storage import JSONStorage
from . import handlers

if TYPE_CHECKING:
    from typing import Tuple


def init_tg() -> Tuple[JSONStorage, Dispatcher]:
    """Initialize Telegram bot objects"""
    # import token from .env file
    load_dotenv()
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        raise EnvironmentError("TELEGRAM_TOKEN is not defined!")

    config.bot = Bot(token=token)
    storage = JSONStorage("users.json")
    dispatcher = Dispatcher(storage=storage)

    return storage, dispatcher


async def on_startup(dispatcher: Dispatcher) -> None:
    """Actions required on Telegram bot startup"""
    dispatcher.include_routers(handlers.message_router, handlers.callback_router)


async def on_shutdown(dispatcher: Dispatcher) -> None:
    """Actions required on Telegram bot shutdown"""
    await dispatcher.storage.close()
