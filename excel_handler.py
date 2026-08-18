import json
import os
from datetime import datetime

DATA_DIR = 'data'
PROBLEMATIC_FILE = os.path.join(DATA_DIR, 'problematic_items.json')
FUTURE_CREATION_FILE = os.path.join(DATA_DIR, 'future_creation.json')
SESSION_FILE = os.path.join(DATA_DIR, 'current_batch_session.json')


class ExcelHandler:
    def __init__(self):
        os.makedirs(DATA_DIR, exist_ok=True)

    def _load_json(self, filepath):
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if not content:
                        return []
                    return json.loads(content)
            except Exception:
                return []
        return []

    def _save_json(self, filepath, data):
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # --- مدیریت آیتم‌های مشکل‌دار ---
    def get_problematic(self):
        return self._load_json(PROBLEMATIC_FILE)

    def add_problematic(self, item):
        items = self.get_problematic()
        item['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        items.append(item)
        self._save_json(PROBLEMATIC_FILE, items)

    def remove_problematic(self, index):
        items = self.get_problematic()
        if 0 <= index < len(items):
            items.pop(index)
            self._save_json(PROBLEMATIC_FILE, items)
            return True
        return False

    def clear_problematic(self):
        self._save_json(PROBLEMATIC_FILE, [])

    # --- مدیریت آیتم‌های ایجاد در آینده ---
    def get_future(self):
        return self._load_json(FUTURE_CREATION_FILE)

    def add_future(self, item):
        items = self.get_future()
        item['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        items.append(item)
        self._save_json(FUTURE_CREATION_FILE, items)

    def remove_future(self, index):
        items = self.get_future()
        if 0 <= index < len(items):
            items.pop(index)
            self._save_json(FUTURE_CREATION_FILE, items)
            return True
        return False

    def clear_future(self):
        self._save_json(FUTURE_CREATION_FILE, [])

    # --- مدیریت Session فعلی ---
    def save_session(self, session_data):
        self._save_json(SESSION_FILE, session_data)

    def load_session(self):
        return self._load_json(SESSION_FILE)

    def clear_session(self):
        if os.path.exists(SESSION_FILE):
            os.remove(SESSION_FILE)