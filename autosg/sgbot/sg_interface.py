"""Implements interface to SteamGifts site for entering giveaways"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

import aiohttp
from bs4 import BeautifulSoup
from tenacity import retry
from tenacity.stop import stop_after_attempt
from tenacity.wait import wait_fixed, wait_random

if TYPE_CHECKING:
    from typing import AsyncGenerator, Generator, Optional
    from aiohttp import ClientSession


SG_URL = "https://www.steamgifts.com/"
VERIFY_URL = SG_URL + "account/settings/profile"
SECTION_URLS = {
    "Wishlist": "search?page=%d&type=wishlist",
    "Recommended": "search?page=%d&type=recommended",
    "Copies": "search?page=%d&copy_min=2",
    "DLC": "search?page=%d&dlc=true",
    "Group": "search?page=%d&type=group",
    "New": "search?page=%d&type=new",
    "All": "search?page=%d",
}
SG_THROTTLE = 10
SG_ENTRY_DELAY = 20


async def verify_token(token: str, session: Optional[ClientSession] = None) -> bool:
    """Verify user-provided SteamGifts token"""
    if not session:
        async with aiohttp.ClientSession() as session:
            return await _verify_token(token, session)

    return await _verify_token(token, session)


@retry(stop=stop_after_attempt(5), wait=wait_fixed(10) + wait_random(10, 30))
async def _verify_token(token: str, session: ClientSession) -> bool:
    """Helper to verify user-provided SteamGifts token using existing session"""
    cookies = {"PHPSESSID": token}

    async with session.get(VERIFY_URL, cookies=cookies) as resp:
        return len(resp.history) == 0


def _get_giveaway_from_soup(soup: BeautifulSoup) -> Giveaway:
    """Get givwaway info from a giveaway soup"""
    giveaway = Giveaway()
    # Fix: handle soup None return value in a proper way
    try:
        giveaway.cost = int(
            soup.find_all("span", class_="giveaway__heading__thin")[-1].text.strip(
                "(P)"
            )
        )

        giveaway.name = soup.find("a", class_="giveaway__heading__name").text

        giveaway.code = soup.find("a", class_="giveaway__heading__name")["href"].split(
            "/"
        )[2]
        try:
            giveaway.steam_id = (
                soup.find("a", target="_blank")["href"].split("/")[-1].split("?")[0]
            )

            int(giveaway.steam_id)
        except ValueError:
            logging.warning(
                f'''Couldn't parse steam_id from {soup.find("a", target="_blank")} for {giveaway.name} ({giveaway.code})'''
            )

        logging.debug(f"{giveaway}")
        return giveaway

    except Exception:
        logging.error(f"Failed to parse giveaway: \n {soup.prettify()}")
        raise


def _get_giveaways_from_soup_page(
    soup: BeautifulSoup,
) -> Generator[Giveaway, None, None]:
    """Get list of giveaways from a page soup"""

    for item in soup.find_all("div", class_="giveaway__row-inner-wrap"):
        if "is-faded" in item["class"]:
            continue
        yield _get_giveaway_from_soup(item)


@dataclass
class Giveaway:
    """Giveaway parameters object"""

    code: str = ""
    name: str = ""
    cost: int = 0
    steam_id: str = ""


class SteamGiftsSession:
    """SteamGifts interface to get info for a user identified by a token"""

    def __init__(self, tg_id: str, token: str) -> None:
        """Set necessary session properties"""
        self.tg_id = tg_id
        self._cookies = {"PHPSESSID": token}
        self.session = aiohttp.ClientSession()
        self._xsrf_token = None
        self._points = None
        self.next_call = 0

    @retry(stop=stop_after_attempt(5), wait=wait_fixed(10) + wait_random(5, 20))
    async def _get_soup_from_page(self, url: str) -> BeautifulSoup:
        """Fetch BS object from an URL"""
        # trottling page fetching
        sleep_time = self.next_call + SG_THROTTLE - time.time()
        self.next_call = max(self.next_call + SG_THROTTLE, time.time())
        await asyncio.sleep(sleep_time)

        async with self.session.get(url, cookies=self._cookies) as response:
            soup = BeautifulSoup(await response.text(), "html.parser")
        return soup

    @retry(stop=stop_after_attempt(5), wait=wait_fixed(10) + wait_random(5, 30))
    async def _update_session(self) -> None:
        """Get current user's parameters on SteamGifts

        Gets points and xsrf_token for interaction.
        """
        soup = await self._get_soup_from_page(SG_URL)
        self._xsrf_token = soup.find("input", {"name": "xsrf_token"})["value"]
        self._points = int(
            soup.find("span", class_="nav__points").text.replace(",", "")
        )

    async def get_points(self) -> int:
        """Method to get current user's points value"""
        await self._update_session()
        return self._points

    async def get_giveaways_from_section(
        self, section: str
    ) -> AsyncGenerator[Giveaway, None]:
        """Collect all giveaways for a given section"""
        await self._update_session()

        page = 1
        while True:
            page_url = SECTION_URLS[section] % page
            filter_url = f"{SG_URL}/giveaways/{page_url}"

            soup = await self._get_soup_from_page(filter_url)
            logging.info(f"{self.tg_id}: parsing page {page} of {section} section")

            if soup.find(class_="pagination--no-results"):
                logging.info(
                    f"{self.tg_id}: page {page} of {section} section is empty, finishing"
                )
                break

            for giveaway in _get_giveaways_from_soup_page(soup):
                yield giveaway

            page += 1

    async def enter_giveaway(self, giveaway: Giveaway) -> bool:
        """Enter a game's giveaway"""
        payload = {
            "xsrf_token": self._xsrf_token,
            "do": "entry_insert",
            "code": giveaway.code,
        }

        async with self.session.post(SG_URL + "ajax.php", data=payload) as entry:
            try:
                json_data = json.loads(await entry.text())
                if json_data["type"] == "success":
                    await asyncio.sleep(SG_ENTRY_DELAY)
                    return True

                if json_data["msg"] != "Previously Won":
                    logging.warning(f"{self.tg_id}: entry error: {json_data['msg']}")

                return False

            except Exception:
                logging.error(f"{self.tg_id}: could not parse json: \n {entry.text()}")
                raise
