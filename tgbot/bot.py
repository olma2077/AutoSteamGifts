import os
from dotenv import load_dotenv

import logging

import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.files import JSONStorage
from aiogram.utils.exceptions import MessageNotModified
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from emoji import emojize

from contextlib import suppress

import sg

# import token from .env file
load_dotenv()
TOKEN = os.getenv('TELEGRAM_TOKEN')

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
storage = JSONStorage('users.json')
dp = Dispatcher(bot, storage=storage)


async def main():
    await set_commands(bot)
    try:
        await asyncio.gather(dp.start_polling(), sg.start_gw_entering(storage))
    finally:
        await bot.session.close()
        await shutdown(dp)


async def set_commands(bot: Bot):
    '''Set available bot commands on Telegram server'''
    commands = [
        types.BotCommand(command="/start", description="Start the bot"),
        types.BotCommand(command="/register", description="Register SG account in the bot"),
        types.BotCommand(command="/configure", description="Configure ASG bot parameters"),
        types.BotCommand(command="/unregister", description="Remove SG account from the bot")
    ]
    await bot.set_my_commands(commands)


async def shutdown(dispatcher: Dispatcher):
    '''Properly shutdown dispatcher'''
    await dispatcher.storage.close()
    await dispatcher.storage.wait_closed()


async def sections_kb(state: FSMContext):
    '''Create KB with sections and current selection state'''
    kb = InlineKeyboardMarkup()
    selected_sections = (await state.get_data())['sections']

    for section in list(sg.SECTION_URLS):
        if section in selected_sections:
            kb.add(InlineKeyboardButton(
                f"{emojize(':check_mark_button:')} {section}",
                callback_data=f'del_section_{section}'
            ))
        else:
            kb.add(InlineKeyboardButton(
                section,
                callback_data=f'add_section_{section}'
            ))

    return kb


@dp.message_handler(commands=['start'])
async def handle_start(message: types.Message, state: FSMContext):
    if 'token' in await state.get_data():
        await message.answer(
            'Welcome back!\n'
            'Your SteamGifts are being taken care of!')
    else:
        await message.answer(
            'Hi there!\n'
            'This bot will help you not to miss SteamGifts giveaways! '
            'Start with /register to give bot access to your account.')


@dp.message_handler(commands=['register'])
async def handle_register(message: types.Message, state: FSMContext):
    if 'token' in await state.get_data():
        await message.answer(
            "You've already registered your token.\n"
            "To update PHPSESSID, /unregister first.")
    else:
        await message.answer(
            'To authenticate on SteamGifts, this bot needs your PHPSESSID.\n'
            'You can find it in your browser cookies when logged in on SteamGifts. '
            'Please, provide its content below.')


@dp.message_handler(commands=['configure'])
async def handle_configure(message: types.Message, state: FSMContext):
    if 'token' in await state.get_data():
        await message.answer(
            "Please, select, which types of giveaways you're interested in.",
            reply_markup=await sections_kb(state))
    else:
        await message.answer('You should /register first.')


@dp.message_handler(commands=['unregister'])
async def handle_unregister(message: types.Message, state: FSMContext):
    if 'token' in await state.get_data():
        await state.finish()
        await message.answer(
            'Your settings and PHPSESSID were removed.\n'
            'Bot will stop entering giveaways for you. /register to start the bot again.')
    else:
        await message.answer('You should /register first.')


@dp.message_handler()
async def handle_token(message: types.Message, state: FSMContext):
    if 'token' in await state.get_data():
        await message.answer(
            "You've already registered your token.\n"
            "To update PHPSESSID, /unregister first.")
    elif await sg.verify_token(message.text):
        await state.update_data(token=message.text,
                                sections=list(sg.SECTION_URLS)[0:1])
        await message.answer(
            'Your PHPSESSID was successfully registered.\n'
            'Bot will start entering giveaways for you. /configure to change default settings.')
    else:
        await message.answer(
            'Provided PHPSESSID is invalid.\n'
            'Please, verify it and provide it again below.')


@dp.callback_query_handler(lambda c: c.data[:3] in ['del', 'add'])
async def update_sections_info(callback_query: types.CallbackQuery, state: FSMContext):
    '''Handle section state update button'''
    section = callback_query.data.split("_")[-1]
    sections = (await state.get_data())['sections']

    if callback_query.data.startswith("add"):
        sections.append(section)
    elif len(sections) > 1:
        sections.remove(section)
    await state.update_data(sections=sections)

    with suppress(MessageNotModified):
        await bot.edit_message_reply_markup(
            message_id=callback_query.message.message_id,
            chat_id=callback_query.message.chat.id,
            reply_markup=await sections_kb(state)
        )

    await callback_query.answer()


if __name__ == '__main__':
    asyncio.run(main())
