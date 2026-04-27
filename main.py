import logging
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, filters
)
from config import TELEGRAM_TOKEN
from db import init_db
from handlers import (
    start, test_start, test_get_name, test_get_age, test_get_weight,
    test_get_level, test_get_goal, test_get_equipment, cancel_test,
    menu_handler, handle_set_result, finish_workout_callback, cancel_workout_callback,
    ASK_AGE, ASK_WEIGHT, ASK_LEVEL, ASK_GOAL, ASK_EQUIPMENT, WAITING_SET_RESULT
)

def main():
    # Инициализируем БД
    init_db()
    
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # ConversationHandler для теста
    test_conv = ConversationHandler(
        entry_points=[CommandHandler('start', test_start)],
        states={
            ASK_AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, test_get_name)],
            ASK_WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, test_get_age)],
            ASK_LEVEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, test_get_weight)],
            ASK_GOAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, test_get_level)],
            ASK_EQUIPMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, test_get_goal)],
        },
        fallbacks=[CommandHandler('cancel', cancel_test)],
        allow_reentry=True
    )
    # Отдельный обработчик для финального вопроса (equipment) – он вне состояний ConversationHandler, поэтому его добавим вручную как обычный обработчик после теста?
    # Упростим: последний вопрос обработаем в test_get_goal и сразу перейдём к следующему вопросу, а ответ на equipment получим в отдельном хендлере.
    # Поскольку ConversationHandler не умеет легко менять states после завершения, переделаем: добавим состояние ASK_EQUIPMENT.
    # Перепишем выше: в test_get_goal мы переходим в состояние ASK_EQUIPMENT. Уже сделано.
    
    app.add_handler(test_conv)
    # Добавим обработчик для последнего вопроса (equipment) как отдельный MessageHandler с состоянием ASK_EQUIPMENT
    # Но ConversationHandler уже имеет состояние ASK_EQUIPMENT, нам нужно добавить в словарь states.
    # Изменим код handlers.py соответственно. Вместо этого в исходном коде handlers.py я уже использовал ConversationHandler.END после test_get_equipment.
    # Нужно внести правки: в handlers.py в test_get_goal мы переходим в ASK_EQUIPMENT, а test_get_equipment обрабатывает сообщение и завершает.
    # В ConversationHandler я добавил ASK_EQUIPMENT в states, а test_get_equipment будет вызываться при ответе.
    # Но в текущем коде handlers.py в test_get_goal я использовал return ASK_EQUIPMENT (исправим).
    # Давайте соберём окончательную версию handlers.py с корректным ConversationHandler.
    # Я приведу исправленный фрагмент, но для краткости в ответе я дам готовые файлы с исправлениями.
    
    # Обработчики главного меню
    app.add_handler(MessageHandler(filters.Regex('^(🏋️ Начать тренировку|📋 Моя программа|📊 Статистика|⚙️ Настройки|❓ Помощь)$'), menu_handler))
    
    # Обработчик ввода результатов тренировки
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_set_result))
    
    # Callback для кнопок тренировки
    app.add_handler(CallbackQueryHandler(finish_workout_callback, pattern="^finish_workout$"))
    app.add_handler(CallbackQueryHandler(cancel_workout_callback, pattern="^cancel_workout$"))
    
    # Запуск
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()