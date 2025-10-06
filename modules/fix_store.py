# modules/fix_store.py
"""
Safe atomic read/write for fixes.json and helpers.
"""
import json
import os
from datetime import datetime, timezone
from uuid import uuid4
from typing import List, Dict, Optional

FIXES_FILE = "fixes.json"

def load_fixes() -> List[Dict]:
    if not os.path.exists(FIXES_FILE):
        return []
    with open(FIXES_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception:
            return []

def save_fixes(fixes: List[Dict]):
    tmp = FIXES_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(fixes, f, ensure_ascii=False, indent=2)
    os.replace(tmp, FIXES_FILE)

def add_fix(source: str, thread_id: Optional[str], thread_name: Optional[str],
            problem_summary: str, fix_text: str, confidence: Optional[float]=None,
            language: Optional[str]=None, tags: Optional[List[str]]=None,
            attachments: Optional[List[str]]=None) -> Dict:
    fixes = load_fixes()
    entry = {
        "id": str(uuid4()),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": source,
        "thread_id": thread_id,
        "thread_name": thread_name,
        "problem_summary": problem_summary,
        "fix": fix_text,
        "confidence": confidence,
        "language": language,
        "tags": tags or [],
        "attachments": attachments or [],
        "version": 1
    }
    fixes.append(entry)
    save_fixes(fixes)
    return entry

def get_similar_fixes(query: str, k: int = 5):
    """
    Simple similarity: substring match in title or tags.
    Returns up to k fix entries.
    """
    fixes = load_fixes()
    results = []
    ql = query.lower()
    for f in fixes:
        title = (f.get("thread_name") or "").lower()
        tags = " ".join(f.get("tags") or []).lower()
        if ql in title or any(ql in t for t in tags.split()):
            results.append(f)
        if len(results) >= k:
            break
    return results[:k]
