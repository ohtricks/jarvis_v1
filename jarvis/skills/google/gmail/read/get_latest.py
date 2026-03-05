from ....base import Skill
from .._common import not_authed_msg, get_alias, normalize_category, build_query
from .....integrations.google import gmail_api as _api


class GoogleGmailGetLatestSkill(Skill):
    name = "google_gmail_get_latest"

    def run(self, args: dict) -> str:
        alias = get_alias(args)
        if not _api.is_authed(alias):
            return not_authed_msg(alias)

        category, err = normalize_category(args.get("category"))
        if err:
            return err

        user_query = (args.get("query") or "").strip() or None
        query = build_query("", user_query, category, inbox_only=True)

        try:
            ids = _api.list_message_ids(alias, query, max_results=1)
            if not ids:
                return "Nenhum email encontrado na caixa de entrada."
            msg = _api.get_message_full(alias, ids[0])
            body = (msg.get("body_text") or "").strip()
            body_preview = body[:1000] + ("..." if len(body) > 1000 else "")
            return (
                f"📧 Último email\n"
                f"Assunto: {msg['subject']}\n"
                f"De: {msg['from']}\n"
                f"Data: {msg['date']}\n"
                f"ID: {msg['id']}\n\n"
                f"{body_preview or msg.get('snippet', '')}"
            )
        except Exception as e:
            return f"Erro ao obter último email: {e}"
