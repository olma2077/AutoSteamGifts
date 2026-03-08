"""Implements interface to SteamGifts site for entering giveaways.

Switched from :mod:`aiohttp` + :mod:`bs4` to Playwright for browser-driven
navigation and DOM extraction.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, AsyncGenerator, Generator, Optional

from tenacity import retry
from tenacity.stop import stop_after_attempt
from tenacity.wait import wait_fixed, wait_random

from playwright.async_api import async_playwright, Browser, BrowserContext, Page


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


@retry(stop=stop_after_attempt(5), wait=wait_fixed(10) + wait_random(10, 30))
async def verify_token(token: str, session: Optional[object] = None) -> bool:
    """Verify user-provided SteamGifts token using Playwright.

    The function navigates to the profile/settings page with the provided
    ``PHPSESSID`` cookie. If the final URL equals the settings page then the
    token is considered valid. The ``session`` parameter is ignored but kept
    for backward compatibility.
    """
    async with async_playwright() as p:
        browser: Browser = await p.chromium.launch(headless=True)
        context: BrowserContext = await browser.new_context()
        await context.add_cookies(
            [
                {
                    "name": "PHPSESSID",
                    "value": token,
                    "domain": "www.steamgifts.com",
                    "path": "/",
                }
            ]
        )
        page: Page = await context.new_page()
        await page.goto(VERIFY_URL)
        valid = page.url == VERIFY_URL
        await browser.close()
        await p.stop()
        return valid


@dataclass
class Giveaway:
    code: str = ""
    name: str = ""
    cost: int = 0
    steam_id: str = ""


class SteamGiftsSession:
    """SteamGifts interface backed by Playwright.

    This class lazily starts Playwright and a browser context. For compatibility
    with existing code that calls ``await sg_session.session.close()``, the
    instance exposes ``session`` referencing itself and implements ``close``.
    """

    def __init__(self, tg_id: str, token: str) -> None:
        self.tg_id = tg_id
        self._token = token
        self._playwright = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self.page: Page | None = None
        self._xsrf_token: Optional[str] = None
        self._points: Optional[int] = None
        self.next_call = 0
        # compatibility: callers expect an object with async close()
        self.session = self

    async def _ensure_browser(self) -> None:
        if self._browser:
            return
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=True)
        self._context = await self._browser.new_context()
        await self._context.add_cookies(
            [
                {
                    "name": "PHPSESSID",
                    "value": self._token,
                    "domain": "www.steamgifts.com",
                    "path": "/",
                }
            ]
        )
        self.page = await self._context.new_page()

    async def close(self) -> None:
        """Close Playwright resources."""
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

    async def _throttle(self) -> None:
        sleep_time = self.next_call + SG_THROTTLE - time.time()
        self.next_call = max(self.next_call + SG_THROTTLE, time.time())
        if sleep_time > 0:
            await asyncio.sleep(sleep_time)

    async def _load(self, url: str):
        await self._ensure_browser()
        await self._throttle()
        assert self.page is not None
        return await self.page.goto(url)

    @retry(stop=stop_after_attempt(5), wait=wait_fixed(10) + wait_random(5, 30))
    async def _update_session(self) -> None:
        """Fetch the home page and extract xsrf token / points."""
        await self._load(SG_URL)
        assert self.page is not None
        self._xsrf_token = await self.page.locator('input[name="xsrf_token"]').get_attribute("value")
        points_text = await self.page.locator('span.nav__points').text_content()
        # defensive: if selector missing, raise to trigger retry
        if points_text is None:
            raise RuntimeError("Could not read points from page")
        self._points = int(points_text.replace(",", ""))

    async def get_points(self) -> int:
        await self._update_session()
        assert self._points is not None
        return self._points

    async def _parse_giveaway(self, element) -> Giveaway:
        giveaway = Giveaway()
        costs = await element.locator('span.giveaway__heading__thin').all_text_contents()
        if costs:
            try:
                giveaway.cost = int(costs[-1].strip("(P)"))
            except Exception:
                logging.debug("Could not parse cost: %s", costs[-1])
        name_el = await element.query_selector('a.giveaway__heading__name')
        if name_el:
            giveaway.name = (await name_el.text_content()) or ""
            href = await name_el.get_attribute("href") or ""
            parts = href.split("/")
            if len(parts) > 2:
                giveaway.code = parts[2]
        try:
            steam_link = await element.query_selector('a[target="_blank"]')
            if steam_link:
                href2 = await steam_link.get_attribute("href") or ""
                giveaway.steam_id = href2.split("/")[-1].split("?")[0]
                int(giveaway.steam_id)
        except Exception:
            logging.warning(f"Couldn't parse steam_id for {giveaway.name} ({giveaway.code})")
        logging.debug(giveaway)
        return giveaway

    async def get_giveaways_from_section(self, section: str) -> AsyncGenerator[Giveaway, None]:
        await self._update_session()

        page_num = 1
        while True:
            page_url = SECTION_URLS[section] % page_num
            filter_url = f"{SG_URL}/giveaways/{page_url}"
            await self._load(filter_url)
            assert self.page is not None
            logging.info(f"{self.tg_id}: parsing page {page_num} of {section} section")

            if await self.page.query_selector('.pagination--no-results'):
                logging.info(f"{self.tg_id}: page {page_num} of {section} section is empty, finishing")
                break

            elements = await self.page.query_selector_all('div.giveaway__row-inner-wrap')
            for el in elements:
                cls = (await el.get_attribute("class")) or ""
                if "is-faded" in cls.split():
                    continue
                yield await self._parse_giveaway(el)

            page_num += 1

    async def enter_giveaway(self, giveaway: Giveaway) -> bool:
        await self._ensure_browser()
        if not self._xsrf_token:
            await self._update_session()
        payload = {
            "xsrf_token": self._xsrf_token,
            "do": "entry_insert",
            "code": giveaway.code,
        }
        assert self._context is not None
        response = await self._context.request.post(SG_URL + "ajax.php", data=payload)
        try:
            json_data = await response.json()
            if json_data.get("type") == "success":
                await asyncio.sleep(SG_ENTRY_DELAY)
                return True
            if json_data.get("msg") != "Previously Won":
                logging.warning(f"{self.tg_id}: entry error: {json_data.get('msg')}")
            return False
        except Exception:
            text = await response.text()
            logging.error(f"{self.tg_id}: could not parse json: \n {text}")
            raise
