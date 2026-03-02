# jarvis/planner.py
from .memory import (
    set_goal, set_active_plan, get_active_plan, advance_active_plan,
    clear_active_plan, set_pending_action, set_pending_risk, get_pending
)

BROWSERS = ("google chrome", "chrome", "safari", "firefox", "microsoft edge", "edge")


def normalize_actions_to_plan(d: dict) -> dict:
    if "plan" not in d and "actions" in d and isinstance(d["actions"], list):
        d["plan"] = []
        for a in d["actions"]:
            if isinstance(a, dict) and a.get("action"):
                d["plan"].append({"step": a.get("action"), **a})
    return d


def classify_action_risk(action: str, args: dict) -> tuple[str, str]:
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


def _confirm_msg(risk: str, note: str) -> str:
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


def guarded_execute(action: str, args: dict, skills: dict, learn_state_fn) -> tuple[bool, str]:
    """
    Executa se safe; se risky/danger, salva pendência e retorna mensagem.
    """
    risk, note = classify_action_risk(action, args)

    if risk == "safe":
        learn_state_fn(action, args)
        return True, skills[action].run(args)

    # pendência (guarda também o modo execute)
    pending_execute = bool(getattr(skills.get(action), "execute", False))
    set_pending_action({"action": action, **args, "_execute": pending_execute})
    set_pending_risk(risk, note)
    return False, _confirm_msg(risk, note)


def _execute_pending_bypass(pending: dict, skills: dict, learn_state_fn) -> str:
    """
    Executa a pendência SEM reavaliar risco (bypass) e respeita o modo _execute salvo.
    Isso permite:
      jarvis --execute "rode git push"
      jarvis yes
    executar de verdade, mesmo sem --execute no segundo comando.
    """
    action = pending.get("action")
    if not action:
        return "Ação pendente inválida."

    # monta args sem "action"
    args = {k: v for k, v in pending.items() if k != "action"}

    skill = skills.get(action)
    if not skill:
        return "Ação pendente inválida."

    # força execute conforme foi salvo na pendência
    pending_execute = bool(pending.get("_execute", False))
    old_execute = getattr(skill, "execute", None)

    try:
        if old_execute is not None:
            skill.execute = pending_execute
        learn_state_fn(action, args)
        return skill.run(args)
    finally:
        if old_execute is not None:
            skill.execute = old_execute


def confirm_pending(cmd: str, skills: dict, learn_state_fn) -> str | None:
    """
    Confirmação de pendência (SEM loop):
    - yes confirma risky e EXECUTA (bypass do gate)
    - YES I KNOW confirma danger e EXECUTA
    - no cancela
    """
    c_raw = (cmd or "").strip()
    c = c_raw.lower()

    pending, risk, note = get_pending()
    has_pending = bool(pending)

    # cancelar pendência
    if c in ("no", "n", "cancelar", "cancel", "parar"):
        if not has_pending:
            return None
        set_pending_action(None)
        return "Cancelado."

    # confirmar risky
    if c in ("yes", "y", "confirmar"):
        if not has_pending:
            return None
        if risk == "danger":
            return "Esta ação é PERIGOSA. Para confirmar, digite exatamente: YES I KNOW"

        # EXECUTA SEM reavaliar (bypass)
        set_pending_action(None)
        return _execute_pending_bypass(pending, skills, learn_state_fn)

    # confirmar danger
    if c_raw.replace('"', "").strip().upper() == "YES I KNOW":
        if not has_pending:
            return None

        if risk != "danger":
            # se não for danger, trata como yes normal (bypass)
            set_pending_action(None)
            return _execute_pending_bypass(pending, skills, learn_state_fn)

        # danger confirmado
        set_pending_action(None)
        return _execute_pending_bypass(pending, skills, learn_state_fn)

    return None


def start_plan(plan: list, goal_text: str, skills: dict, learn_state_fn) -> str:
    set_goal(goal_text)
    set_active_plan(plan, goal=goal_text)

    if not plan:
        clear_active_plan()
        return "Plano vazio. Diga o que você quer que eu faça."

    first = plan[0]
    action = first.get("action")

    if not action:
        advance_active_plan(1)
        return "Plano iniciado, mas o primeiro passo não tinha ação. Diga 'continua'."

    if action == "chat":
        msg = first.get("response") or first.get("t") or ""
        advance_active_plan(1)
        return (msg or "Ok.") + "\n\n➡️ Diga 'continua' para prosseguir."

    if action in skills:
        args = {k: v for k, v in first.items() if k not in ("action", "step")}
        executed, out = guarded_execute(action, args, skills, learn_state_fn)
        if not executed:
            return out
        advance_active_plan(1)
        return out + "\n\n➡️ Diga 'continua' para o próximo passo."

    advance_active_plan(1)
    return f"Ação desconhecida no plano: {action}. Diga 'continua' para pular."


def continue_plan(skills: dict, learn_state_fn) -> str:
    plan, idx = get_active_plan()
    if not plan:
        return "Não há plano ativo. Diga o que você quer que eu faça."
    if idx >= len(plan):
        clear_active_plan()
        return "Plano já estava completo. Se quiser, descreva um novo objetivo."

    item = plan[idx]
    action = item.get("action")

    if not action:
        advance_active_plan(1)
        return "Passei um passo sem ação. Diga 'continua' novamente."

    if action == "chat":
        msg = item.get("response") or item.get("t") or ""
        advance_active_plan(1)
        return msg or "Ok."

    if action in skills:
        args = {k: v for k, v in item.items() if k not in ("action", "step")}
        executed, out = guarded_execute(action, args, skills, learn_state_fn)
        if not executed:
            return out

        advance_active_plan(1)
        plan2, idx2 = get_active_plan()
        if idx2 >= len(plan2):
            clear_active_plan()
            return out + "\n\n✅ Plano concluído."
        return out + "\n\n➡️ Diga 'continua' para o próximo passo."

    advance_active_plan(1)
    return f"Ação desconhecida no plano: {action}. Diga 'continua' para pular."


def run_plan_all(skills: dict, learn_state_fn) -> str:
    plan, idx = get_active_plan()
    if not plan:
        return "Não há plano ativo."

    results = []
    while idx < len(plan):
        item = plan[idx]
        action = item.get("action")

        if not action:
            advance_active_plan(1)
            idx += 1
            continue

        if action == "chat":
            msg = item.get("response") or item.get("t") or ""
            if msg:
                results.append(msg)
            advance_active_plan(1)
            idx += 1
            continue

        if action in skills:
            args = {k: v for k, v in item.items() if k not in ("action", "step")}
            executed, out = guarded_execute(action, args, skills, learn_state_fn)
            if not executed:
                return out
            results.append(out)
            advance_active_plan(1)
            idx += 1
            continue

        results.append(f"Ação desconhecida no plano: {action}")
        advance_active_plan(1)
        idx += 1

    clear_active_plan()
    out = "\n".join([r for r in results if r]).strip()
    return (out + "\n\n✅ Plano concluído.").strip() if out else "✅ Plano concluído."
