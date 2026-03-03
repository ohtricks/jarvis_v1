import os
from .llm import ask_llm
from .prompts import PLANNER_PROMPT, safe_load
from .memory import build_context, should_inject_memory
from .telemetry import debug_set

DEBUG = os.getenv("JARVIS_DEBUG", "0") == "1"

def make_plan(user_input: str) -> dict:
    inject = should_inject_memory(user_input)
    context = build_context(max_turns=4) if inject else ""
    system = PLANNER_PROMPT + ("\n\n" + context if context else "")

    debug_set("memory_injected", inject)

    msgs = [
        {"role": "system", "content": system},
        {"role": "user", "content": user_input},
    ]
    raw = ask_llm(msgs, model="reasoning", temperature=0.0, role="planner")
    if DEBUG:
        print("DEBUG PLANNER:", raw)

    data = safe_load(raw)
    goal = (data.get("goal") or "").strip() or (user_input.strip()[:80])
    plan = data.get("plan")
    if not isinstance(plan, list):
        plan = []
    # limit hard
    plan = plan[:8]

    debug_set("plan", {
        "goal": goal,
        "steps": [s.get("step", "") for s in plan if isinstance(s, dict)],
    })

    return {"goal": goal, "plan": plan}