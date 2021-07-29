from __future__ import annotations
import os
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.files import JSONStorage

from . import handlers

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from typing import Tuple


def init_tg() -> Tuple[Bot, JSONStorage, Dispatcher]:
    '''Initialize Telegram bot objects'''
    # import token from .env file
    load_dotenv()
    TOKEN = os.getenv('TELEGRAM_TOKEN')

    bot = Bot(token=TOKEN)
    storage = JSONStorage('users.json')
    dispatcher = Dispatcher(bot, storage=storage)

    return bot, storage, dispatcher


async def on_startup(dispatcher: Dispatcher):
    '''Actions required on Telegram bot startup'''
    await set_commands(dispatcher.bot)
    handlers.register_commands(dispatcher)
    handlers.register_callbacks(dispatcher)


async def set_commands(bot: Bot):
    '''Set available bot commands on Telegram server'''
    commands = [
        types.BotCommand(command="/start", description="Start the bot"),
        types.BotCommand(command="/register", description="Register SG account in the bot"),
        types.BotCommand(command="/configure", description="Configure ASG bot parameters"),
        types.BotCommand(command="/unregister", description="Remove SG account from the bot")]

    await bot.set_my_commands(commands)


async def on_shutdown(dispatcher: Dispatcher):
    '''Actions required on Telegram bot shutdown'''
    await dispatcher.storage.close()
    await dispatcher.storage.wait_closed()
