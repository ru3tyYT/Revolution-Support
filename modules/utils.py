# modules/utils.py
import re

def sanitize_logs(text: str) -> str:
    # Basic sanitization: redact long tokens and IPs
    text = re.sub(r"\b[A-Za-z0-9_\-]{40,}\b", "[REDACTED_TOKEN]", text)
    text = re.sub(r"\b\d{1,3}(?:\.\d{1,3}){3}\b", "[REDACTED_IP]", text)
    return text

def extract_key_log_lines(text: str, max_lines: int = 300) -> str:
    lines = text.splitlines()
    # prefer lines containing keywords
    keywords = ("ERROR","Exception","Traceback","failed","panic")
    key_lines = [l for l in lines if any(k in l for k in keywords)]
    if not key_lines:
        # fallback: last max_lines lines
        return "\n".join(lines[-max_lines:])
    if len(key_lines) > max_lines:
        return "\n".join(key_lines[-max_lines:])
    return "\n".join(key_lines)

def confidence_heuristic(text: str) -> float:
    # very simple heuristic
    lowered = text.lower()
    if any(p in lowered for p in ("i think", "possibly", "maybe", "not sure", "uncertain")):
        return 0.35
    if "confidence" in lowered:
        return 0.9
    return 0.7
