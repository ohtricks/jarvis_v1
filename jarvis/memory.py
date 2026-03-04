import json
from pathlib import Path
from datetime import datetime
from typing import Any, Optional, Tuple

JARVIS_DIR = Path.home() / ".jarvis"
MEMORY_PATH = JARVIS_DIR / "memory.json"
LOGS_DIR = JARVIS_DIR / "logs"

MAX_TURNS = 8


def _ensure_dir():
    JARVIS_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)


def _default() -> dict[str, Any]:
    return {
        "turns": [],
        "state": {},
        "session": {
            "mode": "dry",  # dry|execute|safe
            "default_browser": "Google Chrome",
            "cwd": None,
        },
        "active_plan": {
            "goal": None,
            "plan": [],
            "idx": 0,
        },
        "pending": {
            "action": None,   # dict | None
            "risk": None,     # safe|risky|danger|None
            "note": None,     # str|None
        },
    }


def load_memory() -> dict[str, Any]:
    _ensure_dir()
    if not MEMORY_PATH.exists():
        return _default()
    try:
        data = json.loads(MEMORY_PATH.read_text(encoding="utf-8"))
        base = _default()
        # merge shallow
        for k, v in data.items():
            base[k] = v
        # ensure sub-objects
        if not isinstance(base.get("turns"), list): base["turns"] = []
        if not isinstance(base.get("state"), dict): base["state"] = {}
        if not isinstance(base.get("session"), dict): base["session"] = _default()["session"]
        if not isinstance(base.get("active_plan"), dict): base["active_plan"] = _default()["active_plan"]
        if not isinstance(base.get("pending"), dict): base["pending"] = _default()["pending"]
        return base
    except Exception:
        return _default()


def save_memory(data: dict[str, Any]) -> None:
    _ensure_dir()
    MEMORY_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# -------------------------
# Turns (chat history)
# -------------------------
def add_turn(user_text: str, jarvis_text: str) -> None:
    mem = load_memory()
    turns = mem.get("turns", [])
    turns.append({
        "ts": datetime.utcnow().isoformat() + "Z",
        "u": (user_text or "").strip()[:600],
        "j": (jarvis_text or "").strip()[:800],
    })
    mem["turns"] = turns[-MAX_TURNS:]
    save_memory(mem)


# -------------------------
# State (structured memory)
# -------------------------
def get_state() -> dict[str, Any]:
    return load_memory().get("state", {}) or {}


def set_state(patch: dict[str, Any]) -> None:
    mem = load_memory()
    state = mem.get("state", {}) or {}
    for k, v in (patch or {}).items():
        if v is None:
            continue
        state[k] = v
    mem["state"] = state
    save_memory(mem)


def build_context(max_turns: int = 4) -> str:
    """
    Contexto compacto para o LLM.
    """
    mem = load_memory()
    state = mem.get("state", {}) or {}
    turns = (mem.get("turns", []) or [])[-max_turns:]
    session = mem.get("session", {}) or {}
    plan = mem.get("active_plan", {}) or {}

    parts = []

    if session:
        parts.append(
            "SESSION:\n"
            f"- mode: {session.get('mode')}\n"
            f"- default_browser: {session.get('default_browser')}\n"
            f"- cwd: {session.get('cwd')}"
        )

    system_fields = {
        k: state.get(k)
        for k in ("cwd", "git_repo", "git_branch")
        if state.get(k) is not None
    }
    if system_fields:
        lines = ["SYSTEM:"]
        for k, v in system_fields.items():
            lines.append(f"- {k}: {v}")
        parts.append("\n".join(lines))

    state_extra = {k: v for k, v in state.items() if k not in ("cwd", "git_repo", "git_branch")}
    if state_extra:
        lines = ["STATE:"]
        for k, v in state_extra.items():
            lines.append(f"- {k}: {v}")
        parts.append("\n".join(lines))

    goal = plan.get("goal")
    if goal:
        parts.append(f"ACTIVE_GOAL:\n- {goal}")

    if turns:
        lines = ["HISTORY (últimas interações):"]
        for t in turns:
            lines.append(f"- U: {t.get('u','')}")
            lines.append(f"  J: {t.get('j','')}")
        parts.append("\n".join(lines))

    return "\n\n".join([p for p in parts if p]).strip()


def should_inject_memory(user_input: str) -> bool:
    s = (user_input or "").strip().lower()
    if not s:
        return False
    # Curto demais: quase sempre é follow-up.
    if len(s) <= 50:
        return True
    markers = ("agora", "depois", "em seguida", "também", "isso", "essa", "esse", "aí", "ai", "então", "entao", "repete", "novamente")
    return any(m in s for m in markers)


# -------------------------
# Session
# -------------------------
def get_session() -> dict[str, Any]:
    return load_memory().get("session", {}) or {}


def set_session_mode(mode: str) -> None:
    mode = (mode or "").strip().lower()
    if mode not in ("dry", "execute", "safe"):
        return
    mem = load_memory()
    mem["session"] = mem.get("session", {}) or {}
    mem["session"]["mode"] = mode
    save_memory(mem)


def set_session(patch: dict[str, Any]) -> None:
    mem = load_memory()
    sess = mem.get("session", {}) or {}
    for k, v in (patch or {}).items():
        if v is None:
            continue
        sess[k] = v
    mem["session"] = sess
    save_memory(mem)


# -------------------------
# Active plan (human readable)
# -------------------------
def set_goal(goal: str) -> None:
    mem = load_memory()
    ap = mem.get("active_plan", {}) or {}
    ap["goal"] = (goal or "").strip()
    mem["active_plan"] = ap
    save_memory(mem)


def set_active_plan(plan: list, goal: Optional[str] = None, idx: int = 0) -> None:
    mem = load_memory()
    mem["active_plan"] = {
        "goal": (goal or mem.get("active_plan", {}).get("goal") or "").strip() or None,
        "plan": plan or [],
        "idx": int(idx or 0),
    }
    save_memory(mem)


def get_active_plan() -> Tuple[list, int, Optional[str]]:
    mem = load_memory()
    ap = mem.get("active_plan", {}) or {}
    return ap.get("plan", []) or [], int(ap.get("idx", 0) or 0), ap.get("goal")


def advance_active_plan(step: int = 1) -> None:
    mem = load_memory()
    ap = mem.get("active_plan", {}) or {}
    ap["idx"] = int(ap.get("idx", 0) or 0) + int(step or 1)
    mem["active_plan"] = ap
    save_memory(mem)


def clear_active_plan() -> None:
    mem = load_memory()
    mem["active_plan"] = _default()["active_plan"]
    save_memory(mem)


def format_active_plan_status() -> str:
    plan, idx, goal = get_active_plan()
    if not plan:
        return "Não há plano ativo no momento."

    lines = []
    if goal:
        lines.append(f"Objetivo atual: {goal}")
    lines.append(f"Progresso: {min(idx, len(plan))}/{len(plan)}")
    lines.append("Próximos passos:")

    for i, p in enumerate(plan):
        step = p.get("step") or p.get("action") or ""
        action = p.get("action") or ""
        if i < idx:
            prefix = "✅"
        elif i == idx:
            prefix = "➡️"
        else:
            prefix = "•"
        lines.append(f"{prefix} [{i+1}] {step} ({action})")

    return "\n".join(lines).strip()


# -------------------------
# Pending confirm
# -------------------------
def set_pending_action(action: Optional[dict]) -> None:
    mem = load_memory()
    mem["pending"] = mem.get("pending", {}) or {}
    mem["pending"]["action"] = action
    save_memory(mem)


def set_pending_risk(risk: Optional[str], note: Optional[str]) -> None:
    mem = load_memory()
    mem["pending"] = mem.get("pending", {}) or {}
    mem["pending"]["risk"] = risk
    mem["pending"]["note"] = note
    save_memory(mem)


def get_pending() -> tuple[Optional[dict], Optional[str], Optional[str]]:
    mem = load_memory()
    p = mem.get("pending", {}) or {}
    return p.get("action"), p.get("risk"), p.get("note")


def clear_pending() -> None:
    mem = load_memory()
    mem["pending"] = _default()["pending"]
    save_memory(mem)


# -------------------------
# Execution history (Fase 8A) — buffer de últimas execuções reais
# Salvo em state["recent_execution"] (máx MAX_EXEC_HISTORY itens, FIFO).
# -------------------------
_MAX_EXEC_HISTORY = 50


def append_execution(event: dict) -> None:
    mem = load_memory()
    state = mem.get("state", {}) or {}
    history: list = state.get("recent_execution") or []
    history.append(event)
    state["recent_execution"] = history[-_MAX_EXEC_HISTORY:]
    mem["state"] = state
    save_memory(mem)


def get_recent_execution(limit: int = 10) -> list[dict]:
    state = load_memory().get("state", {}) or {}
    history: list = state.get("recent_execution") or []
    return history[-limit:]


# -------------------------
# Pending shell allow proposal (Fase 8B)
# -------------------------
def set_pending_shell_allow_proposal(proposal: dict | None) -> None:
    mem = load_memory()
    state = mem.get("state", {}) or {}
    if proposal is None:
        state.pop("pending_shell_allow_proposal", None)
    else:
        state["pending_shell_allow_proposal"] = proposal
    mem["state"] = state
    save_memory(mem)


def get_pending_shell_allow_proposal() -> dict | None:
    return (load_memory().get("state", {}) or {}).get("pending_shell_allow_proposal")


def clear_pending_shell_allow_proposal() -> None:
    set_pending_shell_allow_proposal(None)


# -------------------------
# Pending policy proposal (risk_policy — Fase 8)
# Salvo em state["pending_policy_proposal"].
# -------------------------
def set_pending_policy_proposal(proposal: dict | None) -> None:
    mem = load_memory()
    state = mem.get("state", {}) or {}
    if proposal is None:
        state.pop("pending_policy_proposal", None)
    else:
        state["pending_policy_proposal"] = proposal
    mem["state"] = state
    save_memory(mem)


def get_pending_policy_proposal() -> dict | None:
    mem = load_memory()
    return (mem.get("state", {}) or {}).get("pending_policy_proposal")


def clear_pending_policy_proposal() -> None:
    set_pending_policy_proposal(None)


# -------------------------
# Pending recovery proposal (Fase 7)
# Salvo em state["pending_recovery"] para não quebrar estrutura existente.
# -------------------------
def set_pending_recovery(proposal: dict | None) -> None:
    mem = load_memory()
    state = mem.get("state", {}) or {}
    if proposal is None:
        state.pop("pending_recovery", None)
    else:
        state["pending_recovery"] = proposal
    mem["state"] = state
    save_memory(mem)


def get_pending_recovery() -> dict | None:
    mem = load_memory()
    return (mem.get("state", {}) or {}).get("pending_recovery")


def clear_pending_recovery() -> None:
    set_pending_recovery(None)


# -------------------------
# Reset
# -------------------------
def clear_memory() -> None:
    save_memory(_default())