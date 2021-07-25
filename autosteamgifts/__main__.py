import asyncio
import logging

import autosteamgifts.tgbot.tgbot as tgbot
import autosteamgifts.sgbot.sg as sgbot


async def main():
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
