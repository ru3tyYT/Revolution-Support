import json
import os
from datetime import datetime, timezone
from typing import Dict, List

HISTORY_FILE = "bot_history.json"

def load_history() -> List[Dict]:
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def save_history(history: List[Dict]):
    tmp = HISTORY_FILE + ".tmp"
    history = history[-1000:]
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)
    os.replace(tmp, HISTORY_FILE)

def log_action(action_type: str, user: str, details: str, channel: str = None):
    history = load_history()
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action_type": action_type,
        "user": user,
        "channel": channel,
        "details": details
    }
    history.append(entry)
    save_history(history)

def get_recent_history(limit: int = 50) -> List[Dict]:
    history = load_history()
    return history[-limit:]

def get_history_by_type(action_type: str, limit: int = 50) -> List[Dict]:
    history = load_history()
    filtered = [h for h in history if h.get("action_type") == action_type]
    return filtered[-limit:]

def get_history_by_user(user: str, limit: int = 50) -> List[Dict]:
    history = load_history()
    filtered = [h for h in history if h.get("user") == user]
    return filtered[-limit:]
