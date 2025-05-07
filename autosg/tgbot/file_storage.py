'''Reuse of file storage module from aiogram v2'''
import pathlib
import typing
import json

from aiogram.fsm.storage.memory import MemoryStorage


class _FileStorage(MemoryStorage):
    def __init__(self, path: typing.Union[pathlib.Path, str]) -> None:
        '''
        :param path: file path
        '''
        super().__init__()
        path = self.path = pathlib.Path(path)

        try:
            self.data = self.read(path)
        except FileNotFoundError:
            pass

    async def close(self) -> None:
        if self.data:
            self.write(self.path)
        await super().close()

    def read(self, path: pathlib.Path) -> typing.NoReturn:
        '''Read from a file storage'''
        raise NotImplementedError

    def write(self, path: pathlib.Path) -> typing.NoReturn:
        '''Write to a file storage'''
        raise NotImplementedError


class JSONStorage(_FileStorage):
    '''
    JSON File storage based on MemoryStorage
    '''

    def read(self, path: pathlib.Path):
        with path.open('r') as file:
            return json.load(file)

    def write(self, path: pathlib.Path):
        with path.open('w') as file:
            return json.dump(self.data, file, indent=4)
