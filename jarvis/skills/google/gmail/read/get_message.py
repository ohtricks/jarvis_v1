from ....base import Skill
from .._common import not_authed_msg, get_alias
from .....integrations.google import gmail_api as _api


class GoogleGmailGetMessageSkill(Skill):
    name = "google_gmail_get_message"

    def run(self, args: dict) -> str:
        alias = get_alias(args)
        if not _api.is_authed(alias):
            return not_authed_msg(alias)
        message_id = (args.get("message_id") or args.get("id") or "").strip()
        if not message_id:
            return "Campo 'message_id' é obrigatório."
        try:
            msg = _api.get_message_full(alias, message_id)
            body = (msg.get("body_text") or "").strip()
            body_preview = body[:1000] + ("..." if len(body) > 1000 else "")
            return (
                f"📧 {msg['subject']}\n"
                f"De: {msg['from']}\n"
                f"Para: {msg['to']}\n"
                f"Data: {msg['date']}\n"
                f"ID: {msg['id']}\n\n"
                f"{body_preview or msg.get('snippet', '')}"
            )
        except Exception as e:
            return f"Erro ao obter email: {e}"
