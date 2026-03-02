from .memory import (
    clear_memory, format_active_plan_status, clear_active_plan,
    set_session_mode, get_session,
)
from .queue import (
    format_queue_status, clear_queue, has_active_queue, list_items,
    mark_done, mark_skipped
)
from .risk import handle_confirmation
from .executor import execute_next, execute_all_until_blocked
from .memory import get_pending  # <- vem do memory.py no seu projeto

def handle_builtin(cmd: str, skills: dict, learn_state_fn) -> str | None:
    raw = (cmd or "").strip()
    c = raw.lower()

    # confirmations (NO LLM)
    is_yes = c in ("yes", "y", "confirmar")
    is_no = c in ("no", "n", "cancel", "cancelar")
    is_yes_i_know = raw.replace('"', '').strip().upper() == "YES I KNOW"
    if is_yes or is_no or is_yes_i_know:
        pending, risk, note = get_pending()
        out = handle_confirmation(raw, skills, learn_state_fn)

        # se havia pending e ele estava ligado a um item da queue, atualiza status
        if pending and isinstance(pending, dict) and "_queue_idx" in pending:
            qidx = pending.get("_queue_idx")
            try:
                qidx = int(qidx)
            except Exception:
                qidx = None

            if qidx is not None:
                if is_no:
                    mark_skipped(qidx, "Cancelado pelo usuário.")
                else:
                    # yes / YES I KNOW -> marca done com o output
                    if out is not None:
                        mark_done(qidx, out)

        if out is not None:
            return out

    # memory reset
    if c in ("limpar memoria", "limpar memória", "clear memory", "reset memory"):
        clear_memory()
        clear_queue()
        return "Memória limpa."

    # mode
    if c.startswith("mode "):
        mode = c.split(" ", 1)[1].strip()
        if mode in ("dry", "execute", "safe"):
            set_session_mode(mode)
            return f"Modo definido: {mode}"
        return "Modos válidos: dry | execute | safe"

    if c in ("mode", "modo"):
        sess = get_session()
        return f"Modo atual: {sess.get('mode')}"

    # status
    if c in ("status", "status plano", "plano status"):
        if has_active_queue():
            return format_queue_status()
        return format_active_plan_status()

    # list queue/plan
    if c in ("listar plano", "listar etapas", "mostrar plano", "etapas", "queue", "fila"):
        if not has_active_queue():
            return "Não há fila ativa."
        items = list_items()
        lines = []
        for i, it in enumerate(items):
            st = it.get("status")
            step = it.get("step") or it.get("action") or ""
            if st == "done":
                prefix = "✅"
            elif st == "blocked":
                prefix = "⚠️"
            elif st == "pending":
                prefix = "•"
            elif st == "running":
                prefix = "⏳"
            elif st == "failed":
                prefix = "❌"
            elif st == "skipped":
                prefix = "⏭️"
            else:
                prefix = "•"
            lines.append(f"{prefix} {i+1}. {step}")
        return "\n".join(lines).strip()

    # cancel
    if c in ("cancelar plano", "cancelar", "parar", "stop"):
        clear_active_plan()
        clear_queue()
        return "Plano/fila cancelado. Pronto para o próximo comando."

    # continue
    if c in ("continue", "continua", "continuar", "next", "seguir"):
        if not has_active_queue():
            return "Não há fila ativa. Use 'plan:' para criar um plano."
        return execute_next(skills, learn_state_fn)

    # run all
    if c in ("executar tudo", "executar todas", "executar todas as etapas", "run all", "execute all"):
        if not has_active_queue():
            return "Não há fila ativa."
        return execute_all_until_blocked(skills, learn_state_fn)

    return None