'''Implements interaction with Telegram bot server'''
from __future__ import annotations

import os
from typing import TYPE_CHECKING

from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.files import JSONStorage
from aiogram.types import BotCommand
from dotenv import load_dotenv

from autosg import config

from . import handlers

if TYPE_CHECKING:
    from typing import Tuple


def init_tg() -> Tuple[JSONStorage, Dispatcher]:
    '''Initialize Telegram bot objects'''
    # import token from .env file
    load_dotenv()
    token = os.getenv('TELEGRAM_TOKEN')
    if not token:
        raise EnvironmentError('TELEGRAM_TOKEN is not defined!')

    config.bot = Bot(token=token)
    storage = JSONStorage('users.json')
    dispatcher = Dispatcher(config.bot, storage=storage)

    return storage, dispatcher


async def on_startup(dispatcher: Dispatcher):
    '''Actions required on Telegram bot startup'''
    await set_commands(dispatcher.bot)
    handlers.register_commands(dispatcher)
    handlers.register_callbacks(dispatcher)


async def set_commands(bot: Bot):
    '''Set available bot commands on Telegram server'''
    commands = [
        BotCommand(command="/start", description="Start the bot"),
        BotCommand(command="/status", description="Check current status of the bot"),
        # BotCommand(command="/register", description="Register SG account in the bot"),
        BotCommand(command="/configure", description="Configure ASG bot parameters"),
        BotCommand(command="/unregister", description="Remove SG account from the bot")]

    await bot.set_my_commands(commands)


async def on_shutdown(dispatcher: Dispatcher):
    '''Actions required on Telegram bot shutdown'''
    await dispatcher.storage.close()
    await dispatcher.storage.wait_closed()
