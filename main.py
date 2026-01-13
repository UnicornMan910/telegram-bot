import asyncio
import logging
import sys
from threading import Thread

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand
from aiogram.webhook.aiohttp_server import SimpleRequestHandler
from aiohttp import web

from bot_handlers import register_handlers
from config import BOT_TOKEN, WEBHOOK_URL, WEBAPP_HOST, WEBAPP_PORT, BOT_MODE
from server import app as flask_app  # твой Flask /ping

# ------------------- ЛОГИ -------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# ------------------- BOT -------------------
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())


# Установка команд
async def set_bot_commands():
    commands = [
        BotCommand(command="/start", description="Запустить бота"),
        BotCommand(command="/help", description="Помощь"),
    ]
    await bot.set_my_commands(commands)
    logger.info("Команды бота установлены")


# Запуск Flask в отдельном потоке (для /ping)
def run_flask():
    logger.info(f"Запуск Flask на {WEBAPP_HOST}:{WEBAPP_PORT}")
    flask_app.run(
        host=WEBAPP_HOST,
        port=WEBAPP_PORT,
        debug=False,
        use_reloader=False
    )


# Startup webhook
async def on_startup(app: web.Application):
    logger.info("Запуск бота...")
    register_handlers(dp)
    await set_bot_commands()
    if WEBHOOK_URL:
        await bot.set_webhook(WEBHOOK_URL, drop_pending_updates=True)
        logger.info(f"Webhook установлен: {WEBHOOK_URL}")


# Shutdown webhook
async def on_shutdown(app: web.Application):
    logger.info("Остановка бота...")
    await bot.delete_webhook()
    logger.info("Webhook удален")


# aiohttp приложение для webhook
async def webhook_app():
    app = web.Application()
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)

    # Регистрируем обработчик webhook
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path="/webhook")

    # Добавляем ping на aiohttp (дополнительно к Flask)
    async def ping(request):
        return web.Response(text="OK")
    app.router.add_get("/ping", ping)

    return app


async def main():
    logger.info(f"BOT_MODE: {BOT_MODE}")
    logger.info(f"WEBAPP_HOST: {WEBAPP_HOST}, WEBAPP_PORT: {WEBAPP_PORT}")

    # Flask для /ping в отдельном потоке
    Thread(target=run_flask, daemon=True).start()

    # aiohttp для webhook
    app = await webhook_app()
    runner = web.AppRunner(app)
    await runner.setup()

    # Render любит один порт, берем WEBAPP_PORT
    site = web.TCPSite(runner, WEBAPP_HOST, WEBAPP_PORT)
    await site.start()

    logger.info(f"AIOHTTP webhook сервер запущен на {WEBAPP_HOST}:{WEBAPP_PORT}")

    # Держим процесс живым
    await asyncio.Event().wait()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Приложение остановлено вручную")
    except Exception as e:
        logger.error(f"Ошибка запуска: {e}")
