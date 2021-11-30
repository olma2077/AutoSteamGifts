'''Automates entering SteamGifts giveaways for a user.

User interacts with application using Telegram bot interface.
It is possible to select which SteamGifts sections to check for
available giveaways.
'''
import asyncio
import logging

from autosg import tgbot, sgbot, config


async def main():
    '''Kicks off coroutines for interactions with Telegram bot server and
    SteamGifts site.
    '''
    logging.basicConfig(
        format="[%(asctime)s] %(levelname)s | %(module)s: %(message)s",
        level=logging.WARNING,
        datefmt="%Y-%m-%d %H:%M:%S")

    storage, dispatcher = tgbot.init_tg()
    await tgbot.on_startup(dispatcher)
    try:
        await asyncio.gather(
            dispatcher.start_polling(),
            sgbot.start_gw_entering(storage))
    finally:
        logging.warning('Exiting...')
        await config.bot.session.close()
        await tgbot.on_shutdown(dispatcher)


if __name__ == '__main__':
    asyncio.run(main())
