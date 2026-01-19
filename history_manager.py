import json
import os
import datetime
import logging

class HistoryManager:
    def __init__(self, filename="history.json"):
        # Save in the same directory as the executable or script
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.filepath = os.path.join(base_dir, filename)
        self._ensure_file()

    def _ensure_file(self):
        if not os.path.exists(self.filepath):
            try:
                with open(self.filepath, 'w', encoding='utf-8') as f:
                    json.dump([], f)
            except Exception as e:
                logging.error(f"Failed to init history file: {e}")

    def add_entry(self, text, duration_str=""):
        if not text.strip():
            return

        entry = {
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "text": text,
            "duration": duration_str
        }

        history = self.get_history()
        history.insert(0, entry) # Add to top

        try:
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
        except Exception as e:
             logging.error(f"Failed to save history: {e}")

    def get_history(self):
        try:
            if os.path.exists(self.filepath):
                with open(self.filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logging.error(f"Failed to load history: {e}")
        return []

    def clear(self):
        try:
             with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump([], f)
        except Exception as e:
            logging.error(f"Failed to clear history: {e}")
