'''Defines keyboards' markups'''
from __future__ import annotations

from typing import TYPE_CHECKING

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from autosg import sgbot
from emoji import emojize

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext


async def sections_kb(state: FSMContext):
    '''Create KB with sections and current selection state'''
    buttons = []
    selected_sections = (await state.get_data())['sections']

    for section in list(sgbot.SECTION_URLS):
        if section in selected_sections:
            buttons.append(InlineKeyboardButton(
                text=f"{emojize(':check_mark_button:')} {section}",
                callback_data=f'del_section_{section}'))
        else:
            buttons.append(InlineKeyboardButton(
                text=section,
                callback_data=f'add_section_{section}'))

    return InlineKeyboardMarkup(inline_keyboard=buttons)
