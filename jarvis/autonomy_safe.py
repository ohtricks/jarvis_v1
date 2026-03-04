"""
Gera Recovery Plans heurísticos SEGUROS — sem LLM, sem execução automática.

Regras:
- Nunca sugerir rm -rf, reset --hard, ou qualquer comando destrutivo.
- Máximo 4 passos.
- Preferir ações de diagnóstico read-only primeiro.
- Se não souber o que fazer: plan vazio + instrução manual.
"""

# Comandos que NUNCA devem aparecer num recovery plan
_FORBIDDEN = (
    "rm -rf", "rm -fr", "reset --hard", "clean -fd", "clean -xdf",
    "sudo", "dd ", "mkfs", "shutdown", "reboot",
)


def _is_safe_command(cmd: str) -> bool:
    c = cmd.lower()
    return not any(f in c for f in _FORBIDDEN)


def propose_recovery(goal: str, observation: dict, context_text: str) -> dict:
    """
    Gera uma proposta de recovery heurística baseada nos sinais do observation.

    Retorna:
    {
        "kind": "recovery_proposal",
        "goal": str,
        "reason": str,
        "plan": [{"step": str, "action": "run_shell", "command": str}, ...],
        "requires_user_approval": True,
        "observation_command": str,   # para UX
    }
    """
    signals = observation.get("signals", [])
    command = observation.get("command", "")
    is_git_cmd = "git" in command.lower()

    reason = "Falha ao executar o comando."
    plan: list[dict] = []

    # ── Regras por sinal ──────────────────────────────────────────────────

    if "nothing_to_commit" in signals:
        reason = "Não há mudanças para commitar no repositório."
        plan = [
            {"step": "Verificar estado do repositório", "action": "run_shell", "command": "git status"},
        ]

    elif "not_git_repo" in signals:
        reason = "O diretório atual não é um repositório git."
        plan = [
            {"step": "Verificar diretório atual", "action": "run_shell", "command": "pwd"},
            {"step": "Listar arquivos", "action": "run_shell", "command": "ls -la"},
        ]

    elif "merge_conflict" in signals:
        reason = "Conflito de merge detectado."
        plan = [
            {"step": "Verificar estado do repositório", "action": "run_shell", "command": "git status"},
            {"step": "Ver diferenças", "action": "run_shell", "command": "git diff"},
        ]

    elif "permission_denied" in signals:
        reason = "Permissão negada ao executar o comando."
        plan = [
            {"step": "Verificar diretório atual", "action": "run_shell", "command": "pwd"},
            {"step": "Listar permissões", "action": "run_shell", "command": "ls -la"},
        ]

    elif "untracked_files" in signals:
        reason = "Há arquivos não rastreados no repositório."
        if is_git_cmd:
            plan = [
                {"step": "Verificar estado do repositório", "action": "run_shell", "command": "git status"},
                {"step": "Adicionar arquivos ao staging", "action": "run_shell", "command": "git add -A"},
            ]
        else:
            plan = [
                {"step": "Verificar estado do repositório", "action": "run_shell", "command": "git status"},
            ]

    elif "cmd_not_found" in signals:
        reason = "Comando não encontrado no sistema."
        plan = [
            {"step": "Verificar diretório atual", "action": "run_shell", "command": "pwd"},
        ]

    elif "no_such_file" in signals:
        reason = "Arquivo ou diretório não encontrado."
        plan = [
            {"step": "Verificar diretório atual", "action": "run_shell", "command": "pwd"},
            {"step": "Listar arquivos", "action": "run_shell", "command": "ls -la"},
        ]

    elif "git_fatal" in signals and is_git_cmd:
        reason = "Falha em operação git."
        plan = [
            {"step": "Verificar estado do repositório", "action": "run_shell", "command": "git status"},
        ]

    elif is_git_cmd:
        # Falha git genérica
        reason = "Falha em operação git. Diagnóstico automático."
        plan = [
            {"step": "Verificar estado do repositório", "action": "run_shell", "command": "git status"},
            {"step": "Verificar diretório atual", "action": "run_shell", "command": "pwd"},
        ]

    else:
        # Falha desconhecida — pede intervenção manual
        reason = "Não consegui identificar o problema automaticamente. Intervenção manual necessária."
        plan = []

    # Garantia de segurança: remover qualquer passo proibido
    plan = [s for s in plan if _is_safe_command(s.get("command", ""))]
    plan = plan[:4]

    return {
        "kind": "recovery_proposal",
        "goal": (goal or "Recuperação automática").strip(),
        "reason": reason,
        "plan": plan,
        "requires_user_approval": True,
        "observation_command": command,
    }


def format_recovery_message(failed_output: str, proposal: dict) -> str:
    """
    Gera a mensagem UX para apresentar ao usuário quando há um recovery pendente.
    """
    lines = []

    cmd = proposal.get("observation_command", "")
    reason = proposal.get("reason", "Erro desconhecido.")

    header = "Falha ao executar"
    if cmd:
        header += f": {cmd}"
    lines.append(f"⚠️  {header}")
    lines.append(f"Motivo: {reason}")

    plan = proposal.get("plan") or []
    if not plan:
        lines.append("\n⚙️  Não consegui gerar um plano de recuperação seguro.")
        lines.append("Verifique o erro acima e tente manualmente.")
        return "\n".join(lines)

    lines.append("\n💡 Posso tentar resolver com este plano (NÃO executado ainda):")
    for i, step in enumerate(plan, 1):
        action = step.get("action", "?")
        if action == "run_shell":
            lines.append(f"  {i}) run_shell: {step.get('command', '')}")
        else:
            lines.append(f"  {i}) {action}: {step.get('step', action)}")

    lines.append("\nConfirma que eu execute este plano? (ok / não)")
    return "\n".join(lines)
