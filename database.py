import json
import os

class RatingDatabase:
    def __init__(self, filename='ratings.json'):
        self.filename = filename
        self.load_data()
    
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
    
    def get_rating(self, user_id):
        return self.data.get(str(user_id), 0)
    
    def add_rating(self, user_id, amount=1):
        user_id = str(user_id)
        if user_id not in self.data:
            self.data[user_id] = 0
        self.data[user_id] += amount
        self.save_data()
        return self.data[user_id]
    
    def remove_rating(self, user_id, amount=1):
        user_id = str(user_id)
        if user_id not in self.data:
            self.data[user_id] = 0
        self.data[user_id] -= amount
        self.save_data()
        return self.data[user_id]
    
    def get_top_users(self, limit=10):
        sorted_users = sorted(self.data.items(), key=lambda x: x[1], reverse=True)
        return sorted_users[:limit]