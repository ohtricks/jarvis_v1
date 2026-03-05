from ....base import Skill
from .._common import not_authed_msg, get_alias
from .....integrations.google import gmail_api as _api


class GoogleGmailSendEmailSkill(Skill):
    name = "google_gmail_send_email"

    def __init__(self, execute: bool = False):
        self.execute = execute

    def run(self, args: dict) -> str:
        alias = get_alias(args)
        if not _api.is_authed(alias):
            return not_authed_msg(alias)
        to = (args.get("to") or "").strip()
        subject = (args.get("subject") or "(sem assunto)").strip()
        body = (args.get("body") or "").strip()
        if not to:
            return "Campo 'to' (destinatário) é obrigatório."
        if not body:
            return "Campo 'body' (corpo do email) é obrigatório."
        if not self.execute:
            return (
                f"(dry-run) Eu enviaria um email:\n"
                f"  Para: {to}\n"
                f"  Assunto: {subject}\n"
                f"  Conta: {alias}"
            )
        try:
            result = _api.send_message(
                alias, to, subject, body,
                cc=args.get("cc"),
                bcc=args.get("bcc"),
            )
            return f"✅ Email enviado. ID: {result.get('id')}"
        except Exception as e:
            return f"Erro ao enviar email: {e}"
