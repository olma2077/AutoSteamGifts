'''Defines keyboards' markups'''
from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from emoji import emojize

from autosg import sgbot

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from aiogram.dispatcher import FSMContext


async def sections_kb(state: FSMContext):
    '''Create KB with sections and current selection state'''
    keyboard = InlineKeyboardMarkup()
    selected_sections = (await state.get_data())['sections']

    for section in list(sgbot.SECTION_URLS):
        if section in selected_sections:
            keyboard.add(InlineKeyboardButton(
                f"{emojize(':check_mark_button:')} {section}",
                callback_data=f'del_section_{section}'))
        else:
            keyboard.add(InlineKeyboardButton(
                section,
                callback_data=f'add_section_{section}'))

    return keyboard
