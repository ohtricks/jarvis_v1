from ....base import Skill
from .._common import not_authed_msg, get_alias
from .....integrations.microsoft import outlook_api as _api
from .....integrations.microsoft.outlook_query import build_filter


class MicrosoftOutlookGetLatestSkill(Skill):
    name = "microsoft_outlook_get_latest"

    def run(self, args: dict) -> str:
        alias = get_alias(args)
        if not _api.is_authed(alias):
            return not_authed_msg(alias)

        filter_str, _extra = build_filter()

        try:
            ids = _api.list_message_ids(alias, filter_str, top=1)
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
