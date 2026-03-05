from ....base import Skill
from .._common import not_authed_msg, get_alias, format_meta_list
from .....integrations.google import gmail_api as _api


class GoogleGmailListUnreadSkill(Skill):
    name = "google_gmail_list_unread"

    def run(self, args: dict) -> str:
        alias = get_alias(args)
        if not _api.is_authed(alias):
            return not_authed_msg(alias)
        max_r = int(args.get("max") or args.get("max_results") or 10)
        query = "in:inbox is:unread"
        try:
            ids = _api.list_message_ids(alias, query, max_r)
            if not ids:
                return "Nenhum email não lido encontrado."
            metas = [_api.get_message_meta(alias, i) for i in ids]
            return format_meta_list(metas, alias)
        except Exception as e:
            return f"Erro ao buscar emails não lidos: {e}"
