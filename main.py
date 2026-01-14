import asyncio
import logging
import os

from flask import Flask, request
from aiogram import Bot, Dispatcher
from aiogram.types import Update

from config import BOT_TOKEN, WEBHOOK_URL

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ===== Flask =====
app = Flask(__name__)

@app.route("/ping", methods=["GET", "HEAD"])
def ping():
    return "OK", 200


@app.route("/webhook", methods=["POST"])
def telegram_webhook():
    update = Update.model_validate(request.json)
    asyncio.get_event_loop().create_task(dp.feed_update(bot, update))
    return "OK", 200


async def on_startup():
    await bot.set_webhook(f"{WEBHOOK_URL}/webhook")
    logging.info("Webhook установлен")


def run():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(on_startup())

    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port)


if __name__ == "__main__":
    run()
