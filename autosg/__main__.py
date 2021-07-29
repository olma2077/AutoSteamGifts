'''Automates entering SteamGifts giveaways for a user.

User interacts with application using Telegram bot interface.
It is possible to select which SteamGifts sections to check for
available giveaways.
'''
import asyncio
import logging

import autosg.tgbot as tgbot
import autosg.sgbot as sgbot


async def main():
    '''Kicks off coroutines for interactions with Telegram bot server and
    SteamGifts site.
    '''
    logging.basicConfig(
        format="[%(asctime)s] %(levelname)s : %(name)s : %(message)s",
        level=logging.INFO,
        datefmt="%Y-%m-%d %H:%M:%S")

    bot, storage, dispatcher = tgbot.init_tg()
    await tgbot.on_startup(dispatcher)
    try:
        await asyncio.gather(
            dispatcher.start_polling(),
            sgbot.start_gw_entering(storage))
    finally:
        await bot.session.close()
        await tgbot.on_shutdown(dispatcher)


if __name__ == '__main__':
    asyncio.run(main())
