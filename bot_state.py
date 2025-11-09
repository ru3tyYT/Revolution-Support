"""
Bot state management for enable/disable features
"""
import json
import os
from typing import Dict

STATE_FILE = "bot_state.json"

def load_state() -> Dict:
    if not os.path.exists(STATE_FILE):
        return {
            "bot": True,
            "autoresponse": True,
            "ocr": True,
            "ask": True,
            "say": True,
            "stats": True,
            "analyze": True,
            "search": True,
            "fix": True,
            "history": True,
            "mark_for_review": True
        }
    
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {
            "bot": True,
            "autoresponse": True,
            "ocr": True,
            "ask": True,
            "say": True,
            "stats": True,
            "analyze": True,
            "search": True,
            "fix": True,
            "history": True,
            "mark_for_review": True
        }

def save_state(state: Dict):
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    os.replace(tmp, STATE_FILE)

def is_enabled(feature: str) -> bool:
    """Check if a feature is enabled"""
    state = load_state()
    return state.get(feature, True)

def enable(feature: str):
    """Enable a feature"""
    state = load_state()
    state[feature] = True
    save_state(state)

def disable(feature: str):
    """Disable a feature"""
    state = load_state()
    state[feature] = False
    save_state(state)

def get_all_states() -> Dict:
    """Get all feature states"""
    return load_state()
