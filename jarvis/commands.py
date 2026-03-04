from .memory import (
    clear_memory,
    format_active_plan_status,
    clear_active_plan,
    set_session_mode,
    get_session,
    get_pending_recovery,
    clear_pending_recovery,
)
from .queue import (
    format_queue_status,
    clear_queue,
    enqueue_plan,
    has_active_queue,
    list_items,
    last_blocked,
    unblock_to_pending,
    mark_skipped,
)
from .executor import execute_next, execute_until_blocked, execute_all_until_blocked
from .skills.registry import get_capabilities, get_capabilities_text

_YES_WORDS = frozenset({
    "yes", "y", "confirmar",
    "sim", "s", "ok", "okay", "manda ver", "pode", "pode continuar", "vai", "confirmo",
})
_NO_WORDS = frozenset({
    "no", "n", "cancel", "cancelar",
    "não", "nao", "cancela", "para", "parar",
})

# Palavras exclusivas do approval gate de recovery (separadas do risk gate)
_RECOVERY_APPROVE = frozenset({
    "ok", "okay", "sim", "s", "manda ver", "pode", "pode tentar", "executa",
    "continue com o plano",
})
_RECOVERY_REJECT = frozenset({
    "não", "nao", "n", "cancela", "cancelar", "deixa", "parar",
})


def _handle_recovery_confirmation(c: str, skills: dict, learn_state_fn, proposal: dict) -> str:
    """
    Executa ou rejeita um recovery plan pendente.
    Separado do risk gate — não usa _YES_WORDS/_NO_WORDS diretamente.
    """
    if c in _RECOVERY_APPROVE:
        plan = proposal.get("plan") or []
        if not plan:
            clear_pending_recovery()
            return "Nao ha passos de recovery para executar. Verifique manualmente."

        goal = proposal.get("goal") or "Recuperacao automatica"
        clear_queue()
        enqueue_plan(goal, plan)
        clear_pending_recovery()
        return execute_until_blocked(skills, learn_state_fn)

    # rejeitar
    clear_pending_recovery()
    return "Ok, nao vou tentar automaticamente. Me diga como voce quer proceder."


def _handle_confirmation_v3(raw_cmd: str, skills: dict, learn_state_fn) -> str | None:
    """
    V3: confirmação opera diretamente na queue:
      - acha último item blocked
      - valida required
      - desbloqueia -> pending (inject _execute)
      - retoma automaticamente (execute_until_blocked)
    """
    c_raw = (raw_cmd or "").strip()
    c = c_raw.lower()

    it, idx = last_blocked()
    has_blocked = bool(it)

    # cancel
    if c in _NO_WORDS:
        if not has_blocked:
            return "Não há nenhuma ação bloqueada para cancelar."
        mark_skipped(idx, "Cancelado pelo usuário.")
        return "Cancelado."

    # confirm
    if c in _YES_WORDS or c_raw.replace('"', "").strip().upper() == "YES I KNOW":
        if not has_blocked:
            return "Não há nenhuma ação bloqueada para confirmar."

        confirm = (it.get("confirm") or {}) if isinstance(it, dict) else {}
        required = (confirm.get("required") or "").strip()

        # Regras:
        # - danger exige "YES I KNOW"
        # - risky aceita "yes"/"y"/"confirmar"
        if required.upper() == "YES I KNOW":
            if c_raw.replace('"', "").strip().upper() != "YES I KNOW":
                return "Esta ação é PERIGOSA. Para confirmar, digite exatamente: YES I KNOW"
        # para risky, "yes" já tá ok

        execute_payload = confirm.get("execute_payload") or {"_execute": True}
        unblock_to_pending(idx, execute_payload=execute_payload)

        # retoma automaticamente até o próximo bloqueio/fim
        return execute_until_blocked(skills, learn_state_fn)

    return None


def handle_builtin(cmd: str, skills: dict, learn_state_fn) -> str | None:
    raw = (cmd or "").strip()
    c = raw.lower()

    # Confirmações: prioridade 1 = risk gate (se item bloqueado na queue)
    #               prioridade 2 = recovery gate (se proposta pendente, sem bloqueio)
    _is_confirm = c in _YES_WORDS | _NO_WORDS or raw.replace('"', "").strip().upper() == "YES I KNOW"
    _is_recovery_word = c in _RECOVERY_APPROVE | _RECOVERY_REJECT
    if _is_confirm or _is_recovery_word:
        risk_blocked, _ = last_blocked()
        if risk_blocked:
            # Risk gate tem prioridade absoluta quando há item bloqueado
            out = _handle_confirmation_v3(raw, skills, learn_state_fn)
            if out is not None:
                return out
        else:
            # Sem item bloqueado: verificar recovery pendente primeiro
            proposal = get_pending_recovery()
            if proposal and _is_recovery_word:
                return _handle_recovery_confirmation(c, skills, learn_state_fn, proposal)
            # Nenhum recovery pendente: fluxo normal (retorna "nao ha acao bloqueada")
            if _is_confirm:
                out = _handle_confirmation_v3(raw, skills, learn_state_fn)
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
        # prefer queue status if exists
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

            lines.append(f"{prefix} {i+1}.\n{step}")

        return "\n".join(lines).strip()

    # cancel
    if c in ("cancelar plano", "cancelar", "parar", "stop"):
        clear_active_plan()
        clear_queue()
        return "Plano/fila cancelado. Pronto para o próximo comando."

    # continue (V3: roda loop até bloquear)
    if c in ("continue", "continua", "continuar", "next", "seguir"):
        if not has_active_queue():
            return "Não há fila ativa. Use 'plan:' para criar um plano."
        return execute_until_blocked(skills, learn_state_fn)

    # run all
    if c in ("executar tudo", "executar todas", "executar todas as etapas", "run all", "execute all"):
        if not has_active_queue():
            return "Não há fila ativa."
        return execute_all_until_blocked(skills, learn_state_fn)

    # (opcional) ainda permite "um passo só"
    if c in ("executar proximo", "executar próximo", "run next"):
        if not has_active_queue():
            return "Não há fila ativa."
        return execute_next(skills, learn_state_fn)

    # capability discovery
    if c in ("skills", "capabilities", "habilidades", "capacidades"):
        caps = get_capabilities()
        by_ns: dict[str, list] = {}
        for cap in caps:
            by_ns.setdefault(cap.namespace, []).append(cap)
        lines = ["Capabilities disponíveis:\n"]
        for ns, ns_caps in by_ns.items():
            lines.append(f"[{ns}]")
            for cap in ns_caps:
                risk_tag = f" ({cap.risk})" if cap.risk != "safe" else ""
                lines.append(f"  • {cap.name}{risk_tag} — {cap.description}")
                if cap.examples:
                    exs = " | ".join(f'"{e}"' for e in cap.examples[:2])
                    lines.append(f"    ex: {exs}")
        return "\n".join(lines)

    return None