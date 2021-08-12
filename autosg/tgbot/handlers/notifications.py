'''Notify users on events'''
import autosg.config as config 


async def notify_user(user_id: str, message: str):
    await config.bot.send_message(user_id, message)