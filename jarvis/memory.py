import json
from pathlib import Path
from datetime import datetime
from typing import Any

MEMORY_PATH = Path.home() / ".jarvis" / "memory.json"
MAX_TURNS = 6  # leve


# ===============================
# BASE IO
# ===============================

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
    MEMORY_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def clear_memory() -> None:
    save_memory({"turns": [], "state": {}})


# ===============================
# TURNS (chat history)
# ===============================

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


# ===============================
# STATE
# ===============================

def get_state() -> dict[str, Any]:
    return load_memory().get("state", {}) or {}


def set_state(patch: dict[str, Any]) -> None:
    data = load_memory()
    state = data.get("state", {}) or {}

    for k, v in (patch or {}).items():
        if v is None:
            continue
        state[k] = v

    data["state"] = state
    save_memory(data)


# ===============================
# ACTIVE GOAL MEMORY
# ===============================

def set_goal(goal: str | None) -> None:
    if not goal:
        return
    set_state({"current_goal": goal.strip()[:200]})


def get_goal() -> str:
    return str(get_state().get("current_goal") or "")


def set_active_plan(plan: list[dict], goal: str | None = None) -> None:
    """
    Salva plano ativo com índice inicial.
    """
    patch = {
        "active_plan": plan,
        "active_plan_index": 0,
    }
    if goal:
        patch["current_goal"] = goal.strip()[:200]

    set_state(patch)


def get_active_plan() -> tuple[list[dict], int]:
    st = get_state()
    plan = st.get("active_plan") or []
    idx = int(st.get("active_plan_index") or 0)

    if not isinstance(plan, list):
        plan = []

    return plan, idx


def advance_active_plan(steps: int = 1) -> None:
    st = get_state()
    idx = int(st.get("active_plan_index") or 0)
    idx += steps
    set_state({"active_plan_index": max(idx, 0)})


def clear_active_plan() -> None:
    data = load_memory()
    st = data.get("state", {}) or {}

    st.pop("active_plan", None)
    st.pop("active_plan_index", None)
    st.pop("current_goal", None)

    data["state"] = st
    save_memory(data)


def format_active_plan_status(max_items: int = 6) -> str:
    plan, idx = get_active_plan()
    goal = get_goal()

    if not plan:
        return "Não há plano ativo no momento."

    lines = []

    if goal:
        lines.append(f"Objetivo atual: {goal}")

    lines.append(f"Progresso: {min(idx, len(plan))}/{len(plan)}")
    lines.append("Próximos passos:")

    start = max(idx - 2, 0)
    end = min(idx + max_items, len(plan))

    for i in range(start, end):
        item = plan[i]
        step = item.get("step") or item.get("t") or ""
        action = item.get("action") or ""

        if i < idx:
            mark = "✅"
        elif i == idx:
            mark = "➡️"
        else:
            mark = "•"

        if step:
            lines.append(f"{mark} [{i+1}] {step} ({action})")
        else:
            lines.append(f"{mark} [{i+1}] ({action})")

    return "\n".join(lines)


# ===============================
# CONTEXT INJECTION
# ===============================

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
        "ali", "aí", "ai", "então", "entao", "depois",
        "em seguida", "repete", "repetir",
        "continua", "continuar",
    ]

    if len(s) <= 40:
        return True

    return any(m in s for m in followup_markers)


def set_pending_action(action: dict | None) -> None:
    data = load_memory()
    st = data.get("state", {}) or {}
    if action is None:
        st.pop("pending_action", None)
        st.pop("pending_risk", None)
        st.pop("pending_note", None)
    else:
        st["pending_action"] = action
    data["state"] = st
    save_memory(data)


def set_pending_risk(level: str, note: str = "") -> None:
    set_state({"pending_risk": level, "pending_note": note})


def get_pending() -> tuple[dict | None, str, str]:
    st = get_state()
    a = st.get("pending_action")
    risk = str(st.get("pending_risk") or "")
    note = str(st.get("pending_note") or "")
    if not isinstance(a, dict):
        a = None
    return a, risk, note