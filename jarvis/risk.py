from typing import Tuple, Optional


def classify_action_risk(action: str, args: dict) -> Tuple[str, str]:
    if action in ("open_app", "open_url"):
        return "safe", ""

    if action != "run_shell":
        return "risky", "Ação não classificada."

    cmd = (args.get("command") or "").strip()
    c = cmd.lower()

    safe_prefixes = (
        "pwd",
        "ls",
        "whoami",
        "date",
        "git status",
        "git diff",
        "git log",
        "git branch",
        "python --version",
        "python3 --version",
        "node -v",
        "npm -v",
        "yarn -v",
        "pnpm -v",
    )
    if any(c == p or c.startswith(p + " ") for p in safe_prefixes):
        return "safe", ""

    danger_patterns = [
        "rm -rf",
        "rm -fr",
        "sudo ",
        "dd ",
        "mkfs",
        "diskutil erase",
        "shutdown",
        "reboot",
        ":(){ :|:& };:",
        "chmod -r",
        "chown -r",
        ">/dev/sd",
        " /dev/sd",
    ]
    if any(p in c for p in danger_patterns):
        return "danger", f"Comando potencialmente destrutivo: {cmd}"

    risky_patterns = [
        "git push",
        "git reset --hard",
        "git clean -fd",
        "git clean -xdf",
        "docker system prune",
        "docker volume prune",
        "docker image prune",
        "npm install",
        "pnpm install",
        "yarn install",
        "npm run",
        "pnpm run",
        "yarn run",
        "pip install",
        "pip3 install",
        "composer install",
        "composer update",
        "brew install",
        "brew upgrade",
        "kill ",
        "pkill ",
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


def require_confirmation(
    action: str,
    args: dict,
    desired_execute: bool,
) -> Tuple[bool, str, str, Optional[dict]]:
    """
    V3: Risk gate NÃO executa e NÃO cria pendência fora da queue.
    Retorna: (blocked, risk, note, confirm_payload)
    """
    risk, note = classify_action_risk(action, args)

    if risk == "safe":
        return False, "safe", "", None

    # O "payload" de confirmação fica salvo no item bloqueado da queue.
    if risk == "danger":
        required = "YES I KNOW"
    else:
        required = "yes"

    confirm = {
        "kind": "risk_confirm",
        "required": required,
        # quando confirmar, injeta _execute no args do item antes de retomar
        "execute_payload": {"_execute": bool(desired_execute)},
    }

    return True, risk, note, confirm