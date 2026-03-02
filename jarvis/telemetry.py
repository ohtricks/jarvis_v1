import json
from pathlib import Path
from datetime import datetime

LOG_PATH = Path.home() / ".jarvis" / "logs" / "telemetry.jsonl"
METRICS_PATH = Path.home() / ".jarvis" / "metrics.json"

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