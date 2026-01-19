import json
import os

CONFIG_FILE = "config.json"

DEFAULT_CONFIG = {
    "app_name": "HelpMyToAnswer",
    "whisper_model": "base",
    "device": "auto",  # options: "auto", "cpu", "cuda"
    "use_ollama": true,
    "ollama_model": "llama3",
    "hotkey": "ctrl+alt+r"
}

def load_config():
    if not os.path.exists(CONFIG_FILE):
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG
    
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
            # Merge with default to ensure all keys exist
            for key, value in DEFAULT_CONFIG.items():
                if key not in config:
                    config[key] = value
            return config
    except Exception as e:
        print(f"Error loading config: {e}")
        return DEFAULT_CONFIG

def save_config(config):
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        print(f"Error saving config: {e}")
