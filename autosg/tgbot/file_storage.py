'''Reuse of file storage module from aiogram v2'''
import pathlib
import typing
import json
import logging
import copy

from aiogram.fsm.storage.base import BaseStorage


class FileStorage(BaseStorage):
    def __init__(self, path: typing.Union[pathlib.Path, str]) -> None:
        '''
        :param path: file path
        '''
        super().__init__()
        path = self.path = pathlib.Path(path)

        try:
            self.storage = self.read(path)
        except FileNotFoundError:
            self.storage = {}

    async def close(self) -> None:
        logging.debug('Closing storage')
        if self.storage:
            self.write(self.path)
        await super().close()

    def read(self, path: pathlib.Path) -> typing.NoReturn:
        '''Read from a file storage'''
        raise NotImplementedError

    def write(self, path: pathlib.Path) -> typing.NoReturn:
        '''Write to a file storage'''
        raise NotImplementedError


class JSONStorage(FileStorage):
    '''
    JSON File storage based on MemoryStorage
    '''
    async def set_state(self, key, state):
        pass

    async def get_state(self, key):
        pass

    async def set_data(self, key, data):
        chat = str(key.chat_id)
        user = str(key.user_id)

        self.storage[chat][user]['data'] = copy.deepcopy(data)

    async def get_data(self, key):
        chat = str(key.chat_id)
        user = str(key.user_id)

        return copy.deepcopy(self.storage[chat][user]['data'])

    async def update_data(self, key, data):
        chat = str(key.chat_id)
        user = str(key.user_id)

        self.storage[chat][user]['data'].update(data)

    def read(self, path: pathlib.Path):
        logging.debug(f'Loading state from {path}')
        with path.open('r') as file:
            return json.load(file)

    def write(self, path: pathlib.Path):
        logging.debug(f'Saving state to {path}')
        with path.open('w') as file:
            return json.dump(self.storage, file, indent=4)
