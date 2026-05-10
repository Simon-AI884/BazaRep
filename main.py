import asyncio # Модуль, который даёт возможность одновременно обрабатывать несколько операций ввода/вывода, а приложение при этом не теряет возможности реагировать на внешние воздействия.
import contextlib # Модуль, который подавляет ошибки, если бот принудительно остановлен
import os #Позволяет читать настройки из env и для загрузки конфигурации (БД, API-ключей).
from aiogram import Bot, Dispatcher, types #Импорт трех компонентов из фреймворка,
from aiogram.client.default import DefaultBotProperties #Стандартные параметры бота (Язык, Формат)
from dotenv import load_dotenv #Загрузка переменных окружения

from common.private_commands import private #Загружает список команд (/start, /help, /admin).
from handlers.admins import admin_router #Обработчики команд для админов
from handlers.regular_users import regular_users_router #Обработчики команд для пользователей
from middleware.antiflood import AntiFloodMiddleware #Антифлуд-защита

load_dotenv() #Загрузка переменных окружения

bot = Bot(token=os.getenv('BOT_TOKEN'), default=DefaultBotProperties(parse_mode='HTML'))
dp = Dispatcher()
my_admins_list = []

dp.include_router(admin_router)
dp.include_router(regular_users_router)


async def on_startup():
    dp.message.middleware(AntiFloodMiddleware())
    dp.callback_query.middleware(AntiFloodMiddleware())

    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_my_commands(commands=private, scope=types.BotCommandScopeAllPrivateChats())
    # await bot.delete_my_commands(scope=types.BotCommandScopeAllGroupChats())
    # await bot.delete_my_commands(scope=types.BotCommandScopeAllPrivateChats())


async def main():
    # Асинхронний запуск без блокування потоків
    await on_startup()
    await dp.start_polling(bot)


if __name__ == '__main__':
    with contextlib.suppress(KeyboardInterrupt, SystemExit):
        asyncio.run(main())
