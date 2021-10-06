'''Implements interface to SteamGifts site for entering giveaways'''
from __future__ import annotations
import json
import logging
from dataclasses import dataclass

import aiohttp
from tenacity import retry, stop_after_attempt, wait_fixed, wait_random
from bs4 import BeautifulSoup

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from typing import Optional, Generator
    from aiohttp import ClientSession


SG_URL = 'https://www.steamgifts.com/'
VERIFY_URL = SG_URL + 'account/settings/profile'
SECTION_URLS = {
    'Wishlist': "search?page=%d&type=wishlist",
    'Recommended': "search?page=%d&type=recommended",
    'Copies': "search?page=%d&copy_min=2",
    'DLC': "search?page=%d&dlc=true",
    'Group': "search?page=%d&type=group",
    'New': "search?page=%d&type=new",
    'All': "search?page=%d"}


async def verify_token(token: str, session: Optional[ClientSession] = None) -> bool:
    '''Verify user-provided SteamGifts token'''
    if not session:
        async with aiohttp.ClientSession() as session:
            return await _verify_token(token, session)

    return await _verify_token(token, session)


@retry(stop=stop_after_attempt(10), wait=wait_fixed(5) + wait_random(0, 5))
async def _verify_token(token: str, session: ClientSession) -> bool:
    '''Helper to verify user-provided SteamGifts token using existing session'''
    cookies = {'PHPSESSID': token}

    async with session.get(VERIFY_URL, cookies=cookies) as resp:
        return len(resp.history) == 0


def _get_giveaway_from_soup(soup: BeautifulSoup) -> Giveaway:
    '''Get givwaway info from a giveaway soup'''
    game_cost = int(
        soup.find_all(
            'span',
            class_='giveaway__heading__thin')[-1].text.strip('(P)'))

    game_name = soup.find(
        'a',
        class_='giveaway__heading__name').text

    giveaway_id = soup.find(
        'a',
        class_='giveaway__heading__name')['href'].split('/')[2]

    steam_id = soup.find(
        'a',
        target='_blank')['href'].split('/')[-2]

    logging.debug(f"{game_name} ({steam_id}/{giveaway_id}): {game_cost}")

    return Giveaway(steam_id, giveaway_id, game_name, game_cost)


def _get_giveaways_from_soup_page(soup: BeautifulSoup) -> Generator[Giveaway, None, None]:
    '''Get list of giveaways from a page soup'''

    for item in soup.find_all('div', class_='giveaway__row-inner-wrap'):
        if 'is-faded' in item['class']:
            continue
        yield _get_giveaway_from_soup(item)


@dataclass
class Giveaway:
    '''Giveaway parameters object'''
    def __init__(self, steam_id: str, code: str, name: str, cost: int):
        self.steam_id = steam_id
        self.code = code
        self.name = name
        self.cost = cost


class SteamGiftsSession:
    '''SteamGifts interface to get info for a user identified by a token'''
    def __init__(self, tg_id: str, token: str):
        '''Set necessary session properties'''
        self.tg_id = tg_id
        self._cookies = {'PHPSESSID': token}
        self.session = aiohttp.ClientSession()
        self._xsrf_token = None
        self._points = None

    @retry(stop=stop_after_attempt(10), wait=wait_fixed(3) + wait_random(0, 2))
    async def _get_soup_from_page(self, url: str) -> BeautifulSoup:
        '''Fetch BS object from an URL'''
        async with self.session.get(url, cookies=self._cookies) as response:
            soup = BeautifulSoup(await response.text(), 'html.parser')
        return soup

    async def _update_session(self):
        '''Get current user's parameters on SteamGifts

        Gets points and xsrf_token for interaction.
        '''
        soup = await self._get_soup_from_page(SG_URL)
        self._xsrf_token = soup.find('input', {'name': 'xsrf_token'})['value']
        self._points = int(soup.find('span', class_='nav__points').text.replace(',', ''))

    async def get_points(self) -> int:
        '''Method to get current user's points value'''
        await self._update_session()
        return self._points

    async def get_giveaways_from_section(self, section: str) -> Generator[Giveaway, None, None]:
        '''Collect all giveaways for a given section'''
        await self._update_session()

        page = 1
        while True:
            page_url = SECTION_URLS[section] % page
            filter_url = f"{SG_URL}/giveaways/{page_url}"

            soup = await self._get_soup_from_page(filter_url)
            logging.info(f"{self.tg_id}: parsing page {page} of {section} section")

            if soup.find(class_='pagination--no-results'):
                logging.info(f"{self.tg_id}: page {page} of {section} section is empty, finishing")
                break

            for giveaway in _get_giveaways_from_soup_page(soup):
                yield giveaway

            page += 1

    async def enter_giveaway(self, giveaway: Giveaway) -> bool:
        '''Enter a game's giveaway'''
        payload = {
            'xsrf_token': self._xsrf_token,
            'do': 'entry_insert',
            'code': giveaway.code}

        async with self.session.post(SG_URL + 'ajax.php', data=payload) as entry:
            try:
                json_data = json.loads(await entry.text())
                if json_data['type'] == 'success':
                    return True

                logging.debug(f"{self.tg_id}: entry error: {json_data['msg']}")
                return False
            except Exception:
                logging.error(f"{self.tg_id}: could not parse json:\n {entry.text()}")
                raise
