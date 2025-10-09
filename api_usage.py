import json
import os
from datetime import datetime, timezone
from typing import Dict

USAGE_FILE = "api_usage.json"

# Gemini API pricing (as of 2024)
COST_PER_1K_INPUT = 0.000125
COST_PER_1K_OUTPUT = 0.000375

def load_usage() -> Dict:
    if not os.path.exists(USAGE_FILE):
        return {
            "total_requests": 0,
            "total_input_chars": 0,
            "total_output_chars": 0,
            "total_cost": 0.0,
            "daily": {},
            "monthly": {}
        }
    
    try:
        with open(USAGE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {
            "total_requests": 0,
            "total_input_chars": 0,
            "total_output_chars": 0,
            "total_cost": 0.0,
            "daily": {},
            "monthly": {}
        }

def save_usage(usage: Dict):
    tmp = USAGE_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(usage, f, ensure_ascii=False, indent=2)
    os.replace(tmp, USAGE_FILE)

def track_request(input_text: str, output_text: str):
    usage = load_usage()
    
    input_chars = len(input_text)
    output_chars = len(output_text)
    input_cost = (input_chars / 1000) * COST_PER_1K_INPUT
    output_cost = (output_chars / 1000) * COST_PER_1K_OUTPUT
    total_cost = input_cost + output_cost
    
    usage["total_requests"] += 1
    usage["total_input_chars"] += input_chars
    usage["total_output_chars"] += output_chars
    usage["total_cost"] += total_cost
    
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if today not in usage["daily"]:
        usage["daily"][today] = {
            "requests": 0,
            "input_chars": 0,
            "output_chars": 0,
            "cost": 0.0
        }
    
    usage["daily"][today]["requests"] += 1
    usage["daily"][today]["input_chars"] += input_chars
    usage["daily"][today]["output_chars"] += output_chars
    usage["daily"][today]["cost"] += total_cost
    
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    if month not in usage["monthly"]:
        usage["monthly"][month] = {
            "requests": 0,
            "input_chars": 0,
            "output_chars": 0,
            "cost": 0.0
        }
    
    usage["monthly"][month]["requests"] += 1
    usage["monthly"][month]["input_chars"] += input_chars
    usage["monthly"][month]["output_chars"] += output_chars
    usage["monthly"][month]["cost"] += total_cost
    
    save_usage(usage)
    return total_cost

def get_today_stats() -> Dict:
    usage = load_usage()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return usage["daily"].get(today, {
        "requests": 0,
        "input_chars": 0,
        "output_chars": 0,
        "cost": 0.0
    })

def get_month_stats() -> Dict:
    usage = load_usage()
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    return usage["monthly"].get(month, {
        "requests": 0,
        "input_chars": 0,
        "output_chars": 0,
        "cost": 0.0
    })

def estimate_monthly_cost() -> float:
    today_stats = get_today_stats()
    if today_stats["cost"] == 0:
        return 0.0
    
    now = datetime.now(timezone.utc)
    day_of_month = now.day
    days_in_month = 30
    
    avg_daily_cost = today_stats["cost"]
    estimated_monthly = avg_daily_cost * days_in_month
    
    return estimated_monthly
