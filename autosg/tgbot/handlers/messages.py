'''Process messages from a user'''
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from aiogram import Router
from aiogram.filters import Command, CommandStart

from autosg import sgbot

from .markups import sections_kb

if TYPE_CHECKING:
    from aiogram import Dispatcher
    from aiogram.fsm.context import FSMContext
    from aiogram.types import Message


message_router = Router()


# def register_commands(dispatcher: Dispatcher):
#     '''Register message handlers in dispatcher'''
#     dispatcher.register_message_handler(handle_start, commands=['start'])
#     dispatcher.register_message_handler(handle_status, commands=['status'])
#     # dispatcher.register_message_handler(handle_register, commands=['register'])
#     dispatcher.register_message_handler(handle_configure, commands=['configure'])
#     dispatcher.register_message_handler(handle_unregister, commands=['unregister'])
#     dispatcher.register_message_handler(handle_token)


@message_router.message(CommandStart())
async def handle_start(message: Message, state: FSMContext):
    '''Handle /start command from a user'''
    logging.debug(f'{message.from_user.id}: received /start command')
    logging.debug(f'State: {await state.get_data()}')
    if 'token' in await state.get_data():
        await message.answer(
            'Welcome back!\n'
            'Your SteamGifts are being taken care of!')
    else:
        await message.answer(
            'Hi there!\n'
            'This bot will help you not to miss SteamGifts giveaways! '
            'Start with /register to give bot access to your SG account.')


@message_router.message(Command(commands='status'))
async def handle_status(message: Message, state: FSMContext):
    '''Handle /status command from a user'''
    logging.debug(f'{message.from_user.id}: received /status command')
    logging.debug(f'State: {await state.get_data()}')
    if 'token' in await state.get_data() and message.from_user:
        await message.answer(await sgbot.user_status(message.from_user.id))
    else:
        await message.answer(
            'You are not registered yet. '
            'Start with /register to give bot access to your SG account.')


# async def handle_register(message: Message, state: FSMContext):
#     '''Handle /register command from a user'''
#     if 'token' in await state.get_data():
#         await message.answer(
#             "You've already registered your token.\n"
#             "To update PHPSESSID, /unregister first.")
#     else:
#         await message.answer(
#             'To authenticate on SteamGifts, this bot needs your PHPSESSID.\n'
#             'You can find it in your browser cookies when logged in on SteamGifts. '
#             'Please, provide its content below.')


@message_router.message(Command(commands='configure'))
async def handle_configure(message: Message, state: FSMContext) -> None:
    '''Handle /configure command from a user'''
    logging.debug(f'{message.from_user.id}: received /config command')
    logging.debug(f'State: {await state.get_data()}')
    if 'token' in await state.get_data():
        await message.answer(
            "Please, select, which types of giveaways you're interested in.",
            reply_markup=await sections_kb(state))
    else:
        await message.answer('You should /register first.')


@message_router.message(Command(commands='unregister'))
async def handle_unregister(message: Message, state: FSMContext) -> None:
    '''Handle /unregister command from a user'''
    logging.debug(f'{message.from_user.id}: received /unregister command')
    logging.debug(f'State: {await state.get_data()}')
    if 'token' in await state.get_data() and message.from_user:
        await state.clear()
        await message.answer(
            'Your settings and PHPSESSID were removed.\n'
            'Bot will stop entering giveaways for you. /register to start the bot again.')
        logging.warning(f"{message.from_user.id}: user unregistered!")
    else:
        await message.answer('You should /register first.')


@message_router.message()
async def handle_token(message: Message, state: FSMContext) -> None:
    '''Handle any text message from a user as a SteamGifts token'''
    logging.debug(f'{message.from_user.id}: received text {message.text}')
    logging.debug(f'State: {await state.get_data()}')
    if 'token' in await state.get_data() and message.text and message.from_user:
        if await sgbot.verify_token(message.text):
            await state.update_data(
                token=message.text,
                sections=list(sgbot.SECTION_URLS)[0:1])
            await message.answer(
                'Your PHPSESSID was successfully updated.')
            logging.warning(f"{message.from_user.id}: token successfully updated.")
        else:
            await message.answer(
                'Provided PHPSESSID is invalid.\n'
                'Please, verify it and provide it again below.')
    else:
        await message.answer(
            'Unknown command.\n'
            'Please, try again.')
