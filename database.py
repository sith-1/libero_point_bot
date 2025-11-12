import json
import os
from datetime import datetime

class RatingDatabase:
    def __init__(self, filename='ratings.json', history_filename='history.json'):
        self.filename = filename
        self.history_filename = history_filename
        self.load_data()
        self.load_history()
    
    def load_data(self):
        if os.path.exists(self.filename):
            with open(self.filename, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
        else:
            self.data = {}
            self.save_data()
    
    def save_data(self):
        with open(self.filename, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
    
    def load_history(self):
        """Загрузить историю изменений рейтинга"""
        if os.path.exists(self.history_filename):
            with open(self.history_filename, 'r', encoding='utf-8') as f:
                self.history = json.load(f)
        else:
            self.history = []
            self.save_history()
    
    def save_history(self):
        """Сохранить историю изменений рейтинга"""
        with open(self.history_filename, 'w', encoding='utf-8') as f:
            json.dump(self.history, f, ensure_ascii=False, indent=2)
    
    def add_history_entry(self, changer_id, target_id, amount, comment=None):
        """Добавить запись в историю изменений"""
        entry = {
            'timestamp': datetime.now().isoformat(),
            'changer_id': str(changer_id),
            'target_id': str(target_id),
            'amount': amount,
            'comment': comment
        }
        self.history.append(entry)
        # Ограничиваем историю последними 1000 записями для производительности
        if len(self.history) > 1000:
            self.history = self.history[-1000:]
        self.save_history()
    
    def get_rating_history(self, user_id, limit=5):
        """Получить историю изменений рейтинга для пользователя"""
        user_id = str(user_id)
        user_history = [entry for entry in self.history if entry['target_id'] == user_id]
        # Сортируем по времени (новые первыми) и ограничиваем лимитом
        user_history.sort(key=lambda x: x['timestamp'], reverse=True)
        return user_history[:limit]
    
    def get_recent_history(self, limit=5):
        """Получить последние изменения рейтинга (новые первыми)"""
        recent = self.history[-limit:] if len(self.history) >= limit else self.history
        # Возвращаем в обратном порядке, чтобы новые были первыми
        return list(reversed(recent))
    
    def get_rating(self, user_id):
        return self.data.get(str(user_id), 0)
    
    def add_rating(self, user_id, amount=1, changer_id=None, comment=None):
        user_id = str(user_id)
        if user_id not in self.data:
            self.data[user_id] = 0
        self.data[user_id] += amount
        self.save_data()
        
        # Добавляем запись в историю
        if changer_id is not None:
            self.add_history_entry(changer_id, user_id, amount, comment)
        
        return self.data[user_id]
    
    def remove_rating(self, user_id, amount=1, changer_id=None, comment=None):
        user_id = str(user_id)
        if user_id not in self.data:
            self.data[user_id] = 0
        self.data[user_id] -= amount
        self.save_data()
        
        # Добавляем запись в историю (с отрицательным значением)
        if changer_id is not None:
            self.add_history_entry(changer_id, user_id, -amount, comment)
        
        return self.data[user_id]
    
    def get_top_users(self, limit=10):
        sorted_users = sorted(self.data.items(), key=lambda x: x[1], reverse=True)
        return sorted_users[:limit]
    
    def get_bottom_users(self, limit=10):
        """Получить пользователей с наименьшим рейтингом (антитоп)"""
        sorted_users = sorted(self.data.items(), key=lambda x: x[1], reverse=False)
        return sorted_users[:limit]
    
    def get_all_users_sorted(self):
        """Получить всех пользователей, отсортированных по рейтингу"""
        return sorted(self.data.items(), key=lambda x: x[1], reverse=True)