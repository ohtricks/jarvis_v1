from typing import Tuple

from .queue import (
    next_pending,
    mark_running,
    mark_done,
    mark_failed,
    mark_blocked,
)
from .risk import require_confirmation, confirm_message
from .memory import get_session


def execute_one(skills: dict, learn_state_fn) -> Tuple[str, str]:
    """
    Executa 1 item pendente.
    Retorna (mensagem, state) onde state ∈:
      - done
      - blocked
      - empty
      - failed
    """
    it, idx = next_pending()
    if not it:
        return "Não há itens pendentes na fila.", "empty"

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
        return f"Ação desconhecida: {action}", "failed"

    # Risk gate (V3): se bloquear, grava confirm no item bloqueado
    blocked, risk, note, confirm = require_confirmation(
        action,
        args,
        desired_execute=desired_execute,
    )
    if blocked:
        mark_blocked(idx, risk, note, confirm=confirm)
        return confirm_message(risk, note), "blocked"

    # Execução real (única fonte de execução)
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
        return out, "done"

    except Exception as e:
        mark_failed(idx, str(e))
        return f"Erro ao executar ação: {e}", "failed"


def execute_next(skills: dict, learn_state_fn) -> str:
    msg, _state = execute_one(skills, learn_state_fn)
    return msg


def execute_until_blocked(skills: dict, learn_state_fn, max_steps: int = 50) -> str:
    """
    V3: loop contínuo até:
      - fila acabar
      - bloquear (confirmação)
      - falhar
    """
    outputs = []
    for _ in range(max_steps):
        msg, state = execute_one(skills, learn_state_fn)
        if msg:
            outputs.append(msg)

        if state in ("empty", "blocked", "failed"):
            break

    return "\n".join([o for o in outputs if o]).strip() or "Ok."


# compat com comando antigo "executar tudo"
def execute_all_until_blocked(skills: dict, learn_state_fn) -> str:
    return execute_until_blocked(skills, learn_state_fn)