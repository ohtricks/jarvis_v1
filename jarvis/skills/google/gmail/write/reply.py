from ....base import Skill
from .._common import not_authed_msg, get_alias
from .....integrations.google import gmail_api as _api


class GoogleGmailReplySkill(Skill):
    name = "google_gmail_reply"

    def __init__(self, execute: bool = False):
        self.execute = execute

    def run(self, args: dict) -> str:
        alias = get_alias(args)
        if not _api.is_authed(alias):
            return not_authed_msg(alias)
        message_id = (args.get("message_id") or args.get("id") or "").strip()
        body = (args.get("body") or "").strip()
        if not message_id:
            return "Campo 'message_id' é obrigatório."
        if not body:
            return "Campo 'body' (corpo da resposta) é obrigatório."
        reply_all = bool(args.get("reply_all", False))
        if not self.execute:
            return (
                f"(dry-run) Eu responderia ao email ID: {message_id}\n"
                f"  Reply-all: {reply_all}\n"
                f"  Conta: {alias}"
            )
        try:
            result = _api.reply_message(alias, message_id, body, reply_all=reply_all)
            return f"✅ Resposta enviada. ID: {result.get('id')}"
        except Exception as e:
            return f"Erro ao responder email: {e}"
