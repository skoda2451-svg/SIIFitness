from typing import Dict, List

def generate_program_from_test(test_data: Dict) -> Dict:
    """
    test_data: {'age':..., 'weight':..., 'level':..., 'goal':..., 'equipment':...}
    Возвращает: {
        'exercises': [
            {'name': 'Приседания со штангой', 'sets': 4, 'reps': 10, 'weight': 30},
            ...
        ],
        'version': 1
    }
    """
    goal = test_data.get('goal', 'mass')          # 'mass' или 'functional'
    level = test_data.get('level', 'beginner')    # 'beginner', 'intermediate', 'advanced'
    equipment = test_data.get('equipment', ['barbell', 'pullup_bar', 'dips_bar'])
    
    # Базовая программа для массы
    if goal == 'mass':
        exercises = [
            {"name": "Приседания со штангой", "sets": 3, "reps": 8, "weight": 25},
            {"name": "Жим штанги лёжа", "sets": 3, "reps": 8, "weight": 20},
            {"name": "Тяга штанги в наклоне", "sets": 3, "reps": 8, "weight": 20},
            {"name": "Подтягивания (турник)", "sets": 3, "reps": 5, "weight": 0},
            {"name": "Отжимания на брусьях", "sets": 3, "reps": 6, "weight": 0},
        ]
    else:  # функционал
        exercises = [
            {"name": "Подтягивания широким хватом", "sets": 4, "reps": 6, "weight": 0},
            {"name": "Отжимания на брусьях с весом тела", "sets": 4, "reps": 8, "weight": 0},
            {"name": "Бёрпи", "sets": 3, "reps": 10, "weight": 0},
            {"name": "Выпады с собственным весом", "sets": 3, "reps": 12, "weight": 0},
            {"name": "Планка", "sets": 3, "reps": 30, "unit": "sec", "weight": 0},
        ]
    
    # Корректировка по уровню
    if level == 'beginner':
        for ex in exercises:
            ex['sets'] = max(2, ex['sets'] - 1)
            ex['reps'] = max(5, ex['reps'] - 2)
    elif level == 'advanced':
        for ex in exercises:
            ex['sets'] += 1
            ex['reps'] = int(ex['reps'] * 1.2)
            if 'weight' in ex and ex['weight'] > 0:
                ex['weight'] = int(ex['weight'] * 1.3)
    
    # Проверка оборудования
    if 'barbell' not in equipment:
        exercises = [ex for ex in exercises if 'штанга' not in ex['name'].lower()]
    if 'pullup_bar' not in equipment:
        exercises = [ex for ex in exercises if 'турник' not in ex['name'].lower()]
    if 'dips_bar' not in equipment:
        exercises = [ex for ex in exercises if 'брусья' not in ex['name'].lower()]
    
    return {"exercises": exercises, "version": 1}

def adjust_program_after_workout(old_program: Dict, workout_log: List[Dict]) -> Dict:
    """
    workout_log: список выполненных упражнений с подходами (результаты)
    Каждый подход: {'exercise_name':..., 'set_num':..., 'reps_done':..., 'weight_used':...}
    """
    new_exercises = []
    for ex_template in old_program['exercises']:
        # Находим выполненное упражнение в логе
        performed = [w for w in workout_log if w['exercise_name'] == ex_template['name']]
        if not performed:
            # Пропускаем, если не выполнялось (не должно случиться)
            new_exercises.append(ex_template.copy())
            continue
        
        # Простая прогрессия: если во всех подходах выполнено >= целевых повторений -> увеличиваем нагрузку
        all_completed = all(p['reps_done'] >= ex_template['reps'] for p in performed)
        if all_completed:
            # Увеличиваем вес или повторения
            if ex_template['weight'] > 0:
                ex_template['weight'] = min(ex_template['weight'] + 2.5, 100)  # шаг 2.5 кг
            else:
                ex_template['reps'] = min(ex_template['reps'] + 1, 20)
        else:
            # Не выполнил – можно снизить вес или оставить как есть
            if ex_template['weight'] > 5:
                ex_template['weight'] = max(ex_template['weight'] - 2.5, 0)
        
        new_exercises.append(ex_template)
    
    return {"exercises": new_exercises, "version": old_program.get('version', 1) + 1}