from telegram import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup

# Главное меню (ReplyKeyboard)
def main_menu():
    buttons = [
        [KeyboardButton("🏋️ Начать тренировку")],
        [KeyboardButton("📋 Моя программа"), KeyboardButton("📊 Статистика")],
        [KeyboardButton("⚙️ Настройки"), KeyboardButton("❓ Помощь")]
    ]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

# Inline-клавиатура для теста
def test_question(question_text, options):
    keyboard = []
    for opt in options:
        keyboard.append([InlineKeyboardButton(opt, callback_data=f"test_{opt}")])
    return InlineKeyboardMarkup(keyboard)

# Inline-клавиатура во время тренировки (после показа подхода)
def workout_set_keyboard():
    keyboard = [
        [InlineKeyboardButton("✅ Выполнил", callback_data="set_done")],
        [InlineKeyboardButton("❌ Завершить тренировку", callback_data="finish_workout")]
    ]
    return InlineKeyboardMarkup(keyboard)

# Клавиатура для ввода результата (можно запросить текстом, но удобнее inline-запрос)
# Для простоты используем обычный текст: пользователь пишет число повторений.

def cancel_keyboard():
    keyboard = [[InlineKeyboardButton("❌ Отмена", callback_data="cancel_workout")]]
    return InlineKeyboardMarkup(keyboard)