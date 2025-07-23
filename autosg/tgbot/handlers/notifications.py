'''Notify users on events'''
import logging
from emoji import emojize
from autosg import config


async def notify_on_enter(user_id: str, game: str) -> None:
    '''Notify user when entered a giveaway'''
    await config.bot.send_message(
        user_id,
        f'Just entered giveaway of {game}.')


async def notify_points_left(user_id: str, points: int) -> None:
    '''Notify user on points left'''
    await config.bot.send_message(
        user_id,
        f'{points} points left, sleeping…')


async def notify_expired_token(user_id: str) -> None:
    '''Notify user on expired token and request for new one'''
    logging.debug(f'{user_id}: notifying on expired token')
    await config.bot.send_message(
        user_id,
        'SteamGifts token has expired, please, provide an updated one.')


async def notify_on_start(user_id: str) -> None:
    '''Notify user on bot start'''
    logging.debug(f'{user_id}: notifying on bot start')
    await config.bot.send_message(
        user_id,
        f"{emojize(':warning:')} start working on your entries.")
