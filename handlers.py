import logging
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, filters, ContextTypes
)
from config import TELEGRAM_TOKEN
from db import init_db, get_user, save_user, save_workout_log
from trainer import generate_program_from_test, adjust_program_after_workout
from workout import WorkoutSession
from keyboards import main_menu, workout_set_keyboard, cancel_keyboard

# Состояния для ConversationHandler (тест)
ASK_AGE, ASK_WEIGHT, ASK_LEVEL, ASK_GOAL, ASK_EQUIPMENT = range(5)

# Состояния для тренировки
WAITING_SET_RESULT = 100

# Хранилище активных тренировок (в памяти, для простоты)
active_workouts = {}

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    if user and user.get('test_data'):
        # Уже прошёл тест
        await update.message.reply_text(
            f"Привет, {user.get('name', '')}! Я твой виртуальный фитнес тренер.\n\n"
            "Выбери действие:",
            reply_markup=main_menu()
        )
    else:
        # Начинаем тест
        await update.message.reply_text(
            "Привет! Я твой виртуальный фитнес тренер. Я буду помогать тебе с тренировками, подберу нужную программу и нагрузку, буду следить за твоим прогрессом и достижениями.\n\n"
            "Для начала давай пройдём короткое тестирование, чтобы я подобрал оптимальную программу.\n"
            "Как тебя зовут?"
        )
        return ConversationHandler.END  # мы не используем ConversationHandler для имени, упростим:
        # Но лучше сделать ConversationHandler для теста. Реализуем ниже.
        # Пока просто сохраним имя и спросим дальше.

# Напишем полноценный ConversationHandler для теста:
async def test_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Давай знакомиться! Как тебя зовут?")
    return ASK_AGE

async def test_get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['name'] = update.message.text
    await update.message.reply_text("Сколько тебе лет? (число)")
    return ASK_WEIGHT

async def test_get_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        age = int(update.message.text)
        context.user_data['age'] = age
    except:
        await update.message.reply_text("Пожалуйста, введи число. Сколько тебе лет?")
        return ASK_WEIGHT
    await update.message.reply_text("Какой твой вес (в кг)?")
    return ASK_LEVEL

async def test_get_weight(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        weight = float(update.message.text)
        context.user_data['weight'] = weight
    except:
        await update.message.reply_text("Введи число. Вес в кг?")
        return ASK_LEVEL
    # Уровень подготовки
    await update.message.reply_text(
        "Каков твой уровень подготовки?\n"
        "1 - Начинающий\n"
        "2 - Средний\n"
        "3 - Продвинутый",
        reply_markup=ReplyKeyboardRemove()
    )
    return ASK_GOAL

async def test_get_level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    level_map = {"1": "beginner", "2": "intermediate", "3": "advanced"}
    level = level_map.get(update.message.text.strip(), "beginner")
    context.user_data['level'] = level
    await update.message.reply_text("Какова твоя цель?\n1 - Набор массы\n2 - Функциональная подготовка")
    return ASK_EQUIPMENT

async def test_get_goal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    goal_map = {"1": "mass", "2": "functional"}
    goal = goal_map.get(update.message.text.strip(), "mass")
    context.user_data['goal'] = goal
    await update.message.reply_text(
        "Какое оборудование доступно?\n"
        "Отправь номера через пробел (например: 1 2 3):\n"
        "1 - Штанга 25 кг\n2 - Турник\n3 - Брусья"
    )
    return ConversationHandler.END

async def test_get_equipment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nums = update.message.text.split()
    equipment = []
    if "1" in nums: equipment.append("barbell")
    if "2" in nums: equipment.append("pullup_bar")
    if "3" in nums: equipment.append("dips_bar")
    context.user_data['equipment'] = equipment if equipment else ["barbell","pullup_bar","dips_bar"]
    
    # Сохраняем тестовые данные в БД
    user_id = update.effective_user.id
    save_user(user_id, name=context.user_data['name'], test_data=context.user_data)
    # Генерируем программу
    program = generate_program_from_test(context.user_data)
    save_user(user_id, program=program)
    await update.message.reply_text(
        "Отлично! Программа тренировок готова. Теперь ты можешь начать тренировку.",
        reply_markup=main_menu()
    )
    return ConversationHandler.END

async def cancel_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Тест отменён. Напиши /start, чтобы начать заново.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# Обработчик главного меню
async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "🏋️ Начать тренировку":
        await start_workout(update, context)
    elif text == "📋 Моя программа":
        await show_program(update, context)
    elif text == "📊 Статистика":
        await show_stats(update, context)
    elif text == "⚙️ Настройки":
        await settings(update, context)
    elif text == "❓ Помощь":
        await help_command(update, context)
    else:
        await update.message.reply_text("Используй кнопки меню.", reply_markup=main_menu())

async def start_workout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    if not user or not user.get('program'):
        await update.message.reply_text("Сначала пройди тест: /start")
        return
    program = user['program']
    # Создаём сессию тренировки
    session = WorkoutSession(user_id, program)
    active_workouts[user_id] = session
    # Показываем первое упражнение
    await show_next_exercise(update, context, user_id)

async def show_next_exercise(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    session = active_workouts.get(user_id)
    if not session or session.is_finished():
        return
    ex_info = session.get_current_set_info()
    ex = session.get_current_exercise()
    text = (f"🏋️ {ex['name']}\n"
            f"Подход {ex_info['set_num']} из {ex_info['total_sets']}\n"
            f"Цель: {ex_info['target_reps']} повторений\n"
            f"Вес: {ex_info['weight']} кг\n\n"
            "Выполни подход и напиши количество повторений (число):")
    await update.message.reply_text(text, reply_markup=cancel_keyboard())
    context.user_data['awaiting_set_result'] = True

async def handle_set_result(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    session = active_workouts.get(user_id)
    if not session or not context.user_data.get('awaiting_set_result'):
        await update.message.reply_text("Сейчас нет активной тренировки. Нажми 'Начать тренировку'.")
        return
    try:
        reps = int(update.message.text.strip())
    except:
        await update.message.reply_text("Пожалуйста, введите число повторений.")
        return
    # Регистрируем результат
    session.register_set_result(reps)
    # Проверяем, завершена ли тренировка
    if session.is_finished():
        # Завершаем тренировку
        summary = session.get_summary()
        await update.message.reply_text(summary, reply_markup=main_menu())
        # Сохраняем лог в БД
        save_workout_log(user_id, session.get_log_for_adjustment(), summary)
        # Корректируем программу
        user = get_user(user_id)
        new_program = adjust_program_after_workout(user['program'], session.get_log_for_adjustment())
        save_user(user_id, program=new_program)
        # Удаляем сессию
        del active_workouts[user_id]
        context.user_data['awaiting_set_result'] = False
    else:
        # Следующий подход/упражнение
        await show_next_exercise(update, context, user_id)

async def finish_workout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    session = active_workouts.get(user_id)
    if session:
        summary = session.get_summary()
        await query.edit_message_text(f"⚠️ Тренировка прервана.\n{summary}", reply_markup=main_menu())
        save_workout_log(user_id, session.get_log_for_adjustment(), summary + "(досрочно)")
        # Можно не корректировать программу при досрочном завершении
        del active_workouts[user_id]
        context.user_data['awaiting_set_result'] = False
    else:
        await query.edit_message_text("Нет активной тренировки.", reply_markup=main_menu())

async def cancel_workout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if user_id in active_workouts:
        del active_workouts[user_id]
        context.user_data['awaiting_set_result'] = False
        await query.edit_message_text("Тренировка отменена.", reply_markup=main_menu())
    else:
        await query.edit_message_text("Нет активной тренировки.", reply_markup=main_menu())

async def show_program(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    if not user or not user.get('program'):
        await update.message.reply_text("Программа ещё не подобрана. Пройди тест: /start")
        return
    program = user['program']
    text = "📋 Твоя текущая программа:\n\n"
    for ex in program['exercises']:
        text += f"• {ex['name']}: {ex['sets']} подходов по {ex['reps']} повторений"
        if ex.get('weight'):
            text += f" (вес {ex['weight']} кг)"
        text += "\n"
    await update.message.reply_text(text)

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    # Простейшая статистика: из таблицы workouts берём последние 5 записей
    import sqlite3
    conn = sqlite3.connect("fitness.db")
    c = conn.cursor()
    c.execute("SELECT date, summary FROM workouts WHERE user_id = ? ORDER BY date DESC LIMIT 5", (user_id,))
    rows = c.fetchall()
    conn.close()
    if not rows:
        await update.message.reply_text("Пока нет завершённых тренировок.")
    else:
        text = "📊 Последние тренировки:\n\n"
        for date, summary in rows:
            text += f"{date[:10]}: {summary[:100]}...\n\n"
        await update.message.reply_text(text)

async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Настройки пока в разработке. Для изменения данных пройди /test заново (будет реализовано).")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Помощь:\n"
        "🏋️ Начать тренировку – запустить занятие\n"
        "📋 Моя программа – посмотреть текущие упражнения\n"
        "📊 Статистика – история тренировок\n"
        "⚙️ Настройки – изменить параметры\n"
        "❓ Помощь – это сообщение"
    )