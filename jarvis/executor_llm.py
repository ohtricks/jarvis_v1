from .llm import ask_llm
from .prompts import ACTION_COMPILER_PROMPT, safe_load
from .telemetry import debug_set
from .skills.registry import get_capabilities_text


def make_actions(user_input: str, model: str) -> dict:
    """
    Compila 1-3 ações diretas usando fast ou brain (sem reasoning).

    Retorna:
      {"goal": str, "plan": [...]}  — steps prontos para enqueue_plan()
      {"chat": str}                 — resposta direta sem enfileirar
    """
    caps = get_capabilities_text()
    system = ACTION_COMPILER_PROMPT + "\n\n" + caps
    msgs = [
        {"role": "system", "content": system},
        {"role": "user", "content": user_input},
    ]
    raw = ask_llm(msgs, model=model, temperature=0.0, role="executor_llm")

    try:
        data = safe_load(raw)
    except Exception:
        return {"chat": "Não consegui processar o pedido. Tente 'plan:' para um plano detalhado."}

    # Forma C: chat direto (skill inexistente ou limitação)
    if data.get("action") == "chat":
        return {"chat": data.get("response") or ""}

    # Forma A: ação única → normalizar para plan de 1 step
    if "action" in data and "plan" not in data:
        action = data.get("action")
        args = {k: v for k, v in data.items() if k not in ("action", "step")}
        step_label = data.get("step") or action
        plan = [{"step": step_label, "action": action, **args}]
        debug_set("executor_llm_steps", 1)
        return {"goal": user_input[:80], "plan": plan}

    # Forma B: plan com 2-3 steps
    goal = (data.get("goal") or user_input[:80]).strip()
    plan = data.get("plan") or []
    if not isinstance(plan, list):
        plan = []
    plan = plan[:3]  # hard limit

    debug_set("executor_llm_steps", len(plan))
    return {"goal": goal, "plan": plan}
