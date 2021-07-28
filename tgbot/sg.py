import asyncio
import aiohttp
from tenacity import retry, stop_after_attempt, wait_fixed, wait_random
from bs4 import BeautifulSoup
import json
import logging
import time

from typing import List, Tuple
from aiogram.contrib.fsm_storage.files import JSONStorage


SG_URL = 'https://www.steamgifts.com/'
VERIFY_URL = SG_URL + 'account/settings/profile'
SECTION_URLS = {
    'Wishlist': "search?page=%d&type=wishlist",
    'Recommended': "search?page=%d&type=recommended",
    'Copies': "search?page=%d&copy_min=2",
    'DLC': "search?page=%d&dlc=true",
    'Group': "search?page=%d&type=group",
    'New': "search?page=%d&type=new",
    'All': "search?page=%d"
}

SG_CYCLE = 900
MIN_POINTS_TO_ENTER = 10
_session = None


@retry(stop=stop_after_attempt(10), wait=wait_fixed(3) + wait_random(0, 2))
async def verify_token(token: str) -> bool:
    cookies = {'PHPSESSID': token}
    async with _session.get(VERIFY_URL, cookies=cookies) as resp:
        return len(resp.history) == 0


class SGUser:
    def __init__(self, id, token: str, sections: list) -> None:
        self.id = id
        self.cookies = {
            'PHPSESSID': token
        }
        self.sections = sections

    @retry(stop=stop_after_attempt(10), wait=wait_fixed(3) + wait_random(0, 2))
    async def get_soup_from_page(self, url: str) -> BeautifulSoup:
        async with _session.get(url, cookies=self.cookies) as response:
            soup = BeautifulSoup(await response.text(), 'html.parser')
        return soup

    async def get_points(self) -> None:
        soup = await self.get_soup_from_page(SG_URL)
        self.xsrf_token = soup.find('input', {'name': 'xsrf_token'})['value']
        self.points = int(soup.find('span', class_='nav__points').text)

    def get_games_list(self, soup: BeautifulSoup) -> List[BeautifulSoup]:
        games_list = []

        for item in soup.find_all('div', class_='giveaway__row-inner-wrap'):
            if 'is-faded' in item['class']:
                continue
            games_list.append(item)

        return games_list

    def get_game_details(self, soup: BeautifulSoup) -> Tuple[str, int]:
        game_cost = int(
            soup.find_all('span', class_='giveaway__heading__thin')[-1]
            .text.strip('(P)'))
        game_name = soup.find('a', class_='giveaway__heading__name').text
        logging.debug(f"{game_name}: {game_cost}")

        return game_name, game_cost

    async def enter_giveaway(self, soup: BeautifulSoup) -> bool:
        game_id = soup.find('a', class_='giveaway__heading__name')['href'].split('/')[2]
        payload = {
            'xsrf_token': self.xsrf_token,
            'do': 'entry_insert',
            'code': game_id
        }

        async with _session.post(SG_URL + 'ajax.php', data=payload) as entry:
            try:
                json_data = json.loads(await entry.text())
                if json_data['type'] == 'success':
                    return True
                else:
                    logging.debug(f"{self.id}: Entry error: {json_data['msg']}")
                    return False
            except:
                logging.error(f"Could not parse json:\n {entry.text()}")
                raise


    async def enter_sg_section(self, section: str) -> None:
        await self.get_points()
        if self.points >= MIN_POINTS_TO_ENTER:
            logging.info(f"{self.id}: Starting with {self.points} points")
            page = 1
            while True:
                page_url = SECTION_URLS[section] % page
                filter_url = f"{SG_URL}/giveaways/{page_url}"

                soup = await self.get_soup_from_page(filter_url)
                logging.info(f"{self.id}: checking page {page} of {section} section")

                if soup.find(class_='pagination--no-results'):
                    logging.info(f"{self.id}: page {page} of {section} section is empty, skipping")
                    break

                games_list = self.get_games_list(soup)

                for game in games_list:
                    game_name, game_cost = self.get_game_details(game)

                    if game_cost > self.points:
                        logging.info(f"{self.id}: {game_name} is too expensive for now, skipping")
                        continue

                    if not await self.enter_giveaway(game):
                        pass
                        logging.debug(f"{self.id}: Could not enter {game_name}")
                    else:
                        logging.info(f"{self.id}: Entered {game_name}")
                        self.points -= game_cost
                    await asyncio.sleep(2)

                    if self.points < MIN_POINTS_TO_ENTER:
                        logging.info(f"{self.id}: Out of points!")
                        return

                page += 1
                await asyncio.sleep(5)
        else:
            logging.info(f"{self.id}: Out of points!")

    async def enter_giveaways(self) -> None:
        for section in self.sections:
            logging.info(f"{self.id}: polling section {section}")
            await self.enter_sg_section(section)


async def start_gw_entering(storage: JSONStorage) -> None:
    global _session
    _session = aiohttp.ClientSession()

    while True:
        for user in storage.data.items():
            id = user[0]
            if 'token' in user[1][user[0]]['data']:
                token = user[1][user[0]]['data']['token']
                sections = user[1][user[0]]['data']['sections']
                if await verify_token(token):
                    sg_user = SGUser(id, token, sections)
                    logging.info(f"{id}: Polling user with {sections}")
                    await sg_user.enter_giveaways()
            await asyncio.sleep(1)
        logging.debug(f"Cycle finished, sleeping for {SG_CYCLE//60} min")
        await asyncio.sleep(SG_CYCLE)
