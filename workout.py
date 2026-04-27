from typing import List, Dict, Optional

class WorkoutSession:
    def __init__(self, user_id: int, program: Dict):
        self.user_id = user_id
        self.program = program          # {'exercises': [...]}
        self.exercises = program['exercises']
        self.current_ex_index = 0       # индекс текущего упражнения
        self.current_set = 1            # текущий подход (1..sets)
        self.results = []               # список выполненных подходов
        self.completed = False
    
    def get_current_exercise(self) -> Optional[Dict]:
        if self.current_ex_index >= len(self.exercises):
            return None
        return self.exercises[self.current_ex_index]
    
    def get_current_set_info(self) -> Dict:
        ex = self.get_current_exercise()
        if not ex:
            return {}
        return {
            "exercise_name": ex['name'],
            "set_num": self.current_set,
            "total_sets": ex['sets'],
            "target_reps": ex['reps'],
            "weight": ex.get('weight', 0)
        }
    
    def register_set_result(self, reps_done: int, weight_used: Optional[float] = None):
        ex = self.get_current_exercise()
        if not ex:
            return
        # Сохраняем результат подхода
        self.results.append({
            "exercise_name": ex['name'],
            "set_num": self.current_set,
            "target_reps": ex['reps'],
            "reps_done": reps_done,
            "weight_used": weight_used if weight_used is not None else ex.get('weight', 0)
        })
        # Переходим к следующему подходу
        if self.current_set < ex['sets']:
            self.current_set += 1
        else:
            # Упражнение закончено -> следующее
            self.current_ex_index += 1
            self.current_set = 1
    
    def is_finished(self) -> bool:
        return self.current_ex_index >= len(self.exercises)
    
    def get_summary(self) -> str:
        total_sets = len(self.results)
        text = f"✅ Тренировка завершена!\nВыполнено подходов: {total_sets}\n\n"
        for ex_name in set(r['exercise_name'] for r in self.results):
            ex_results = [r for r in self.results if r['exercise_name'] == ex_name]
            text += f"🏋️ {ex_name}:\n"
            for r in ex_results:
                text += f"  Подход {r['set_num']}: {r['reps_done']} повторений (вес {r['weight_used']} кг)\n"
            text += "\n"
        return text
    
    def get_log_for_adjustment(self) -> List[Dict]:
        """Возвращает данные для корректировки программы (trainer.adjust_program_after_workout)"""
        return self.results