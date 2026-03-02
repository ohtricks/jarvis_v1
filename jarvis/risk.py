# jarvis/risk.py
from .memory import (
    set_pending_action,
    set_pending_risk,
    get_pending,
    clear_pending,
    get_session,  # ✅ novo
)
from typing import Tuple, Optional


def classify_action_risk(action: str, args: dict) -> Tuple[str, str]:
    if action in ("open_app", "open_url"):
        return "safe", ""

    if action != "run_shell":
        return "risky", "Ação não classificada."

    cmd = (args.get("command") or "").strip()
    c = cmd.lower()

    safe_prefixes = (
        "pwd", "ls", "whoami", "date",
        "git status", "git diff", "git log", "git branch",
        "python --version", "python3 --version",
        "node -v", "npm -v", "yarn -v", "pnpm -v",
    )
    if any(c == p or c.startswith(p + " ") for p in safe_prefixes):
        return "safe", ""

    danger_patterns = [
        "rm -rf", "rm -fr", "sudo ", "dd ", "mkfs", "diskutil erase",
        "shutdown", "reboot", ":(){ :|:& };:",
        "chmod -r", "chown -r",
        ">/dev/sd", " /dev/sd",
    ]
    if any(p in c for p in danger_patterns):
        return "danger", f"Comando potencialmente destrutivo: {cmd}"

    risky_patterns = [
        "git push", "git reset --hard", "git clean -fd", "git clean -xdf",
        "docker system prune", "docker volume prune", "docker image prune",
        "npm install", "pnpm install", "yarn install",
        "npm run", "pnpm run", "yarn run",
        "pip install", "pip3 install",
        "composer install", "composer update",
        "brew install", "brew upgrade",
        "kill ", "pkill ",
    ]
    if any(p in c for p in risky_patterns):
        return "risky", f"Comando com impacto: {cmd}"

    return "risky", f"Confirmar execução: {cmd}"


def confirm_message(risk: str, note: str) -> str:
    if risk == "danger":
        return (
            "⚠️ AÇÃO PERIGOSA detectada.\n"
            f"{note}\n\n"
            "Para confirmar, digite exatamente: YES I KNOW\n"
            "Para cancelar: jarvis no"
        )
    return (
        "⚠️ Confirmação necessária.\n"
        f"{note}\n\n"
        "Para confirmar: jarvis yes\n"
        "Para cancelar: jarvis no"
    )


def require_confirmation(action: str, args: dict, skills: dict, desired_execute: bool) -> Tuple[bool, str, str]:
    """
    Retorna (blocked, risk, note)
    """
    risk, note = classify_action_risk(action, args)
    if risk == "safe":
        return False, "safe", ""

    # salva pendência com o execute desejado (no momento do pedido)
    set_pending_action({"action": action, **args, "_execute": bool(desired_execute)})
    set_pending_risk(risk, note)
    return True, risk, note


def _execute_pending(pending: dict, skills: dict, learn_state_fn) -> str:
    action = pending.get("action")
    if not action:
        return "Ação pendente inválida."

    args = {k: v for k, v in pending.items() if k != "action"}
    skill = skills.get(action)
    if not skill:
        return "Ação pendente inválida."

    # ✅ regra nova:
    # Se a pendência foi criada em dry (_execute=false), mas o usuário está em mode execute,
    # então executar de verdade na confirmação.
    sess = get_session() or {}
    session_mode = (sess.get("mode") or "dry").lower()

    pending_execute = bool(pending.get("_execute", False))
    if not pending_execute and session_mode == "execute":
        pending_execute = True

    old_execute = getattr(skill, "execute", None)
    try:
        if old_execute is not None:
            skill.execute = pending_execute
        learn_state_fn(action, args)
        return skill.run(args)
    finally:
        if old_execute is not None:
            skill.execute = old_execute


def handle_confirmation(cmd: str, skills: dict, learn_state_fn) -> Optional[str]:
    """
    yes/no/YES I KNOW, tudo sem LLM.
    """
    c_raw = (cmd or "").strip()
    c = c_raw.lower()

    pending, risk, note = get_pending()
    has_pending = bool(pending)

    if c in ("no", "n", "cancelar", "cancel"):
        if not has_pending:
            return "Não há nenhuma ação pendente para cancelar."
        clear_pending()
        return "Cancelado."

    if c in ("yes", "y", "confirmar"):
        if not has_pending:
            return "Não há nenhuma ação pendente para confirmar."
        if risk == "danger":
            return "Esta ação é PERIGOSA. Para confirmar, digite exatamente: YES I KNOW"
        clear_pending()
        return _execute_pending(pending, skills, learn_state_fn)

    if c_raw.replace('"', "").strip().upper() == "YES I KNOW":
        if not has_pending:
            return "Não há nenhuma ação pendente para confirmar."
        clear_pending()
        return _execute_pending(pending, skills, learn_state_fn)

    return None