import os
from .llm import ask_llm
from .prompts import ROUTER_PROMPT, safe_load

DEBUG = os.getenv("JARVIS_DEBUG", "0") == "1"

PREFIXES = {
    "plan:": "planner",
    "think:": "planner",
    "reason:": "planner",
    "exec:": "executor",
    "brain:": "executor",
    "fast:": "fast_reply",
}

def strip_forced_prefix(user_input: str) -> tuple[str, str | None]:
    raw = (user_input or "").strip()
    low = raw.lower()
    for p, route in PREFIXES.items():
        if low.startswith(p):
            return raw[len(p):].strip(), route
    return raw, None

def route_input(user_input: str) -> dict:
    msgs = [
        {"role": "system", "content": ROUTER_PROMPT},
        {"role": "user", "content": user_input},
    ]
    raw = ask_llm(msgs, model="fast", temperature=0.0)
    if DEBUG:
        print("DEBUG ROUTER:", raw)

    data = safe_load(raw)
    route = data.get("route")
    if route not in ("fast_reply", "planner", "executor"):
        return {"route": "executor", "needs_actions": True}

    if route == "fast_reply":
        resp = (data.get("response") or "").strip()
        if not resp:
            return {"route": "executor", "needs_actions": False}
        return {"route": "fast_reply", "needs_actions": False, "response": resp}

    return {"route": route, "needs_actions": bool(data.get("needs_actions", True))}
