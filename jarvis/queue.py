import json
from pathlib import Path
from datetime import datetime
from typing import Any, Optional, Tuple

QUEUE_PATH = Path.home() / ".jarvis" / "queue.json"


def _ensure_dir():
    QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)


def _default() -> dict[str, Any]:
    return {
        "goal": None,
        "items": [],  # list[dict]
    }


def load_queue() -> dict[str, Any]:
    _ensure_dir()
    if not QUEUE_PATH.exists():
        return _default()
    try:
        data = json.loads(QUEUE_PATH.read_text(encoding="utf-8"))
        if not isinstance(data.get("items"), list):
            data["items"] = []
        if "goal" not in data:
            data["goal"] = None
        return data
    except Exception:
        return _default()


def save_queue(q: dict[str, Any]) -> None:
    _ensure_dir()
    QUEUE_PATH.write_text(json.dumps(q, ensure_ascii=False, indent=2), encoding="utf-8")


def clear_queue() -> None:
    save_queue(_default())


def enqueue_plan(goal: str, plan: list[dict]) -> None:
    q = _default()
    q["goal"] = (goal or "").strip() or None
    now = datetime.utcnow().isoformat() + "Z"

    items = []
    for i, step in enumerate(plan or []):
        action = step.get("action")
        if not action:
            continue
        args = {k: v for k, v in step.items() if k not in ("step", "action")}
        items.append({
            "id": f"a_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{i+1}",
            "ts": now,
            "step_index": i,
            "step": step.get("step") or action,
            "status": "pending",  # pending|running|blocked|done|failed|skipped
            "action": action,
            "args": args,
            "risk": None,
            "result": None,
            "error": None,
        })

    q["items"] = items
    save_queue(q)


def get_goal() -> Optional[str]:
    return load_queue().get("goal")


def list_items() -> list[dict]:
    return load_queue().get("items", []) or []


def next_pending() -> Tuple[Optional[dict], int]:
    items = list_items()
    for idx, it in enumerate(items):
        if it.get("status") == "pending":
            return it, idx
    return None, -1


def first_blocked() -> Tuple[Optional[dict], int]:
    items = list_items()
    for idx, it in enumerate(items):
        if it.get("status") == "blocked":
            return it, idx
    return None, -1


def set_item(idx: int, patch: dict) -> None:
    q = load_queue()
    items = q.get("items", []) or []
    if idx < 0 or idx >= len(items):
        return
    it = items[idx]
    for k, v in patch.items():
        it[k] = v
    items[idx] = it
    q["items"] = items
    save_queue(q)


def mark_done(idx: int, result: str) -> None:
    set_item(idx, {"status": "done", "result": result, "error": None})


def mark_failed(idx: int, error: str) -> None:
    set_item(idx, {"status": "failed", "error": error})


def mark_skipped(idx: int, note: str = "Cancelado.") -> None:
    set_item(idx, {"status": "skipped", "error": note})


def mark_blocked(idx: int, risk: str, note: str) -> None:
    set_item(idx, {"status": "blocked", "risk": risk, "error": note})


def mark_running(idx: int) -> None:
    set_item(idx, {"status": "running"})


def has_active_queue() -> bool:
    items = list_items()
    return any(it.get("status") in ("pending", "running", "blocked") for it in items)


def format_queue_status() -> str:
    q = load_queue()
    goal = q.get("goal")
    items = q.get("items", []) or []

    if not items:
        return "Não há fila ativa."

    done = sum(1 for i in items if i.get("status") in ("done", "skipped"))
    total = len(items)

    lines = []
    if goal:
        lines.append(f"Objetivo (queue): {goal}")
    lines.append(f"Progresso (queue): {done}/{total}")
    lines.append("Itens:")

    for i, it in enumerate(items):
        st = it.get("status")
        step = it.get("step") or it.get("action") or ""
        if st == "done":
            prefix = "✅"
        elif st == "blocked":
            prefix = "⚠️"
        elif st == "pending":
            prefix = "•"
        elif st == "running":
            prefix = "⏳"
        elif st == "failed":
            prefix = "❌"
        elif st == "skipped":
            prefix = "⏭️"
        else:
            prefix = "•"
        lines.append(f"{prefix} [{i+1}] {step} ({it.get('action')})")

    return "\n".join(lines).strip()