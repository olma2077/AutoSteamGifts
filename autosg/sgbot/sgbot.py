from __future__ import annotations
import asyncio
import logging

from . import sg

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from typing import List, Optional, Dict
    from aiogram.contrib.fsm_storage.files import JSONStorage

SG_CYCLE = 300
MIN_POINTS_TO_ENTER = 10


class SGUser:
    def __init__(self, tg_id: str, token: str, sections: List):
        self.tg_id = tg_id
        self.token = token
        self.sections = sections
        self.sg_session = sg.SteamGiftsSession(tg_id, token)

    async def enter_giveaways(self):
        '''Enter giveaways for a user'''
        for section in self.sections:
            logging.info(f"{self.tg_id}: Polling section {section}")

            points = await self.sg_session.get_points()
            if points > MIN_POINTS_TO_ENTER:
                logging.info(f"{self.tg_id}: Starting with {points} points")
                giveaways = await self.sg_session.get_giveaways_from_section(section)

                if len(giveaways):
                    for giveaway in giveaways:
                        if giveaway.cost > points:
                            logging.info(f"{self.tg_id}: {giveaway.name} is too expensive for now!")
                            continue

                        if not await self.sg_session.enter_giveaway(giveaway):
                            logging.debug(f"{self.tg_id}: Could not enter {giveaway.name}")
                        else:
                            logging.info(f"{self.tg_id}: Entered {giveaway.name}")
                            points -= giveaway.cost

                        if points < MIN_POINTS_TO_ENTER:
                            logging.info(f"{self.tg_id}: Out of points!")
                            return
            else:
                logging.info(f"{self.tg_id}: Out of points!")


def _parse_user(user: Dict) -> Optional[Dict]:
    '''Parse user data from Telegram storage entry'''
    if 'token' not in user[1][user[0]]['data']:
        return None

    id = user[0]
    token = user[1][user[0]]['data']['token']
    sections = user[1][user[0]]['data']['sections']

    return {'tg_id': id,
            'token': token,
            'sections': sections}


async def _get_users_from_storage(storage: JSONStorage) -> Dict:
    '''Parse users from Telegram storage'''
    users = {}
    for user_entry in storage.data.items():
        if user := _parse_user(user_entry):
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
            await users[user].sg_session._session.close()

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
    users = {}
    while True:
        users = await _sync_users(storage, users)

        for user in users:
            logging.info(f"{user}: Polling user with {users[user].sections}")
            await users[user].enter_giveaways()

        await asyncio.sleep(SG_CYCLE)