import os
import time
from typing import Tuple

from .queue import (
    next_pending,
    mark_running,
    mark_done,
    mark_failed,
    mark_blocked,
    list_items,
)
from .risk import require_confirmation, confirm_message
from .memory import get_session, build_context, set_pending_recovery
from .telemetry import debug_append
from .observation import observe_step, should_propose_recovery
from . import autonomy_safe

DEBUG = os.getenv("JARVIS_DEBUG", "0") == "1"


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
    step_label = it.get("step", action)

    sess = get_session()
    mode = (sess.get("mode") or "dry").lower()

    # decide execução desejada: dry -> nunca executa
    desired_execute = (mode == "execute")
    if mode == "safe":
        # safe mode executa apenas safe automaticamente; risky/danger sempre bloqueia
        desired_execute = True  # mas o gate bloqueia risky/danger

    if action not in skills:
        mark_failed(idx, f"Ação desconhecida: {action}")
        if DEBUG:
            debug_append("execution", {"step": step_label, "action": action, "risk": "unknown", "status": "failed", "output": f"Ação desconhecida: {action}", "ms": 0})
        return f"Ação desconhecida: {action}", "failed"

    t0 = time.time()

    # Risk gate (V3): se bloquear, grava confirm no item bloqueado
    blocked, risk, note, confirm = require_confirmation(
        action,
        args,
        desired_execute=desired_execute,
    )
    if blocked:
        mark_blocked(idx, risk, note, confirm=confirm)
        if DEBUG:
            debug_append("execution", {"step": step_label, "action": action, "risk": risk, "status": "blocked", "output": note, "ms": int((time.time() - t0) * 1000)})
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
        if DEBUG:
            debug_append("execution", {"step": step_label, "action": action, "risk": risk, "status": "done", "output": out, "ms": int((time.time() - t0) * 1000)})
        return out, "done"

    except Exception as e:
        mark_failed(idx, str(e))
        if DEBUG:
            debug_append("execution", {"step": step_label, "action": action, "risk": risk, "status": "failed", "output": str(e), "ms": int((time.time() - t0) * 1000)})
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


def execute_until_blocked_or_recovery(
    skills: dict,
    learn_state_fn,
    goal: str = "",
    max_steps: int = 50,
) -> dict:
    """
    Como execute_until_blocked, mas ao detectar falha em run_shell:
    - gera observation e verifica se deve propor recovery
    - se sim: salva proposal, retorna {"state":"recovery_pending", "message":..., "proposal":...}
    - se não: comportamento normal de falha

    O executor NÃO executa o recovery plan. Só propõe.

    Retorna sempre um dict:
      {"state": str, "message": str, "proposal": dict | None}
    """
    outputs: list[str] = []
    last_state = "empty"

    for _ in range(max_steps):
        msg, state = execute_one(skills, learn_state_fn)
        last_state = state
        if msg:
            outputs.append(msg)

        if state == "failed":
            # Busca o item que falhou na queue para detalhes
            failed_item: dict | None = None
            for it in reversed(list_items()):
                if it.get("status") == "failed":
                    failed_item = it
                    break

            action = (failed_item.get("action") or "") if failed_item else ""
            args = (failed_item.get("args") or {}) if failed_item else {}
            error_out = (failed_item.get("error") or msg) if failed_item else msg

            obs = observe_step(action, args, error_out, state)

            if should_propose_recovery(obs):
                context_text = build_context(max_turns=2)
                proposal = autonomy_safe.propose_recovery(goal, obs, context_text)
                set_pending_recovery(proposal)

                # Outputs anteriores ao passo que falhou (contexto para o usuário)
                prior = "\n".join([o for o in outputs[:-1] if o]).strip()
                recovery_ux = autonomy_safe.format_recovery_message(msg, proposal)
                full_ux = (prior + "\n\n" + recovery_ux).strip() if prior else recovery_ux

                return {"state": "recovery_pending", "message": full_ux, "proposal": proposal}

            break  # falha sem recovery → sai do loop normalmente

        if state in ("empty", "blocked"):
            break

    out = "\n".join([o for o in outputs if o]).strip() or "Ok."
    return {"state": last_state, "message": out, "proposal": None}