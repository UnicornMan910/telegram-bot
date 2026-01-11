import asyncio
import logging
import sys
from threading import Thread

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from bot_handlers import register_handlers
from config import BOT_TOKEN, WEBHOOK_URL, WEBAPP_HOST, WEBAPP_PORT, BOT_MODE, IS_PRODUCTION
from webapp import app as flask_app

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Глобальные переменные для бота
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())


async def set_bot_commands():
    commands = [
        BotCommand(command="/start", description="Запустить бота"),
        BotCommand(command="/help", description="Помощь"),
    ]
    await bot.set_my_commands(commands)
    logger.info("Команды бота установлены")


def run_flask():
    """Запуск Flask приложения"""
    logger.info(f"Запуск Flask на {WEBAPP_HOST}:{WEBAPP_PORT}")
    flask_app.run(
        host=WEBAPP_HOST,
        port=WEBAPP_PORT,
        debug=False,  # На продакшене debug должен быть False
        use_reloader=False
    )


async def setup_webhook():
    """Настройка вебхука для бота"""
    webhook_info = await bot.get_webhook_info()
    if webhook_info.url != WEBHOOK_URL:
        await bot.set_webhook(
            url=WEBHOOK_URL,
            drop_pending_updates=True
        )
        logger.info(f"Вебхук установлен: {WEBHOOK_URL}")


async def on_startup():
    """Действия при запуске приложения"""
    logger.info("Запуск приложения...")

    # Устанавливаем команды бота
    await set_bot_commands()

    if BOT_MODE == "webhook" and WEBHOOK_URL:
        await setup_webhook()


async def on_shutdown():
    """Действия при остановке приложения"""
    logger.info("Остановка приложения...")
    if BOT_MODE == "webhook":
        await bot.delete_webhook()
        logger.info("Вебхук удален")


async def webhook_app():
    """Создание aiohttp приложения для вебхуков"""
    # Регистрируем обработчики бота
    register_handlers(dp)

    # Создаем aiohttp приложение
    app = web.Application()

    # Добавляем обработчик вебхука
    webhook_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
    )
    webhook_handler.register(app, path="/webhook")

    # Настройка событий запуска/остановки
    app.on_startup.append(lambda _: on_startup())
    app.on_shutdown.append(lambda _: on_shutdown())

    return app


async def polling_mode():
    """Режим polling для локальной разработки"""
    logger.info("Запуск в режиме polling...")
    register_handlers(dp)
    await on_startup()
    await dp.start_polling(bot)


async def main():
    """Основная функция запуска"""
    logger.info(f"Режим работы: {BOT_MODE}")
    logger.info(f"Flask порт: {WEBAPP_PORT}")

    if BOT_MODE == "webhook":
        # Запускаем Flask в отдельном потоке
        flask_thread = Thread(target=run_flask, daemon=True)
        flask_thread.start()

        # Создаем и запускаем aiohttp приложение для вебхуков
        app = await webhook_app()

        # Запускаем aiohttp сервер
        runner = web.AppRunner(app)
        await runner.setup()

        # Используем порт 8000 для вебхуков (Flask будет на WEBAPP_PORT)
        site = web.TCPSite(runner, '0.0.0.0', 8000)
        await site.start()

        logger.info(f"Сервер вебхуков запущен на порту 8000")
        logger.info(f"Admin панель доступна на порту {WEBAPP_PORT}")

        # Бесконечное ожидание
        await asyncio.Event().wait()

    else:
        # Polling режим - запускаем Flask и бота
        flask_thread = Thread(target=run_flask, daemon=True)
        flask_thread.start()

        await polling_mode()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Приложение остановлено")
    except Exception as e:

        logger.error(f"Ошибка запуска: {e}")

import threading
from server import app

def run_flask():
    app.run(host="0.0.0.0", port=10000)

threading.Thread(target=run_flask).start()
