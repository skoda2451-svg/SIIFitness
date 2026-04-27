import os
import logging
from contextlib import asynccontextmanager
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from starlette.applications import Starlette
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.routing import Route
import uvicorn

from db import init_db
from handlers import (
    start, test_get_name, test_get_age, test_get_weight, test_get_level,
    test_get_goal, test_get_equipment, cancel_test, menu_handler,
    handle_set_result, finish_workout_callback, cancel_workout_callback,
    ASK_NAME, ASK_AGE, ASK_WEIGHT, ASK_LEVEL, ASK_GOAL, ASK_EQUIPMENT
)

logging.basicConfig(level=logging.INFO)

# Глобальная переменная для бота (альтернатива хранению в app.state)
_bot_app = None

async def init_bot() -> Application:
    global _bot_app
    if _bot_app:
        return _bot_app
    init_db()
    app = Application.builder().token(os.environ["TELEGRAM_TOKEN"]).build()
    # Добавляем все обработчики
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, test_get_name)],
            ASK_AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, test_get_age)],
            ASK_WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, test_get_weight)],
            ASK_LEVEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, test_get_level)],
            ASK_GOAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, test_get_goal)],
            ASK_EQUIPMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, test_get_equipment)],
        },
        fallbacks=[CommandHandler('cancel', cancel_test)],
        allow_reentry=True
    )
    app.add_handler(conv_handler)
    app.add_handler(MessageHandler(filters.Regex('^(🏋️ Начать тренировку|📋 Моя программа|📊 Статистика|⚙️ Настройки|❓ Помощь)$'), menu_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_set_result))
    app.add_handler(CallbackQueryHandler(finish_workout_callback, pattern="^finish_workout$"))
    app.add_handler(CallbackQueryHandler(cancel_workout_callback, pattern="^cancel_workout$"))

    await app.initialize()
    _bot_app = app
    return app

@asynccontextmanager
async def lifespan(app: Starlette):
    logging.info("Starting up...")
    bot = await init_bot()
    webhook_url = os.environ.get("RENDER_EXTERNAL_URL") + "/webhook"
    await bot.bot.set_webhook(webhook_url)
    logging.info(f"Webhook set to {webhook_url}")
    yield
    logging.info("Shutting down...")
    await bot.bot.delete_webhook()
    await bot.shutdown()

async def health(request):
    return PlainTextResponse("OK", status_code=200)

async def webhook(request):
    bot = _bot_app
    if bot is None:
        return JSONResponse({"error": "bot not ready"}, status_code=503)
    req_data = await request.json()
    update = Update.de_json(req_data, bot.bot)
    await bot.process_update(update)
    return JSONResponse({"status": "ok"})

starlette_app = Starlette(
    routes=[
        Route("/", endpoint=health),
        Route("/webhook", endpoint=webhook, methods=["POST"]),
    ],
    lifespan=lifespan,
)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(starlette_app, host="0.0.0.0", port=port)