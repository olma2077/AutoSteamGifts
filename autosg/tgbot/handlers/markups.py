from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from emoji import emojize

import autosg.sgbot.sg as sg

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from aiogram.dispatcher import FSMContext


async def sections_kb(state: FSMContext):
    '''Create KB with sections and current selection state'''
    kb = InlineKeyboardMarkup()
    selected_sections = (await state.get_data())['sections']

    for section in list(sg.SECTION_URLS):
        if section in selected_sections:
            kb.add(InlineKeyboardButton(
                f"{emojize(':check_mark_button:')} {section}",
                callback_data=f'del_section_{section}'))
        else:
            kb.add(InlineKeyboardButton(
                section,
                callback_data=f'add_section_{section}'))

    return kb
