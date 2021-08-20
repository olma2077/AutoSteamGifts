'''Notify users on events'''
from autosg import config


async def notify_on_enter(user_id: str, game: str):
    '''Notify user when entered a giveaway'''
    await config.bot.send_message(
        user_id,
        f'Just entered giveaway of {game}.')


async def notify_points_left(user_id: str, points: int):
    '''Notify user on points left'''
    await config.bot.send_message(
        user_id,
        f'{points} points left, sleeping…')
