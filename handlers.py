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
from keyboards import main_menu, cancel_keyboard

# Состояния для теста
ASK_NAME, ASK_AGE, ASK_WEIGHT, ASK_LEVEL, ASK_GOAL, ASK_EQUIPMENT = range(6)

active_workouts = {}
logging.basicConfig(level=logging.INFO)

# --- Тест (ConversationHandler) ---
async def test_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я твой виртуальный фитнес тренер. Я буду помогать тебе с тренировками.\n"
        "Для начала давай познакомимся. Как тебя зовут?"
    )
    return ASK_NAME

async def test_get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['name'] = update.message.text
    await update.message.reply_text("Сколько тебе лет? (число)")
    return ASK_AGE

async def test_get_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        age = int(update.message.text)
        context.user_data['age'] = age
    except:
        await update.message.reply_text("Пожалуйста, введи число. Сколько тебе лет?")
        return ASK_AGE
    await update.message.reply_text("Какой твой вес (в кг)?")
    return ASK_WEIGHT

async def test_get_weight(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        weight = float(update.message.text)
        context.user_data['weight'] = weight
    except:
        await update.message.reply_text("Введи число. Вес в кг?")
        return ASK_WEIGHT
    await update.message.reply_text(
        "Каков твой уровень подготовки?\n"
        "1 - Начинающий\n2 - Средний\n3 - Продвинутый"
    )
    return ASK_LEVEL

async def test_get_level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    level_map = {"1": "beginner", "2": "intermediate", "3": "advanced"}
    level = level_map.get(update.message.text.strip(), "beginner")
    context.user_data['level'] = level
    await update.message.reply_text(
        "Какова твоя цель?\n1 - Набор массы\n2 - Функциональная подготовка"
    )
    return ASK_GOAL

async def test_get_goal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    goal_map = {"1": "mass", "2": "functional"}
    goal = goal_map.get(update.message.text.strip(), "mass")
    context.user_data['goal'] = goal
    await update.message.reply_text(
        "Какое оборудование доступно?\nОтправь номера через пробел (например: 1 2 3):\n"
        "1 - Штанга 25 кг\n2 - Турник\n3 - Брусья",
        reply_markup=ReplyKeyboardRemove()
    )
    return ASK_EQUIPMENT

async def test_get_equipment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nums = update.message.text.split()
    equipment = []
    if "1" in nums: equipment.append("barbell")
    if "2" in nums: equipment.append("pullup_bar")
    if "3" in nums: equipment.append("dips_bar")
    if not equipment:
        equipment = ["barbell", "pullup_bar", "dips_bar"]
    context.user_data['equipment'] = equipment
    # Сохраняем в БД
    user_id = update.effective_user.id
    save_user(user_id, name=context.user_data['name'], test_data=context.user_data)
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

# --- Основное меню ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    if user and user.get('test_data'):
        await update.message.reply_text(
            f"С возвращением, {user['name']}! Выбери действие:",
            reply_markup=main_menu()
        )
    else:
        # Запускаем тест
        await test_start(update, context)
        return ASK_NAME

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

# --- Тренировка ---
async def start_workout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    if not user or not user.get('program'):
        await update.message.reply_text("Сначала пройди тест через /start")
        return
    program = user['program']
    session = WorkoutSession(user_id, program)
    active_workouts[user_id] = session
    await show_next_exercise(update, context, user_id)

async def show_next_exercise(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    session = active_workouts.get(user_id)
    if not session or session.is_finished():
        return
    info = session.get_current_set_info()
    await update.message.reply_text(
        f"🏋️ {info['exercise_name']}\n"
        f"Подход {info['set_num']} из {info['total_sets']}\n"
        f"Цель: {info['target_reps']} повторений\n"
        f"Вес: {info['weight']} кг\n\n"
        "Выполни подход и напиши количество повторений (число):",
        reply_markup=cancel_keyboard()
    )
    context.user_data['awaiting_set'] = True

async def handle_set_result(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    session = active_workouts.get(user_id)
    if not session or not context.user_data.get('awaiting_set'):
        await update.message.reply_text("Нет активной тренировки. Нажми 'Начать тренировку'.")
        return
    try:
        reps = int(update.message.text.strip())
    except:
        await update.message.reply_text("Введите число повторений.")
        return
    session.register_set_result(reps)
    if session.is_finished():
        summary = session.get_summary()
        await update.message.reply_text(summary, reply_markup=main_menu())
        save_workout_log(user_id, session.get_log_for_adjustment(), summary)
        user = get_user(user_id)
        new_program = adjust_program_after_workout(user['program'], session.get_log_for_adjustment())
        save_user(user_id, program=new_program)
        del active_workouts[user_id]
        context.user_data['awaiting_set'] = False
    else:
        await show_next_exercise(update, context, user_id)

async def finish_workout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if user_id in active_workouts:
        session = active_workouts[user_id]
        summary = session.get_summary()
        await query.edit_message_text(f"⚠️ Тренировка прервана.\n{summary}", reply_markup=main_menu())
        save_workout_log(user_id, session.get_log_for_adjustment(), summary + " (досрочно)")
        del active_workouts[user_id]
        context.user_data['awaiting_set'] = False
    else:
        await query.edit_message_text("Нет активной тренировки.", reply_markup=main_menu())

async def cancel_workout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if user_id in active_workouts:
        del active_workouts[user_id]
        context.user_data['awaiting_set'] = False
        await query.edit_message_text("Тренировка отменена.", reply_markup=main_menu())
    else:
        await query.edit_message_text("Нет активной тренировки.", reply_markup=main_menu())

# --- Вспомогательные функции ---
async def show_program(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    if not user or not user.get('program'):
        await update.message.reply_text("Программа не подобрана. Пройди тест: /start")
        return
    program = user['program']
    text = "📋 Твоя программа:\n\n"
    for ex in program['exercises']:
        text += f"• {ex['name']}: {ex['sets']} х {ex['reps']}"
        if ex.get('weight'):
            text += f" (вес {ex['weight']} кг)"
        text += "\n"
    await update.message.reply_text(text)

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    import sqlite3
    conn = sqlite3.connect("fitness.db")
    c = conn.cursor()
    c.execute("SELECT date, summary FROM workouts WHERE user_id = ? ORDER BY date DESC LIMIT 5", (update.effective_user.id,))
    rows = c.fetchall()
    conn.close()
    if not rows:
        await update.message.reply_text("Нет завершённых тренировок.")
    else:
        text = "📊 Последние тренировки:\n\n"
        for date, summary in rows:
            text += f"{date[:10]}: {summary[:80]}...\n\n"
        await update.message.reply_text(text)

async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Настройки в разработке. Для сброса данных напишите /start заново.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Помощь:\n"
        "🏋️ Начать тренировку – запустить занятие\n"
        "📋 Моя программа – посмотреть упражнения\n"
        "📊 Статистика – история тренировок\n"
        "⚙️ Настройки – изменить данные\n"
        "❓ Помощь – это сообщение"
    )