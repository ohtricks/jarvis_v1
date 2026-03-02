from .queue import next_pending, first_blocked, mark_running, mark_done, mark_failed, mark_blocked
from .risk import require_confirmation, confirm_message
from .memory import get_session

def execute_next(skills: dict, learn_state_fn) -> str:
    it, idx = next_pending()

    # se não tem pending, mas tem blocked => re-exibe a confirmação
    if not it:
        blocked_it, bidx = first_blocked()
        if blocked_it:
            risk = blocked_it.get("risk") or "risky"
            note = blocked_it.get("error") or "Confirmação necessária."
            return confirm_message(risk, note)
        return "Não há itens pendentes na fila."

    action = it.get("action")
    args = it.get("args", {}) or {}

    sess = get_session()
    mode = (sess.get("mode") or "dry").lower()

    # decide execução desejada
    desired_execute = (mode == "execute")
    if mode == "safe":
        desired_execute = True  # safe-mode executa safe automaticamente; risky/danger bloqueia via gate

    if action not in skills:
        mark_failed(idx, f"Ação desconhecida: {action}")
        return f"Ação desconhecida: {action}"

    # injeta metadados pra confirmação conseguir atualizar a fila
    args_with_meta = dict(args)
    args_with_meta["_queue_idx"] = idx

    # Risk gate
    blocked, risk, note = require_confirmation(action, args_with_meta, skills, desired_execute=desired_execute)

    if blocked:
        mark_blocked(idx, risk, note)
        return confirm_message(risk, note)

    # Execução
    mark_running(idx)
    try:
        skill = skills[action]
        old_execute = getattr(skill, "execute", None)
        try:
            if old_execute is not None:
                skill.execute = bool(desired_execute)

            # remove meta antes de enviar pra skill
            clean_args = {k: v for k, v in args.items()}
            learn_state_fn(action, clean_args)
            out = skill.run(clean_args)
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
            # se ficou bloqueado, devolve a confirmação; se não, termina
            blocked_it, _bidx = first_blocked()
            if blocked_it:
                risk = blocked_it.get("risk") or "risky"
                note = blocked_it.get("error") or "Confirmação necessária."
                outputs.append(confirm_message(risk, note))
            break

        out = execute_next(skills, learn_state_fn)
        outputs.append(out)

        if out.startswith("⚠️"):
            break

    return "\n".join([o for o in outputs if o]).strip() or "Ok."