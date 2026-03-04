from .base import Skill


class GmailListTodaySkill(Skill):
    name = "gmail_list_today"

    def run(self, args: dict) -> str:
        alias = (args.get("account") or args.get("alias") or "default").strip()
        max_results = int(args.get("max_results") or 10)

        from ..gmail_api import is_authenticated, list_recent_emails

        if not is_authenticated(alias):
            return (
                f"Gmail não autenticado (alias: {alias}).\n"
                f"Para conectar: auth gmail {alias}"
            )

        try:
            emails = list_recent_emails(alias, max_results=max_results)
        except Exception as e:
            return f"Erro ao buscar emails: {e}"

        if not emails:
            return "Nenhum email encontrado na caixa de entrada."

        lines = [f"Últimos {len(emails)} emails (alias: {alias}):"]
        for i, e in enumerate(emails, 1):
            lines.append(
                f"\n{i}. {e['subject']}\n"
                f"   De: {e['from']}\n"
                f"   {e['date']}"
            )
        return "\n".join(lines)
