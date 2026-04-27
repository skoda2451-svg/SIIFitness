import sqlite3
import json
from typing import Dict, List, Optional, Any

DB_NAME = "fitness.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Пользователи: основные данные + результат теста (JSON)
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        name TEXT,
        test_data TEXT,          -- JSON с ответами на тест
        program TEXT,            -- JSON с текущей программой тренировок
        last_workout TEXT,       -- дата последней тренировки
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Логи тренировок (для анализа и прогресса)
    c.execute('''CREATE TABLE IF NOT EXISTS workouts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        exercises TEXT,          -- JSON: список упражнений с выполненными подходами
        summary TEXT             -- текстовая сводка
    )''')
    
    conn.commit()
    conn.close()

def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT user_id, name, test_data, program FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {
            "user_id": row[0],
            "name": row[1],
            "test_data": json.loads(row[2]) if row[2] else None,
            "program": json.loads(row[3]) if row[3] else None,
        }
    return None

def save_user(user_id: int, name: str = None, test_data: Dict = None, program: Dict = None):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Проверяем, существует ли пользователь
    c.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    exists = c.fetchone()
    if exists:
        updates = []
        params = []
        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if test_data is not None:
            updates.append("test_data = ?")
            params.append(json.dumps(test_data))
        if program is not None:
            updates.append("program = ?")
            params.append(json.dumps(program))
        if updates:
            sql = f"UPDATE users SET {', '.join(updates)} WHERE user_id = ?"
            params.append(user_id)
            c.execute(sql, params)
    else:
        c.execute("INSERT INTO users (user_id, name, test_data, program) VALUES (?, ?, ?, ?)",
                  (user_id, name, json.dumps(test_data) if test_data else None, json.dumps(program) if program else None))
    conn.commit()
    conn.close()

def save_workout_log(user_id: int, exercises: List[Dict], summary: str):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO workouts (user_id, exercises, summary) VALUES (?, ?, ?)",
              (user_id, json.dumps(exercises), summary))
    conn.commit()
    conn.close()