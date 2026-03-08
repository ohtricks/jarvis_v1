from ....base import Skill
from .._common import not_authed_msg, get_alias
from .....integrations.microsoft import outlook_api as _api


class MicrosoftOutlookArchiveSkill(Skill):
    name = "microsoft_outlook_archive"

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
            return f"(dry-run) Eu arquivaria o email ID: {message_id}  (conta: {alias})"
        try:
            _api.move_to_archive(alias, message_id)
            return f"✅ Email {message_id} arquivado no Outlook."
        except Exception as e:
            return f"Erro ao arquivar email: {e}"
