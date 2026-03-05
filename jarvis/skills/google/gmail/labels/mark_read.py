from ....base import Skill
from .._common import not_authed_msg, get_alias
from .....integrations.google import gmail_api as _api


class GoogleGmailMarkReadSkill(Skill):
    name = "google_gmail_mark_read"

    def __init__(self, execute: bool = False):
        self.execute = execute

    def run(self, args: dict) -> str:
        alias = get_alias(args)
        if not _api.is_authed(alias):
            return not_authed_msg(alias)
        message_id = (args.get("message_id") or args.get("id") or "").strip()
        if not message_id:
            return "Campo 'message_id' é obrigatório."
        if not self.execute:
            return f"(dry-run) Eu marcaria como lido o email ID: {message_id}  (conta: {alias})"
        try:
            _api.modify_message_labels(alias, message_id, remove=["UNREAD"])
            return f"✅ Email {message_id} marcado como lido."
        except Exception as e:
            return f"Erro ao marcar email como lido: {e}"
