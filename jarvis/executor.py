from .queue import next_pending, mark_running, mark_done, mark_failed, mark_blocked
from .risk import require_confirmation, confirm_message
from .memory import get_session

def execute_next(skills: dict, learn_state_fn) -> str:
    it, idx = next_pending()
    if not it:
        return "Não há itens pendentes na fila."

    action = it.get("action")
    args = it.get("args", {}) or {}

    sess = get_session()
    mode = (sess.get("mode") or "dry").lower()

    # decide execução desejada: dry -> nunca executa
    desired_execute = (mode == "execute")
    if mode == "safe":
        # safe mode executa apenas safe automaticamente; risky/danger sempre bloqueia
        desired_execute = True  # mas o gate bloqueia risky/danger

    if action not in skills:
        mark_failed(idx, f"Ação desconhecida: {action}")
        return f"Ação desconhecida: {action}"

    # Risk gate
    blocked, risk, note = require_confirmation(action, args, skills, desired_execute=desired_execute)

    if blocked:
        mark_blocked(idx, risk, note)
        # safe-mode: sempre bloqueia risky/danger
        return confirm_message(risk, note)

    # Execução
    mark_running(idx)
    try:
        skill = skills[action]
        # força execute conforme modo
        old_execute = getattr(skill, "execute", None)
        try:
            if old_execute is not None:
                skill.execute = bool(desired_execute)
            learn_state_fn(action, args)
            out = skill.run(args)
        finally:
            if old_execute is not None:
                skill.execute = old_execute

        mark_done(idx, out)
        return out
    except Exception as e:
        mark_failed(idx, str(e))
        return f"Erro ao executar ação: {e}"


def execute_all_until_blocked(skills: dict, learn_state_fn) -> str:
    outputs = []
    while True:
        it, _ = next_pending()
        if not it:
            break
        out = execute_next(skills, learn_state_fn)
        outputs.append(out)
        # Se gate bloqueou, para
        if out.startswith("⚠️"):
            break
    return "\n".join([o for o in outputs if o]).strip() or "Ok."