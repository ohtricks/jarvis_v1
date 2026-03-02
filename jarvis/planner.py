import os
from .llm import ask_llm
from .prompts import PLANNER_PROMPT, safe_load
from .memory import build_context, should_inject_memory

DEBUG = os.getenv("JARVIS_DEBUG", "0") == "1"

def make_plan(user_input: str) -> dict:
    context = build_context(max_turns=4) if should_inject_memory(user_input) else ""
    system = PLANNER_PROMPT + ("\n\n" + context if context else "")

    msgs = [
        {"role": "system", "content": system},
        {"role": "user", "content": user_input},
    ]
    raw = ask_llm(msgs, model="reasoning", temperature=0.0)
    if DEBUG:
        print("DEBUG PLANNER:", raw)

    data = safe_load(raw)
    goal = (data.get("goal") or "").strip() or (user_input.strip()[:80])
    plan = data.get("plan")
    if not isinstance(plan, list):
        plan = []
    # limit hard
    plan = plan[:8]
    return {"goal": goal, "plan": plan}