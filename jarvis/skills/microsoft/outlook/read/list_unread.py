from ....base import Skill
from .._common import not_authed_msg, get_alias, format_meta_list
from .....integrations.microsoft import outlook_api as _api
from .....integrations.microsoft.outlook_query import build_filter


class MicrosoftOutlookListUnreadSkill(Skill):
    name = "microsoft_outlook_list_unread"

    def run(self, args: dict) -> str:
        alias = get_alias(args)
        if not _api.is_authed(alias):
            return not_authed_msg(alias)

        max_r = int(args.get("max") or args.get("max_results") or 10)
        filter_str, _extra = build_filter(is_unread=True)

        try:
            ids = _api.list_message_ids(alias, filter_str, top=max_r)
            if not ids:
                return "Nenhum email não lido encontrado."
            metas = [_api.get_message_meta(alias, i) for i in ids]
            return format_meta_list(metas, alias)
        except Exception as e:
            return f"Erro ao buscar emails não lidos: {e}"
