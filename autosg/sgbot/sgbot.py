'''Implements logic of entering giveaways for a user from Telegram.

Uses user data from tgbot module, interaction with steamgits site is
isolated in sg_interface.

'''
from __future__ import annotations
import asyncio
import logging

from . import sg_interface as sg
from autosg.tgbot.handlers import notifications

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from typing import List, Optional, Dict
    from aiogram.contrib.fsm_storage.files import JSONStorage


SG_CYCLE = 1800
MIN_POINTS_TO_ENTER = 10
MAX_POINTS_TO_KEEP = 350
MIN_POINTS = 0
MAX_POINTS = 400


class SGUser:
    '''Handles user-related operations with steamgift giveaways'''
    users = {}

    def __init__(self, tg_id: str, token: str, sections: List):
        '''Set necessary properties, start steamgifts session'''
        self.tg_id = tg_id
        self.token = token
        self.sections = sections
        self.sg_session = sg.SteamGiftsSession(tg_id, token)
        self.points = 0

    async def get_points(self):
        '''Return current amount of points for a user'''
        return await self.sg_session.get_points()

    async def _enter_giveaways_section(self, section: str, min_points: int = MIN_POINTS_TO_ENTER):
        '''Enter giveaways for a given section'''
        if self.points < min_points:
            logging.info(f"{self.tg_id}: out of points!")
            return

        async for giveaway in self.sg_session.get_giveaways_from_section(section):
            if giveaway.cost > self.points:
                logging.info(f"{self.tg_id}: {giveaway.name} is too expensive for now!")
                continue

            if not await self.sg_session.enter_giveaway(giveaway):
                logging.debug(f"{self.tg_id}: could not enter {giveaway.name}")
            else:
                logging.info(f"{self.tg_id}: entered {giveaway.name}")
                self.points -= giveaway.cost
                await notifications.notify_on_enter(self.tg_id, giveaway.name)
                await asyncio.sleep(2)

            if self.points < min_points:
                logging.info(f"{self.tg_id}: out of points!")
                return

    async def _burn_points(self):
        '''Burn points for a user in case there are too many unused points left'''
        await self._enter_giveaways_section('All', MAX_POINTS_TO_KEEP)

    async def enter_giveaways(self):
        '''Enter giveaways for a user'''
        self.points = await self.sg_session.get_points()

        for section in self.sections:
            logging.info(f"{self.tg_id}: polling section {section}")

            if self.points > MIN_POINTS_TO_ENTER:
                logging.info(f"{self.tg_id}: starting with {self.points} points")
                await self._enter_giveaways_section(section)
            else:
                logging.info(f"{self.tg_id}: out of points!")
                return

        if self.points > MAX_POINTS_TO_KEEP:
            logging.info(f"{self.tg_id}: too many points left, burning")
            await self._burn_points()

        await notifications.notify_points_left(self.tg_id, self.points)


async def user_status(idx: int):
    '''Returns status string for a given user'''
    return f'You have {await SGUser.users[str(idx)].get_points()} points unused.'


def _parse_user(user: Dict) -> Optional[Dict]:
    '''Parse user data from Telegram storage entry'''
    if 'token' not in user[1][user[0]]['data']:
        return None

    idx = user[0]
    token = user[1][user[0]]['data']['token']
    sections = user[1][user[0]]['data']['sections']

    return {'tg_id': idx,
            'token': token,
            'sections': sections}


async def _get_users_from_storage(storage: JSONStorage) -> Dict:
    '''Parse users from Telegram storage'''
    users = {}
    for user_entry in storage.data.items():
        user = _parse_user(user_entry)
        if user:
            if await sg.verify_token(user['token']):
                users[user['tg_id']] = user

    return users


async def _cleanup_users(storage_users: Dict, users: Dict) -> Dict:
    '''Remove users we don't have in Telegram bot anymore'''
    new_users = {}
    for user in users:
        if user in storage_users:
            new_users[user] = users[user]
        else:
            await users[user].sg_session.session.close()
            logging.info(f"{user}: sg token became invalid, removing user from poll")

    return new_users


def _update_users(storage_users: Dict, users: Dict) -> Dict:
    '''Update existing users' parameters'''
    if len(users):
        for user in storage_users:
            if user in users:
                users[user].token = storage_users[user]['token']
                users[user].sections = storage_users[user]['sections']

    return users


def _add_users(storage_users: Dict, users: Dict) -> Dict:
    '''Add new users from Telegram bot'''
    if len(users) != len(storage_users):
        for user_id, user in storage_users.items():
            users[user_id] = SGUser(user['tg_id'],
                                    user['token'],
                                    user['sections'])
            logging.info(f"{user_id}: added user to poll")

    return users


async def _sync_users(storage: JSONStorage, users: Dict) -> Dict:
    '''Actualize list of users to enter giveaways for from Telegram storage'''
    storage_users = await _get_users_from_storage(storage)

    users = await _cleanup_users(storage_users, users)
    users = _update_users(storage_users, users)
    users = _add_users(storage_users, users)

    return users


async def start_gw_entering(storage: JSONStorage):
    '''Cycle through registered users and enter giveaways for them'''
    try:
        while True:
            SGUser.users = await _sync_users(storage, SGUser.users)

            for user in SGUser.users.values():
                logging.info(f"{user.tg_id}: polling user with sections: {user.sections}")
                await user.enter_giveaways()

            await asyncio.sleep(SG_CYCLE)
    finally:
        logging.info('Closing user sessions…')
        for user in SGUser.users.values():
            await user.sg_session.session.close()
        logging.info('User sessions closed')
