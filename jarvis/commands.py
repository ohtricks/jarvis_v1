# jarvis/commands.py
from .memory import clear_memory, clear_active_plan, format_active_plan_status, get_active_plan
from .planner import continue_plan, run_plan_all, confirm_pending

def handle_builtin(cmd: str, skills: dict, learn_state_fn) -> str | None:
    c = (cmd or "").strip().lower()

    # pendências (risk gate)
    pending = confirm_pending(c, skills, learn_state_fn)
    if pending is not None:
        return pending

    if c in ("limpar memoria", "limpar memória", "clear memory", "reset memory"):
        clear_memory()
        return "Memória limpa."

    if c in ("status", "status plano", "plano status"):
        return format_active_plan_status()

    if c in ("cancelar", "cancelar plano", "parar", "stop", "limpar plano", "reset plano"):
        clear_active_plan()
        return "Plano cancelado. Pronto para o próximo comando."

    if c in ("listar etapas", "etapas", "listar plano", "mostrar plano"):
        plan, idx = get_active_plan()
        if not plan:
            return "Não há plano ativo."
        lines = []
        for i, p in enumerate(plan):
            mark = "✅" if i < idx else "•"
            step = p.get("step") or p.get("action") or ""
            lines.append(f"{mark} {i+1}. {step}")
        return "\n".join(lines)

    if c in ("continua", "continuar", "seguir", "next", "continue"):
        return continue_plan(skills, learn_state_fn)

    if c in ("executar tudo", "executar todas", "executar plano", "run all", "execute all", "executar todas as etapas"):
        return run_plan_all(skills, learn_state_fn)

    return None