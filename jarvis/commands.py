from .memory import (
    clear_memory,
    format_active_plan_status,
    clear_active_plan,
    set_session_mode,
    get_session,
    get_pending_recovery,
    clear_pending_recovery,
    get_pending_policy_proposal,
    clear_pending_policy_proposal,
    get_recent_execution,
    get_pending_shell_allow_proposal,
    clear_pending_shell_allow_proposal,
)
from .risk_policy import add_to_policy
from .shell_policy import add_allow_prefix as _shell_add_allow_prefix
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

# ── Policy proposal (risk_policy) ────────────────────────────────────────────
# Mapeamento de palavra-chave do usuário para bucket no risk_policy.json
_POLICY_BUCKET_MAP: dict[str, str] = {
    "safe":    "safe_prefixes",
    "risky":   "risky_patterns",
    "risk":    "risky_patterns",
    "danger":  "danger_patterns",
    "perigoso": "danger_patterns",
}
_POLICY_BUCKET_LABEL: dict[str, str] = {
    "safe_prefixes":   "seguro (safe) — executa sem confirmação",
    "risky_patterns":  "risky — pede confirmação",
    "danger_patterns": "danger — exige YES I KNOW",
}


def _extract_command_pattern(cmd: str) -> str:
    """
    Extrai até 2 tokens base de um comando, ignorando flags e argumentos.
    Ex: "git commit -m 'msg'" → "git commit"
        "git add ."           → "git add"
        "npm install axios"   → "npm install"
    """
    tokens = cmd.strip().split()
    base: list[str] = []
    for token in tokens:
        if token.startswith("-"):
            break
        base.append(token)
        if len(base) >= 2:
            break
    return " ".join(base)


def _handle_policy_proposal(c: str, proposal: dict) -> str | None:
    """
    Verifica se o input é uma ação de policy ("adicionar safe/risky/danger").
    Retorna resposta string se processou, None caso contrário.
    Não trata "cancelar" — deixa para os gates normais (risk/recovery).
    """
    for prefix in ("adicionar ", "add "):
        if c.startswith(prefix):
            rest = c[len(prefix):].strip()
            bucket = _POLICY_BUCKET_MAP.get(rest)
            if not bucket:
                return None  # palavra não reconhecida como bucket, não interferir
            cmd_pattern = _extract_command_pattern(proposal["command"])
            if not cmd_pattern:
                return "Nao consegui extrair o padrao do comando."
            added = add_to_policy(bucket, cmd_pattern)
            clear_pending_policy_proposal()
            label = _POLICY_BUCKET_LABEL.get(bucket, bucket)
            if added:
                return (
                    f"✅ '{cmd_pattern}' adicionado como {label}.\n"
                    "Agora voce pode tentar novamente o comando."
                )
            return f"'{cmd_pattern}' ja existe em {label}."
    return None


# ── Risk / Confirmation words ────────────────────────────────────────────────
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


# ── Gmail keywords ────────────────────────────────────────────────────────────
_GMAIL_KEYWORDS = frozenset({
    "gmail", "email", "emails", "inbox", "caixa de entrada",
})
_GMAIL_READ_WORDS = frozenset({
    "ler", "leia", "listar", "lista", "ver", "veja",
    "mostre", "mostra", "últimos", "ultimos", "recentes", "recente", "novos",
})


def _detect_gmail_read(words: set[str]) -> bool:
    return bool(words & _GMAIL_KEYWORDS) and bool(words & _GMAIL_READ_WORDS)


def handle_builtin(cmd: str, skills: dict, learn_state_fn) -> str | None:
    raw = (cmd or "").strip()
    c = raw.lower()

    # ── Gmail: builtin explícito "auth gmail [alias]" ─────────────────────────
    if c == "auth gmail" or c.startswith("auth gmail "):
        alias = raw[len("auth gmail"):].strip() or "default"
        from .wizards.gmail_oauth_wizard import run_gmail_oauth_wizard
        _success, msg = run_gmail_oauth_wizard(initial_alias=alias if alias != "default" else None)
        return msg

    # ── Gmail: status de contas autenticadas ──────────────────────────────────
    if c == "gmail status" or c.startswith("gmail status "):
        alias = raw[len("gmail status"):].strip() or None
        from .integrations.google import gmail_api as _gapi
        if alias:
            authed = _gapi.is_authed(alias)
            return f"gmail '{alias}': {'✅ conectado' if authed else '❌ não conectado'}"
        # Varrer os dois paths de credenciais
        from pathlib import Path
        dirs = []
        for base in [_gapi.NEW_CREDS_DIR, _gapi.OLD_CREDS_DIR]:
            if base.exists():
                dirs += [d.name for d in base.iterdir() if d.is_dir() and (d / "token.json").exists()]
        if not dirs:
            return "Nenhuma conta Gmail conectada. Use: auth gmail"
        return "Contas Gmail conectadas:\n" + "\n".join(f"  • {d}" for d in sorted(set(dirs)))

    if c == "gmail accounts":
        from pathlib import Path
        from .integrations.google import gmail_api as _gapi
        dirs = []
        for base in [_gapi.NEW_CREDS_DIR, _gapi.OLD_CREDS_DIR]:
            if base.exists():
                dirs += [d.name for d in base.iterdir() if d.is_dir() and (d / "token.json").exists()]
        if not dirs:
            return "Nenhuma conta Gmail conectada. Use: auth gmail"
        return "Contas Gmail conectadas:\n" + "\n".join(f"  • {d}" for d in sorted(set(dirs)))

    # ── Gmail: auto-wizard quando não autenticado ─────────────────────────────
    words = set(c.split())
    if _detect_gmail_read(words):
        from .integrations.google import gmail_api as _gapi
        alias = "default"
        if not _gapi.is_authed(alias):
            print("\nEu preciso acessar o Gmail. Iniciando configuração OAuth...\n", flush=True)
            from .wizards.gmail_oauth_wizard import run_gmail_oauth_wizard
            success, msg = run_gmail_oauth_wizard(initial_alias=None)
            if not success:
                return msg
            # Auto-retry direto via skill (sem LLM)
            if "google_gmail_list_today" in skills:
                result = skills["google_gmail_list_today"].run({"account": alias})
                return f"{msg}\n\nBuscando seus emails...\n\n{result}"
            return f"{msg}\n\nAgora você pode pedir novamente para listar seus emails."
        else:
            # Já autenticado: despacha direto para skill (sem LLM)
            if "google_gmail_list_today" in skills:
                return skills["google_gmail_list_today"].run({"account": alias})

    # Prioridade 0: Policy proposal ("adicionar safe/risky/danger")
    # Separado do risk gate e do recovery gate — altera ~/.jarvis/risk_policy.json.
    pending_policy = get_pending_policy_proposal()
    if pending_policy:
        out = _handle_policy_proposal(c, pending_policy)
        if out is not None:
            return out

    # Prioridade 0.5: Shell allow proposal ("permitir <prefix>") e cancelamento
    pending_shell = get_pending_shell_allow_proposal()

    if c.startswith("permitir "):
        user_prefix = raw[len("permitir "):].strip()
        if user_prefix:
            _shell_add_allow_prefix(user_prefix)
            clear_pending_shell_allow_proposal()
            return f"Ok. '{user_prefix}' adicionado a allowlist. Tente novamente o comando."
        elif pending_shell:
            suggested = pending_shell.get("suggested_prefix", "")
            if suggested:
                _shell_add_allow_prefix(suggested)
                clear_pending_shell_allow_proposal()
                return f"Ok. '{suggested}' adicionado a allowlist. Tente novamente o comando."
        return "Use: permitir <comando-base>  (ex: permitir git commit)"

    # "cancelar" quando há proposta de shell pendente e sem item bloqueado no risk gate
    if pending_shell and c in ("cancelar", "não", "nao", "n", "cancel"):
        risk_b, _ = last_blocked()
        if not risk_b:
            clear_pending_shell_allow_proposal()
            return "Ok, nao alterei a allowlist."

    # Prioridade 1 = risk gate (se item bloqueado na queue)
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

    # execution history (sem LLM — dados reais do executor)
    if c in (
        "ultimos comandos", "últimos comandos",
        "history", "historico", "histórico",
        "o que executou", "quais comandos executou",
        "últimas execuções", "ultimas execucoes",
        "o que voce executou", "o que você executou",
    ):
        history = get_recent_execution(limit=10)
        if not history:
            return "Nenhuma execucao registrada ainda nesta sessao."
        lines = ["Últimas execuções:"]
        for i, ev in enumerate(reversed(history), 1):
            action = ev.get("action", "?")
            ev_args = ev.get("args") or {}
            status = ev.get("status", "?")
            if action == "run_shell":
                cmd_str = ev_args.get("command", "?")
                lines.append(f"{i}) run_shell: {cmd_str}  [{status}]")
            elif action == "open_app":
                lines.append(f"{i}) open_app: {ev_args.get('app', '?')}  [{status}]")
            elif action == "open_url":
                lines.append(f"{i}) open_url: {ev_args.get('url', '?')}  [{status}]")
            else:
                lines.append(f"{i}) {action}  [{status}]")
        return "\n".join(lines)

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