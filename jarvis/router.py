# jarvis/router.py
from .brain import ask_llm
from .prompts import ROUTER_PROMPT
from .utils import safe_load

def route_input(user_input: str, debug: bool = False) -> dict:
    msgs = [
        {"role": "system", "content": ROUTER_PROMPT},
        {"role": "user", "content": user_input},
    ]
    raw = ask_llm(msgs, model="fast", temperature=0.0)
    if debug:
        print("DEBUG ROUTER:", raw)

    data = safe_load(raw)

    if data.get("route") not in ("fast_reply", "brain", "reasoning"):
        return {"route": "brain", "needs_actions": True}

    if data["route"] == "fast_reply":
        resp = (data.get("response") or "").strip()
        if not resp:
            return {"route": "brain", "needs_actions": False}
        return {"route": "fast_reply", "needs_actions": False, "response": resp}

    return {"route": data["route"], "needs_actions": bool(data.get("needs_actions", True))}