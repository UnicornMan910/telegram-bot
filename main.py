async def main():
    logger.info(f"BOT_MODE: {BOT_MODE}")
    logger.info(f"WEBAPP_HOST: {WEBAPP_HOST}, WEBAPP_PORT: {WEBAPP_PORT}")

    if BOT_MODE != "webhook":
        # Flask нужен ТОЛЬКО не в webhook режиме
        Thread(target=run_flask, daemon=True).start()

    # aiohttp для webhook
    app = await webhook_app()
    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, WEBAPP_HOST, WEBAPP_PORT)
    await site.start()

    logger.info(f"AIOHTTP сервер запущен на {WEBAPP_HOST}:{WEBAPP_PORT}")

    await asyncio.Event().wait()
