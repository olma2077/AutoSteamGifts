'''Process callbacks from users' interactions with keyboards'''
from __future__ import annotations
from contextlib import suppress

from aiogram.utils.exceptions import MessageNotModified

from .markups import sections_kb

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from aiogram import Dispatcher
    from aiogram.types import CallbackQuery
    from aiogram.dispatcher import FSMContext


def register_callbacks(dispatcher: Dispatcher):
    '''Register callback handlers in dispatcher'''
    dispatcher.register_callback_query_handler(
        update_sections_info,
        lambda c: c.data[:3] in ['del', 'add'])


async def update_sections_info(callback_query: CallbackQuery, state: FSMContext):
    '''Handle section state update button'''
    section = callback_query.data.split("_")[-1]
    sections = (await state.get_data())['sections']

    if callback_query.data.startswith("add"):
        sections.append(section)
    elif len(sections) > 1:
        sections.remove(section)
    await state.update_data(sections=sections)

    with suppress(MessageNotModified):
        await callback_query.message.edit_reply_markup(
            reply_markup=await sections_kb(state))

    await callback_query.answer()
