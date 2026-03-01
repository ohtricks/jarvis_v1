import json
import os
from pathlib import Path
from datetime import datetime
from typing import Any


MEMORY_PATH = Path.home() / ".jarvis" / "memory.json"
MAX_TURNS = 6  # mantém leve


def _ensure_dir():
    MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)


def load_memory() -> dict[str, Any]:
    _ensure_dir()
    if not MEMORY_PATH.exists():
        return {"turns": []}

    try:
        data = json.loads(MEMORY_PATH.read_text(encoding="utf-8"))
        if "turns" not in data or not isinstance(data["turns"], list):
            return {"turns": []}
        return data
    except Exception:
        return {"turns": []}


def save_memory(data: dict[str, Any]) -> None:
    _ensure_dir()
    MEMORY_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def clear_memory() -> None:
    save_memory({"turns": []})


def add_turn(user_text: str, jarvis_text: str) -> None:
    data = load_memory()
    turns = data.get("turns", [])

    turns.append({
        "ts": datetime.utcnow().isoformat() + "Z",
        "u": (user_text or "").strip()[:500],
        "j": (jarvis_text or "").strip()[:500],
    })

    # mantém só os últimos N
    turns = turns[-MAX_TURNS:]
    data["turns"] = turns
    save_memory(data)


def build_context(max_turns: int = 4) -> str:
    """
    Contexto compacto e barato (para injetar no executor).
    """
    data = load_memory()
    turns = data.get("turns", [])[-max_turns:]

    if not turns:
        return ""

    lines = ["MEMORY (últimas interações):"]
    for t in turns:
        u = t.get("u", "")
        j = t.get("j", "")
        # bem curto, para não gastar tokens
        lines.append(f"- U: {u}")
        lines.append(f"  J: {j}")

    return "\n".join(lines)


def should_inject_memory(user_input: str) -> bool:
    """
    Só injeta memória quando a frase parece follow-up / referência.
    Mantém custo baixo.
    """
    s = (user_input or "").strip().lower()
    if not s:
        return False

    followup_markers = [
        "agora", "também", "de novo", "novamente",
        "igual", "mesmo", "isso", "essa", "esse", "aquele",
        "ali", "aí", "então", "depois", "em seguida",
        "tambem",  # sem acento
    ]

    # se for muito curto, é comum ser follow-up
    if len(s) <= 40:
        return True

    return any(m in s for m in followup_markers)