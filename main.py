import logging
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, filters
)
from config import TELEGRAM_TOKEN
from db import init_db
from handlers import (
    start, test_get_name, test_get_age, test_get_weight, test_get_level,
    test_get_goal, test_get_equipment, cancel_test, menu_handler,
    handle_set_result, finish_workout_callback, cancel_workout_callback,
    ASK_NAME, ASK_AGE, ASK_WEIGHT, ASK_LEVEL, ASK_GOAL, ASK_EQUIPMENT
)

def main():
    init_db()
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    # ConversationHandler для теста
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

    # Меню (после прохождения теста)
    app.add_handler(MessageHandler(filters.Regex('^(🏋️ Начать тренировку|📋 Моя программа|📊 Статистика|⚙️ Настройки|❓ Помощь)$'), menu_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_set_result))
    app.add_handler(CallbackQueryHandler(finish_workout_callback, pattern="^finish_workout$"))
    app.add_handler(CallbackQueryHandler(cancel_workout_callback, pattern="^cancel_workout$"))

    logging.info("Бот запущен")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()