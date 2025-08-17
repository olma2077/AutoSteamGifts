"""Process callbacks from users' interactions with keyboards"""

from __future__ import annotations

from contextlib import suppress
from typing import TYPE_CHECKING

from aiogram import Router
from aiogram.exceptions import TelegramBadRequest

from .markups import sections_kb

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.types import CallbackQuery


callback_router = Router()


@callback_router.callback_query(lambda c: c.data[:3] in ["del", "add"])
async def update_sections_info(
    callback_query: CallbackQuery, state: FSMContext
) -> None:
    """Handle section state update button"""
    section = callback_query.data.split("_")[-1]
    sections = (await state.get_data())["sections"]

    if callback_query.data.startswith("add"):
        sections.append(section)
    elif len(sections) > 1:
        sections.remove(section)
    await state.update_data(sections=sections)

    with suppress(TelegramBadRequest):
        await callback_query.message.edit_reply_markup(
            reply_markup=await sections_kb(state)
        )

    await callback_query.answer()
