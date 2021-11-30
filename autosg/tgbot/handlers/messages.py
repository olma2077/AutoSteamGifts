'''Process messages from a user'''
from __future__ import annotations
import logging

from autosg import sgbot
from .markups import sections_kb

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from aiogram import Dispatcher
    from aiogram.types import Message
    from aiogram.dispatcher import FSMContext


def register_commands(dispatcher: Dispatcher):
    '''Register message handlers in dispatcher'''
    dispatcher.register_message_handler(handle_start, commands=['start'])
    dispatcher.register_message_handler(handle_status, commands=['status'])
    dispatcher.register_message_handler(handle_register, commands=['register'])
    dispatcher.register_message_handler(handle_configure, commands=['configure'])
    dispatcher.register_message_handler(handle_unregister, commands=['unregister'])
    dispatcher.register_message_handler(handle_token)


async def handle_start(message: Message, state: FSMContext):
    '''Handle /start command from a user'''
    if 'token' in await state.get_data():
        await message.answer(
            'Welcome back!\n'
            'Your SteamGifts are being taken care of!')
    else:
        await message.answer(
            'Hi there!\n'
            'This bot will help you not to miss SteamGifts giveaways! '
            'Start with /register to give bot access to your SG account.')


async def handle_status(message: Message, state: FSMContext):
    '''Handle /status command from a user'''
    if 'token' in await state.get_data():
        await message.answer(await sgbot.user_status(message.from_user.id))
    else:
        await message.answer(
            'You are not registered yet. '
            'Start with /register to give bot access to your SG account.')


async def handle_register(message: Message, state: FSMContext):
    '''Handle /register command from a user'''
    if 'token' in await state.get_data():
        await message.answer(
            "You've already registered your token.\n"
            "To update PHPSESSID, /unregister first.")
    else:
        await message.answer(
            'To authenticate on SteamGifts, this bot needs your PHPSESSID.\n'
            'You can find it in your browser cookies when logged in on SteamGifts. '
            'Please, provide its content below.')


async def handle_configure(message: Message, state: FSMContext):
    '''Handle /configure command from a user'''
    if 'token' in await state.get_data():
        await message.answer(
            "Please, select, which types of giveaways you're interested in.",
            reply_markup=await sections_kb(state))
    else:
        await message.answer('You should /register first.')


async def handle_unregister(message: Message, state: FSMContext):
    '''Handle /unregister command from a user'''
    if 'token' in await state.get_data():
        await state.finish()
        await message.answer(
            'Your settings and PHPSESSID were removed.\n'
            'Bot will stop entering giveaways for you. /register to start the bot again.')
        logging.warning(f"{message.from_user.id}: user unregistered!")
    else:
        await message.answer('You should /register first.')


async def handle_token(message: Message, state: FSMContext):
    '''Handle any text message from a user as a SteamGifts token'''
    if 'token' in await state.get_data():
        await message.answer(
            "You've already registered your token.\n"
            "To update PHPSESSID, /unregister first.")
    elif await sgbot.verify_token(message.text):
        await state.update_data(
            token=message.text,
            sections=list(sgbot.SECTION_URLS)[0:1])
        await message.answer(
            'Your PHPSESSID was successfully registered.\n'
            'Bot will start entering giveaways for you. /configure to change default settings.')
        logging.warning(f"{message.from_user.id}: new user registered!")
    else:
        await message.answer(
            'Provided PHPSESSID is invalid.\n'
            'Please, verify it and provide it again below.')
