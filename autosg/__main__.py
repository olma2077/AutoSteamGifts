'''Automates entering SteamGifts giveaways for a user.

User interacts with application using Telegram bot interface.
It is possible to select which SteamGifts sections to check for
available giveaways.
'''
import asyncio
import logging
import os

from dotenv import load_dotenv

from autosg import config, sgbot, tgbot


async def main():
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
        await asyncio.gather(
            dispatcher.start_polling(config.bot),
            sgbot.start_gw_entering(storage))
    finally:
        logging.warning('Exiting...')
        await dispatcher.stop_polling()


if __name__ == '__main__':
    asyncio.run(main())
