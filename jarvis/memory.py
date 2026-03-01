import json
from pathlib import Path
from datetime import datetime
from typing import Any

MEMORY_PATH = Path.home() / ".jarvis" / "memory.json"
MAX_TURNS = 6  # leve


def _ensure_dir():
    MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)


def load_memory() -> dict[str, Any]:
    _ensure_dir()
    if not MEMORY_PATH.exists():
        return {"turns": [], "state": {}}

    try:
        data = json.loads(MEMORY_PATH.read_text(encoding="utf-8"))
        if "turns" not in data or not isinstance(data["turns"], list):
            data["turns"] = []
        if "state" not in data or not isinstance(data["state"], dict):
            data["state"] = {}
        return data
    except Exception:
        return {"turns": [], "state": {}}


def save_memory(data: dict[str, Any]) -> None:
    _ensure_dir()
    MEMORY_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def clear_memory() -> None:
    save_memory({"turns": [], "state": {}})


def add_turn(user_text: str, jarvis_text: str) -> None:
    data = load_memory()
    turns = data.get("turns", [])

    turns.append({
        "ts": datetime.utcnow().isoformat() + "Z",
        "u": (user_text or "").strip()[:500],
        "j": (jarvis_text or "").strip()[:500],
    })

    data["turns"] = turns[-MAX_TURNS:]
    save_memory(data)


def get_state() -> dict[str, Any]:
    return load_memory().get("state", {}) or {}


def set_state(patch: dict[str, Any]) -> None:
    data = load_memory()
    state = data.get("state", {}) or {}
    # merge raso (V1)
    for k, v in (patch or {}).items():
        if v is None:
            continue
        state[k] = v
    data["state"] = state
    save_memory(data)


def build_context(max_turns: int = 3) -> str:
    """
    Contexto compacto: STATE + últimos turns.
    Mantém tokens baixos.
    """
    data = load_memory()
    state = data.get("state", {}) or {}
    turns = (data.get("turns", []) or [])[-max_turns:]

    parts = []

    if state:
        # estado curto, estilo key=value
        lines = ["STATE:"]
        for k, v in state.items():
            lines.append(f"- {k}: {v}")
        parts.append("\n".join(lines))

    if turns:
        lines = ["HISTORY (últimas interações):"]
        for t in turns:
            lines.append(f"- U: {t.get('u','')}")
            lines.append(f"  J: {t.get('j','')}")
        parts.append("\n".join(lines))

    return "\n\n".join(parts).strip()


def should_inject_memory(user_input: str) -> bool:
    s = (user_input or "").strip().lower()
    if not s:
        return False

    followup_markers = [
        "agora", "também", "de novo", "novamente",
        "igual", "mesmo", "isso", "essa", "esse", "aquele",
        "ali", "aí", "ai", "então", "entao", "depois", "em seguida",
        "repete", "repetir",
    ]

    if len(s) <= 40:
        return True

    return any(m in s for m in followup_markers)