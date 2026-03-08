from ....base import Skill
from .._common import not_authed_msg, get_alias, format_meta_list
from .....integrations.microsoft import outlook_api as _api
from .....integrations.microsoft.outlook_query import build_filter, received_after_hours, received_after_days


class MicrosoftOutlookListTodaySkill(Skill):
    name = "microsoft_outlook_list_today"

    def run(self, args: dict) -> str:
        alias = get_alias(args)
        if not _api.is_authed(alias):
            return not_authed_msg(alias)

        max_r = int(args.get("max") or args.get("max_results") or 10)
        hours = 12 if args.get("period") == "morning" else 24
        cutoff = received_after_hours(hours)
        filter_str, extra = build_filter(received_after=cutoff)

        try:
            ids = _api.list_message_ids(alias, filter_str, top=max_r)
            if not ids:
                return "Nenhum email encontrado na caixa de entrada de hoje."
            metas = [_api.get_message_meta(alias, i) for i in ids]
            return format_meta_list(metas, alias)
        except Exception as e:
            return f"Erro ao buscar emails: {e}"
