from typing import Tuple, Optional
from . import risk_policy


def classify_action_risk(action: str, args: dict) -> Tuple[str, str, str]:
    """
    Retorna (risk, note, matched) onde matched indica a fonte da classificação:
      "fixed"          — open_app/open_url ou ação não run_shell
      "safe_prefix"    — bateu em safe_prefixes
      "danger_pattern" — bateu em danger_patterns
      "risky_pattern"  — bateu em risky_patterns
      "fallback"       — não bateu em nenhuma regra → risky por padrão

    O campo matched é usado internamente para detectar se o usuário pode
    querer adicionar esse comando às regras de policy.
    """
    if action in ("open_app", "open_url"):
        return "safe", "", "fixed"

    _FIXED_SKILL_RISK = {
        # Git
        "git_status":       ("safe",   "",                                                "fixed"),
        "git_add_all":      ("risky",  "Vai adicionar todos os arquivos ao stage.",       "fixed"),
        "git_commit":       ("risky",  "Vai criar um commit no repositório.",             "fixed"),
        "git_push":         ("risky",  "Vai enviar commits para o repositório remoto.",   "fixed"),
        # Gmail
        "gmail_list_today": ("safe",   "",                                                "fixed"),
    }
    if action in _FIXED_SKILL_RISK:
        return _FIXED_SKILL_RISK[action]

    if action != "run_shell":
        return "risky", "Ação não classificada.", "fixed"

    cmd = (args.get("command") or "").strip()
    c = cmd.lower()

    policy = risk_policy.load_policy()
    safe_prefixes   = policy["safe_prefixes"]
    danger_patterns = policy["danger_patterns"]
    risky_patterns  = policy["risky_patterns"]

    if any(c == p or c.startswith(p + " ") for p in safe_prefixes):
        return "safe", "", "safe_prefix"

    if any(p in c for p in danger_patterns):
        return "danger", f"Comando potencialmente destrutivo: {cmd}", "danger_pattern"

    if any(p in c for p in risky_patterns):
        return "risky", f"Comando com impacto: {cmd}", "risky_pattern"

    return "risky", f"Confirmar execução: {cmd}", "fallback"


def confirm_message(risk: str, note: str) -> str:
    if risk == "danger":
        return (
            "⚠️  AÇÃO PERIGOSA detectada.\n"
            f"{note}\n\n"
            "Para confirmar, digite exatamente: YES I KNOW\n"
            "Para cancelar: não"
        )

    base = (
        "⚠️  Confirmação necessária.\n"
        f"{note}\n\n"
        "Para confirmar: yes\n"
        "Para cancelar: não"
    )

    # Quando cai no fallback (não está em nenhuma regra conhecida), sugerir policy
    if note.startswith("Confirmar execução:"):
        base += (
            "\n\n💡 Esse comando não está nas regras. Para adicionar e evitar "
            "esta pergunta futuramente:\n"
            "  adicionar safe   → executar sempre sem confirmação\n"
            "  adicionar risky  → sempre pedir confirmação (padrão atual)\n"
            "  adicionar danger → exigir YES I KNOW"
        )

    return base


def require_confirmation(
    action: str,
    args: dict,
    desired_execute: bool,
) -> Tuple[bool, str, str, Optional[dict]]:
    """
    V3:
    - Se args['_execute'] == True → já confirmado, não bloqueia.
    - desired_execute existe para o executor, mas não afeta o bloqueio.
    - Quando o comando cai no "fallback" (não está nas regras), salva
      pending_policy_proposal em memory para o usuário poder adicionar às regras.
    """
    # ✅ bypass após confirmação
    if bool(args.get("_execute")) is True:
        return False, "safe", "", None

    risk, note, matched = classify_action_risk(action, args)

    if risk == "safe":
        return False, "safe", "", None

    # Fallback: comando não está em nenhuma regra → oferecer adição à policy
    if action == "run_shell" and matched == "fallback":
        cmd = (args.get("command") or "").strip()
        from .memory import set_pending_policy_proposal
        set_pending_policy_proposal({
            "kind": "risk_policy_proposal",
            "command": cmd,
            "suggested_bucket": "risky_patterns",
            "options": ["safe_prefixes", "risky_patterns", "danger_patterns"],
        })

    required = "YES I KNOW" if risk == "danger" else "yes"

    confirm = {
        "kind": "risk_confirm",
        "required": required,
        # ✅ confirmação sempre injeta bypass, independente do mode
        "execute_payload": {"_execute": True},
    }

    return True, risk, note, confirm
