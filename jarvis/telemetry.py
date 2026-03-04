import json
import os
import uuid
from pathlib import Path
from datetime import datetime, date

LOGS_DIR = Path.home() / ".jarvis" / "logs"
LOG_PATH = LOGS_DIR / "telemetry.jsonl"
METRICS_PATH = Path.home() / ".jarvis" / "metrics.json"

DEBUG = os.getenv("JARVIS_DEBUG", "0") == "1"


def _safe_input(s: str) -> str:
    """Mascara user_input se contiver credenciais/tokens antes de gravar no log."""
    try:
        from .security import redact
        return redact(s)
    except Exception:
        return s

def _ensure():
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)

def log_event(event: str, data: dict):
    _ensure()
    row = {
        "ts": datetime.utcnow().isoformat() + "Z",
        "event": event,
        "data": data or {},
    }
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")

def add_token_usage(model: str, prompt: int, completion: int, total: int):
    _ensure()
    try:
        metrics = json.loads(METRICS_PATH.read_text(encoding="utf-8")) if METRICS_PATH.exists() else {}
    except Exception:
        metrics = {}

    metrics.setdefault("by_model", {})
    m = metrics["by_model"].setdefault(model, {"prompt": 0, "completion": 0, "total": 0})
    m["prompt"] += int(prompt or 0)
    m["completion"] += int(completion or 0)
    m["total"] += int(total or 0)

    metrics.setdefault("total", {"prompt": 0, "completion": 0, "total": 0})
    metrics["total"]["prompt"] += int(prompt or 0)
    metrics["total"]["completion"] += int(completion or 0)
    metrics["total"]["total"] += int(total or 0)

    METRICS_PATH.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")


# ─── Debug Log (JARVIS_DEBUG=1) ────────────────────────────────────────────────

_debug_entry: dict | None = None


def _debug_log_path() -> Path:
    return LOGS_DIR / f"debug-{date.today().isoformat()}.jsonl"


def start_debug_entry(user_input: str, mode: str) -> None:
    global _debug_entry
    if not DEBUG:
        return
    _debug_entry = {
        "ts": datetime.utcnow().isoformat() + "Z",
        "request_id": uuid.uuid4().hex[:8],
        "user_input": _safe_input(user_input),
        "mode": mode,
        "route": None,
        "route_forced": False,
        "memory_injected": False,
        "llm_calls": [],
        "plan": None,
        "execution": [],
        "response": None,
        "total_ms": None,
        "total_tokens": 0,
    }


def debug_set(key: str, value) -> None:
    if not DEBUG or _debug_entry is None:
        return
    _debug_entry[key] = value


def debug_append(key: str, item: dict) -> None:
    if not DEBUG or _debug_entry is None:
        return
    lst = _debug_entry.get(key)
    if isinstance(lst, list):
        lst.append(item)


def flush_debug_entry(response: str, total_ms: int) -> None:
    global _debug_entry
    if not DEBUG or _debug_entry is None:
        return
    _debug_entry["response"] = response
    _debug_entry["total_ms"] = total_ms
    _debug_entry["total_tokens"] = sum(
        c.get("total_tokens", 0) for c in _debug_entry.get("llm_calls", [])
    )
    _ensure()
    with _debug_log_path().open("a", encoding="utf-8") as f:
        f.write(json.dumps(_debug_entry, ensure_ascii=False) + "\n")
    _debug_entry = None