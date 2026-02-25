import os

from aiogram import types, Bot
from aiogram.filters import Filter


class IsAdmin(Filter):
    def __init__(self):
        None

    async def __call__(self, message: types.Message, bot: Bot):
        admin_ids = list(map(int, os.getenv('ADMINS_UID', '').split(',')))
        return message.from_user.id in admin_ids
