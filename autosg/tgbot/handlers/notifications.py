'''Notify users on events'''
from autosg import config


async def notify_on_enter(user_id: str, game: str, points: int):
    '''Notify user when entered a giveaway'''
    await config.bot.send_message(
        user_id,
        f'Just entered giveaway of {game}.\n{points} points left.')
