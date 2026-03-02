# jarvis/utils.py
import json

def clean_json(text: str) -> str:
    t = (text or "").strip()
    if t.startswith("```"):
        t = t.replace("```json", "").replace("```", "").strip()
    return t

def safe_load(text: str) -> dict:
    return json.loads(clean_json(text))