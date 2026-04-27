import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from starlette.applications import Starlette
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.routing import Route
import uvicorn

# Импортируем всю логику вашего бота из существующих файлов
from db import init_db, get_user, save_user
from handlers import (
    start, test_get_name, test_get_age, test_get_weight, test_get_level,
    test_get_goal, test_get_equipment, cancel_test, menu_handler,
    handle_set_result, finish_workout_callback, cancel_workout_callback,
    ASK_NAME, ASK_AGE, ASK_WEIGHT, ASK_LEVEL, ASK_GOAL, ASK_EQUIPMENT
)

logging.basicConfig(level=logging.INFO)

# --- Инициализация бота (так же, как и в main.py) ---
async def init_bot() -> Application:
    """Создаёт и настраивает экземпляр приложения бота"""
    init_db() # Инициализируем БД

    app = Application.builder().token(os.environ["TELEGRAM_TOKEN"]).build()

    test_conv = ConversationHandler(
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
    app.add_handler(test_conv)
    app.add_handler(MessageHandler(filters.Regex('^(🏋️ Начать тренировку|📋 Моя программа|📊 Статистика|⚙️ Настройки|❓ Помощь)$'), menu_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_set_result))
    app.add_handler(CallbackQueryHandler(finish_workout_callback, pattern="^finish_workout$"))
    app.add_handler(CallbackQueryHandler(cancel_workout_callback, pattern="^cancel_workout$"))

    await app.initialize()
    return app

# --- Обработчик вебхуков для Starlette ---
async def health(request):
    """Эндпоинт для проверки здоровья бота на Render"""
    return PlainTextResponse("OK", status_code=200)

async def webhook(request):
    """Принимает запросы от Telegram и передаёт их боту"""
    bot_app = request.app.state.bot_app
    
    # Получаем и обновляем Update из тела запроса
    req_data = await request.json()
    update = Update.de_json(req_data, bot_app.bot)
    
    # Передаём обновление в приложение бота на обработку
    await bot_app.process_update(update)
    return JSONResponse({"status": "ok"})

# --- Точка входа для Uvicorn ---
async def startup():
    """Инициализирует бота и сохраняет его в состояние приложения Starlette"""
    app.state.bot_app = await init_bot()
    webhook_url = os.environ.get("RENDER_EXTERNAL_URL") + "/webhook"
    await app.state.bot_app.bot.set_webhook(webhook_url)
    logging.info(f"Webhook set to {webhook_url}")

async def shutdown():
    """Выключает бота при остановке сервера"""
    await app.state.bot_app.bot.delete_webhook()
    await app.state.bot_app.shutdown()

# Создаём приложение Starlette
starlette_app = Starlette(
    routes=[
        Route("/", endpoint=health),
        Route("/webhook", endpoint=webhook, methods=["POST"]),
    ],
    on_startup=[startup],
    on_shutdown=[shutdown],
)

if __name__ == "__main__":
    uvicorn.run(starlette_app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))