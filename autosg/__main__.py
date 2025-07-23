'''Automates entering SteamGifts giveaways for a user.

User interacts with application using Telegram bot interface.
It is possible to select which SteamGifts sections to check for
available giveaways.
'''
import asyncio
from asyncio import TaskGroup
import logging
import os

from dotenv import load_dotenv

from autosg import config, sgbot, tgbot


async def main() -> None:
    '''Kicks off coroutines for interactions with Telegram bot server and
    SteamGifts site.
    '''
    load_dotenv()
    log_level = os.getenv('LOG_LEVEL', default='WARNING')

    logging.basicConfig(
        format="[%(asctime)s] %(levelname)s | %(module)s: %(message)s",
        level=log_level,
        datefmt="%Y-%m-%d %H:%M:%S")

    storage, dispatcher = tgbot.init_tg()
    await tgbot.on_startup(dispatcher)

    try:
        async with TaskGroup() as tgroup:
            tgroup.create_task(dispatcher.start_polling(config.bot, handle_signals=False))
            tgroup.create_task(sgbot.start_gw_entering(storage))
    finally:
        logging.warning('Exiting...')


if __name__ == '__main__':
    asyncio.run(main())
